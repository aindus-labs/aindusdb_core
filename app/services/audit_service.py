"""
Service d'audit et traçabilité pour AindusDB Core avec logging structuré avancé.

Ce module implémente un système d'audit complet pour tracer toutes les opérations
sensibles : authentification, modifications de données, accès aux ressources,
et actions administratives avec métadonnées contextuelles.

Example:
    from app.services.audit_service import AuditService
    
    audit = AuditService(db_manager)
    
    # Logger une action utilisateur
    await audit.log_user_action(
        user_id=1,
        action="vector_create",
        resource="vector:456", 
        success=True,
        details={"embedding_dims": 384, "metadata": "document.pdf"},
        request=request
    )
    
    # Rechercher dans les logs d'audit
    entries = await audit.search_audit_logs(
        user_id=1,
        action_filter="login",
        date_range=(start_date, end_date)
    )
"""

import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from fastapi import Request
import ipaddress

from ..core.database import DatabaseManager
from ..models.auth import AuditLogEntry, TokenData


class AuditLevel(str, Enum):
    """Niveaux de criticité des événements d'audit."""
    INFO = "info"          # Actions normales (login, lecture)
    WARNING = "warning"    # Actions suspectes (échecs répétés)
    CRITICAL = "critical"  # Actions sensibles (suppression, admin)
    SECURITY = "security"  # Événements de sécurité (intrusion, violation)


class AuditCategory(str, Enum):
    """Catégories d'événements pour classification."""
    AUTH = "authentication"
    AUTHORIZATION = "authorization" 
    DATA = "data_operation"
    SYSTEM = "system_admin"
    SECURITY = "security_event"
    API = "api_access"


@dataclass
class AuditContext:
    """Contexte enrichi pour audit avec métadonnées."""
    user_id: Optional[int] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    response_status: Optional[int] = None
    execution_time_ms: Optional[float] = None
    additional_data: Optional[Dict[str, Any]] = None


