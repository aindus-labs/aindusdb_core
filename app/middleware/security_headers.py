"""
Security Headers Middleware pour AindusDB Core - Protection Enterprise.

Ce middleware implémente les headers de sécurité essentiels conformément aux 
standards OWASP et entreprise pour protéger contre les attaques communes :
CSRF, XSS, clickjacking, content sniffing, mixed content.

Features:
- HSTS (HTTP Strict Transport Security)
- CSP (Content Security Policy)  
- X-Frame-Options (Clickjacking protection)
- X-Content-Type-Options (MIME sniffing)
- X-XSS-Protection (XSS filtering)
- Referrer-Policy (Privacy protection)
- Permissions-Policy (Feature control)

Example:
    from app.middleware.security_headers import SecurityHeadersMiddleware
    
    app.add_middleware(SecurityHeadersMiddleware)
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time

from ..core.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware de sécurité pour headers enterprise avec protection OWASP.
    
    Implémente automatiquement tous les headers de sécurité critiques
    pour protéger l'application contre les attaques web communes.
    Configurable selon l'environnement (dev, staging, production).
    
    Headers implémentés:
    - Strict-Transport-Security: Force HTTPS pendant 1 an
    - Content-Security-Policy: Politique stricte anti-XSS
    - X-Frame-Options: Protection clickjacking
    - X-Content-Type-Options: Prévention MIME confusion
    - X-XSS-Protection: Filtrage XSS navigateur
    - Referrer-Policy: Contrôle informations référent
    - Permissions-Policy: Restriction APIs sensibles
    - Cache-Control: Contrôle cache sensible
    
    Attributes:
        environment: Environnement cible (dev, prod)
        enable_csp: Activer Content Security Policy
        enable_hsts: Activer HTTP Strict Transport Security
        
    Example:
        # Configuration production maximale
        app.add_middleware(
            SecurityHeadersMiddleware,
            environment="production",
            enable_csp=True,
            enable_hsts=True
        )
    """
    
    def __init__(
        self,
        app,
        environment: str = "production",
        enable_csp: bool = True,
        enable_hsts: bool = True,
        csp_report_uri: str = None
    ):
        """
        Initialiser le middleware de sécurité.
        
        Args:
            app: Application FastAPI
            environment: Environment (dev, staging, production)
            enable_csp: Activer Content Security Policy
            enable_hsts: Activer HSTS pour HTTPS forcé
            csp_report_uri: URI pour rapports CSP violations
        """
        super().__init__(app)
        self.environment = environment
        self.enable_csp = enable_csp
        self.enable_hsts = enable_hsts
        self.csp_report_uri = csp_report_uri
        
        # Métriques sécurité
        self.requests_processed = 0
        self.csp_violations = 0
        
        logger.info(f"SecurityHeadersMiddleware initialized for {environment}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Traiter la requête et ajouter les headers de sécurité.
        
        Args:
            request: Requête HTTP entrante
            call_next: Handler suivant dans la chaîne
            
        Returns:
            Response: Réponse avec headers sécurisés
        """
        start_time = time.time()
        
        # Traiter la requête
        response = await call_next(request)
        
        # Ajouter headers de sécurité selon environnement
        await self._add_security_headers(request, response)
        
        # Métriques
        self.requests_processed += 1
        processing_time = (time.time() - start_time) * 1000
        
        if processing_time > 100:  # Log si > 100ms
            logger.warning(f"Slow security headers processing: {processing_time:.1f}ms")
        
        return response
    
    async def _add_security_headers(self, request: Request, response: Response):
        """
        Ajouter tous les headers de sécurité appropriés.
        
        Args:
            request: Requête originale
            response: Réponse à enrichir
        """
        
        # 1. HSTS - Force HTTPS pendant 1 an (production uniquement)
        if self.enable_hsts and self.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # 2. Content Security Policy - Protection XSS stricte
        if self.enable_csp:
            csp_policy = self._build_csp_policy()
            response.headers["Content-Security-Policy"] = csp_policy
        
        # 3. X-Frame-Options - Protection clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # 4. X-Content-Type-Options - Prévention MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # 5. X-XSS-Protection - Activer filtrage XSS navigateur
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # 6. Referrer-Policy - Limiter informations référent
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 7. Permissions-Policy - Restreindre APIs dangereuses
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )
        
        # 8. Cache-Control pour endpoints sensibles
        if self._is_sensitive_endpoint(request.url.path):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, proxy-revalidate"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # 9. Server header - Masquer informations serveur
        response.headers["Server"] = "AindusDB-Core"
        
        # 10. Cross-Origin headers pour API
        if request.url.path.startswith("/api/"):
            response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # 11. Headers développement (dev uniquement)
        if self.environment == "development":
            response.headers["X-Debug-Environment"] = "development"
    
    def _build_csp_policy(self) -> str:
        """
        Construire politique Content Security Policy stricte.
        
        Returns:
            str: Politique CSP complète
        """
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",  # FastAPI docs nécessitent unsafe-inline
            "style-src 'self' 'unsafe-inline' fonts.googleapis.com",
            "font-src 'self' fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "object-src 'none'",
        ]
        
        # Ajouter report-uri si configuré
        if self.csp_report_uri:
            csp_directives.append(f"report-uri {self.csp_report_uri}")
        
        # Production : CSP plus strict
        if self.environment == "production":
            csp_directives.append("upgrade-insecure-requests")
        
        return "; ".join(csp_directives)
    
    def _is_sensitive_endpoint(self, path: str) -> bool:
        """
        Vérifier si l'endpoint est sensible (auth, admin, etc.).
        
        Args:
            path: Chemin URL de la requête
            
        Returns:
            bool: True si endpoint sensible
        """
        sensitive_patterns = [
            "/auth/",
            "/admin/",
            "/api/v1/security/",
            "/api/v1/users/",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        
        return any(pattern in path for pattern in sensitive_patterns)
    
    def get_metrics(self) -> dict:
        """
        Obtenir les métriques du middleware sécurité.
        
        Returns:
            dict: Métriques de sécurité
        """
        return {
            "requests_processed": self.requests_processed,
            "csp_violations": self.csp_violations,
            "environment": self.environment,
            "csp_enabled": self.enable_csp,
            "hsts_enabled": self.enable_hsts
        }
