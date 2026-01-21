"""
Service de logging structuré pour AindusDB Core avec contexte enrichi et filtres.

Ce module implémente le système de logging production avec :
- Configuration YAML centralisée avec rotation automatique
- Formatters JSON pour agrégation (ELK, Fluentd)
- Filtres pour contexte HTTP, sanitisation et rate limiting
- Loggers spécialisés par composant avec niveaux configurables

Example:
    from app.core.logging import get_logger, LogContext
    
    logger = get_logger(__name__)
    
    # Logging simple
    logger.info("Vector created", extra={"vector_id": 123})
    
    # Avec contexte enrichi
    with LogContext(user_id=456, operation="batch_insert"):
        logger.info("Processing batch", extra={"count": 1000})
"""

import logging
import logging.config
import contextvars
import time
import json
import re
import os
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

import yaml
from fastapi import Request


# Variables de contexte pour propagation des métadonnées
request_id_var: contextvars.ContextVar = contextvars.ContextVar('request_id', default=None)
user_id_var: contextvars.ContextVar = contextvars.ContextVar('user_id', default=None)
correlation_id_var: contextvars.ContextVar = contextvars.ContextVar('correlation_id', default=None)
operation_var: contextvars.ContextVar = contextvars.ContextVar('operation', default=None)


class RequestContextFilter(logging.Filter):
    """
    Filtre pour enrichir automatiquement les logs avec contexte de requête HTTP.
    
    Injecte automatiquement request_id, user_id, correlation_id dans tous les logs
    depuis les variables de contexte asyncio. Compatible FastAPI middleware.
    
    Example:
        # Le filtre ajoute automatiquement ces champs:
        {
            "timestamp": "2024-01-20T12:45:00.123Z",
            "level": "INFO", 
            "message": "Vector created",
            "request_id": "req_abc123",
            "user_id": 456,
            "correlation_id": "corr_xyz789"
        }
    """
    
    def filter(self, record):
        """Enrichir le record avec variables de contexte."""
        record.request_id = request_id_var.get() or "unknown"
        record.user_id = user_id_var.get() or None
        record.correlation_id = correlation_id_var.get() or "unknown"
        record.operation = operation_var.get() or "unknown"
        return True


class SanitizeFilter(logging.Filter):
    """
    Filtre pour masquer informations sensibles dans les logs.
    
    Remplace automatiquement les mots de passe, tokens, clés API
    par [REDACTED] pour éviter les fuites de données en production.
    
    Attributes:
        patterns: Liste des patterns regex à masquer
        replacement: Texte de remplacement (défaut: [REDACTED])
    """
    
    def __init__(self, patterns: List[str] = None, replacement: str = "[REDACTED]"):
        super().__init__()
        self.patterns = patterns or [
            r'password["\s]*[:=]["\s]*([^"\\s,}]+)',
            r'token["\s]*[:=]["\s]*([^"\\s,}]+)', 
            r'secret["\s]*[:=]["\s]*([^"\\s,}]+)',
            r'key["\s]*[:=]["\s]*([^"\\s,}]+)',
            r'authorization["\s]*[:=]["\s]*([^"\\s,}]+)',
            r'x-api-key["\s]*[:=]["\s]*([^"\\s,}]+)'
        ]
        self.replacement = replacement
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.patterns]
    
    def filter(self, record):
        """Masquer données sensibles dans le message et args."""
        # Sanitize message
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            for pattern in self.compiled_patterns:
                message = pattern.sub(lambda m: m.group(0).replace(m.group(1), self.replacement), message)
            record.msg = message
            record.args = ()
        
        return True


