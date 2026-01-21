"""
Modèles d'authentification et d'autorisation pour AindusDB Core.

Ce module contient tous les modèles Pydantic pour la sécurité : utilisateurs, tokens JWT,
rôles, permissions et audit. Il implémente un système RBAC (Role-Based Access Control)
complet avec gestion des refresh tokens et traçabilité des actions.

Example:
    from app.models.auth import User, UserCreate, TokenResponse
    
    # Création d'utilisateur
    new_user = UserCreate(
        username="john_doe", 
        email="john@example.com",
        password="secure_password_123"
    )
    
    # Réponse JWT après login
    token_response = TokenResponse(
        access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        refresh_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        token_type="Bearer",
        expires_in=3600
    )
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, EmailStr, Field, validator
import re


class UserRole(str, Enum):
    """
    Énumération des rôles utilisateur dans AindusDB Core.
    
    Hiérarchie des permissions :
    - ADMIN : Accès complet au système
    - MANAGER : Gestion des utilisateurs et données
    - USER : Opérations vectorielles standard
    - READONLY : Lecture seule des données
    """
    ADMIN = "admin"
    MANAGER = "manager" 
    USER = "user"
    READONLY = "readonly"


class Permission(str, Enum):
    """
    Permissions granulaires pour contrôle d'accès précis.
    
    Format : RESOURCE:ACTION
    Exemples : vectors:read, users:create, system:admin
    """
    # Permissions vecteurs
    VECTORS_READ = "vectors:read"
    VECTORS_CREATE = "vectors:create"
    VECTORS_UPDATE = "vectors:update"
    VECTORS_DELETE = "vectors:delete"
    VECTORS_SEARCH = "vectors:search"
    
    # Permissions utilisateurs
    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    
    # Permissions système
    SYSTEM_HEALTH = "system:health"
    SYSTEM_METRICS = "system:metrics"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_ADMIN = "system:admin"
    
    # Permissions audit
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"


class UserBase(BaseModel):
    """
    Modèle de base utilisateur avec validations communes.
    
    Contient les champs partagés entre création, mise à jour et lecture.
    Implémente les validations métier pour username, email et rôles.
    """
    username: str = Field(..., min_length=3, max_length=50, description="Nom d'utilisateur unique")
    email: EmailStr = Field(..., description="Adresse email valide")
    full_name: Optional[str] = Field(None, max_length=100, description="Nom complet optionnel")
    is_active: bool = Field(True, description="Compte actif/désactivé")
    role: UserRole = Field(UserRole.USER, description="Rôle principal de l'utilisateur")
    
    @validator('username')
    def validate_username(cls, v):
        """Valider format du nom d'utilisateur."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username must contain only letters, numbers, underscores and hyphens')
        return v.lower()
    
    class Config:
        """Configuration Pydantic avec exemple."""
        schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john.doe@company.com",
                "full_name": "John Doe",
                "is_active": True,
                "role": "user"
            }
        }