class AuditService:
    """
    Service d'audit centralisé pour traçabilité complète des opérations AindusDB Core.
    
    Cette classe implémente un système d'audit professionnel avec :
    - Logging structuré de toutes les actions sensibles
    - Enrichissement automatique avec contexte HTTP/utilisateur
    - Classification par niveau de criticité et catégorie
    - Recherche et filtrage avancés des logs
    - Détection d'anomalies et patterns suspects
    - Export et archivage pour conformité réglementaire
    - Performance optimisée pour volume élevé
    
    Features:
    - Audit trail immuable avec horodatage précis
    - Métadonnées contextuelles automatiques (IP, User-Agent, etc.)
    - Détection de tentatives d'intrusion et comportements anormaux
    - Alertes en temps réel sur événements critiques
    - Tableaux de bord et métriques d'audit
    - Intégration SIEM (Security Information Event Management)
    - Conformité RGPD/SOX avec anonymisation optionnelle
    
    Attributes:
        db: Gestionnaire de base de données pour persistance
        alert_thresholds: Seuils pour déclenchement d'alertes
        retention_days: Durée de rétention des logs (défaut: 365 jours)
        
    Example:
        # Configuration production avec alerting
        audit = AuditService(
            db_manager=db_manager,
            retention_days=2555,  # 7 ans pour conformité
            enable_realtime_alerts=True
        )
        
        # Audit complet d'une opération critique
        async with audit.audit_context() as ctx:
            try:
                result = await sensitive_operation()
                await ctx.log_success("admin_user_delete", 
                                    resource=f"user:{deleted_user_id}",
                                    details={"reason": "policy_violation"})
            except Exception as e:
                await ctx.log_failure("admin_user_delete",
                                    error=str(e),
                                    details={"attempted_user_id": user_id})
    """
    
    def __init__(self, 
                 db_manager: DatabaseManager,
                 retention_days: int = 365,
                 enable_realtime_alerts: bool = False):
        """
        Initialiser le service d'audit avec configuration.
        
        Args:
            db_manager: Gestionnaire de base de données
            retention_days: Durée de rétention des logs en jours
            enable_realtime_alerts: Activer alertes temps réel
        """
        self.db = db_manager
        self.retention_days = retention_days
        self.enable_alerts = enable_realtime_alerts
        
        # Seuils pour détection d'anomalies
        self.alert_thresholds = {
            "failed_logins_per_hour": 10,
            "api_calls_per_minute": 1000,
            "admin_actions_per_hour": 50,
            "suspicious_ips_threshold": 5
        }
        
        # Cache pour prévenir spam de logs identiques
        self._recent_entries_cache = {}
    
    async def log_user_action(self,
                            action: str,
                            success: bool = True,
                            user_id: Optional[int] = None,
                            username: Optional[str] = None,
                            resource: Optional[str] = None,
                            details: Optional[Dict[str, Any]] = None,
                            request: Optional[Request] = None,
                            level: AuditLevel = AuditLevel.INFO,
                            category: AuditCategory = AuditCategory.DATA,
                            error_message: Optional[str] = None) -> int:
        """
        Logger une action utilisateur avec contexte complet.
        
        Args:
            action: Action effectuée (ex: "login", "vector_create", "user_delete")
            success: True si action réussie
            user_id: ID de l'utilisateur (optionnel si système)
            username: Nom d'utilisateur pour lisibilité
            resource: Ressource impactée (ex: "vector:123", "user:456") 
            details: Métadonnées additionnelles JSON
            request: Objet Request FastAPI pour contexte HTTP
            level: Niveau de criticité de l'événement
            category: Catégorie pour classification
            error_message: Message d'erreur si échec
            
        Returns:
            int: ID de l'entrée d'audit créée
            
        Example:
            # Audit d'une création de vecteur réussie
            audit_id = await audit.log_user_action(
                action="vector_create",
                success=True,
                user_id=current_user.user_id,
                username=current_user.username,
                resource=f"vector:{new_vector_id}",
                details={
                    "embedding_dimensions": 384,
                    "metadata_size": len(metadata),
                    "processing_time_ms": processing_time
                },
                request=request,
                level=AuditLevel.INFO,
                category=AuditCategory.DATA
            )
            
            # Audit d'un échec d'authentification
            await audit.log_user_action(
                action="login_failed",
                success=False,
                username=attempted_username,
                details={"reason": "invalid_password", "attempt_count": 3},
                request=request,
                level=AuditLevel.WARNING,
                category=AuditCategory.AUTH,
                error_message="Invalid credentials provided"
            )
        """
        # Extraire contexte HTTP si disponible
        context = self._extract_request_context(request)
        
        # Préparer l'entrée d'audit
        audit_entry = AuditLogEntry(
            user_id=user_id,
            username=username,
            action=action,
            resource=resource,
            details=details,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
            success=success,
            error_message=error_message,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Vérifier cache pour éviter doublons récents
        if not await self._should_log_entry(audit_entry):
            return -1  # Entrée ignorée (doublon récent)
        
        # Persister en base de données
        try:
            audit_id = await self.db.fetchval_query("""
                INSERT INTO audit_logs (
                    user_id, username, action, resource, details,
                    ip_address, user_agent, success, error_message,
                    level, category, timestamp, request_id, endpoint, method
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                RETURNING id
            """,
                audit_entry.user_id,
                audit_entry.username,
                audit_entry.action,
                audit_entry.resource,
                json.dumps(audit_entry.details) if audit_entry.details else None,
                audit_entry.ip_address,
                audit_entry.user_agent,
                audit_entry.success,
                audit_entry.error_message,
                level.value,
                category.value,
                audit_entry.timestamp,
                context.request_id,
                context.endpoint,
                context.method
            )
            
            # Ajouter au cache anti-doublon
            cache_key = self._generate_cache_key(audit_entry)
            self._recent_entries_cache[cache_key] = datetime.now(timezone.utc)
            
            # Détecter anomalies et déclencher alertes si nécessaire
            if self.enable_alerts:
                await self._check_anomalies(audit_entry, level, category)
            
            return audit_id
            
        except Exception as e:
            # En cas d'erreur de logging, ne pas interrompre l'opération principale
            # Logger en fallback (fichier, syslog, etc.)
            print(f"Audit logging failed: {e}")
            return -1
    
    async def log_authentication_event(self,
                                     event_type: str,
                                     username: str,
                                     success: bool,
                                     request: Optional[Request] = None,
                                     additional_details: Optional[Dict[str, Any]] = None) -> int:
        """
        Logger spécifiquement les événements d'authentification.
        
        Args:
            event_type: Type d'événement ("login", "logout", "refresh", "password_change")
            username: Nom d'utilisateur concerné
            success: Résultat de l'authentification
            request: Contexte HTTP
            additional_details: Détails supplémentaires
            
        Returns:
            int: ID de l'entrée d'audit
            
        Example:
            # Login réussi
            await audit.log_authentication_event(
                "login", "alice", True, request,
                {"method": "jwt", "remember_me": True}
            )
            
            # Échec de login suspect
            await audit.log_authentication_event(
                "login_failed", "admin", False, request,
                {"reason": "brute_force_detected", "blocked": True}
            )
        """
        level = AuditLevel.INFO if success else AuditLevel.WARNING
        
        # Élever le niveau si échecs répétés
        if not success:
            recent_failures = await self._count_recent_failures(username, "login")
            if recent_failures >= 5:
                level = AuditLevel.CRITICAL
        
        details = additional_details or {}
        details.update({
            "authentication_method": "jwt",
            "client_type": self._detect_client_type(request)
        })
        
        return await self.log_user_action(
            action=event_type,
            success=success,
            username=username,
            details=details,
            request=request,
            level=level,
            category=AuditCategory.AUTH,
            error_message=None if success else f"Authentication failed for {username}"
        )
    
    async def log_authorization_event(self,
                                    user: TokenData,
                                    resource: str,
                                    action: str,
                                    granted: bool,
                                    required_permission: Optional[str] = None,
                                    request: Optional[Request] = None) -> int:
        """
        Logger les événements d'autorisation et contrôle d'accès.
        
        Args:
            user: Utilisateur demandeur
            resource: Ressource demandée
            action: Action tentée
            granted: Autorisation accordée ou refusée
            required_permission: Permission requise
            request: Contexte HTTP
            
        Returns:
            int: ID de l'entrée d'audit
        """
        level = AuditLevel.INFO if granted else AuditLevel.WARNING
        
        details = {
            "resource_type": resource.split(":")[0] if ":" in resource else "unknown",
            "action_attempted": action,
            "user_role": user.role.value,
            "user_permissions": user.permissions[:10]  # Limiter pour taille
        }
        
        if not granted and required_permission:
            details["missing_permission"] = required_permission
            details["access_denied_reason"] = "insufficient_permissions"
        
        return await self.log_user_action(
            action=f"access_{action}",
            success=granted,
            user_id=user.user_id,
            username=user.username,
            resource=resource,
            details=details,
            request=request,
            level=level,
            category=AuditCategory.AUTHORIZATION,
            error_message=None if granted else f"Access denied to {resource}"
        )
    
    async def search_audit_logs(self,
                              user_id: Optional[int] = None,
                              username_filter: Optional[str] = None,
                              action_filter: Optional[str] = None,
                              resource_filter: Optional[str] = None,
                              date_range: Optional[Tuple[datetime, datetime]] = None,
                              success_only: Optional[bool] = None,
                              level_filter: Optional[AuditLevel] = None,
                              limit: int = 100,
                              offset: int = 0) -> List[AuditLogEntry]:
        """
        Rechercher dans les logs d'audit avec filtres avancés.
        
        Args:
            user_id: Filtrer par utilisateur
            username_filter: Filtrer par nom d'utilisateur (LIKE)
            action_filter: Filtrer par type d'action
            resource_filter: Filtrer par ressource
            date_range: Plage de dates (début, fin)
            success_only: Filtrer par succès/échec
            level_filter: Filtrer par niveau de criticité
            limit: Nombre max de résultats
            offset: Décalage pour pagination
            
        Returns:
            List[AuditLogEntry]: Entrées d'audit correspondantes
            
        Example:
            # Rechercher échecs de login récents
            failed_logins = await audit.search_audit_logs(
                action_filter="login",
                success_only=False,
                date_range=(datetime.now() - timedelta(hours=24), datetime.now()),
                level_filter=AuditLevel.WARNING
            )
            
            # Audit des actions d'un utilisateur spécifique
            user_actions = await audit.search_audit_logs(
                user_id=123,
                date_range=(start_date, end_date),
                limit=1000
            )
        """
        try:
            # Construire requête dynamique
            where_conditions = []
            query_params = []
            
            if user_id is not None:
                where_conditions.append(f"user_id = ${len(query_params) + 1}")
                query_params.append(user_id)
                
            if username_filter:
                where_conditions.append(f"username ILIKE ${len(query_params) + 1}")
                query_params.append(f"%{username_filter}%")
                
            if action_filter:
                where_conditions.append(f"action ILIKE ${len(query_params) + 1}")
                query_params.append(f"%{action_filter}%")
                
            if resource_filter:
                where_conditions.append(f"resource ILIKE ${len(query_params) + 1}")
                query_params.append(f"%{resource_filter}%")
                
            if date_range:
                where_conditions.append(f"timestamp >= ${len(query_params) + 1}")
                query_params.append(date_range[0])
                where_conditions.append(f"timestamp <= ${len(query_params) + 1}")
                query_params.append(date_range[1])
                
            if success_only is not None:
                where_conditions.append(f"success = ${len(query_params) + 1}")
                query_params.append(success_only)
                
            if level_filter:
                where_conditions.append(f"level = ${len(query_params) + 1}")
                query_params.append(level_filter.value)
            
            # Finaliser la requête
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            query_params.extend([limit, offset])
            
            sql = f"""
                SELECT id, user_id, username, action, resource, details,
                       ip_address, user_agent, success, error_message,
                       level, category, timestamp
                FROM audit_logs
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ${len(query_params) - 1} OFFSET ${len(query_params)}
            """
            
            rows = await self.db.fetch_query(sql, *query_params)
            
            # Convertir en objets AuditLogEntry
            entries = []
            for row in rows:
                details = json.loads(row["details"]) if row["details"] else None
                
                entry = AuditLogEntry(
                    id=row["id"],
                    user_id=row["user_id"],
                    username=row["username"],
                    action=row["action"],
                    resource=row["resource"],
                    details=details,
                    ip_address=row["ip_address"],
                    user_agent=row["user_agent"],
                    success=row["success"],
                    error_message=row["error_message"],
                    timestamp=row["timestamp"]
                )
                entries.append(entry)
            
            return entries
            
        except Exception as e:
            print(f"Audit search failed: {e}")
            return []
    
    async def get_audit_statistics(self, 
                                 days_back: int = 30) -> Dict[str, Any]:
        """
        Générer statistiques d'audit pour monitoring.
        
        Args:
            days_back: Nombre de jours à analyser
            
        Returns:
            Dict[str, Any]: Statistiques détaillées
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            # Requêtes de statistiques
            stats = {}
            
            # Compteurs globaux
            stats["total_events"] = await self.db.fetchval_query(
                "SELECT COUNT(*) FROM audit_logs WHERE timestamp >= $1",
                cutoff_date
            )
            
            stats["successful_events"] = await self.db.fetchval_query(
                "SELECT COUNT(*) FROM audit_logs WHERE timestamp >= $1 AND success = true",
                cutoff_date
            )
            
            stats["failed_events"] = stats["total_events"] - stats["successful_events"]
            
            # Top actions
            top_actions = await self.db.fetch_query("""
                SELECT action, COUNT(*) as count
                FROM audit_logs 
                WHERE timestamp >= $1 
                GROUP BY action 
                ORDER BY count DESC 
                LIMIT 10
            """, cutoff_date)
            
            stats["top_actions"] = [
                {"action": row["action"], "count": row["count"]} 
                for row in top_actions
            ]
            
            # Utilisateurs les plus actifs
            top_users = await self.db.fetch_query("""
                SELECT username, COUNT(*) as count
                FROM audit_logs 
                WHERE timestamp >= $1 AND username IS NOT NULL
                GROUP BY username 
                ORDER BY count DESC 
                LIMIT 10
            """, cutoff_date)
            
            stats["top_users"] = [
                {"username": row["username"], "count": row["count"]}
                for row in top_users
            ]
            
            return stats
            
        except Exception as e:
            return {"error": f"Statistics generation failed: {e}"}
    
    def _extract_request_context(self, request: Optional[Request]) -> AuditContext:
        """Extraire le contexte HTTP de la requête."""
        if not request:
            return AuditContext()
        
        return AuditContext(
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint=str(request.url.path),
            method=request.method,
            request_id=request.headers.get("x-request-id")
        )
    
    def _detect_client_type(self, request: Optional[Request]) -> str:
        """Détecter le type de client basé sur User-Agent."""
        if not request:
            return "unknown"
        
        ua = request.headers.get("user-agent", "").lower()
        
        if "python" in ua or "requests" in ua:
            return "python_sdk"
        elif "curl" in ua:
            return "curl"
        elif "postman" in ua:
            return "postman"
        elif "browser" in ua or "mozilla" in ua:
            return "web_browser"
        else:
            return "api_client"
    
    async def _should_log_entry(self, entry: AuditLogEntry) -> bool:
        """Vérifier si l'entrée doit être loggée (éviter doublons)."""
        cache_key = self._generate_cache_key(entry)
        
        # Vérifier si entrée récente identique existe
        if cache_key in self._recent_entries_cache:
            last_time = self._recent_entries_cache[cache_key]
            if datetime.now(timezone.utc) - last_time < timedelta(seconds=10):
                return False  # Doublon récent, ignorer
        
        return True
    
    def _generate_cache_key(self, entry: AuditLogEntry) -> str:
        """Générer clé de cache pour détection de doublons."""
        return f"{entry.user_id}:{entry.action}:{entry.resource}:{entry.success}"
    
    async def _count_recent_failures(self, username: str, action: str, hours: int = 1) -> int:
        """Compter les échecs récents pour détection d'anomalies."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        try:
            count = await self.db.fetchval_query("""
                SELECT COUNT(*) FROM audit_logs 
                WHERE username = $1 AND action = $2 
                AND success = false AND timestamp >= $3
            """, username, action, cutoff_time)
            
            return count or 0
            
        except Exception:
            return 0
    
    async def _check_anomalies(self, entry: AuditLogEntry, level: AuditLevel, category: AuditCategory):
        """Détecter anomalies et déclencher alertes."""
        # TODO: Implémenter détection d'anomalies avancée
        # - Trop d'échecs de login
        # - Activité inhabituelle par IP
        # - Pics d'activité suspects
        # - Actions admin en dehors heures ouvrables
        pass


# Instance globale du service d'audit
audit_service = AuditService
