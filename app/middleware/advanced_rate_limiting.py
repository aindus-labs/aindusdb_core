"""
🛡️ Advanced Rate Limiting Middleware
Protection contre DDoS et brute force avec Redis/In-memory

Créé : 20 janvier 2026
Objectif : Jalon 3.1 - Rate Limiting & Protection DDoS
"""

import time
import asyncio
import hashlib
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import logging

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception pour rate limit dépassé."""
    def __init__(self, limit: str, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": limit,
                "retry_after": retry_after
            }
        )


class MemoryRateLimiter:
    """Rate limiter basé sur la mémoire (fallback)."""
    
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.cleanup_task = None
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window: int
    ) -> tuple[bool, int]:
        """Vérifier si la requête est autorisée."""
        now = time.time()
        window_start = now - window
        
        # Nettoyer les anciennes requêtes
        if key in self.requests:
            while self.requests[key] and self.requests[key][0] < window_start:
                self.requests[key].popleft()
        
        # Vérifier la limite
        request_count = len(self.requests[key])
        
        if request_count >= limit:
            # Calculer quand la prochaine requête sera autorisée
            oldest_request = self.requests[key][0] if self.requests[key] else now
            retry_after = int(oldest_request + window - now) + 1
            return False, retry_after
        
        # Ajouter la requête actuelle
        self.requests[key].append(now)
        return True, 0
    
    async def cleanup(self):
        """Nettoyer les anciennes entrées."""
        while True:
            await asyncio.sleep(300)  # Nettoyer toutes les 5 minutes
            now = time.time()
            cutoff = now - 3600  # Garder 1 heure d'historique
            
            for key in list(self.requests.keys()):
                while self.requests[key] and self.requests[key][0] < cutoff:
                    self.requests[key].popleft()
                
                if not self.requests[key]:
                    del self.requests[key]


class RedisRateLimiter:
    """Rate limiter basé sur Redis (production)."""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = None
    
    async def connect(self):
        """Connexion à Redis."""
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            logger.info("Rate limiter connecté à Redis")
        except Exception as e:
            logger.error(f"Impossible de se connecter à Redis: {e}")
            self.redis = None
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window: int
    ) -> tuple[bool, int]:
        """Vérifier avec Redis (sliding window)."""
        if not self.redis:
            return True, 0
        
        try:
            now = time.time()
            pipeline = self.redis.pipeline()
            
            # Supprimer les anciennes entrées
            pipeline.zremrangebyscore(key, 0, now - window)
            
            # Compter les requêtes actuelles
            pipeline.zcard(key)
            
            # Ajouter la requête actuelle
            pipeline.zadd(key, {str(now): now})
            
            # Définir l'expiration
            pipeline.expire(key, window)
            
            results = await pipeline.execute()
            request_count = results[1]
            
            if request_count >= limit:
                # Calculer retry_after
                oldest = await self.redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window - now) + 1
                else:
                    retry_after = window
                return False, retry_after
            
            return True, 0
            
        except Exception as e:
            logger.error(f"Erreur Redis rate limit: {e}")
            return True, 0  # Fallback sur autorisation


class AdvancedRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware avancé de rate limiting."""
    
    def __init__(
        self,
        app,
        redis_url: Optional[str] = None,
        default_limits: str = "100/minute,1000/hour",
        key_func: Optional[Callable[[Request], str]] = None,
        skip_paths: list = None,
        protected_paths: Dict[str, str] = None,
        enable_brute_force: bool = True,
        enable_ddos_protection: bool = True
    ):
        super().__init__(app)
        
        # Configuration
        self.redis_url = redis_url
        self.default_limits = self._parse_limits(default_limits)
        self.key_func = key_func or self._default_key_func
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.protected_paths = protected_paths or {
            "/auth/login": "5/minute,20/hour",
            "/auth/register": "3/minute,10/hour",
            "/auth/forgot-password": "3/hour",
            "/api/v1/veritas": "50/minute,500/hour"
        }
        self.enable_brute_force = enable_brute_force
        self.enable_ddos_protection = enable_ddos_protection
        
        # Rate limiters
        self.memory_limiter = MemoryRateLimiter()
        self.redis_limiter = None
        
        # Brute force tracking
        self.failed_attempts: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Dict[str, datetime] = {}
        
        # DDoS detection
        self.global_requests = deque()
        self.ddos_threshold = 1000  # requêtes/seconde
        self.ddos_window = 60  # secondes
    
    async def dispatch(self, request: Request, call_next):
        """Traiter la requête avec rate limiting."""
        
        # Skip paths
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        # DDoS protection
        if self.enable_ddos_protection:
            if await self._check_ddos(request):
                raise RateLimitExceeded("DDoS protection", 300)
        
        # Brute force protection
        if self.enable_brute_force:
            if await self._check_brute_force(request):
                raise RateLimitExceeded("Brute force protection", 900)
        
        # Rate limiting par endpoint
        limits = self._get_limits_for_path(request.url.path)
        key = self.key_func(request)
        
        for limit, window in limits:
            allowed, retry_after = await self._check_rate_limit(key, limit, window)
            if not allowed:
                # Log de l'alerte
                await self._log_rate_limit_violation(request, limit, window, retry_after)
                raise RateLimitExceeded(f"{limit}/{window}s", retry_after)
        
        # Exécuter la requête
        response = await call_next(request)
        
        # Ajouter headers rate limit
        response.headers["X-RateLimit-Limit"] = str(limits[0][0])
        response.headers["X-RateLimit-Remaining"] = str(max(0, limits[0][0] - 1))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + limits[0][1])
        
        return response
    
    async def _check_rate_limit(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Vérifier le rate limit."""
        if self.redis_limiter:
            return await self.redis_limiter.is_allowed(key, limit, window)
        else:
            return await self.memory_limiter.is_allowed(key, limit, window)
    
    async def _check_ddos(self, request: Request) -> bool:
        """Vérifier si attaque DDoS en cours."""
        now = time.time()
        
        # Nettoyer les anciennes requêtes
        while self.global_requests and self.global_requests[0] < now - self.ddos_window:
            self.global_requests.popleft()
        
        # Ajouter la requête actuelle
        self.global_requests.append(now)
        
        # Vérifier le seuil DDoS
        if len(self.global_requests) > self.ddos_threshold * self.ddos_window:
            logger.warning(f"DDoS attack detected! {len(self.global_requests)} requests in {self.ddos_window}s")
            return True
        
        return False
    
    async def _check_brute_force(self, request: Request) -> bool:
        """Vérifier les tentatives de brute force."""
        client_ip = self._get_client_ip(request)
        
        # Vérifier si l'IP est bloquée
        if client_ip in self.blocked_ips:
            if datetime.now() < self.blocked_ips[client_ip]:
                return True
            else:
                del self.blocked_ips[client_ip]
        
        # Pour les endpoints d'auth, vérifier les échecs
        if "/auth/" in request.url.path and request.method in ["POST"]:
            now = time.time()
            window_start = now - 900  # 15 minutes
            
            # Nettoyer les anciennes tentatives
            while self.failed_attempts[client_ip] and self.failed_attempts[client_ip][0] < window_start:
                self.failed_attempts[client_ip].popleft()
            
            # Vérifier le nombre d'échecs
            if len(self.failed_attempts[client_ip]) >= 10:
                # Bloquer l'IP pour 15 minutes
                self.blocked_ips[client_ip] = datetime.now() + timedelta(minutes=15)
                logger.warning(f"IP {client_ip} bloquée pour brute force")
                return True
        
        return False
    
    def _get_limits_for_path(self, path: str) -> list:
        """Obtenir les limites pour un chemin spécifique."""
        for protected_path, limits_str in self.protected_paths.items():
            if path.startswith(protected_path):
                return self._parse_limits(limits_str)
        return self.default_limits
    
    def _parse_limits(self, limits_str: str) -> list:
        """Parser la chaîne de limites."""
        limits = []
        for limit_str in limits_str.split(","):
            limit_str = limit_str.strip()
            if "/" in limit_str:
                limit, period = limit_str.split("/")
                limit = int(limit)
                
                if period == "second":
                    window = 1
                elif period == "minute":
                    window = 60
                elif period == "hour":
                    window = 3600
                elif period == "day":
                    window = 86400
                else:
                    continue
                
                limits.append((limit, window))
        
        return limits
    
    def _default_key_func(self, request: Request) -> str:
        """Fonction par défaut pour générer la clé."""
        # Utiliser IP + User-Agent + endpoint
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")[:50]
        path = request.url.path
        
        key = f"rate_limit:{hashlib.md5(f'{client_ip}:{user_agent}:{path}'.encode()).hexdigest()}"
        return key
    
    def _get_client_ip(self, request: Request) -> str:
        """Obtenir l'IP réelle du client."""
        # Vérifier les headers de proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback sur l'IP de connexion
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    async def _log_rate_limit_violation(
        self, 
        request: Request, 
        limit: int, 
        window: int, 
        retry_after: int
    ):
        """Logger les violations de rate limit."""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")[:100]
        
        logger.warning(
            f"Rate limit violation - IP: {client_ip}, "
            f"Path: {request.url.path}, "
            f"Limit: {limit}/{window}s, "
            f"Retry-After: {retry_after}s, "
            f"User-Agent: {user_agent}"
        )
    
    async def start(self):
        """Démarrer le middleware."""
        # Connexion Redis si disponible
        if self.redis_url:
            self.redis_limiter = RedisRateLimiter(self.redis_url)
            await self.redis_limiter.connect()
        
        # Démarrer le cleanup de mémoire
        asyncio.create_task(self.memory_limiter.cleanup())
        
        logger.info("Advanced Rate Limiting Middleware démarré")
    
    async def stop(self):
        """Arrêter le middleware."""
        if self.redis_limiter and self.redis_limiter.redis:
            await self.redis_limiter.redis.close()
        logger.info("Advanced Rate Limiting Middleware arrêté")


# Factory pour faciliter la configuration
def create_rate_limiter(
    redis_url: Optional[str] = None,
    limits: str = "100/minute,1000/hour",
    protected_paths: Dict[str, str] = None
) -> AdvancedRateLimitMiddleware:
    """Créer une instance du middleware de rate limiting."""
    
    # Configuration par défaut pour les paths sensibles
    default_protected_paths = {
        "/auth/login": "5/minute,20/hour",
        "/auth/register": "3/minute,10/hour",
        "/auth/forgot-password": "3/hour",
        "/auth/reset-password": "5/hour",
        "/api/v1/veritas/verify": "10/minute,100/hour",
        "/api/v1/veritas/calculate": "20/minute,200/hour",
        "/api/v1/admin": "50/minute,500/hour"
    }
    
    if protected_paths:
        default_protected_paths.update(protected_paths)
    
    return AdvancedRateLimitMiddleware(
        app=None,  # Sera défini lors de l'ajout à FastAPI
        redis_url=redis_url,
        default_limits=limits,
        protected_paths=default_protected_paths,
        enable_brute_force=True,
        enable_ddos_protection=True
    )