class UserCreate(UserBase):
    """
    Modèle pour création d'utilisateur avec mot de passe.
    
    Hérite de UserBase et ajoute le champ password avec validation
    de robustesse. Le mot de passe est hashé avant stockage.
    """
    password: str = Field(..., min_length=8, max_length=128, description="Mot de passe sécurisé")
    
    @validator('password')
    def validate_password(cls, v):
        """Valider la robustesse du mot de passe."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Vérifier présence de majuscule, minuscule, chiffre et caractère spécial
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)  
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in '!@#$%^&*(),.?":{}|<>' for c in v)
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                'Password must contain at least one uppercase letter, '
                'one lowercase letter, one digit, and one special character'
            )
        
        return v
    
    class Config:
        """Configuration avec exemple de création."""
        schema_extra = {
            "example": {
                "username": "alice_smith",
                "email": "alice@company.com", 
                "full_name": "Alice Smith",
                "password": "SecurePass123!",
                "role": "manager"
            }
        }


class UserUpdate(BaseModel):
    """
    Modèle pour mise à jour utilisateur avec champs optionnels.
    
    Tous les champs sont optionnels pour permettre des mises à jour
    partielles. Seuls les champs fournis seront modifiés.
    """
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    
    class Config:
        schema_extra = {
            "example": {
                "full_name": "Alice Johnson",
                "role": "admin"
            }
        }


class User(UserBase):
    """
    Modèle complet utilisateur avec métadonnées système.
    
    Représente un utilisateur stocké en base avec ID, dates de création/modification
    et permissions calculées. Utilisé pour les réponses API.
    """
    id: int = Field(..., description="Identifiant unique auto-généré")
    permissions: List[Permission] = Field(default_factory=list, description="Permissions effectives")
    created_at: datetime = Field(..., description="Date de création du compte")
    updated_at: Optional[datetime] = Field(None, description="Dernière modification")
    last_login: Optional[datetime] = Field(None, description="Dernière connexion")
    
    class Config:
        """Configuration avec exemple complet."""
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "username": "admin_user",
                "email": "admin@aindusdb.com",
                "full_name": "System Administrator", 
                "is_active": True,
                "role": "admin",
                "permissions": [
                    "vectors:read", "vectors:create", "vectors:update", "vectors:delete",
                    "users:read", "users:create", "users:update", "users:delete", 
                    "system:admin", "audit:read"
                ],
                "created_at": "2026-01-20T10:00:00Z",
                "updated_at": "2026-01-20T12:30:00Z",
                "last_login": "2026-01-20T12:30:00Z"
            }
        }


class LoginRequest(BaseModel):
    """
    Requête d'authentification avec username/password.
    
    Utilisé pour l'endpoint POST /auth/login avec validation
    des credentials et génération des tokens JWT.
    """
    username: str = Field(..., description="Nom d'utilisateur ou email")
    password: str = Field(..., description="Mot de passe")
    remember_me: bool = Field(False, description="Session étendue (refresh token longue durée)")
    
    class Config:
        schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "SecurePass123!",
                "remember_me": True
            }
        }


class TokenData(BaseModel):
    """
    Données contenues dans le payload JWT.
    
    Informations encodées dans le token pour identification et autorisation
    sans requête base de données à chaque appel API.
    """
    user_id: int = Field(..., description="ID utilisateur unique")
    username: str = Field(..., description="Nom d'utilisateur")
    role: UserRole = Field(..., description="Rôle principal")
    permissions: List[str] = Field(default_factory=list, description="Liste des permissions")
    token_type: str = Field("access", description="Type de token (access/refresh)")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": 1,
                "username": "john_doe", 
                "role": "user",
                "permissions": ["vectors:read", "vectors:create", "vectors:search"],
                "token_type": "access"
            }
        }


class TokenResponse(BaseModel):
    """
    Réponse d'authentification avec tokens JWT.
    
    Retournée après login réussi, contient access token (courte durée),
    refresh token (longue durée) et métadonnées d'expiration.
    """
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token") 
    token_type: str = Field("Bearer", description="Type de token (Bearer)")
    expires_in: int = Field(..., description="Durée de vie access token en secondes")
    refresh_expires_in: int = Field(..., description="Durée de vie refresh token en secondes")
    scope: str = Field("vector_operations", description="Portée des permissions")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImpvaG5fZG9lIiwicm9sZSI6InVzZXIiLCJwZXJtaXNzaW9ucyI6WyJ2ZWN0b3JzOnJlYWQiLCJ2ZWN0b3JzOmNyZWF0ZSJdLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM3MzkzNjAwfQ.signature",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImpvaG5fZG9lIiwidG9rZW5fdHlwZSI6InJlZnJlc2giLCJleHAiOjE3Mzc5OTg0MDB9.signature",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_expires_in": 604800,
                "scope": "vector_operations"
            }
        }


class RefreshRequest(BaseModel):
    """
    Requête de renouvellement de token avec refresh token.
    
    Utilisé pour obtenir un nouvel access token sans re-authentification
    complète, en utilisant le refresh token valide.
    """
    refresh_token: str = Field(..., description="Refresh token valide")
    
    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
            }
        }


class PasswordChangeRequest(BaseModel):
    """
    Requête de changement de mot de passe.
    
    Nécessite l'ancien mot de passe pour validation et le nouveau
    avec les mêmes règles de robustesse que la création.
    """
    current_password: str = Field(..., description="Mot de passe actuel")
    new_password: str = Field(..., min_length=8, description="Nouveau mot de passe")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Appliquer les mêmes règles que UserCreate.password"""
        # Réutiliser la validation de UserCreate
        return UserCreate.validate_password(v)
    
    class Config:
        schema_extra = {
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewSecurePass456!"
            }
        }


class RolePermissionMapping(BaseModel):
    """
    Mapping des rôles vers leurs permissions par défaut.
    
    Définit les permissions accordées automatiquement à chaque rôle.
    Utilisé pour l'initialisation et la vérification des droits.
    """
    role: UserRole
    permissions: List[Permission]
    description: str = Field(..., description="Description du rôle")
    
    class Config:
        schema_extra = {
            "example": {
                "role": "manager",
                "permissions": [
                    "vectors:read", "vectors:create", "vectors:update", "vectors:delete",
                    "users:read", "users:create", "system:health"
                ],
                "description": "Manager avec accès étendu aux vecteurs et utilisateurs"
            }
        }


