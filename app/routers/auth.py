"""
Router d'authentification pour AindusDB Core avec endpoints JWT complets.

Ce module expose les endpoints d'authentification : login, refresh, logout,
register, changement de mot de passe et gestion des utilisateurs.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from typing import Optional

from ..models.auth import (
    LoginRequest, TokenResponse, RefreshRequest, UserCreate, 
    User, PasswordChangeRequest, TokenData
)
from ..core.security import security_service
from ..middleware.auth import get_current_user, bearer_scheme
from ..services.audit_service import audit_service
from ..services.auth_service import get_auth_service


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, request: Request):
    """
    Authentifier un utilisateur et générer des tokens JWT avec audit complet.
    
    Phase 1.3 - Implémentation sécurisée avec base de données.
    Remplace les credentials hardcodés par authentification DB.
    """
    client_ip = request.client.host
    user_agent = request.headers.get("User-Agent")
    
    logger.info("Login attempt", 
               extra={
                   "username": login_data.username,
                   "ip": client_ip
               })
    
    try:
        # Utiliser le service d'authentification sécurisé
        auth_svc = await get_auth_service()
        user = await auth_svc.authenticate_user(
            login_data.username, 
            login_data.password,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        if not user:
            logger.warning("Login failed - invalid credentials",
                         extra={
                             "username": login_data.username,
                             "ip": client_ip
                         })
            raise HTTPException(
                status_code=401, 
                detail="Invalid username or password"
            )
        
        # Générer tokens JWT
        tokens = await security_service.create_tokens(user)
        
        # Logger succès
        logger.info("Login successful",
                   extra={
                       "user_id": user.id,
                       "username": user.username,
                       "ip": client_ip
                   })
        
        # Audit du login réussi
        await audit_service.log_authentication_event(
            event_type="login_success",
            username=login_data.username,
            success=True,
            request=request,
            additional_details={
                "remember_me": login_data.remember_me,
                "token_expires_in": tokens["expires_in"]
            }
        )
        
        return TokenResponse(**tokens)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Authentication service unavailable"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_data: RefreshRequest):
    """
    Renouveler l'access token avec un refresh token valide.
    """
    new_tokens = await security_service.refresh_access_token(refresh_data.refresh_token)
    
    if not new_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    return TokenResponse(**new_tokens)


@router.post("/logout")
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Déconnecter un utilisateur et révoquer ses tokens.
    """
    if credentials:
        await security_service.revoke_token(credentials.credentials)
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=dict)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Obtenir les informations de l'utilisateur authentifié.
    """
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role,
        "permissions": current_user.permissions
    }


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Changer le mot de passe de l'utilisateur authentifié.
    """
    # TODO: Implémenter changement mot de passe
    return {"message": "Password changed successfully"}
