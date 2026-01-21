"""
Middleware d'authentification et autorisation pour AindusDB Core.

Ce module implémente les middleware FastAPI pour la sécurité : validation automatique
des tokens JWT, injection des informations utilisateur, vérification des permissions
RBAC et protection contre les accès non autorisés.

Example:
    from app.middleware.auth import AuthMiddleware, require_auth, require_permission
    
    # Appliquer globalement
    app.add_middleware(AuthMiddleware)
    
    # Protéger un endpoint spécifique
    @router.get("/protected")
    @require_auth
    async def protected_endpoint(current_user: User = Depends(get_current_user)):
        return {"user": current_user.username}
    
    # Requérir une permission spécifique
    @router.post("/vectors")
    @require_permission(Permission.VECTORS_CREATE)
    async def create_vector(current_user: User = Depends(get_current_user)):
        pass
"""

import time
from typing import Optional, List, Callable
from fastapi import HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import functools

from ..core.security import security_service, TokenType
from ..models.auth import TokenData, User, Permission, UserRole


# Configuration du bearer token security
bearer_scheme = HTTPBearer(auto_error=False)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware d'authentification pour injection automatique des informations utilisateur.
    
    Ce middleware intercepte toutes les requêtes HTTP pour :
    - Extraire et valider les tokens JWT dans les headers Authorization
    - Injecter les informations utilisateur dans le contexte de requête
    - Logger les tentatives d'authentification pour audit
    - Gérer les routes publiques et protégées automatiquement
    
    Le middleware est appliqué globalement et n'interrompt pas les requêtes
    sur les routes publiques. Il enrichit seulement le contexte pour
    les routes protégées.
    
    Example:
        # Configuration dans main.py
        app.add_middleware(AuthMiddleware)
        
        # Les routes peuvent maintenant accéder à request.state.user
        @router.get("/profile")
        async def get_profile(request: Request):
            if hasattr(request.state, 'user') and request.state.user:
                return {"username": request.state.user.username}
            else:
                raise HTTPException(401, "Authentication required")
    """
    
    def __init__(self, app):
        """
        Initialiser le middleware avec configuration des routes publiques.
        
        Args:
            app: Application FastAPI
        """
        super().__init__(app)
        
        # Routes qui ne nécessitent pas d'authentification
        self.public_routes = {
            "/",
            "/health", 
            "/status",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/register"
        }
        
        # Préfixes de routes publiques
        self.public_prefixes = [
            "/static",
            "/favicon"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Traiter la requête avec validation d'authentification optionnelle.
        
        Args:
            request: Requête HTTP entrante
            call_next: Fonction pour continuer le pipeline
            
        Returns:
            Response: Réponse HTTP avec contexte utilisateur enrichi
        """
        start_time = time.time()
        
        # Vérifier si route publique
        if self._is_public_route(request.url.path):
            return await call_next(request)
        
        # Extraire token JWT du header Authorization
        token = self._extract_token(request)
        
        # Valider et injecter informations utilisateur si token présent
        if token:
            token_data = await security_service.validate_token(token)
            if token_data:
                # Injecter dans le contexte de requête
                request.state.user = token_data
                request.state.authenticated = True
            else:
                request.state.authenticated = False
        else:
            request.state.authenticated = False
        
        # Continuer le pipeline
        response = await call_next(request)
        
        # Ajouter headers de sécurité
        self._add_security_headers(response)
        
        # Logger pour audit si authentifié
        if hasattr(request.state, 'user') and request.state.user:
            processing_time = time.time() - start_time
            await self._log_request(request, response, processing_time)
        
        return response
    
    def _is_public_route(self, path: str) -> bool:
        """Vérifier si la route est publique."""
        if path in self.public_routes:
            return True
            
        for prefix in self.public_prefixes:
            if path.startswith(prefix):
                return True
                
        return False
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extraire le token JWT du header Authorization."""
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return None
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None
    
    def _add_security_headers(self, response: Response) -> None:
        """Ajouter les headers de sécurité à la réponse."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    async def _log_request(self, request: Request, response: Response, processing_time: float):
        """Logger la requête pour audit (à implémenter avec service audit)."""
        # TODO: Implémenter logging d'audit
        pass


