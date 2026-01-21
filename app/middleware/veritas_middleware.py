"""
Middleware VERITAS pour détection et traitement du protocole de vérification.

Ce middleware détecte les requêtes demandant une vérification VERITAS et configure
le contexte approprié pour le traitement avec preuves et traçabilité.

Example:
    from app.middleware.veritas_middleware import VeritasMiddleware
    
    app = FastAPI()
    app.add_middleware(VeritasMiddleware)
    
    # Requête client avec header X-Aindus-Veritas: true
    # Active automatiquement le mode vérification
"""

import time
import asyncio
from typing import Callable, Optional, Dict, Any
from contextlib import contextmanager

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.logging import get_logger, LogContext
from ..core.metrics import metrics_service
from ..models.veritas import VerificationAudit
from ..services.audit_service import audit_service


class VeritasMiddleware(BaseHTTPMiddleware):
    """
    Middleware de détection et configuration du protocole VERITAS.
    
    Détecte automatiquement les requêtes nécessitant une vérification VERITAS
    via le header HTTP 'X-Aindus-Veritas' et configure le contexte approprié.
    
    Features:
    - Détection header X-Aindus-Veritas pour activation mode vérification
    - Configuration contexte de traçabilité enrichi
    - Audit automatique des sessions de vérification
    - Métriques spécifiques VERITAS
    - Injection metadata pour services downstream
    - Validation des réponses VERITAS-compatible
    
    Attributes:
        enable_audit: Activer audit automatique des sessions VERITAS
        enable_metrics: Collecter métriques spécifiques VERITAS
        max_verification_time_ms: Timeout max pour vérifications
        
    Example:
        # Configuration production
        app.add_middleware(VeritasMiddleware,
                          enable_audit=True,
                          enable_metrics=True,
                          max_verification_time_ms=30000)
                          
        # Requête client
        headers = {"X-Aindus-Veritas": "true"}
        response = requests.post("/search", headers=headers, json=query)
    """
    
    def __init__(self,
                 app: FastAPI,
                 enable_audit: bool = True,
                 enable_metrics: bool = True,
                 max_verification_time_ms: int = 30000):
        super().__init__(app)
        
        self.enable_audit = enable_audit
        self.enable_metrics = enable_metrics
        self.max_verification_time_ms = max_verification_time_ms
        
        self.logger = get_logger("aindusdb.middleware.veritas")
        
        # Compteur de sessions VERITAS
        self._active_verifications = 0
        self._verification_stats = {
            "total_requests": 0,
            "veritas_requests": 0,
            "successful_verifications": 0,
            "failed_verifications": 0
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Traiter requête avec détection et configuration VERITAS.
        
        Args:
            request: Requête FastAPI
            call_next: Fonction suivante dans la chaîne
            
        Returns:
            Response: Réponse avec métadonnées VERITAS
        """
        # Incrémenter statistiques globales
        self._verification_stats["total_requests"] += 1
        
        # Détecter mode VERITAS
        veritas_mode = self._detect_veritas_mode(request)
        verification_id = None
        start_time = time.time()
        
        # Configurer contexte si mode VERITAS activé
        if veritas_mode:
            verification_id = self._generate_verification_id()
            self._verification_stats["veritas_requests"] += 1
            self._active_verifications += 1
            
            # Configurer état requête
            request.state.veritas_mode = True
            request.state.verification_id = verification_id
            request.state.verification_start = start_time
            
            self.logger.info("VERITAS mode activated",
                           extra={
                               "verification_id": verification_id,
                               "request_path": request.url.path,
                               "user_agent": request.headers.get("user-agent", "unknown")
                           })
        else:
            request.state.veritas_mode = False
        
        # Variables pour audit
        success = True
        error_details = None
        response = None
        
        try:
            # Traiter requête avec contexte enrichi
            with self._verification_context(verification_id, veritas_mode):
                response = await call_next(request)
                
                # Valider réponse VERITAS si mode activé
                if veritas_mode:
                    await self._validate_veritas_response(request, response)
            
        except Exception as e:
            success = False
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "verification_failed": True
            }
            
            self.logger.error("VERITAS verification failed",
                            extra={
                                "verification_id": verification_id,
                                "error": str(e)
                            }, exc_info=True)
            raise
            
        finally:
            # Calculs finaux
            verification_time_ms = int((time.time() - start_time) * 1000)
            
            # Audit si mode VERITAS
            if veritas_mode and self.enable_audit:
                await self._audit_verification_session(
                    request, verification_id, success, 
                    verification_time_ms, error_details
                )
            
            # Métriques
            if self.enable_metrics:
                await self._record_veritas_metrics(
                    request, veritas_mode, success, verification_time_ms
                )
            
            # Nettoyer état
            if veritas_mode:
                self._active_verifications = max(0, self._active_verifications - 1)
                if success:
                    self._verification_stats["successful_verifications"] += 1
                else:
                    self._verification_stats["failed_verifications"] += 1
            
            # Ajouter headers de réponse
            if response:
                self._add_veritas_headers(response, veritas_mode, verification_id, verification_time_ms)
        
        return response
    
    def _detect_veritas_mode(self, request: Request) -> bool:
        """
        Détecter si la requête demande le mode VERITAS.
        
        Args:
            request: Requête FastAPI
            
        Returns:
            bool: True si mode VERITAS activé
        """
        # Header principal X-Aindus-Veritas
        veritas_header = request.headers.get("x-aindus-veritas", "").lower()
        if veritas_header in ["true", "1", "on", "enabled"]:
            return True
        
        # Header alternatif X-Veritas-Mode (pour compatibilité)
        veritas_mode_header = request.headers.get("x-veritas-mode", "").lower()
        if veritas_mode_header in ["true", "1", "on", "enabled"]:
            return True
        
        # Paramètre query string veritas=true
        veritas_param = request.query_params.get("veritas", "").lower()
        if veritas_param in ["true", "1", "on", "enabled"]:
            return True
        
        # Détection automatique pour certains endpoints
        path = request.url.path
        auto_veritas_paths = [
            "/api/v1/rag/verify",
            "/api/v1/calculations/verify", 
            "/api/v1/proofs/generate"
        ]
        
        if any(path.startswith(auto_path) for auto_path in auto_veritas_paths):
            return True
        
        return False
    
    def _generate_verification_id(self) -> str:
        """Générer ID unique de vérification."""
        import uuid
        return f"veritas_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    @contextmanager
    def _verification_context(self, verification_id: Optional[str], veritas_mode: bool):
        """
        Context manager pour enrichissement du contexte de logging.
        
        Args:
            verification_id: ID de vérification
            veritas_mode: Mode VERITAS activé
        """
        if veritas_mode and verification_id:
            # Enrichir contexte de logging avec données VERITAS
            with LogContext(
                verification_id=verification_id,
                veritas_mode=True,
                operation="veritas_verification"
            ):
                yield
        else:
            yield
    
    async def _validate_veritas_response(self, request: Request, response: Response):
        """
        Valider qu'une réponse est conforme au protocole VERITAS.
        
        Args:
            request: Requête originale
            response: Réponse à valider
        """
        # Vérifier content-type JSON pour validation
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return  # Pas de validation pour non-JSON
        
        # TODO: Valider structure de réponse VERITAS si nécessaire
        # Nécessiterait de parser le body JSON et vérifier présence des champs requis
        
        verification_id = getattr(request.state, 'verification_id', None)
        self.logger.debug("VERITAS response validated",
                         extra={
                             "verification_id": verification_id,
                             "status_code": response.status_code,
                             "content_type": content_type
                         })
    
    async def _audit_verification_session(self,
                                        request: Request,
                                        verification_id: str,
                                        success: bool,
                                        verification_time_ms: int,
                                        error_details: Optional[Dict[str, Any]]):
        """Auditer une session de vérification VERITAS."""
        try:
            # Extraire informations de la requête
            user_id = getattr(request.state, 'user_id', None)
            
            # Créer enregistrement d'audit
            audit_data = {
                "request_id": verification_id,
                "user_id": user_id,
                "verification_type": "full_veritas" if success else "failed_verification",
                "input_query": f"{request.method} {request.url.path}",
                "documents_used": [],  # TODO: extraire des services downstream
                "final_confidence": None,  # TODO: extraire de la réponse
                "success": success,
                "verification_time_ms": verification_time_ms,
                "error_details": error_details,
                "veritas_version": "1.0"
            }
            
            # Enregistrer via service d'audit
            await audit_service.log_security_event(
                user_id=user_id,
                event_type="veritas_verification",
                resource="veritas_session",
                details=audit_data,
                level="info" if success else "warning"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to audit VERITAS session: {e}")
    
    async def _record_veritas_metrics(self,
                                    request: Request,
                                    veritas_mode: bool,
                                    success: bool,
                                    verification_time_ms: int):
        """Enregistrer métriques VERITAS."""
        try:
            # Métriques de base
            if veritas_mode:
                # Compteur de requêtes VERITAS
                metrics_service.increment_counter(
                    "aindusdb_veritas_requests_total",
                    {
                        "endpoint": request.url.path,
                        "method": request.method,
                        "status": "success" if success else "failed"
                    }
                )
                
                # Latence des vérifications
                metrics_service.observe_histogram(
                    "aindusdb_veritas_verification_duration_seconds",
                    verification_time_ms / 1000.0,
                    {
                        "endpoint": request.url.path,
                        "status": "success" if success else "failed"
                    }
                )
                
                # Gauge des vérifications actives
                metrics_service.set_gauge(
                    "aindusdb_veritas_active_verifications",
                    self._active_verifications
                )
            
        except Exception as e:
            self.logger.error(f"Failed to record VERITAS metrics: {e}")
    
    def _add_veritas_headers(self,
                           response: Response,
                           veritas_mode: bool,
                           verification_id: Optional[str],
                           verification_time_ms: int):
        """Ajouter headers VERITAS à la réponse."""
        if veritas_mode and verification_id:
            response.headers["X-Veritas-Enabled"] = "true"
            response.headers["X-Verification-ID"] = verification_id
            response.headers["X-Verification-Time"] = f"{verification_time_ms}ms"
            response.headers["X-Veritas-Version"] = "1.0"
        else:
            response.headers["X-Veritas-Enabled"] = "false"
        
        # Header pour statistiques (debug)
        response.headers["X-Veritas-Stats"] = (
            f"total:{self._verification_stats['total_requests']},"
            f"veritas:{self._verification_stats['veritas_requests']},"
            f"success:{self._verification_stats['successful_verifications']}"
        )
    
    def get_verification_stats(self) -> Dict[str, Any]:
        """Obtenir statistiques des vérifications."""
        return {
            **self._verification_stats,
            "active_verifications": self._active_verifications,
            "success_rate": (
                self._verification_stats["successful_verifications"] / 
                max(self._verification_stats["veritas_requests"], 1)
            ),
            "veritas_adoption_rate": (
                self._verification_stats["veritas_requests"] /
                max(self._verification_stats["total_requests"], 1)
            )
        }


class VeritasResponseMiddleware(BaseHTTPMiddleware):
    """
    Middleware de post-traitement des réponses VERITAS.
    
    Applique des transformations et validations sur les réponses
    pour assurer la conformité au protocole VERITAS.
    """
    
    def __init__(self, app: FastAPI, strict_validation: bool = False):
        super().__init__(app)
        self.strict_validation = strict_validation
        self.logger = get_logger("aindusdb.middleware.veritas_response")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Post-traiter les réponses VERITAS."""
        response = await call_next(request)
        
        # Vérifier si mode VERITAS activé
        veritas_mode = getattr(request.state, 'veritas_mode', False)
        
        if veritas_mode:
            await self._post_process_veritas_response(request, response)
        
        return response
    
    async def _post_process_veritas_response(self, request: Request, response: Response):
        """Post-traiter une réponse VERITAS."""
        try:
            verification_id = getattr(request.state, 'verification_id', None)
            
            # Log du post-traitement
            self.logger.debug("Post-processing VERITAS response",
                            extra={
                                "verification_id": verification_id,
                                "status_code": response.status_code,
                                "content_length": len(response.body) if hasattr(response, 'body') else 0
                            })
            
            # TODO: Transformations spécifiques VERITAS
            # - Validation format VeritasReadyResponse
            # - Enrichissement métadonnées
            # - Calcul scores de confiance finaux
            
        except Exception as e:
            self.logger.error(f"Error in VERITAS response post-processing: {e}")


class VeritasContextManager:
    """
    Gestionnaire de contexte global pour sessions VERITAS.
    
    Fournit un accès centralisé aux données de contexte VERITAS
    pour tous les services de l'application.
    """
    
    def __init__(self):
        self._contexts: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger("aindusdb.middleware.veritas_context")
    
    def create_context(self, verification_id: str, **kwargs) -> None:
        """Créer un nouveau contexte VERITAS."""
        self._contexts[verification_id] = {
            "verification_id": verification_id,
            "created_at": time.time(),
            **kwargs
        }
        
        self.logger.debug(f"Created VERITAS context: {verification_id}")
    
    def get_context(self, verification_id: str) -> Optional[Dict[str, Any]]:
        """Obtenir un contexte VERITAS."""
        return self._contexts.get(verification_id)
    
    def update_context(self, verification_id: str, **kwargs) -> None:
        """Mettre à jour un contexte VERITAS."""
        if verification_id in self._contexts:
            self._contexts[verification_id].update(kwargs)
    
    def remove_context(self, verification_id: str) -> None:
        """Supprimer un contexte VERITAS."""
        if verification_id in self._contexts:
            del self._contexts[verification_id]
            self.logger.debug(f"Removed VERITAS context: {verification_id}")
    
    def cleanup_expired_contexts(self, max_age_seconds: int = 3600) -> None:
        """Nettoyer les contextes expirés."""
        current_time = time.time()
        expired_ids = [
            vid for vid, context in self._contexts.items()
            if current_time - context.get("created_at", 0) > max_age_seconds
        ]
        
        for vid in expired_ids:
            self.remove_context(vid)
        
        if expired_ids:
            self.logger.info(f"Cleaned up {len(expired_ids)} expired VERITAS contexts")


# Instance globale du gestionnaire de contexte
veritas_context_manager = VeritasContextManager()