class AuditLogEntry(BaseModel):
    """
    Entrée de journal d'audit pour traçabilité des actions.
    
    Enregistre toutes les actions sensibles avec contexte complet :
    qui, quoi, quand, où et résultat de l'opération.
    """
    id: Optional[int] = Field(None, description="ID unique de l'entrée")
    user_id: Optional[int] = Field(None, description="ID utilisateur (null pour système)")
    username: Optional[str] = Field(None, description="Nom d'utilisateur")
    action: str = Field(..., description="Action effectuée (ex: login, vector_create)")
    resource: Optional[str] = Field(None, description="Ressource impactée (ex: vector:123)")
    details: Optional[Dict[str, Any]] = Field(None, description="Détails additionnels JSON")
    ip_address: Optional[str] = Field(None, description="Adresse IP source")
    user_agent: Optional[str] = Field(None, description="User-Agent du client")
    success: bool = Field(..., description="Opération réussie ou échouée")
    error_message: Optional[str] = Field(None, description="Message d'erreur si échec")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Horodatage UTC")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "user_id": 5,
                "username": "alice_smith",
                "action": "vector_create",
                "resource": "vector:789",
                "details": {
                    "embedding_dimensions": 384,
                    "metadata": "Important document",
                    "table": "vectors"
                },
                "ip_address": "192.168.1.100",
                "user_agent": "Python/requests",
                "success": True,
                "error_message": None,
                "timestamp": "2026-01-20T15:30:45Z"
            }
        }


class UserStats(BaseModel):
    """
    Statistiques d'utilisation par utilisateur.
    
    Métriques calculées pour monitoring et facturation :
    nombre d'opérations, dernière activité, quotas.
    """
    user_id: int
    username: str
    total_vectors_created: int = Field(0, description="Vecteurs créés au total")
    total_searches_performed: int = Field(0, description="Recherches effectuées")
    last_activity: Optional[datetime] = Field(None, description="Dernière activité")
    api_calls_today: int = Field(0, description="Appels API aujourd'hui")
    quota_limit: Optional[int] = Field(None, description="Limite de quota (null = illimité)")
    quota_used: int = Field(0, description="Quota utilisé ce mois")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": 3,
                "username": "data_scientist",
                "total_vectors_created": 15420,
                "total_searches_performed": 8965,
                "last_activity": "2026-01-20T14:25:00Z",
                "api_calls_today": 156,
                "quota_limit": 100000,
                "quota_used": 42356
            }
        }


# Mapping par défaut des rôles vers permissions
DEFAULT_ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        # Toutes les permissions système
        Permission.VECTORS_READ, Permission.VECTORS_CREATE, Permission.VECTORS_UPDATE, Permission.VECTORS_DELETE, Permission.VECTORS_SEARCH,
        Permission.USERS_READ, Permission.USERS_CREATE, Permission.USERS_UPDATE, Permission.USERS_DELETE,
        Permission.SYSTEM_HEALTH, Permission.SYSTEM_METRICS, Permission.SYSTEM_CONFIG, Permission.SYSTEM_ADMIN,
        Permission.AUDIT_READ, Permission.AUDIT_EXPORT
    ],
    UserRole.MANAGER: [
        # Accès étendu vecteurs et utilisateurs
        Permission.VECTORS_READ, Permission.VECTORS_CREATE, Permission.VECTORS_UPDATE, Permission.VECTORS_DELETE, Permission.VECTORS_SEARCH,
        Permission.USERS_READ, Permission.USERS_CREATE, Permission.USERS_UPDATE,
        Permission.SYSTEM_HEALTH, Permission.SYSTEM_METRICS,
        Permission.AUDIT_READ
    ],
    UserRole.USER: [
        # Opérations vectorielles standard
        Permission.VECTORS_READ, Permission.VECTORS_CREATE, Permission.VECTORS_UPDATE, Permission.VECTORS_SEARCH,
        Permission.SYSTEM_HEALTH
    ],
    UserRole.READONLY: [
        # Lecture seule
        Permission.VECTORS_READ, Permission.VECTORS_SEARCH,
        Permission.SYSTEM_HEALTH
    ]
}


def get_role_permissions(role: UserRole) -> List[Permission]:
    """
    Obtenir les permissions par défaut d'un rôle.
    
    Args:
        role: Rôle utilisateur
        
    Returns:
        List[Permission]: Liste des permissions accordées
        
    Example:
        perms = get_role_permissions(UserRole.MANAGER)
        print(f"Manager permissions: {[p.value for p in perms]}")
    """
    return DEFAULT_ROLE_PERMISSIONS.get(role, [])
