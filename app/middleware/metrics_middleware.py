"""
Middleware de métriques Prometheus pour FastAPI avec collecte automatique.

Ce middleware capture automatiquement les métriques HTTP pour monitoring :
- Compteurs de requêtes par endpoint, méthode, status code
- Histogrammes de latence avec buckets configurables
- Taille des requêtes et réponses
- Métriques utilisateur et authentification
- Intégration transparente avec le service de métriques

Example:
    from app.middleware.metrics_middleware import PrometheusMetricsMiddleware
    
    app = FastAPI()
    app.add_middleware(PrometheusMetricsMiddleware,
                      exclude_paths=["/health", "/metrics"])
"""

import time
import asyncio
from typing import Callable, Optional, List, Set
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from ..core.metrics import metrics_service
from ..core.logging import get_logger
from ..core.security import security_service


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware FastAPI pour collecte automatique de métriques Prometheus.
    
    Capture transparentement toutes les requêtes HTTP avec :
    - Compteurs de requêtes avec labels enrichis (méthode, endpoint, status, rôle utilisateur)
    - Histogrammes de latence pour analyse des performances
    - Métriques de taille des payloads (requête/réponse)
    - Tracking des utilisateurs actifs et sessions
    - Métriques d'authentification et autorisation
    
    Features:
    - Labels dynamiques selon contexte (utilisateur, rôle, etc.)
    - Exclusion de paths configurables (health checks, métriques)
    - Normalisation des endpoints pour éviter explosion de cardinalité
    - Intégration avec système d'authentification JWT
    - Métriques business automatiques (vecteurs, recherches)
    
    Attributes:
        exclude_paths: Chemins à exclure du monitoring
        normalize_endpoints: Normaliser endpoints avec paramètres
        track_user_metrics: Suivre métriques par utilisateur
        max_path_length: Longueur max des chemins (troncature)
        
    Example:
        # Configuration production avec exclusions
        app.add_middleware(PrometheusMetricsMiddleware,
                          exclude_paths=["/health", "/metrics", "/docs"],
                          normalize_endpoints=True,
                          track_user_metrics=True)
    """
    
    def __init__(self,
                 app: FastAPI,
                 exclude_paths: Optional[List[str]] = None,
                 normalize_endpoints: bool = True,
                 track_user_metrics: bool = True,
                 max_path_length: int = 100):
        super().__init__(app)
        
        self.exclude_paths = set(exclude_paths or [
            "/health", "/healthcheck", "/metrics", "/favicon.ico",
            "/docs", "/redoc", "/openapi.json"
        ])
        
        self.normalize_endpoints = normalize_endpoints
        self.track_user_metrics = track_user_metrics
        self.max_path_length = max_path_length
        
        self.logger = get_logger("aindusdb.middleware.metrics")
        
        # Cache pour normalisation des endpoints
        self._endpoint_cache = {}
        
        # Set pour tracking utilisateurs actifs
        self._active_users_5min = set()
        self._active_users_1hour = set()
        self._active_users_24hour = set()
        
        # Démarrer nettoyage périodique
        asyncio.create_task(self._cleanup_active_users())
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Capturer métriques pour une requête HTTP.
        
        Args:
            request: Requête FastAPI
            call_next: Fonction suivante dans la chaîne middleware
            
        Returns:
            Response: Réponse avec métriques capturées
        """
        # Vérifier si path exclu
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Timestamp de début
        start_time = time.time()
        
        # Extraire contexte utilisateur
        user_context = await self._extract_user_context(request)
        user_role = user_context.get("role", "anonymous") if user_context else "anonymous"
        user_id = user_context.get("user_id") if user_context else None
        
        # Normaliser endpoint
        endpoint = self._normalize_endpoint(request)
        
        # Mesurer taille requête
        request_size = await self._get_request_size(request)
        
        # Variables pour capture réponse
        response = None
        status_code = 500  # Défaut en cas d'exception
        
        try:
            # Traiter requête
            response = await call_next(request)
            status_code = response.status_code
            
            # Mesurer taille réponse
            response_size = self._get_response_size(response)
            
        except Exception as e:
            # Exception non gérée - compter comme erreur 500
            self.logger.error(f"Exception in metrics middleware: {e}")
            status_code = 500
            response_size = 0
            raise
            
        finally:
            # Calculer latence
            duration = time.time() - start_time
            
            # Enregistrer métriques HTTP de base
            await self._record_http_metrics(
                request.method, endpoint, status_code, 
                user_role, duration, request_size, response_size
            )
            
            # Enregistrer métriques utilisateur si authentifié
            if user_id and self.track_user_metrics:
                await self._record_user_metrics(user_id, endpoint, request.method)
            
            # Métriques spécifiques par endpoint
            await self._record_endpoint_specific_metrics(
                endpoint, request.method, status_code, user_context
            )
        
        return response
    
    async def _extract_user_context(self, request: Request) -> Optional[dict]:
        """
        Extraire contexte utilisateur depuis JWT.
        
        Args:
            request: Requête FastAPI
            
        Returns:
            Optional[dict]: Contexte utilisateur ou None
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
                "permissions": payload.get("permissions", [])
            }
            
        except Exception:
            # Ne pas faire échouer la requête pour erreur d'extraction
            return None
    
    def _normalize_endpoint(self, request: Request) -> str:
        """
        Normaliser endpoint pour éviter explosion de cardinalité.
        
        Args:
            request: Requête FastAPI
            
        Returns:
            str: Endpoint normalisé
        """
        path = request.url.path
        
        # Utiliser cache si déjà calculé
        if path in self._endpoint_cache:
            return self._endpoint_cache[path]
        
        # Pas de normalisation - retourner tel quel
        if not self.normalize_endpoints:
            normalized = path[:self.max_path_length]
            self._endpoint_cache[path] = normalized
            return normalized
        
        # Trouver route correspondante
        try:
            for route in request.app.routes:
                match, _ = route.matches({"type": "http", "path": path, "method": request.method})
                if match == Match.FULL:
                    # Route trouvée - utiliser son pattern
                    normalized = str(route.path)[:self.max_path_length]
                    self._endpoint_cache[path] = normalized
                    return normalized
        except Exception:
            pass
        
        # Fallback: normalisation simple des IDs numériques
        import re
        normalized = re.sub(r'/\d+', '/{id}', path)
        normalized = re.sub(r'/[a-f0-9-]{8,}', '/{uuid}', normalized)  # UUIDs
        normalized = normalized[:self.max_path_length]
        
        self._endpoint_cache[path] = normalized
        return normalized
    
    async def _get_request_size(self, request: Request) -> int:
        """Obtenir taille de la requête en bytes."""
        try:
            # Header Content-Length si disponible
            content_length = request.headers.get("content-length")
            if content_length:
                return int(content_length)
            
            # Calculer depuis body (coûteux)
            body = await request.body()
            return len(body)
            
        except Exception:
            return 0
    
    def _get_response_size(self, response: Response) -> int:
        """Obtenir taille de la réponse en bytes."""
        try:
            # Header Content-Length si disponible
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)
            
            # Calculer depuis body si accessible
            if hasattr(response, 'body') and response.body:
                return len(response.body)
            
            return 0
            
        except Exception:
            return 0
    
    async def _record_http_metrics(self,
                                 method: str,
                                 endpoint: str, 
                                 status_code: int,
                                 user_role: str,
                                 duration: float,
                                 request_size: int,
                                 response_size: int):
        """Enregistrer métriques HTTP de base."""
        try:
            # Compteur de requêtes
            metrics_service.http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code),
                user_role=user_role
            ).inc()
            
            # Histogramme de latence
            metrics_service.http_request_duration.labels(
                method=method,
                endpoint=endpoint, 
                status_code=str(status_code)
            ).observe(duration)
            
            # Taille requête
            if request_size > 0:
                metrics_service.http_request_size.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(request_size)
            
            # Taille réponse
            if response_size > 0:
                metrics_service.http_response_size.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=str(status_code)
                ).observe(response_size)
            
        except Exception as e:
            self.logger.error(f"Error recording HTTP metrics: {e}")
    
    async def _record_user_metrics(self, user_id: int, endpoint: str, method: str):
        """Enregistrer métriques par utilisateur."""
        try:
            # Ajouter aux utilisateurs actifs
            current_time = time.time()
            self._active_users_5min.add((user_id, current_time))
            self._active_users_1hour.add((user_id, current_time))
            self._active_users_24hour.add((user_id, current_time))
            
            # Mettre à jour gauges
            metrics_service.active_users.labels('5min').set(len(self._active_users_5min))
            metrics_service.active_users.labels('1hour').set(len(self._active_users_1hour))
            metrics_service.active_users.labels('24hour').set(len(self._active_users_24hour))
            
        except Exception as e:
            self.logger.error(f"Error recording user metrics: {e}")
    
    async def _record_endpoint_specific_metrics(self,
                                              endpoint: str,
                                              method: str,
                                              status_code: int,
                                              user_context: Optional[dict]):
        """Enregistrer métriques spécifiques par type d'endpoint."""
        try:
            # Métriques d'authentification
            if "/auth/" in endpoint:
                result = "success" if status_code < 400 else "failure"
                user_agent = "unknown"  # TODO: extraire depuis request si nécessaire
                
                metrics_service.auth_attempts_total.labels(
                    method=endpoint.split('/')[-1],  # login, refresh, etc.
                    result=result,
                    user_agent_type=user_agent
                ).inc()
            
            # Métriques de vecteurs
            elif "/vectors" in endpoint:
                if method == "POST" and status_code < 400:
                    user_id = str(user_context.get("user_id", "unknown")) if user_context else "unknown"
                    user_role = user_context.get("role", "unknown") if user_context else "unknown"
                    
                    metrics_service.vectors_total.labels(
                        user_id=user_id,
                        user_role=user_role,
                        embedding_model="default"
                    ).inc()
                
                elif "/search" in endpoint and method == "POST" and status_code < 400:
                    user_id = str(user_context.get("user_id", "unknown")) if user_context else "unknown"
                    user_role = user_context.get("role", "unknown") if user_context else "unknown"
                    
                    metrics_service.vector_searches_total.labels(
                        search_type="similarity",
                        user_id=user_id,
                        user_role=user_role
                    ).inc()
            
        except Exception as e:
            self.logger.error(f"Error recording endpoint-specific metrics: {e}")
    
    async def _cleanup_active_users(self):
        """Nettoyer périodiquement les utilisateurs actifs expirés."""
        while True:
            try:
                current_time = time.time()
                
                # Nettoyer utilisateurs 5min
                self._active_users_5min = {
                    (user_id, timestamp) for user_id, timestamp in self._active_users_5min
                    if current_time - timestamp < 300  # 5 minutes
                }
                
                # Nettoyer utilisateurs 1hour  
                self._active_users_1hour = {
                    (user_id, timestamp) for user_id, timestamp in self._active_users_1hour
                    if current_time - timestamp < 3600  # 1 heure
                }
                
                # Nettoyer utilisateurs 24hour
                self._active_users_24hour = {
                    (user_id, timestamp) for user_id, timestamp in self._active_users_24hour
                    if current_time - timestamp < 86400  # 24 heures
                }
                
                # Mettre à jour gauges
                metrics_service.active_users.labels('5min').set(len(self._active_users_5min))
                metrics_service.active_users.labels('1hour').set(len(self._active_users_1hour))
                metrics_service.active_users.labels('24hour').set(len(self._active_users_24hour))
                
                # Attendre 60 secondes avant prochain nettoyage
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in active users cleanup: {e}")
                await asyncio.sleep(60)


class BusinessMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour métriques business spécifiques à AindusDB.
    
    Complément au PrometheusMetricsMiddleware pour capturer des métriques
    métier plus spécifiques selon le contenu des requêtes/réponses.
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.logger = get_logger("aindusdb.middleware.business_metrics")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Capturer métriques business selon le contenu."""
        response = await call_next(request)
        
        try:
            await self._analyze_business_metrics(request, response)
        except Exception as e:
            self.logger.error(f"Error in business metrics analysis: {e}")
        
        return response
    
    async def _analyze_business_metrics(self, request: Request, response: Response):
        """Analyser requête/réponse pour métriques business."""
        # TODO: Implémenter analyse selon besoins spécifiques
        # Exemples:
        # - Compter nombre de vecteurs dans requête batch
        # - Mesurer taille des embeddings
        # - Tracker utilisation par modèle d'embedding
        # - Métriques de qualité des recherches
        pass


class HealthMetricsCollector:
    """
    Collecteur de métriques de santé système pour monitoring proactif.
    
    Collecte périodiquement des métriques de santé :
    - État des connexions base de données
    - Utilisation cache et hit rates
    - Métriques de performance des services
    """
    
    def __init__(self):
        self.logger = get_logger("aindusdb.middleware.health_metrics")
        self.collection_task = None
        self.running = False
    
    async def start(self):
        """Démarrer la collecte périodique."""
        if self.running:
            return
        
        self.running = True
        self.collection_task = asyncio.create_task(self._collect_health_metrics())
        self.logger.info("Health metrics collector started")
    
    async def stop(self):
        """Arrêter la collecte."""
        self.running = False
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Health metrics collector stopped")
    
    async def _collect_health_metrics(self):
        """Boucle de collecte des métriques de santé."""
        while self.running:
            try:
                # Collecter métriques de base de données
                await metrics_service.collect_database_metrics()
                
                # TODO: Collecter métriques cache
                # TODO: Collecter métriques services
                
                # Attendre 30 secondes avant prochaine collecte
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error collecting health metrics: {e}")
                await asyncio.sleep(60)  # Attendre plus en cas d'erreur


# Instance globale du collecteur de santé
health_collector = HealthMetricsCollector()
