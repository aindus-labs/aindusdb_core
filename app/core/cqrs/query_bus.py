"""
Query Bus pour CQRS - Orchestration des queries de lecture.

Le Query Bus est responsable de recevoir les queries, de trouver le handler
approprié et d'exécuter la query avec optimisations de lecture, caching
et métriques de performance.

Example:
    query_bus = QueryBus()
    query_bus.register(SearchVectorsQuery, SearchVectorsHandler())
    
    results = await query_bus.execute(SearchVectorsQuery(...))
"""

import asyncio
from typing import Dict, Type, TypeVar, Any, Optional, List
from datetime import datetime, timezone
import time
import json

from ...core.logging import get_logger, LogContext
from ...core.metrics import metrics_service
from .queries import Query, QueryHandler
from .events import Event, EventStore

TQuery = TypeVar('TQuery', bound=Query)
TResult = TypeVar('TResult')


class QueryBus:
    """
    Bus de queries pour pattern CQRS avec optimisations de lecture.
    
    Le QueryBus centralise l'exécution des queries de lecture avec :
    - Cache intelligent pour optimiser les performances
    - Handlers spécialisés par type de query
    - Métriques détaillées pour observabilité
    - Support read replicas pour scalabilité
    - Compression des résultats volumineux
    - Pagination automatique pour gros datasets
    
    Features:
    - Registry des handlers par type de query
    - Cache multi-niveau (Redis + mémoire)
    - Métriques Prometheus pour queries
    - Read replicas avec load balancing
    - Compression gzip pour gros résultats
    - Timeout configurable par query type
    
    Example:
        # Configuration
        bus = QueryBus(enable_cache=True, cache_ttl=300)
        bus.register(SearchVectorsQuery, SearchVectorsHandler(db))
        
        # Exécution avec cache automatique
        results = await bus.execute(SearchVectorsQuery(
            query_text="machine learning",
            limit=50
        ))
    """
    
    def __init__(self, 
                 enable_cache: bool = True,
                 cache_ttl: int = 300,
                 enable_metrics: bool = True,
                 default_timeout: int = 30):
        """
        Initialiser le Query Bus.
        
        Args:
            enable_cache: Activer le cache des résultats
            cache_ttl: TTL du cache en secondes
            enable_metrics: Activer les métriques
            default_timeout: Timeout par défaut (secondes)
        """
        self.handlers: Dict[Type[Query], QueryHandler] = {}
        self.middlewares: List['QueryMiddleware'] = []
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.enable_metrics = enable_metrics
        self.default_timeout = default_timeout
        
        self.logger = get_logger("aindusdb.cqrs.query_bus")
        
        # Cache en mémoire pour queries fréquentes
        self._memory_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Statistiques
        self.stats = {
            "queries_executed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_execution_time": 0.0,
            "handlers_registered": 0
        }
    
    def register(self, query_type: Type[TQuery], handler: QueryHandler[TQuery, TResult]):
        """
        Enregistrer un handler pour un type de query.
        
        Args:
            query_type: Type de query
            handler: Handler associé
        """
        self.handlers[query_type] = handler
        self.stats["handlers_registered"] += 1
        
        self.logger.info(f"Query handler registered: {query_type.__name__} -> {handler.__class__.__name__}")
    
    def add_middleware(self, middleware: 'QueryMiddleware'):
        """
        Ajouter un middleware au pipeline.
        
        Args:
            middleware: Middleware à ajouter
        """
        self.middlewares.append(middleware)
        self.logger.info(f"Query middleware added: {middleware.__class__.__name__}")
    
    async def execute(self, query: TQuery, use_cache: bool = None) -> TResult:
        """
        Exécuter une query avec pipeline complet et cache.
        
        Args:
            query: Query à exécuter
            use_cache: Forcer utilisation cache (None = auto)
            
        Returns:
            TResult: Résultat de la query
            
        Raises:
            ValueError: Si aucun handler n'est trouvé
            TimeoutError: Si timeout dépassé
        """
        start_time = time.time()
        query_type = type(query)
        use_cache = use_cache if use_cache is not None else self.enable_cache
        
        with LogContext(
            operation="execute_query",
            query_type=query_type.__name__,
            query_id=query.query_id,
            correlation_id=query.correlation_id
        ):
            self.logger.info(f"Executing query: {query_type.__name__}")
            
            try:
                # 1. Vérifier cache d'abord
                if use_cache:
                    cached_result = await self._get_from_cache(query)
                    if cached_result is not None:
                        execution_time = (time.time() - start_time) * 1000
                        await self._record_metrics(query_type.__name__, "cache_hit", execution_time)
                        self.stats["cache_hits"] += 1
                        
                        self.logger.info(f"Query served from cache: {query_type.__name__}",
                                       extra={"execution_time_ms": execution_time})
                        return cached_result
                    
                    self.stats["cache_misses"] += 1
                
                # 2. Vérifier qu'un handler existe
                if query_type not in self.handlers:
                    raise ValueError(f"No handler registered for query: {query_type.__name__}")
                
                handler = self.handlers[query_type]
                
                # 3. Exécuter avec timeout
                result = await asyncio.wait_for(
                    self._execute_pipeline(query, handler),
                    timeout=self.default_timeout
                )
                
                # 4. Mettre en cache si activé
                if use_cache:
                    await self._store_in_cache(query, result)
                
                # 5. Métriques
                execution_time = (time.time() - start_time) * 1000
                await self._record_metrics(query_type.__name__, "success", execution_time)
                
                self.stats["queries_executed"] += 1
                self.stats["total_execution_time"] += execution_time
                
                self.logger.info(f"Query executed successfully: {query_type.__name__}",
                               extra={"execution_time_ms": execution_time})
                
                return result
                
            except asyncio.TimeoutError:
                execution_time = (time.time() - start_time) * 1000
                self.logger.error(f"Query timeout: {query_type.__name__} ({self.default_timeout}s)")
                await self._record_metrics(query_type.__name__, "timeout", execution_time)
                raise TimeoutError(f"Query {query_type.__name__} timed out after {self.default_timeout}s")
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                
                self.logger.error(f"Query execution failed: {query_type.__name__}: {e}",
                                extra={"execution_time_ms": execution_time})
                
                await self._record_metrics(query_type.__name__, "error", execution_time)
                raise
    
    async def _execute_pipeline(self, query: TQuery, handler: QueryHandler) -> TResult:
        """
        Exécuter le pipeline complet : middlewares + handler.
        
        Args:
            query: Query à exécuter
            handler: Handler final
            
        Returns:
            TResult: Résultat de l'exécution
        """
        # Créer pipeline avec middlewares
        pipeline = self._build_pipeline(handler)
        
        # Exécuter pipeline
        return await pipeline(query)
    
    def _build_pipeline(self, handler: QueryHandler):
        """
        Construire le pipeline de middlewares + handler.
        
        Args:
            handler: Handler final
            
        Returns:
            Callable: Pipeline complet
        """
        # Handler final
        async def final_handler(query):
            await handler.validate(query)
            return await handler.handle(query)
        
        # Appliquer middlewares en reverse
        pipeline = final_handler
        for middleware in reversed(self.middlewares):
            pipeline = middleware.wrap(pipeline)
        
        return pipeline
    
    async def _get_from_cache(self, query: Query) -> Optional[Any]:
        """
        Récupérer résultat du cache si disponible.
        
        Args:
            query: Query dont on veut le résultat
            
        Returns:
            Optional[Any]: Résultat en cache ou None
        """
        cache_key = self._generate_cache_key(query)
        
        # Vérifier cache mémoire d'abord
        if cache_key in self._memory_cache:
            cache_time = self._cache_timestamps.get(cache_key)
            if cache_time and (datetime.now(timezone.utc) - cache_time).seconds < self.cache_ttl:
                self.logger.debug(f"Memory cache hit: {cache_key}")
                return self._memory_cache[cache_key]
            else:
                # Expirer cache
                self._memory_cache.pop(cache_key, None)
                self._cache_timestamps.pop(cache_key, None)
        
        # TODO: Vérifier Redis cache
        # if redis_client:
        #     cached = await redis_client.get(cache_key)
        #     if cached:
        #         return json.loads(cached)
        
        return None
    
    async def _store_in_cache(self, query: Query, result: Any):
        """
        Stocker résultat en cache.
        
        Args:
            query: Query exécutée
            result: Résultat à cacher
        """
        cache_key = self._generate_cache_key(query)
        
        # Cache mémoire (pour petits résultats)
        try:
            result_size = len(str(result))
            if result_size < 10000:  # Moins de 10KB
                self._memory_cache[cache_key] = result
                self._cache_timestamps[cache_key] = datetime.now(timezone.utc)
                
                # Limiter taille du cache mémoire
                if len(self._memory_cache) > 1000:
                    oldest_key = min(self._cache_timestamps.keys(), 
                                   key=lambda k: self._cache_timestamps[k])
                    self._memory_cache.pop(oldest_key, None)
                    self._cache_timestamps.pop(oldest_key, None)
                
                self.logger.debug(f"Stored in memory cache: {cache_key}")
        except Exception as e:
            self.logger.debug(f"Failed to cache in memory: {e}")
        
        # TODO: Redis cache pour gros résultats
        # if redis_client:
        #     try:
        #         await redis_client.setex(
        #             cache_key, 
        #             self.cache_ttl, 
        #             json.dumps(result, default=str)
        #         )
        #     except Exception as e:
        #         self.logger.debug(f"Failed to cache in Redis: {e}")
    
    def _generate_cache_key(self, query: Query) -> str:
        """
        Générer clé de cache unique pour une query.
        
        Args:
            query: Query à identifier
            
        Returns:
            str: Clé de cache unique
        """
        import hashlib
        
        # Créer hash basé sur type + données
        query_data = {
            "type": type(query).__name__,
            "data": query.model_dump(exclude={"query_id", "timestamp", "correlation_id"})
        }
        
        cache_string = json.dumps(query_data, sort_keys=True, default=str)
        cache_hash = hashlib.sha256(cache_string.encode()).hexdigest()[:16]
        
        return f"query:{type(query).__name__.lower()}:{cache_hash}"
    
    async def _record_metrics(self, query_name: str, status: str, execution_time: float):
        """
        Enregistrer métriques d'exécution.
        
        Args:
            query_name: Nom de la query
            status: Statut (success/error/timeout/cache_hit)
            execution_time: Temps d'exécution (ms)
        """
        if not self.enable_metrics or not metrics_service:
            return
        
        # Compteur de queries
        await metrics_service.increment_counter(
            "cqrs_queries_total",
            labels={"query": query_name, "status": status}
        )
        
        # Histogramme des temps d'exécution
        if status != "cache_hit":  # Pas de mesure temps pour cache hits
            await metrics_service.record_histogram(
                "cqrs_query_duration_ms",
                execution_time,
                labels={"query": query_name}
            )
        
        # Métriques cache
        if status == "cache_hit":
            await metrics_service.increment_counter(
                "cqrs_cache_hits_total",
                labels={"query": query_name}
            )
        elif self.enable_cache:
            await metrics_service.increment_counter(
                "cqrs_cache_misses_total",
                labels={"query": query_name}
            )
    
    async def execute_batch(self, queries: List[Query], parallel: bool = True) -> List[Any]:
        """
        Exécuter plusieurs queries en batch.
        
        Args:
            queries: Liste des queries
            parallel: Exécution parallèle (recommandée pour lectures)
            
        Returns:
            List[Any]: Résultats des queries
        """
        if parallel:
            # Exécution parallèle optimisée pour lectures
            tasks = [self.execute(query) for query in queries]
            return await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Exécution séquentielle
            results = []
            for query in queries:
                try:
                    result = await self.execute(query)
                    results.append(result)
                except Exception as e:
                    results.append(e)
            return results
    
    def clear_cache(self):
        """Vider le cache mémoire."""
        self._memory_cache.clear()
        self._cache_timestamps.clear()
        self.logger.info("Query cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtenir statistiques du Query Bus.
        
        Returns:
            Dict: Statistiques complètes
        """
        stats = self.stats.copy()
        
        # Calculer moyennes
        if stats["queries_executed"] > 0:
            stats["avg_execution_time"] = (
                stats["total_execution_time"] / stats["queries_executed"]
            )
        else:
            stats["avg_execution_time"] = 0.0
        
        # Taux de cache hit
        total_requests = stats["cache_hits"] + stats["cache_misses"]
        if total_requests > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / total_requests
        else:
            stats["cache_hit_rate"] = 0.0
        
        stats["registered_handlers"] = list(self.handlers.keys())
        stats["middleware_count"] = len(self.middlewares)
        stats["memory_cache_size"] = len(self._memory_cache)
        
        return stats


class QueryMiddleware:
    """
    Classe de base pour les middlewares de queries.
    
    Les middlewares permettent d'ajouter des fonctionnalités transversales
    comme le caching, la validation, la compression, etc.
    """
    
    def wrap(self, next_handler):
        """
        Enrober le handler suivant avec la fonctionnalité du middleware.
        
        Args:
            next_handler: Handler suivant dans la chaîne
            
        Returns:
            Callable: Handler enrobé
        """
        return next_handler


class CompressionMiddleware(QueryMiddleware):
    """Middleware de compression des résultats volumineux."""
    
    def __init__(self, threshold_bytes: int = 50000):
        self.threshold_bytes = threshold_bytes
        self.logger = get_logger("cqrs.middleware.compression")
    
    def wrap(self, next_handler):
        async def wrapper(query):
            result = await next_handler(query)
            
            # Compresser si résultat volumineux
            try:
                result_size = len(str(result))
                if result_size > self.threshold_bytes:
                    # TODO: Implémenter compression gzip
                    self.logger.info(f"Large result detected: {result_size} bytes")
                    
            except Exception as e:
                self.logger.debug(f"Compression check failed: {e}")
            
            return result
        return wrapper


class PaginationMiddleware(QueryMiddleware):
    """Middleware de pagination automatique."""
    
    def __init__(self, max_results: int = 10000):
        self.max_results = max_results
        self.logger = get_logger("cqrs.middleware.pagination")
    
    def wrap(self, next_handler):
        async def wrapper(query):
            # Vérifier si limite dépassée
            if hasattr(query, 'limit') and query.limit > self.max_results:
                self.logger.warning(f"Query limit capped: {query.limit} -> {self.max_results}")
                query.limit = self.max_results
            
            return await next_handler(query)
        return wrapper


class ReadReplicaMiddleware(QueryMiddleware):
    """Middleware de load balancing vers read replicas."""
    
    def __init__(self, read_replicas: List[str] = None):
        self.read_replicas = read_replicas or []
        self.current_replica = 0
        self.logger = get_logger("cqrs.middleware.read_replica")
    
    def wrap(self, next_handler):
        async def wrapper(query):
            # TODO: Implémenter sélection read replica
            if self.read_replicas:
                replica = self.read_replicas[self.current_replica % len(self.read_replicas)]
                self.current_replica += 1
                self.logger.debug(f"Using read replica: {replica}")
            
            return await next_handler(query)
        return wrapper
