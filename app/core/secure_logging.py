"""
🔒 Secure Logging Service
Logging sécurisé avec masquage des données sensibles et monitoring

Créé : 20 janvier 2026
Objectif : Jalon 3.2 - Logging Sécurisé & Monitoring
"""

import re
import json
import hashlib
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import gzip
import aiofiles
from pydantic import BaseModel, Field, validator, model_validator, field_validator

from app.core.database import db_manager


class SecurityLogEntry(BaseModel):
    """Entrée de log de sécurité."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str = Field(..., pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    event_type: str = Field(..., description="Type d'événement")
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    message: str = Field(..., max_length=1000)
    details: Optional[Dict[str, Any]] = None
    risk_score: int = Field(default=0, ge=0, le=10)
    correlation_id: Optional[str] = None
    
    @field_validator('user_id')
    def hash_user_id(cls, v):
        """Hasher l'ID utilisateur pour la confidentialité."""
        if v:
            return hashlib.sha256(v.encode()).hexdigest()[:16]
        return v
    
    @field_validator('ip_address')
    def anonymize_ip(cls, v):
        """Anonymiser l'IP (GDPR)."""
        if v and '.' in v:
            parts = v.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.***"
        return v


class SecurityFilter(logging.Filter):
    """Filtre pour masquer les données sensibles dans les logs."""
    
    # Patterns à masquer
    SENSITIVE_PATTERNS = [
        # Passwords
        (r'password["\s]*[:=]["\s]*([^"\\s,}]+)', 'password":"***"'),
        (r'passwd["\s]*[:=]["\s]*([^"\\s,}]+)', 'passwd":"***"'),
        (r'pwd["\s]*[:=]["\s]*([^"\\s,}]+)', 'pwd":"***"'),
        
        # Tokens et clés API
        (r'token["\s]*[:=]["\s]*([A-Za-z0-9+/]{20,}=*)', 'token":"***"'),
        (r'api_key["\s]*[:=]["\s]*([A-Za-z0-9]{20,})', 'api_key":"***"'),
        (r'secret["\s]*[:=]["\s]*([A-Za-z0-9+/]{20,}=*)', 'secret":"***"'),
        
        # Données personnelles (emails, téléphones)
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.com'),
        (r'\b\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,9}\b', '***-***-****'),
        
        # Numéros de carte bancaire
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '****-****-****-****'),
        
        # Clés JWT
        (r'eyJ[A-Za-z0-9+/]*\.[A-Za-z0-9+/]*\.[A-Za-z0-9+/]*', 'JWT_TOKEN_***'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Appliquer le filtrage sur le message."""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            # Masquer les données sensibles
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.msg = re.sub(pattern, replacement, record.msg, flags=re.IGNORECASE)
        
        # Filtrer les arguments
        if hasattr(record, 'args') and record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, replacement in self.SENSITIVE_PATTERNS:
                        arg = re.sub(pattern, replacement, arg, flags=re.IGNORECASE)
                new_args.append(arg)
            record.args = tuple(new_args)
        
        return True


class SecureLogger:
    """Logger sécurisé pour les événements de sécurité."""
    
    def __init__(self, name: str = "security"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Ajouter le filtre de sécurité
        security_filter = SecurityFilter()
        self.logger.addFilter(security_filter)
        
        # Handler pour la console (dev)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        self.logger.addHandler(console_handler)
        
        # Handler pour les fichiers (production)
        self.file_handler = None
        self.audit_handler = None
        
        # Buffer pour les logs async
        self.log_buffer: List[SecurityLogEntry] = []
        self.buffer_size = 100
        
    async def setup_file_logging(self, log_dir: str = "logs"):
        """Configurer le logging vers fichiers."""
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # Handler pour les logs généraux
        log_file = log_path / "security.log"
        self.file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=100*1024*1024,  # 100MB
            backupCount=10
        )
        self.file_handler.setFormatter(
            logging.Formatter(
                '{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}'
            )
        )
        self.logger.addHandler(self.file_handler)
        
        # Handler pour les logs d'audit
        audit_file = log_path / "audit.log"
        self.audit_handler = logging.handlers.RotatingFileHandler(
            audit_file,
            maxBytes=50*1024*1024,  # 50MB
            backupCount=5
        )
        self.audit_handler.setFormatter(
            logging.Formatter(
                '{"timestamp":"%(asctime)s","event":"%(message)s"}'
            )
        )
        self.logger.addHandler(self.audit_handler)
    
    async def log_security_event(
        self,
        event_type: str,
        message: str,
        level: str = "INFO",
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        risk_score: int = 0,
        correlation_id: Optional[str] = None
    ):
        """Logger un événement de sécurité."""
        
        # Créer l'entrée de log
        entry = SecurityLogEntry(
            level=level,
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            message=message,
            details=details,
            risk_score=risk_score,
            correlation_id=correlation_id
        )
        
        # Logger immédiatement
        log_message = self._format_log_message(entry)
        getattr(self.logger, level.lower())(log_message)
        
        # Ajouter au buffer pour la base de données
        self.log_buffer.append(entry)
        
        # Sauvegarder en base si buffer plein
        if len(self.log_buffer) >= self.buffer_size:
            await self._flush_to_database()
    
    async def _flush_to_database(self):
        """Sauvegarder les logs en base de données."""
        if not self.log_buffer:
            return
        
        try:
            # Créer la table si elle n'existe pas
            await self._ensure_audit_table()
            
            # Insérer les logs
            for entry in self.log_buffer:
                await db_manager.execute(
                    """
                    INSERT INTO security_audit_log 
                    (timestamp, level, event_type, user_id, ip_address, 
                     user_agent, endpoint, method, status_code, message, 
                     details, risk_score, correlation_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    """,
                    entry.timestamp,
                    entry.level,
                    entry.event_type,
                    entry.user_id,
                    entry.ip_address,
                    entry.user_agent,
                    entry.endpoint,
                    entry.method,
                    entry.status_code,
                    entry.message,
                    json.dumps(entry.details) if entry.details else None,
                    entry.risk_score,
                    entry.correlation_id
                )
            
            self.log_buffer.clear()
            
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde logs en base: {e}")
    
    async def _ensure_audit_table(self):
        """S'assurer que la table d'audit existe."""
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS security_audit_log (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                level VARCHAR(10) NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                user_id VARCHAR(64),
                ip_address VARCHAR(45),
                user_agent TEXT,
                endpoint VARCHAR(255),
                method VARCHAR(10),
                status_code INTEGER,
                message TEXT NOT NULL,
                details JSONB,
                risk_score INTEGER DEFAULT 0,
                correlation_id VARCHAR(64),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        # Index pour les requêtes
        await db_manager.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
            ON security_audit_log(timestamp)
        """)
        
        await db_manager.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_event_type 
            ON security_audit_log(event_type)
        """)
        
        await db_manager.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_risk_score 
            ON security_audit_log(risk_score)
        """)
    
    def _format_log_message(self, entry: SecurityLogEntry) -> str:
        """Formater le message de log."""
        parts = [
            f"[{entry.event_type}]",
            entry.message
        ]
        
        if entry.user_id:
            parts.append(f"user:{entry.user_id}")
        if entry.ip_address:
            parts.append(f"ip:{entry.ip_address}")
        if entry.endpoint:
            parts.append(f"endpoint:{entry.endpoint}")
        if entry.risk_score > 0:
            parts.append(f"risk:{entry.risk_score}/10")
        
        return " ".join(parts)
    
    async def search_logs(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_risk_score: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Rechercher dans les logs de sécurité."""
        
        conditions = []
        params = []
        param_count = 1
        
        if event_type:
            conditions.append(f"event_type = ${param_count}")
            params.append(event_type)
            param_count += 1
        
        if user_id:
            conditions.append(f"user_id = ${param_count}")
            params.append(user_id)
            param_count += 1
        
        if ip_address:
            conditions.append(f"ip_address = ${param_count}")
            params.append(ip_address)
            param_count += 1
        
        if start_time:
            conditions.append(f"timestamp >= ${param_count}")
            params.append(start_time)
            param_count += 1
        
        if end_time:
            conditions.append(f"timestamp <= ${param_count}")
            params.append(end_time)
            param_count += 1
        
        if min_risk_score > 0:
            conditions.append(f"risk_score >= ${param_count}")
            params.append(min_risk_score)
            param_count += 1
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT * FROM security_audit_log
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_count}
        """
        params.append(limit)
        
        return await db_manager.fetch_all(query, *params)
    
    async def get_security_stats(self, days: int = 7) -> Dict[str, Any]:
        """Obtenir des statistiques de sécurité."""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Événements par type
        events_by_type = await db_manager.fetch_all("""
            SELECT event_type, COUNT(*) as count
            FROM security_audit_log
            WHERE timestamp >= $1
            GROUP BY event_type
            ORDER BY count DESC
        """, start_time)
        
        # Événements à risque
        high_risk_events = await db_manager.fetch_one("""
            SELECT COUNT(*) as count
            FROM security_audit_log
            WHERE timestamp >= $1 AND risk_score >= 7
        """, start_time)
        
        # Top IPs suspectes
        suspicious_ips = await db_manager.fetch_all("""
            SELECT ip_address, COUNT(*) as count, AVG(risk_score) as avg_risk
            FROM security_audit_log
            WHERE timestamp >= $1 AND ip_address IS NOT NULL
            GROUP BY ip_address
            HAVING COUNT(*) > 10
            ORDER BY count DESC
            LIMIT 10
        """, start_time)
        
        return {
            "period_days": days,
            "total_events": sum(e["count"] for e in events_by_type),
            "events_by_type": dict(events_by_type),
            "high_risk_events": high_risk_events["count"],
            "suspicious_ips": suspicious_ips
        }
    
    async def cleanup_old_logs(self, days_to_keep: int = 90):
        """Nettoyer les anciens logs."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted = await db_manager.fetch_one("""
            DELETE FROM security_audit_log
            WHERE timestamp < $1
            RETURNING COUNT(*) as count
        """, cutoff_date)
        
        self.logger.info(f"Nettoyé {deleted['count']} anciens logs")
    
    async def export_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        format: str = "json"
    ) -> str:
        """Exporter les logs dans un fichier."""
        
        logs = await self.search_logs(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Créer le fichier d'export
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"logs/security_export_{timestamp}.{format}"
        
        if format == "json":
            # Formater en JSON
            export_data = []
            for log in logs:
                export_data.append({
                    "timestamp": log["timestamp"].isoformat(),
                    "event_type": log["event_type"],
                    "message": log["message"],
                    "risk_score": log["risk_score"]
                })
            
            async with aiofiles.open(filename, 'w') as f:
                await f.write(json.dumps(export_data, indent=2))
        
        elif format == "csv":
            # Formater en CSV
            import csv
            
            async with aiofiles.open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'event_type', 'message', 'risk_score'])
                
                for log in logs:
                    writer.writerow([
                        log["timestamp"].isoformat(),
                        log["event_type"],
                        log["message"],
                        log["risk_score"]
                    ])
        
        # Compresser le fichier
        with open(filename, 'rb') as f_in:
            with gzip.open(f"{filename}.gz", 'wb') as f_out:
                f_out.writelines(f_in)
        
        Path(filename).unlink()  # Supprimer le fichier non compressé
        
        return f"{filename}.gz"


# Instance globale du logger sécurisé
secure_logger = SecureLogger()


# Middleware pour intégrer le logging sécurisé
class SecurityLoggingMiddleware:
    """Middleware pour logger automatiquement les événements de sécurité."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extraire les informations de la requête
        request = Request(scope, receive)
        
        # Générer un correlation ID
        correlation_id = hashlib.md5(
            f"{request.url.path}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Logger la requête
        await secure_logger.log_security_event(
            event_type="HTTP_REQUEST",
            message=f"{request.method} {request.url.path}",
            level="INFO",
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            endpoint=request.url.path,
            method=request.method,
            correlation_id=correlation_id
        )
        
        # Intercepter la réponse
        response_status = 200
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_status = message["status"]
                
                # Logger les réponses d'erreur
                if response_status >= 400:
                    await secure_logger.log_security_event(
                        event_type="HTTP_ERROR",
                        message=f"HTTP {response_status} on {request.method} {request.url.path}",
                        level="WARNING" if response_status < 500 else "ERROR",
                        ip_address=self._get_client_ip(request),
                        endpoint=request.url.path,
                        method=request.method,
                        status_code=response_status,
                        risk_score=5 if response_status >= 500 else 3,
                        correlation_id=correlation_id
                    )
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
    
    def _get_client_ip(self, request):
        """Obtenir l'IP réelle du client."""
        # Vérifier les headers de proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return getattr(request.client, "host", "unknown")
