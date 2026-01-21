"""
Service d'intégration du cache Redis avec les opérations vectorielles d'AindusDB Core.

Ce module fait le pont entre les services vectorielles et le cache Redis,
implémentant les stratégies de mise en cache optimales pour améliorer
les performances des opérations d'embedding et de recherche.

Example:
    from app.services.cache_service import CacheService
    from app.core.cache import CacheManager
    
    # Initialiser avec cache
    cache_manager = CacheManager()
    await cache_manager.connect()
    cache_service = CacheService(cache_manager)
    
    # Utilisation avec fallback automatique
    embedding = await cache_service.get_or_compute_embedding(
        text="Hello world",
        compute_func=lambda: compute_embedding("Hello world")
    )
"""

from typing import List, Dict, Any, Optional, Callable, Awaitable
import hashlib
import time

from ..core.cache import CacheManager
from ..models.vector import VectorSearchRequest, VectorSearchResponse


class CacheService:
    """
    Service d'intégration cache pour AindusDB Core avec stratégies optimisées.
    
    Cette classe implémente les patterns de cache les plus efficaces pour
    les opérations vectorielles : cache-aside avec fallback automatique,
    invalidation intelligente et métriques de performance.
    
    Features:
    - Cache-aside pattern avec compute automatique
    - Stratégies TTL adaptatives selon le type de données
    - Invalidation en cascade pour cohérence
    - Métriques de hit/miss rate intégrées
    - Support des opérations batch avec cache parallèle
    
    Attributes:
        cache_manager: Instance du gestionnaire Redis
        hit_count: Compteur des cache hits
        miss_count: Compteur des cache miss
        
    Example:
        # Pattern cache-aside avec compute automatique
        embedding = await cache_service.get_or_compute_embedding(
            text="Machine learning vector database",
            model="sentence-transformers/all-MiniLM-L6-v2",
            compute_func=embedding_model.encode
        )
    """
    
    def __init__(self, cache_manager: CacheManager):
        """
        Initialiser le service de cache avec le gestionnaire Redis.
        
        Args:
            cache_manager: Instance connectée du CacheManager
        """
        self.cache_manager = cache_manager
        self.hit_count = 0
        self.miss_count = 0
        
    async def get_or_compute_embedding(self, 
                                     text: str, 
                                     model: str,
                                     compute_func: Callable[[], Awaitable[List[float]]],
                                     ttl: Optional[int] = None) -> List[float]:
        """
        Récupérer un embedding depuis le cache ou le calculer avec fallback automatique.
        
        Implémente le pattern cache-aside : vérifie le cache en premier,
        calcule et stocke si absent. Optimisé pour les embeddings avec
        déduplication automatique des textes identiques.
        
        Args:
            text: Texte source pour l'embedding
            model: Nom du modèle d'embedding 
            compute_func: Fonction async pour calculer l'embedding si absent
            ttl: TTL optionnel pour override
            
        Returns:
            List[float]: Vecteur d'embedding (depuis cache ou calculé)
            
        Example:
            # Avec modèle sentence-transformers
            async def compute_embedding():
                return model.encode([text])[0].tolist()
                
            embedding = await cache_service.get_or_compute_embedding(
                text="Document content here",
                model="all-MiniLM-L6-v2", 
                compute_func=compute_embedding,
                ttl=7200  # 2h cache
            )
        """
        # Générer la clé de cache
        cache_key = self.cache_manager.generate_embedding_key(text, model)
        
        # Tentative de récupération depuis le cache
        cached_embedding = await self.cache_manager.get_embedding(cache_key)
        
        if cached_embedding is not None:
            self.hit_count += 1
            return cached_embedding
            
        # Cache miss - calcul nécessaire
        self.miss_count += 1
        
        # Calculer l'embedding
        start_time = time.time()
        embedding = await compute_func()
        compute_time = time.time() - start_time
        
        # Stocker dans le cache avec métadonnées de performance
        metadata = {
            "model": model,
            "text_length": len(text),
            "compute_time_ms": round(compute_time * 1000, 2),
            "timestamp": int(time.time())
        }
        
        await self.cache_manager.set_embedding(
            cache_key, 
            embedding, 
            metadata=metadata,
            ttl=ttl
        )
        
        return embedding
    
    async def batch_get_or_compute_embeddings(self,
                                            texts: List[str],
                                            model: str,
                                            compute_func: Callable[[List[str]], Awaitable[List[List[float]]]],
                                            ttl: Optional[int] = None) -> List[List[float]]:
        """
        Traitement batch d'embeddings avec cache parallèle optimisé.
        
        Vérifie le cache pour tous les textes en parallèle, identifie
        ceux manquants, calcule seulement les nécessaires en batch
        et reconstitue l'ordre original.
        
        Args:
            texts: Liste des textes à traiter
            model: Nom du modèle d'embedding
            compute_func: Fonction batch pour calculer les embeddings manquants
            ttl: TTL optionnel
            
        Returns:
            List[List[float]]: Embeddings dans l'ordre original
            
        Example:
            # Traitement batch avec cache hybride
            async def compute_batch(texts):
                return model.encode(texts).tolist()
                
            embeddings = await cache_service.batch_get_or_compute_embeddings(
                texts=["doc1", "doc2", "doc3"],
                model="all-MiniLM-L6-v2",
                compute_func=compute_batch
            )
        """
        # Générer toutes les clés de cache
        cache_keys = [self.cache_manager.generate_embedding_key(text, model) 
                     for text in texts]
        
        # Récupération parallèle depuis le cache
        cached_results = []
        missing_indices = []
        missing_texts = []
        
        for i, (text, key) in enumerate(zip(texts, cache_keys)):
            cached_embedding = await self.cache_manager.get_embedding(key)
            
            if cached_embedding is not None:
                cached_results.append((i, cached_embedding))
                self.hit_count += 1
            else:
                missing_indices.append(i)
                missing_texts.append(text)
                self.miss_count += 1
        
        # Calculer les embeddings manquants en batch
        computed_embeddings = []
        if missing_texts:
            start_time = time.time()
            computed_embeddings = await compute_func(missing_texts)
            compute_time = time.time() - start_time
            
            # Stocker les nouveaux embeddings en cache
            for j, (text, embedding) in enumerate(zip(missing_texts, computed_embeddings)):
                cache_key = cache_keys[missing_indices[j]]
                metadata = {
                    "model": model,
                    "text_length": len(text),
                    "batch_size": len(missing_texts),
                    "batch_compute_time_ms": round(compute_time * 1000, 2),
                    "timestamp": int(time.time())
                }
                
                await self.cache_manager.set_embedding(
                    cache_key, 
                    embedding, 
                    metadata=metadata,
                    ttl=ttl
                )
        
        # Reconstituer l'ordre original
        results = [None] * len(texts)
        
        # Placer les résultats cachés
        for i, embedding in cached_results:
            results[i] = embedding
            
        # Placer les résultats calculés
        for j, i in enumerate(missing_indices):
            results[i] = computed_embeddings[j]
            
        return results
    
    async def cache_search_results(self, 
                                 request: VectorSearchRequest,
                                 results: VectorSearchResponse,
                                 ttl: Optional[int] = None) -> bool:
        """
        Mettre en cache les résultats de recherche vectorielle.
        
        Args:
            request: Requête de recherche originale
            results: Résultats à cacher
            ttl: TTL optionnel
            
        Returns:
            bool: True si mis en cache avec succès
            
        Example:
            search_request = VectorSearchRequest(
                query_vector=[0.1, 0.2, 0.3],
                limit=20,
                threshold=0.8
            )
            
            # Après recherche dans la DB
            cached = await cache_service.cache_search_results(
                search_request, search_response, ttl=300
            )
        """
        cache_key = self.cache_manager.generate_search_key(
            request.query_vector,
            request.limit,
            request.threshold
        )
        
        # Convertir la réponse en format cachable
        cache_results = [
            {
                "id": result.id,
                "metadata": result.metadata, 
                "distance": result.distance
            }
            for result in results.results
        ]
        
        return await self.cache_manager.set_search_results(
            cache_key, 
            cache_results, 
            ttl=ttl
        )
    
    async def get_cached_search_results(self, 
                                      request: VectorSearchRequest) -> Optional[List[Dict[str, Any]]]:
        """
        Récupérer les résultats de recherche depuis le cache.
        
        Args:
            request: Requête de recherche
            
        Returns:
            Optional[List[Dict[str, Any]]]: Résultats cachés ou None
            
        Example:
            cached_results = await cache_service.get_cached_search_results(request)
            if cached_results:
                # Utiliser les résultats cachés
                return VectorSearchResponse.from_cache(cached_results)
            else:
                # Effectuer la recherche en base
                return await vector_service.search_vectors(request)
        """
        cache_key = self.cache_manager.generate_search_key(
            request.query_vector,
            request.limit, 
            request.threshold
        )
        
        cached_results = await self.cache_manager.get_search_results(cache_key)
        if cached_results:
            self.hit_count += 1
            return cached_results
        
        self.miss_count += 1
        return None
    
    async def invalidate_model_cache(self, model: str) -> int:
        """
        Invalider tous les embeddings d'un modèle spécifique.
        
        Utile lors des mises à jour de modèles ou changements de versions.
        
        Args:
            model: Nom du modèle à invalider
            
        Returns:
            int: Nombre de clés supprimées
            
        Example:
            # Invalider après mise à jour de modèle
            deleted = await cache_service.invalidate_model_cache("old_model_v1")
            print(f"{deleted} embeddings invalidés pour old_model_v1")
        """
        pattern = f"{self.cache_manager.prefix}:embedding:{model}:*"
        return await self.cache_manager.invalidate_pattern(pattern)
    
    async def warm_up_cache(self, 
                          common_texts: List[str], 
                          model: str,
                          compute_func: Callable[[List[str]], Awaitable[List[List[float]]]]) -> int:
        """
        Préchauffer le cache avec des textes fréquemment utilisés.
        
        Stratégie proactive pour améliorer les performances lors
        du démarrage ou après invalidation de cache.
        
        Args:
            common_texts: Textes à précalculer et cacher
            model: Modèle d'embedding à utiliser
            compute_func: Fonction de calcul batch
            
        Returns:
            int: Nombre d'embeddings précalculés
            
        Example:
            # Préchauffage avec requêtes fréquentes
            common_queries = ["search query", "machine learning", "database"]
            warmed = await cache_service.warm_up_cache(
                common_queries, "sentence-transformers", compute_batch
            )
        """
        # Filtrer les textes déjà en cache
        texts_to_compute = []
        
        for text in common_texts:
            cache_key = self.cache_manager.generate_embedding_key(text, model)
            if await self.cache_manager.get_embedding(cache_key) is None:
                texts_to_compute.append(text)
        
        if not texts_to_compute:
            return 0
            
        # Calculer et cacher en batch
        await self.batch_get_or_compute_embeddings(
            texts_to_compute,
            model,
            compute_func
        )
        
        return len(texts_to_compute)
    
    def get_cache_performance_stats(self) -> Dict[str, Any]:
        """
        Obtenir les statistiques de performance du cache.
        
        Returns:
            Dict[str, Any]: Métriques hit/miss et performance
            
        Example:
            stats = cache_service.get_cache_performance_stats()
            print(f"Hit rate: {stats['hit_rate']:.2%}")
            print(f"Total requests: {stats['total_requests']}")
        """
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / max(1, total_requests)
        
        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'cache_efficiency': 'excellent' if hit_rate > 0.8 else 'good' if hit_rate > 0.5 else 'needs_optimization'
        }