class VeritasThoughtFilter(logging.Filter):
    """
    Filtre spécialisé VERITAS pour indexer les balises <thought> et <action>.
    
    Détecte et enrichit automatiquement les logs contenant des traces
    de raisonnement VERITAS avec métadonnées pour indexation avancée.
    
    Features:
    - Extraction automatique des balises <thought>...</thought>
    - Extraction automatique des balises <action>...</action>
    - Enrichissement contexte avec métadonnées VERITAS
    - Classification automatique du type de raisonnement
    - Support pour search et analytics sur les traces
    
    Example:
        # Log avec traces VERITAS
        logger.info("<thought>Je dois calculer F=ma</thought> Réponse générée")
        # Sera enrichi avec: thought_content, thought_type, veritas_trace=True
    """
    
    def __init__(self):
        super().__init__()
        
        # Patterns pour extraction des balises VERITAS
        self.thought_pattern = re.compile(r'<thought>(.*?)</thought>', re.DOTALL | re.IGNORECASE)
        self.action_pattern = re.compile(r'<action>(.*?)</action>', re.DOTALL | re.IGNORECASE)
        
        # Patterns pour classification du type de raisonnement
        self.reasoning_classifiers = {
            'calculation': [r'calcul', r'\d+\s*[+\-*/]\s*\d+', r'formule', r'équation'],
            'physics': [r'force', r'masse', r'accélération', r'F\s*=\s*m\s*[*×]\s*a'],
            'mathematics': [r'theorem', r'proof', r'démonstration', r'QED'],
            'logic': [r'si.*alors', r'donc', r'par conséquent', r'logical'],
            'verification': [r'vérif', r'check', r'confirm', r'validate'],
            'assumption': [r'suppose', r'assume', r'posons', r'soit']
        }
    
    def filter(self, record):
        """
        Enrichir le log avec métadonnées VERITAS si traces détectées.
        
        Args:
            record: Enregistrement de log à analyser
            
        Returns:
            bool: True pour conserver le log
        """
        message = getattr(record, 'msg', '')
        if not isinstance(message, str):
            return True
        
        # Détecter et extraire balises <thought>
        thought_matches = self.thought_pattern.findall(message)
        if thought_matches:
            record.veritas_trace = True
            record.thought_content = [match.strip() for match in thought_matches]
            record.thought_count = len(thought_matches)
            
            # Classifier le type de raisonnement
            record.thought_types = self._classify_reasoning(thought_matches)
            
            # Ajouter au contexte pour recherche
            if hasattr(record, 'extra'):
                record.extra.update({
                    'veritas_thought': True,
                    'thought_extracted': True
                })
        
        # Détecter et extraire balises <action>
        action_matches = self.action_pattern.findall(message)
        if action_matches:
            record.veritas_trace = getattr(record, 'veritas_trace', False) or True
            record.action_content = [match.strip() for match in action_matches]
            record.action_count = len(action_matches)
            
            if hasattr(record, 'extra'):
                record.extra.update({
                    'veritas_action': True,
                    'action_extracted': True
                })
        
        # Enrichir avec contexte général VERITAS si traces détectées
        if hasattr(record, 'veritas_trace'):
            record.log_category = 'veritas_reasoning'
            record.searchable = True
            record.reasoning_timestamp = datetime.now(timezone.utc).isoformat()
        
        return True
    
    def _classify_reasoning(self, thought_contents: List[str]) -> List[str]:
        """
        Classifier automatiquement le type de raisonnement.
        
        Args:
            thought_contents: Liste des contenus de pensée extraits
            
        Returns:
            List[str]: Types de raisonnement détectés
        """
        detected_types = set()
        combined_content = ' '.join(thought_contents).lower()
        
        for reasoning_type, patterns in self.reasoning_classifiers.items():
            for pattern in patterns:
                if re.search(pattern, combined_content, re.IGNORECASE):
                    detected_types.add(reasoning_type)
                    break
        
        return list(detected_types) if detected_types else ['general_reasoning']


class RateLimitFilter(logging.Filter):
    """
    Filtre pour limiter le débit des logs identiques.
    
    Prévient le spam de logs en limitant les messages identiques
    à un certain nombre par minute. Utile pour éviter la surcharge
    lors d'erreurs répétitives.
    
    Attributes:
        max_per_minute: Nombre max de messages identiques par minute
        message_counts: Cache des compteurs par message
    """
    
    def __init__(self, max_per_minute: int = 60):
        super().__init__()
        self.max_per_minute = max_per_minute
        self.message_counts: Dict[str, Dict[str, Any]] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def filter(self, record):
        """Appliquer rate limiting sur message."""
        now = time.time()
        
        # Nettoyage périodique du cache
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(now)
            self.last_cleanup = now
        
        # Générer clé unique pour le message
        message_key = f"{record.levelname}:{record.module}:{record.getMessage()}"
        
        # Vérifier limite
        if message_key not in self.message_counts:
            self.message_counts[message_key] = {
                "count": 1,
                "window_start": now,
                "last_seen": now
            }
            return True
        
        entry = self.message_counts[message_key]
        
        # Reset window si > 1 minute
        if now - entry["window_start"] > 60:
            entry["count"] = 1
            entry["window_start"] = now
            entry["last_seen"] = now
            return True
        
        # Incrémenter compteur
        entry["count"] += 1
        entry["last_seen"] = now
        
        # Autoriser si sous la limite
        if entry["count"] <= self.max_per_minute:
            return True
        
        # Rate limited - ajouter message d'avertissement periodique
        if entry["count"] == self.max_per_minute + 1:
            record.msg = f"[RATE LIMITED] {record.getMessage()} (further identical messages will be suppressed)"
            return True
        
        return False  # Supprimer le message
    
    def _cleanup_old_entries(self, current_time: float):
        """Nettoyer les entrées anciennes du cache."""
        cutoff_time = current_time - 300  # 5 minutes
        keys_to_remove = [
            key for key, entry in self.message_counts.items()
            if entry["last_seen"] < cutoff_time
        ]
        for key in keys_to_remove:
            del self.message_counts[key]


