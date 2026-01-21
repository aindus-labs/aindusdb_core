"""
🛡️ Middleware de Validation Sécurisée - AindusDB Core
Validation et sanitisation de toutes les entrées

Créé : 20 janvier 2026
Objectif : Phase 2.2 - Middleware de validation globale
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import json
import logging
import time
from typing import Dict, Any, List, Optional
import re

from ..models.secure_schemas import security_validator, DANGEROUS_KEYWORDS

logger = logging.getLogger(__name__)

class SecurityValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour la validation et la sanitisation de toutes les requêtes.
    
    Effectue les vérifications suivantes :
    - Validation des tailles de requêtes
    - Détection d'injections
    - Sanitisation des entrées
    - Rate limiting basique
    - Validation des headers
    """
    
    def __init__(self, app, 
                 max_request_size: int = 10 * 1024 * 1024,  # 10MB
                 max_header_size: int = 8192,  # 8KB
                 blocked_user_agents: List[str] = None):
        """
        Initialiser le middleware de sécurité.
        
        Args:
            app: Application FastAPI
            max_request_size: Taille maximale des requêtes en bytes
            max_header_size: Taille maximale des headers
            blocked_user_agents: List de User-Agents bloqués
        """
        super().__init__(app)
        self.max_request_size = max_request_size
        self.max_header_size = max_header_size
        self.blocked_user_agents = blocked_user_agents or [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zap', 'burp',
            'scanner', 'crawler', 'bot', 'spider'
        ]
        
        # Patterns de détection
        self.injection_patterns = [
            r"(union\s+select|select\s+.*\s+from\s+.*\s+where)",
            r"(drop\s+table|delete\s+from|insert\s+into)",
            r"(exec\s*\(|eval\s*\(|system\s*\()",
            r"(\$\w+\s*:\s*\{|\{.*\$\w+)",
            r"(<script|javascript:|on\w+\s*=)",
        ]
        
        # Stats de sécurité
        self.stats = {
            "requests_blocked": 0,
            "injections_detected": 0,
            "large_requests_blocked": 0,
            "suspicious_ua_blocked": 0
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Traiter une requête avec validation sécurisée."""
        start_time = time.time()
        
        try:
            # 1. Validation de base
            await self._validate_basic_request(request)
            
            # 2. Validation des headers
            await self._validate_headers(request)
            
            # 3. Validation du corps si présent
            await self._validate_body(request)
            
            # 4. Traiter la requête
            response = await call_next(request)
            
            # 5. Ajouter headers de sécurité
            response = self._add_security_headers(response)
            
            # Log de la requête
            self._log_request(request, response, time.time() - start_time)
            
            return response
            
        except HTTPException as e:
            self.stats["requests_blocked"] += 1
            logger.warning(f"Request blocked: {e.detail}", extra={
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host
            })
            return JSONResponse(
                status_code=e.status_code,
                content={"error": "Security validation failed", "detail": e.detail}
            )
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal security error"}
            )
    
    async def _validate_basic_request(self, request: Request):
        """Validation de base de la requête."""
        # Vérifier la méthode
        if request.method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']:
            raise HTTPException(
                status_code=405,
                detail="Method not allowed"
            )
        
        # Vérifier l'URL
        if len(str(request.url)) > 2048:
            raise HTTPException(
                status_code=414,
                detail="URL too long"
            )
        
        # Vérifier les caractères dans l'URL
        if security_validator.detect_injection(request.url.path):
            self.stats["injections_detected"] += 1
            raise HTTPException(
                status_code=400,
                detail="Invalid characters in URL"
            )
    
    async def _validate_headers(self, request: Request):
        """Valider les headers de la requête."""
        # Taille totale des headers
        header_size = sum(len(k) + len(v) for k, v in request.headers.items())
        if header_size > self.max_header_size:
            raise HTTPException(
                status_code=431,
                detail="Request header fields too large"
            )
        
        # User-Agent suspect
        user_agent = request.headers.get("User-Agent", "").lower()
        for blocked in self.blocked_user_agents:
            if blocked in user_agent:
                self.stats["suspicious_ua_blocked"] += 1
                raise HTTPException(
                    status_code=403,
                    detail="Access denied"
                )
        
        # Headers suspects
        suspicious_headers = ['x-forwarded-for', 'x-real-ip', 'x-originating-ip']
        for header in suspicious_headers:
            if header in request.headers:
                # Validation basique de l'IP
                value = request.headers[header]
                if not self._is_valid_ip(value):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid IP in {header}"
                    )
    
    async def _validate_body(self, request: Request):
        """Valider le corps de la requête."""
        if request.method in ['GET', 'DELETE', 'HEAD', 'OPTIONS']:
            return
        
        # Vérifier Content-Length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            self.stats["large_requests_blocked"] += 1
            raise HTTPException(
                status_code=413,
                detail="Request entity too large"
            )
        
        # Lire et valider le contenu
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            await self._validate_json_body(request)
        elif "application/x-www-form-urlencoded" in content_type:
            await self._validate_form_body(request)
        elif "multipart/form-data" in content_type:
            await self._validate_multipart_body(request)
    
    async def _validate_json_body(self, request: Request):
        """Valider le corps JSON."""
        try:
            body = await request.body()
            
            # Vérifier la taille
            if len(body) > self.max_request_size:
                self.stats["large_requests_blocked"] += 1
                raise HTTPException(
                    status_code=413,
                    detail="JSON too large"
                )
            
            # Parser et valider
            try:
                data = json.loads(body.decode())
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON"
                )
            
            # Validation récursive
            self._validate_json_data(data)
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            logger.error(f"JSON validation error: {e}")
            raise HTTPException(
                status_code=400,
                detail="JSON validation failed"
            )
    
    async def _validate_form_body(self, request: Request):
        """Valider le corps formulaire."""
        try:
            body = await request.body()
            if len(body) > self.max_request_size:
                self.stats["large_requests_blocked"] += 1
                raise HTTPException(
                    status_code=413,
                    detail="Form data too large"
                )
            
            # Parser les données
            form_data = body.decode()
            
            # Vérifier les injections
            if security_validator.detect_injection(form_data):
                self.stats["injections_detected"] += 1
                raise HTTPException(
                    status_code=400,
                    detail="Invalid form data"
                )
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=400,
                detail="Form validation failed"
            )
    
    async def _validate_multipart_body(self, request: Request):
        """Valider le corps multipart."""
        # Pour multipart, on laisse FastAPI gérer
        # mais on pourrait ajouter des validations ici
        pass
    
    def _validate_json_data(self, data: Any, depth: int = 0):
        """Validation récursive des données JSON."""
        if depth > 10:  # Profondeur max
            raise HTTPException(
                status_code=400,
                detail="JSON structure too deep"
            )
        
        if isinstance(data, dict):
            for key, value in data.items():
                # Valider la clé
                if not isinstance(key, str):
                    raise HTTPException(
                        status_code=400,
                        detail="JSON keys must be strings"
                    )
                
                if len(key) > 100:
                    raise HTTPException(
                        status_code=400,
                        detail="JSON key too long"
                    )
                
                # Valider la valeur
                self._validate_json_value(value, depth + 1)
                
        elif isinstance(data, list):
            for item in data:
                self._validate_json_value(item, depth + 1)
    
    def _validate_json_value(self, value: Any, depth: int):
        """Valider une valeur JSON."""
        if isinstance(value, (dict, list)):
            self._validate_json_data(value, depth)
        elif isinstance(value, str):
            # Taille max
            if len(value) > 1000:
                raise HTTPException(
                    status_code=400,
                    detail="String value too long"
                )
            
            # Injection
            if security_validator.detect_injection(value):
                self.stats["injections_detected"] += 1
                raise HTTPException(
                    status_code=400,
                    detail="Invalid string content"
                )
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Valider une adresse IP."""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def _add_security_headers(self, response: Response) -> Response:
        """Ajouter les headers de sécurité."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response
    
    def _log_request(self, request: Request, response: Response, duration: float):
        """Logger la requête pour audit."""
        if duration > 5.0:  # Requêtes lentes
            logger.warning(f"Slow request detected", extra={
                "path": request.url.path,
                "method": request.method,
                "duration": duration,
                "status": response.status_code
            })
    
    def get_stats(self) -> Dict[str, int]:
        """Obtenir les statistiques de sécurité."""
        return self.stats.copy()

# Middleware de rate limiting simple
class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting basique en mémoire."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # {ip: [(timestamp, count)]}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Appliquer le rate limiting."""
        client_ip = request.client.host
        now = time.time()
        
        # Nettoyer les anciennes entrées
        self._cleanup_old_requests(now)
        
        # Vérifier le quota
        if client_ip in self.requests:
            total_requests = sum(count for _, count in self.requests[client_ip])
            if total_requests >= self.requests_per_minute:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests"
                )
        
        # Enregistrer la requête
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Ajouter ou incrémenter
        minute_key = int(now // 60) * 60
        for i, (timestamp, count) in enumerate(self.requests[client_ip]):
            if timestamp == minute_key:
                self.requests[client_ip][i] = (timestamp, count + 1)
                break
        else:
            self.requests[client_ip].append((minute_key, 1))
        
        return await call_next(request)
    
    def _cleanup_old_requests(self, now: float):
        """Nettoyer les requêtes anciennes (> 1 heure)."""
        cutoff = now - 3600
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                (ts, count) for ts, count in self.requests[ip]
                if ts > cutoff
            ]
            if not self.requests[ip]:
                del self.requests[ip]
