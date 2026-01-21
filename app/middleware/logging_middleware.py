"""
Middleware de logging FastAPI pour AindusDB Core avec contexte enrichi et tracing.

Ce middleware capture automatiquement toutes les requêtes HTTP avec :
- Génération d'ID de requête unique pour tracing
- Injection du contexte utilisateur depuis JWT
- Logging des performances (latence, taille payload)
- Gestion des erreurs avec stack traces
- Corrélation distribué pour microservices

Example:
    from app.middleware.logging_middleware import LoggingMiddleware
    
    app = FastAPI()
    app.add_middleware(LoggingMiddleware, 
                      log_requests=True,
                      log_responses=True,
                      include_sensitive_headers=False)
"""

import time
import uuid
import json
import asyncio
from typing import Callable, Optional, Dict, Any, List
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from ..core.logging import get_logger, setup_request_context, LogContext, request_id_var
from ..core.security import security_service
from ..models.auth import TokenData


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware de logging automatique pour toutes les requêtes FastAPI.
    
    Capture et log toutes les requêtes HTTP entrants avec contexte enrichi :
    - ID de requête unique pour tracing distribué
    - Informations utilisateur depuis JWT (si authentifié)
    - Métriques de performance (latence, taille payload)
    - Headers et body (configurable pour sécurité)
    - Gestion d'erreurs avec logging structuré
    
    Features:
    - Logging JSON structuré pour agrégation
    - Corrélation ID pour tracing multi-services
    - Sanitisation automatique des données sensibles
    - Rate limiting pour éviter spam logs
    - Métriques de santé et monitoring
    
    Attributes:
        log_requests: Activer logging des requêtes entrantes
        log_responses: Activer logging des réponses
        include_request_body: Logger le body des requêtes (attention données sensibles)
        include_response_body: Logger le body des réponses
        include_headers: Logger les headers HTTP
        max_body_size: Taille max du body à logger (bytes)
        sensitive_headers: Headers à masquer dans les logs
        exclude_paths: Chemins à exclure du logging (health checks)
        
    Example:
        # Configuration production sécurisée
        app.add_middleware(LoggingMiddleware,
                          log_requests=True,
                          log_responses=True,
                          include_request_body=False,  # Sécurité
                          include_headers=True,
                          exclude_paths=["/health", "/metrics", "/docs"])
    """
    
    def __init__(self,
                 app: FastAPI,
                 log_requests: bool = True,
                 log_responses: bool = True,
                 include_request_body: bool = False,
                 include_response_body: bool = False,
                 include_headers: bool = True,
                 max_body_size: int = 65536,  # 64KB
                 sensitive_headers: Optional[List[str]] = None,
                 exclude_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.include_request_body = include_request_body
        self.include_response_body = include_response_body
        self.include_headers = include_headers
        self.max_body_size = max_body_size
        
        self.sensitive_headers = sensitive_headers or [
            "authorization", "x-api-key", "cookie", "set-cookie",
            "x-auth-token", "x-access-token", "x-refresh-token"
        ]
        
        self.exclude_paths = set(exclude_paths or [
            "/health", "/healthcheck", "/metrics", "/favicon.ico",
            "/docs", "/redoc", "/openapi.json"
        ])
        
        self.logger = get_logger("aindusdb.middleware.logging")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Traiter une requête HTTP avec logging complet.
        
        Args:
            request: Requête FastAPI
            call_next: Fonction suivante dans la chaîne middleware
            
        Returns:
            Response: Réponse HTTP avec headers de tracing ajoutés
        """
        # Générer ID unique pour cette requête
        request_id = self._generate_request_id()
        correlation_id = request.headers.get("x-correlation-id", request_id)
        
        # Configurer contexte logging
        setup_request_context(request_id)
        
        # Vérifier si path exclu
        if request.url.path in self.exclude_paths:
            response = await call_next(request)
            self._add_trace_headers(response, request_id, correlation_id)
            return response
        
        # Extraire informations utilisateur si authentifié
        user_data = await self._extract_user_context(request)
        user_id = user_data.get("user_id") if user_data else None
        username = user_data.get("username") if user_data else None
        
        # Timestamp de début
        start_time = time.time()
        start_datetime = datetime.now(timezone.utc)
        
        # Logger requête entrante
        if self.log_requests:
            await self._log_request(request, request_id, correlation_id, user_data, start_datetime)
        
        # Traiter la requête avec contexte
        response = None
        error = None
        
        try:
            with LogContext(request_id=request_id, 
                          user_id=user_id,
                          correlation_id=correlation_id,
                          operation=f"{request.method} {request.url.path}"):
                
                response = await call_next(request)
                
        except Exception as e:
            error = e
            self.logger.error("Request processing failed",
                            extra={
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                                "request_method": request.method,
                                "request_path": request.url.path,
                                "user_id": user_id,
                                "username": username
                            }, exc_info=True)
            raise
        
        finally:
            # Calculer métriques de performance
            duration_ms = (time.time() - start_time) * 1000
            
            # Logger réponse
            if self.log_responses and response:
                await self._log_response(request, response, duration_ms, 
                                       request_id, correlation_id, user_data)
            
            # Ajouter headers de tracing
            if response:
                self._add_trace_headers(response, request_id, correlation_id)
        
        return response
    
    def _generate_request_id(self) -> str:
        """Générer ID unique pour requête."""
        return f"req_{uuid.uuid4().hex[:12]}"
    
    async def _extract_user_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extraire contexte utilisateur depuis JWT.
        
        Args:
            request: Requête FastAPI
            
        Returns:
            Optional[Dict]: Données utilisateur ou None
        """
        try:
            # Récupérer token depuis header Authorization
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header[7:]  # Supprimer "Bearer "
            
            # Valider et décoder token
            payload = await security_service.verify_access_token(token)
            if not payload:
                return None
            
            return {
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "role": payload.get("role"),
                "permissions": payload.get("permissions", [])[:5]  # Limiter pour taille log
            }
            
        except Exception as e:
            # Ne pas faire échouer la requête pour erreur d'extraction contexte
            self.logger.debug("Failed to extract user context", extra={"error": str(e)})
            return None
    
    async def _log_request(self,
                          request: Request,
                          request_id: str,
                          correlation_id: str,
                          user_data: Optional[Dict[str, Any]],
                          timestamp: datetime):
        """Logger une requête entrante."""
        log_data = {
            "event_type": "http_request",
            "request_id": request_id,
            "correlation_id": correlation_id,
            "timestamp": timestamp.isoformat(),
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length")
        }
        
        # Ajouter contexte utilisateur
        if user_data:
            log_data["user"] = user_data
        
        # Ajouter headers si configuré
        if self.include_headers:
            log_data["headers"] = self._sanitize_headers(dict(request.headers))
        
        # Ajouter body si configuré (attention sécurité)
        if self.include_request_body and request.method in ["POST", "PUT", "PATCH"]:
            body = await self._read_request_body(request)
            if body:
                log_data["request_body"] = body
        
        self.logger.info("HTTP request received", extra=log_data)
    
    async def _log_response(self,
                           request: Request,
                           response: Response,
                           duration_ms: float,
                           request_id: str,
                           correlation_id: str,
                           user_data: Optional[Dict[str, Any]]):
        """Logger une réponse sortante."""
        log_data = {
            "event_type": "http_response",
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "response_size": len(response.body) if hasattr(response, 'body') else None
        }
        
        # Ajouter contexte utilisateur
        if user_data:
            log_data["user_id"] = user_data.get("user_id")
            log_data["username"] = user_data.get("username")
        
        # Ajouter headers de réponse si configuré
        if self.include_headers:
            log_data["response_headers"] = dict(response.headers)
        
        # Ajouter body de réponse si configuré
        if self.include_response_body and hasattr(response, 'body'):
            if len(response.body) <= self.max_body_size:
                try:
                    log_data["response_body"] = response.body.decode('utf-8')
                except UnicodeDecodeError:
                    log_data["response_body"] = "[Binary content]"
        
        # Déterminer niveau de log selon status
        if response.status_code >= 500:
            level = "error"
        elif response.status_code >= 400:
            level = "warning"
        elif duration_ms > 5000:  # Réponse lente
            level = "warning"
        else:
            level = "info"
        
        getattr(self.logger, level)("HTTP response sent", extra=log_data)
    
    def _get_client_ip(self, request: Request) -> str:
        """Obtenir IP client en gérant proxies/load balancers."""
        # Vérifier headers de proxy dans l'ordre de priorité
        forwarded_headers = [
            "x-forwarded-for",
            "x-real-ip", 
            "x-client-ip",
            "cf-connecting-ip"  # Cloudflare
        ]
        
        for header in forwarded_headers:
            if header in request.headers:
                # X-Forwarded-For peut contenir plusieurs IPs
                ip = request.headers[header].split(',')[0].strip()
                if ip and ip != "unknown":
                    return ip
        
        # Fallback sur IP de connexion directe
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Masquer headers sensibles pour sécurité."""
        sanitized = {}
        
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in self.sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    async def _read_request_body(self, request: Request) -> Optional[str]:
        """
        Lire body de requête de manière sécurisée.
        
        Args:
            request: Requête FastAPI
            
        Returns:
            Optional[str]: Body de requête ou None
        """
        try:
            # Vérifier taille pour éviter OOM
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_body_size:
                return f"[Body too large: {content_length} bytes]"
            
            # Lire body
            body_bytes = await request.body()
            
            if len(body_bytes) == 0:
                return None
            
            if len(body_bytes) > self.max_body_size:
                return f"[Body truncated: {len(body_bytes)} bytes]"
            
            # Décoder en UTF-8
            body_str = body_bytes.decode('utf-8')
            
            # Essayer de parser en JSON pour vérification
            try:
                json.loads(body_str)
                # JSON valide, on peut le retourner tel quel
                return body_str
            except json.JSONDecodeError:
                # Pas du JSON, retourner tel quel mais tronqué si trop long
                if len(body_str) > 1000:
                    return body_str[:1000] + "...[truncated]"
                return body_str
                
        except UnicodeDecodeError:
            return "[Binary content]"
        except Exception as e:
            return f"[Error reading body: {str(e)}]"
    
    def _add_trace_headers(self, response: Response, request_id: str, correlation_id: str):
        """Ajouter headers de tracing à la réponse."""
        response.headers["x-request-id"] = request_id
        response.headers["x-correlation-id"] = correlation_id
        response.headers["x-served-by"] = "aindusdb-core"


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour mesurer et logger les temps de réponse détaillés.
    
    Complément au LoggingMiddleware pour analyse fine des performances :
    - Timing par étape (auth, business logic, db, etc.)
    - Détection des goulots d'étranglement
    - Métriques pour alerting sur latence
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.logger = get_logger("aindusdb.middleware.timing")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Mesurer timing détaillé de la requête."""
        timings = {}
        
        # Timestamp global
        start_time = time.perf_counter()
        timings["start"] = start_time
        
        # Traiter requête
        response = await call_next(request)
        
        # Timestamp final
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Logger métriques de timing
        self.logger.info("Request timing metrics", extra={
            "event_type": "request_timing",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "total_time_ms": round(total_time_ms, 2),
            "timings": timings
        })
        
        # Ajouter header de timing
        response.headers["x-response-time"] = f"{total_time_ms:.2f}ms"
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour capture et logging centralisé des erreurs.
    
    Capture toutes les exceptions non gérées avec :
    - Stack trace complet pour debugging
    - Contexte de requête pour reproduction
    - Classification par type d'erreur
    - Réponse JSON structurée pour clients
    """
    
    def __init__(self, app: FastAPI, include_stacktrace: bool = False):
        super().__init__(app)
        self.include_stacktrace = include_stacktrace
        self.logger = get_logger("aindusdb.middleware.errors")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Gérer les erreurs avec logging complet."""
        try:
            return await call_next(request)
            
        except Exception as e:
            # Logger erreur avec contexte complet
            request_id = request_id_var.get() or "unknown"
            
            error_data = {
                "event_type": "unhandled_exception",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": request.client.host if request.client else "unknown"
            }
            
            self.logger.error("Unhandled exception in request processing",
                            extra=error_data, exc_info=True)
            
            # Retourner réponse JSON d'erreur
            error_response = {
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "request_id": request_id
            }
            
            if self.include_stacktrace:
                import traceback
                error_response["stacktrace"] = traceback.format_exc()
            
            return Response(
                content=json.dumps(error_response),
                status_code=500,
                media_type="application/json"
            )