class LevelFilter(logging.Filter):
    """Filtre pour ne garder que certains niveaux de logs."""
    
    def __init__(self, level: str):
        super().__init__()
        self.level = getattr(logging, level.upper())
    
    def filter(self, record):
        return record.levelno >= self.level


class JSONFormatter(logging.Formatter):
    """
    Formatter JSON enrichi pour logs structurés avec métadonnées.
    
    Produit des logs JSON compatibles avec Elasticsearch, Fluentd,
    et autres systèmes d'agrégation. Ajoute automatiquement des
    métadonnées système et contexte applicatif.
    """
    
    def format(self, record):
        """Formatter le record en JSON structuré."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread
        }
        
        # Ajouter contexte de requête si disponible
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'user_id') and record.user_id:
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id
        if hasattr(record, 'operation'):
            log_entry["operation"] = record.operation
        
        # Ajouter exception si présente
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Ajouter extra fields
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                              'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                              'thread', 'threadName', 'processName', 'process', 'message', 'exc_info',
                              'exc_text', 'stack_info', 'request_id', 'user_id', 'correlation_id', 'operation']:
                    log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class AuditFormatter(logging.Formatter):
    """Formatter spécialisé pour logs d'audit sécurisé."""
    
    def format(self, record):
        """Formatter pour audit trail."""
        audit_entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "audit_type": getattr(record, 'audit_type', 'general'),
            "user": getattr(record, 'user', 'system'),
            "action": getattr(record, 'action', 'unknown'),
            "resource": getattr(record, 'resource', None),
            "result": getattr(record, 'result', 'unknown'),
            "ip": getattr(record, 'ip', None),
            "user_agent": getattr(record, 'user_agent', None),
            "details": getattr(record, 'details', {}),
            "message": record.getMessage()
        }
        
        return json.dumps(audit_entry, ensure_ascii=False, default=str)


class MetricsFormatter(logging.Formatter):
    """Formatter pour logs de métriques business."""
    
    def format(self, record):
        """Formatter pour métriques."""
        metrics_entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "metric_name": getattr(record, 'metric_name', 'unknown'),
            "metric_value": getattr(record, 'metric_value', 0),
            "metric_type": getattr(record, 'metric_type', 'gauge'),
            "tags": getattr(record, 'tags', {}),
            "context": getattr(record, 'context', {}),
            "message": record.getMessage()
        }
        
        return json.dumps(metrics_entry, ensure_ascii=False, default=str)