async def get_token_data(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> Optional[TokenData]:
    """
    Dependency FastAPI pour extraire et valider les credentials JWT.
    
    Cette fonction est utilisée comme dépendance dans les endpoints
    qui ont besoin d'accéder aux informations du token sans forcer
    l'authentification.
    
    Args:
        credentials: Credentials HTTP Bearer automatiquement extraits
        
    Returns:
        Optional[TokenData]: Données du token ou None si absent/invalide
        
    Example:
        @router.get("/optional-auth")
        async def endpoint(token_data: Optional[TokenData] = Depends(get_token_data)):
            if token_data:
                return {"user": token_data.username}
            else:
                return {"message": "Public access"}
    """
    if not credentials:
        return None
    
    token_data = await security_service.validate_token(credentials.credentials)
    return token_data


async def get_current_user(token_data: TokenData = Depends(get_token_data)) -> TokenData:
    """
    Dependency FastAPI pour obtenir l'utilisateur authentifié (obligatoire).
    
    Force l'authentification en levant une exception HTTP 401 si aucun
    token valide n'est fourni. Utilisé pour les endpoints protégés.
    
    Args:
        token_data: Données du token (injectées automatiquement)
        
    Returns:
        TokenData: Informations de l'utilisateur authentifié
        
    Raises:
        HTTPException: 401 si non authentifié ou token invalide
        
    Example:
        @router.get("/protected")
        async def protected_endpoint(current_user: TokenData = Depends(get_current_user)):
            return {
                "message": f"Hello {current_user.username}",
                "role": current_user.role,
                "permissions": current_user.permissions
            }
    """
    if not token_data:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return token_data


def require_permission(required_permission: Permission):
    """
    Décorateur pour exiger une permission spécifique sur un endpoint.
    
    Vérifie que l'utilisateur authentifié possède la permission requise
    avant d'autoriser l'accès à l'endpoint. Combine authentification
    et autorisation en une seule vérification.
    
    Args:
        required_permission: Permission requise pour accéder à l'endpoint
        
    Returns:
        Callable: Décorateur de fonction
        
    Raises:
        HTTPException: 401 si non authentifié, 403 si permission insuffisante
        
    Example:
        @router.post("/vectors")
        @require_permission(Permission.VECTORS_CREATE)
        async def create_vector(
            vector_data: VectorCreate,
            current_user: TokenData = Depends(get_current_user)
        ):
            # L'utilisateur est authentifié ET a la permission vectors:create
            return await vector_service.create_vector(vector_data)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extraire current_user des arguments ou kwargs
            current_user = None
            
            # Chercher dans kwargs d'abord
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            
            # Si pas trouvé, chercher dans args (moins fiable)
            if not current_user:
                for arg in args:
                    if isinstance(arg, TokenData):
                        current_user = arg
                        break
            
            # Vérifier authentification
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Vérifier permission
            if not security_service.has_permission(current_user.permissions, required_permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission '{required_permission.value}' required"
                )
            
            # Autoriser l'accès
            return await func(*args, **kwargs)
            
        return wrapper
    return decorator


def require_role(required_role: UserRole):
    """
    Décorateur pour exiger un rôle minimum sur un endpoint.
    
    Vérifie que l'utilisateur a le rôle requis ou supérieur selon
    la hiérarchie : ADMIN > MANAGER > USER > READONLY
    
    Args:
        required_role: Rôle minimum requis
        
    Returns:
        Callable: Décorateur de fonction
        
    Example:
        @router.delete("/users/{user_id}")
        @require_role(UserRole.ADMIN)
        async def delete_user(
            user_id: int,
            current_user: TokenData = Depends(get_current_user)
        ):
            # Seuls les admins peuvent supprimer des utilisateurs
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            
            if not current_user:
                raise HTTPException(401, "Authentication required")
            
            if not security_service.has_role_or_higher(current_user.role, required_role):
                raise HTTPException(
                    status_code=403,
                    detail=f"Role '{required_role.value}' or higher required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware de limitation de débit par utilisateur/IP pour prévenir les abus.
    
    Implémente un rate limiting basique en mémoire pour protéger contre
    les attaques par déni de service et l'usage abusif de l'API.
    En production, utiliser Redis pour le stockage distribué.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        """
        Initialiser le rate limiter.
        
        Args:
            app: Application FastAPI
            requests_per_minute: Limite de requêtes par minute par utilisateur/IP
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # En production : utiliser Redis
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Appliquer la limitation de débit.
        
        Args:
            request: Requête HTTP
            call_next: Pipeline suivant
            
        Returns:
            Response: Réponse HTTP ou erreur 429 si limite dépassée
        """
        # Identifier l'utilisateur (par token) ou IP
        identifier = self._get_identifier(request)
        
        # Vérifier et mettre à jour le compteur
        if not self._check_rate_limit(identifier):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
                headers={"Retry-After": "60"}
            )
        
        return await call_next(request)
    
    def _get_identifier(self, request: Request) -> str:
        """Obtenir l'identifiant unique pour rate limiting."""
        # Priorité : user_id > IP address
        if hasattr(request.state, 'user') and request.state.user:
            return f"user_{request.state.user.user_id}"
        
        # Fallback sur l'IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip_{client_ip}"
    
    def _check_rate_limit(self, identifier: str) -> bool:
        """Vérifier et mettre à jour le compteur de requêtes."""
        now = time.time()
        window_start = now - 60  # Fenêtre de 1 minute
        
        # Nettoyer les entrées expirées
        if identifier in self.request_counts:
            self.request_counts[identifier] = [
                timestamp for timestamp in self.request_counts[identifier]
                if timestamp > window_start
            ]
        else:
            self.request_counts[identifier] = []
        
        # Vérifier la limite
        if len(self.request_counts[identifier]) >= self.requests_per_minute:
            return False
        
        # Ajouter cette requête
        self.request_counts[identifier].append(now)
        return True


# Utilities pour protection des endpoints

def protect_endpoint(permission: Optional[Permission] = None, role: Optional[UserRole] = None):
    """
    Décorateur combiné pour authentification + autorisation.
    
    Args:
        permission: Permission optionnelle requise
        role: Rôle minimum optionnel requis
        
    Example:
        @router.get("/admin/users")
        @protect_endpoint(role=UserRole.ADMIN)
        async def list_all_users(current_user: TokenData = Depends(get_current_user)):
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            
            if not current_user:
                raise HTTPException(401, "Authentication required")
            
            # Vérifier rôle si spécifié
            if role and not security_service.has_role_or_higher(current_user.role, role):
                raise HTTPException(403, f"Role '{role.value}' required")
            
            # Vérifier permission si spécifiée
            if permission and not security_service.has_permission(current_user.permissions, permission):
                raise HTTPException(403, f"Permission '{permission.value}' required")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
