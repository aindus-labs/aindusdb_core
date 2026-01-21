"""
🔐 Service d'Authentification Sécurisé - AindusDB Core
Implémentation remplaçant les credentials hardcodés par authentification DB

Créé : 20 janvier 2026
Objectif : Phase 1.3 - Authentification temporaire sécurisée
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import asyncio
from asyncpg import Record

from ..core.database import get_db_manager, DatabaseManager
from ..core.security import SecurityService
from ..models.auth import User, TokenData
import logging

logger = logging.getLogger(__name__)

class AuthService:
    """Service d'authentification sécurisé avec base de données."""
    
    def __init__(self, security_service: SecurityService):
        self.security_service = security_service
        self.db_manager = None
        self._max_login_attempts = 5
        self._lockout_duration = timedelta(minutes=15)
    
    async def initialize(self):
        """Initialiser le service avec le gestionnaire de base de données."""
        self.db_manager = get_db_manager()
    
    async def authenticate_user(self, username: str, password: str, 
                              ip_address: str = None, user_agent: str = None) -> Optional[User]:
        """
        Authentifier un utilisateur via base de données.
        
        Args:
            username: Nom d'utilisateur ou email
            password: Mot de passe en clair
            ip_address: IP du client pour audit
            user_agent: User-Agent pour audit
            
        Returns:
            User si authentification réussie, None sinon
        """
        if not self.db_manager:
            await self.initialize()
        
        try:
            async with self.db_manager.get_connection() as conn:
                # Récupérer utilisateur avec verrouillage
                user_record = await conn.fetchrow("""
                    SELECT id, username, email, password_hash, is_active, is_verified,
                           is_admin, role, permissions, login_attempts, locked_until,
                           last_login, created_at
                    FROM users 
                    WHERE username = $1 OR email = $1
                    FOR UPDATE
                """, username)
                
                if not user_record:
                    await self._log_auth_event(
                        username, 'login_failed', ip_address, user_agent,
                        success=False, failure_reason='user_not_found'
                    )
                    return None
                
                # Vérifier si compte est verrouillé
                if user_record['locked_until'] and user_record['locked_until'] > datetime.now(timezone.utc):
                    await self._log_auth_event(
                        user_record['username'], 'login_failed', ip_address, user_agent,
                        success=False, failure_reason='account_locked'
                    )
                    return None
                
                # Vérifier si compte est actif
                if not user_record['is_active']:
                    await self._log_auth_event(
                        user_record['username'], 'login_failed', ip_address, user_agent,
                        success=False, failure_reason='account_inactive'
                    )
                    return None
                
                # Vérifier le mot de passe
                if not self.security_service.verify_password(password, user_record['password_hash']):
                    # Incrémenter tentatives échouées
                    await self._handle_failed_login(user_record, ip_address, user_agent)
                    return None
                
                # Authentification réussie!
                await self._handle_successful_login(user_record, ip_address, user_agent)
                
                # Créer objet User
                user = User(
                    id=user_record['id'],
                    username=user_record['username'],
                    email=user_record['email'],
                    is_active=user_record['is_active'],
                    is_verified=user_record['is_verified'],
                    is_admin=user_record['is_admin'],
                    role=user_record['role'],
                    permissions=user_record['permissions'] or [],
                    last_login=user_record['last_login'],
                    created_at=user_record['created_at']
                )
                
                return user
                
        except Exception as e:
            logger.error(f"Erreur lors de l'authentification: {e}")
            await self._log_auth_event(
                username, 'login_failed', ip_address, user_agent,
                success=False, failure_reason='system_error'
            )
            return None
    
    async def create_user(self, username: str, email: str, password: str,
                         role: str = 'user', permissions: List[str] = None) -> Dict[str, Any]:
        """
        Créer un nouvel utilisateur.
        
        Returns:
            Dict avec success, user_id, et message d'erreur si échec
        """
        if not self.db_manager:
            await self.initialize()
        
        try:
            async with self.db_manager.get_connection() as conn:
                # Vérifier unicité
                existing = await conn.fetchrow("""
                    SELECT username, email FROM users 
                    WHERE username = $1 OR email = $2
                """, username, email)
                
                if existing:
                    if existing['username'] == username:
                        return {"success": False, "error": "Username already exists"}
                    else:
                        return {"success": False, "error": "Email already registered"}
                
                # Hasher le mot de passe
                password_hash = self.security_service.hash_password(password)
                
                # Insérer utilisateur
                user_id = await conn.fetchval("""
                    INSERT INTO users (username, email, password_hash, role, permissions)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """, username, email, password_hash, role, permissions or [])
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "message": "User created successfully"
                }
                
        except Exception as e:
            logger.error(f"Erreur création utilisateur: {e}")
            return {"success": False, "error": "Database error"}
    
    async def change_password(self, user_id: str, old_password: str, 
                            new_password: str) -> Dict[str, Any]:
        """Changer le mot de passe d'un utilisateur."""
        if not self.db_manager:
            await self.initialize()
        
        try:
            async with self.db_manager.get_connection() as conn:
                # Récupérer utilisateur
                user_record = await conn.fetchrow("""
                    SELECT password_hash FROM users WHERE id = $1 AND is_active = true
                """, user_id)
                
                if not user_record:
                    return {"success": False, "error": "User not found"}
                
                # Vérifier ancien mot de passe
                if not self.security_service.verify_password(old_password, user_record['password_hash']):
                    return {"success": False, "error": "Invalid current password"}
                
                # Hasher et mettre à jour
                new_hash = self.security_service.hash_password(new_password)
                await conn.execute("""
                    UPDATE users 
                    SET password_hash = $1, password_changed_at = CURRENT_TIMESTAMP
                    WHERE id = $2
                """, new_hash, user_id)
                
                return {"success": True, "message": "Password changed successfully"}
                
        except Exception as e:
            logger.error(f"Erreur changement mot de passe: {e}")
            return {"success": False, "error": "Database error"}
    
    async def revoke_user_sessions(self, user_id: str) -> bool:
        """Révoquer toutes les sessions actives d'un utilisateur."""
        if not self.db_manager:
            await self.initialize()
        
        try:
            async with self.db_manager.get_connection() as conn:
                await conn.execute("""
                    UPDATE user_sessions 
                    SET is_active = false 
                    WHERE user_id = $1 AND is_active = true
                """, user_id)
                return True
        except Exception as e:
            logger.error(f"Erreur révocation sessions: {e}")
            return False
    
    async def _handle_failed_login(self, user_record: Record, ip_address: str, user_agent: str):
        """Gérer une tentative de connexion échouée."""
        attempts = user_record['login_attempts'] + 1
        
        async with self.db_manager.get_connection() as conn:
            if attempts >= self._max_login_attempts:
                # Verrouiller le compte
                lock_until = datetime.now(timezone.utc) + self._lockout_duration
                await conn.execute("""
                    UPDATE users 
                    SET login_attempts = $1, locked_until = $2
                    WHERE id = $3
                """, attempts, lock_until, user_record['id'])
                
                await self._log_auth_event(
                    user_record['username'], 'account_locked', ip_address, user_agent,
                    success=False, failure_reason='too_many_attempts'
                )
            else:
                # Incrémenter tentatives
                await conn.execute("""
                    UPDATE users 
                    SET login_attempts = $1
                    WHERE id = $2
                """, attempts, user_record['id'])
            
            await self._log_auth_event(
                user_record['username'], 'login_failed', ip_address, user_agent,
                success=False, failure_reason='invalid_password'
            )
    
    async def _handle_successful_login(self, user_record: Record, ip_address: str, user_agent: str):
        """Gérer une connexion réussie."""
        async with self.db_manager.get_connection() as conn:
            # Réinitialiser tentatives et déverrouiller
            await conn.execute("""
                UPDATE users 
                SET login_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP
                WHERE id = $1
            """, user_record['id'])
            
            await self._log_auth_event(
                user_record['username'], 'login_success', ip_address, user_agent,
                success=True
            )
    
    async def _log_auth_event(self, username: str, event_type: str, 
                            ip_address: str, user_agent: str,
                            success: bool, failure_reason: str = None):
        """Logger un événement d'authentification."""
        try:
            async with self.db_manager.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO auth_audit_log 
                    (username, event_type, ip_address, user_agent, success, failure_reason)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, username, event_type, ip_address, user_agent, success, failure_reason)
        except Exception as e:
            logger.error(f"Erreur logging auth event: {e}")

# Instance globale
auth_service = None

async def get_auth_service() -> AuthService:
    """Obtenir l'instance du service d'authentification."""
    global auth_service
    if auth_service is None:
        from ..core.security import security_service
        auth_service = AuthService(security_service)
        await auth_service.initialize()
    return auth_service