class LoggingService:
    """
    Service centralisé de logging avec configuration dynamique.
    
    Gère la configuration des loggers, la rotation des fichiers,
    et l'intégration avec les systèmes externes (Elasticsearch, Syslog).
    
    Features:
    - Configuration YAML centralisée avec hot-reload
    - Loggers spécialisés par module avec héritage
    - Méthodes utilitaires pour audit et métriques
    - Intégration monitoring et alerting
    
    Example:
        logging_service = LoggingService()
        await logging_service.setup()
        
        logger = logging_service.get_logger("aindusdb.core")
        logger.info("Service started", extra={"version": "1.0.0"})
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialiser le service de logging.
        
        Args:
            config_path: Chemin vers le fichier de configuration YAML
        """
        self.config_path = config_path or "config/logging.yaml"
        self.loggers: Dict[str, logging.Logger] = {}
        self.setup_complete = False
    
    async def setup(self):
        """Configurer le système de logging depuis YAML."""
        if self.setup_complete:
            return
            
        try:
            # Créer dossiers logs si nécessaire
            self._ensure_log_directories()
            
            # Charger configuration YAML
            config = self._load_config()
            
            # Appliquer configuration avec variables d'environnement
            config = self._apply_environment_overrides(config)
            
            # Configurer logging
            logging.config.dictConfig(config)
            
            # Enregistrer les classes custom
            self._register_custom_classes()
            
            self.setup_complete = True
            
            # Logger initial
            logger = self.get_logger("aindusdb.core.logging")
            logger.info("Logging system initialized", extra={
                "config_path": self.config_path,
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
                "log_format": os.getenv("LOG_FORMAT", "json")
            })
            
        except Exception as e:
            # Fallback logging en cas d'erreur
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger("aindusdb.core.logging")
            logger.error(f"Failed to setup logging: {e}", exc_info=True)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Obtenir un logger configuré par nom.
        
        Args:
            name: Nom du logger (ex: "aindusdb.core.database")
            
        Returns:
            logging.Logger: Logger configuré
        """
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(name)
        return self.loggers[name]
    
    def _load_config(self) -> Dict[str, Any]:
        """Charger configuration depuis YAML."""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Logging config not found: {self.config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _apply_environment_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Appliquer overrides depuis variables d'environnement."""
        # LOG_LEVEL override
        log_level = os.getenv("LOG_LEVEL")
        if log_level:
            config["root"]["level"] = log_level.upper()
            for logger_config in config.get("loggers", {}).values():
                if isinstance(logger_config, dict) and "level" in logger_config:
                    logger_config["level"] = log_level.upper()
        
        # LOG_FORMAT override
        log_format = os.getenv("LOG_FORMAT", "json")
        for handler_name, handler_config in config.get("handlers", {}).items():
            if isinstance(handler_config, dict):
                if log_format == "simple":
                    handler_config["formatter"] = "simple"
                elif log_format == "detailed":
                    handler_config["formatter"] = "detailed"
                else:
                    handler_config["formatter"] = "json"
        
        # LOG_TO_CONSOLE override
        if os.getenv("LOG_TO_CONSOLE", "true").lower() == "false":
            # Supprimer handlers console
            for logger_config in config.get("loggers", {}).values():
                if isinstance(logger_config, dict) and "handlers" in logger_config:
                    logger_config["handlers"] = [
                        h for h in logger_config["handlers"] 
                        if not h.startswith("console")
                    ]
        
        return config
    
    def _ensure_log_directories(self):
        """Créer les dossiers de logs nécessaires."""
        log_dirs = [
            "logs",
            "logs/audit", 
            "logs/metrics",
            "logs/critical"
        ]
        
        for log_dir in log_dirs:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    def _register_custom_classes(self):
        """Enregistrer les classes custom pour logging.config."""
        # Les classes sont déjà importées dans ce module
        pass


@contextmanager
def LogContext(request_id: str = None, 
               user_id: int = None,
               correlation_id: str = None,
               operation: str = None):
    """
    Context manager pour enrichir temporairement les logs.
    
    Args:
        request_id: ID unique de la requête
        user_id: ID utilisateur
        correlation_id: ID de corrélation pour tracing distribué
        operation: Nom de l'opération en cours
        
    Example:
        with LogContext(request_id="req_123", user_id=456):
            logger.info("Processing request")  # Aura automatiquement request_id et user_id
    """
    # Sauvegarder valeurs actuelles
    old_request_id = request_id_var.get()
    old_user_id = user_id_var.get()
    old_correlation_id = correlation_id_var.get()
    old_operation = operation_var.get()
    
    # Définir nouvelles valeurs
    tokens = []
    if request_id is not None:
        tokens.append(request_id_var.set(request_id))
    if user_id is not None:
        tokens.append(user_id_var.set(user_id))
    if correlation_id is not None:
        tokens.append(correlation_id_var.set(correlation_id))
    if operation is not None:
        tokens.append(operation_var.set(operation))
    
    try:
        yield
    finally:
        # Restaurer valeurs précédentes
        for token in tokens:
            token.var.set(token.old_value)


def get_logger(name: str) -> logging.Logger:
    """
    Obtenir un logger configuré - fonction utilitaire.
    
    Args:
        name: Nom du module (généralement __name__)
        
    Returns:
        logging.Logger: Logger configuré
        
    Example:
        from app.core.logging import get_logger
        
        logger = get_logger(__name__)
        logger.info("Hello world")
    """
    return logging.getLogger(name)


# Instance globale du service de logging
logging_service = LoggingService()


def setup_request_context(request_id: str, user_id: Optional[int] = None):
    """
    Configurer le contexte pour une requête HTTP.
    
    À appeler depuis le middleware FastAPI pour enrichir automatiquement
    tous les logs de la requête.
    
    Args:
        request_id: ID unique de la requête
        user_id: ID utilisateur authentifié (optionnel)
    """
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
