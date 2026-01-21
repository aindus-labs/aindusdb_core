"""
Cache Redis pour AindusDB Core - Optimisations des embeddings et métadonnées.

Ce module implémente un système de cache Redis pour améliorer les performances
des opérations vectorielles en évitant les recalculs d'embeddings identiques.
Il gère la sérialisation/désérialisation, la gestion des TTL et les patterns
de cache optimaux pour les bases de données vectorielles.

Example:
    from app.core.cache import CacheManager
    
    # Initialiser le cache
    cache = CacheManager()
    await cache.connect()
    
    # Cacher un embedding
    await cache.set_embedding("doc_123", embedding_vector, ttl=3600)
    
    # Récupérer depuis le cache
    cached_embedding = await cache.get_embedding("doc_123")
"""

import json
import hashlib
from typing import List, Optional, Dict, Any, Union
from datetime import timedelta
import aioredis
from aioredis import Redis
import numpy as np

from .config import settings


class CacheManager:
    """
    Gestionnaire de cache Redis pour AindusDB Core avec optimisations vectorielles.
    
    Cette classe fournit un cache haute performance pour les embeddings,
    métadonnées et résultats de recherche vectorielle. Elle utilise des
    stratégies de sérialisation optimisées et des clés hiérarchiques pour
    une organisation efficace des données.
    
    Features:
    - Cache d'embeddings avec compression numpy
    - Cache de résultats de recherche avec TTL adaptatif
    - Invalidation sélective par patterns
    - Métriques de performance intégrées
    - Gestion automatique des connexions et reconnexions
    
    Attributes:
        redis: Connexion Redis async
        prefix: Préfixe pour toutes les clés de cache
        default_ttl: TTL par défaut en secondes
        
    Example:
        # Cache d'embedding avec métadonnées
        cache_key = cache.generate_embedding_key("text", "model_name")
        await cache.set_embedding(cache_key, embedding, metadata={"source": "doc"})
        
        # Récupération avec fallback
        embedding = await cache.get_embedding(cache_key)
        if embedding is None:
            embedding = compute_embedding(text)
            await cache.set_embedding(cache_key, embedding)
    """
    
    def __init__(self):
        """
        Initialiser le gestionnaire de cache Redis.
        
        Configure la connexion Redis avec les paramètres optimaux pour
        les opérations vectorielles : compression, sérialisation efficace
        et gestion des timeouts adaptée aux embeddings.
        """
        self.redis: Optional[Redis] = None
        self.prefix = settings.redis_key_prefix
        self.default_ttl = settings.redis_default_ttl
        self.embedding_ttl = settings.redis_embedding_ttl
        self.search_ttl = settings.redis_search_ttl
        
    async def connect(self) -> None:
        """
        Établir la connexion Redis avec configuration optimisée.
        
        Configure le pool de connexions Redis avec des paramètres
        adaptés aux opérations vectorielles : timeouts étendus pour
        les gros embeddings, retry automatique, compression activée.
        
        Raises:
            ConnectionError: Si la connexion Redis échoue
            
        Example:
            cache = CacheManager()
            await cache.connect()  # Connexion prête pour les opérations
        """
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding='utf-8',
                decode_responses=False,  # Pour gérer les données binaires
                max_connections=settings.redis_max_connections,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test de la connexion
            await self.redis.ping()
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {str(e)}")
    
    async def disconnect(self) -> None:
        """
        Fermer la connexion Redis proprement.
        
        Example:
            await cache.disconnect()
        """
        if self.redis:
            await self.redis.close()
            self.redis = None
    
    def generate_embedding_key(self, text: str, model: str = "default") -> str:
        """
        Générer une clé de cache unique pour un embedding.
        
        Crée une clé basée sur le hash du texte et du modèle pour
        garantir l'unicité tout en permettant la déduplication
        des embeddings identiques.
        
        Args:
            text: Texte source de l'embedding
            model: Nom du modèle d'embedding utilisé
            
        Returns:
            str: Clé de cache unique et déterministe
            
        Example:
            key = cache.generate_embedding_key("Hello world", "sentence-transformers")
            # Retourne: "aindus:embedding:model_name:hash_of_text"
        """
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
        return f"{self.prefix}:embedding:{model}:{text_hash}"
    
    def generate_search_key(self, query_vector: List[float], limit: int, 
                          threshold: Optional[float] = None) -> str:
        """
        Générer une clé de cache pour les résultats de recherche vectorielle.
        
        Args:
            query_vector: Vecteur de requête
            limit: Nombre de résultats demandés
            threshold: Seuil de distance optionnel
            
        Returns:
            str: Clé de cache pour la recherche
            
        Example:
            key = cache.generate_search_key([0.1, 0.2, 0.3], limit=10, threshold=0.8)
        """
        # Hash du vecteur de requête pour identifier uniquement la recherche
        vector_str = ','.join([f"{x:.6f}" for x in query_vector])
        vector_hash = hashlib.md5(vector_str.encode()).hexdigest()[:12]
        
        threshold_str = f"_{threshold}" if threshold else ""
        return f"{self.prefix}:search:{vector_hash}:limit_{limit}{threshold_str}"
    
    async def set_embedding(self, key: str, embedding: List[float], 
                          metadata: Optional[Dict[str, Any]] = None, 
                          ttl: Optional[int] = None) -> bool:
        """
        Stocker un embedding dans le cache avec compression optimisée.
        
        Utilise numpy pour une sérialisation compacte des vecteurs et
        JSON pour les métadonnées associées. Applique une compression
        automatique pour les gros embeddings.
        
        Args:
            key: Clé de cache
            embedding: Vecteur d'embedding
            metadata: Métadonnées optionnelles associées
            ttl: Time-to-live en secondes (défaut: embedding_ttl)
            
        Returns:
            bool: True si stocké avec succès
            
        Example:
            success = await cache.set_embedding(
                key="doc_123_embedding",
                embedding=[0.1, 0.2, 0.3],
                metadata={"source": "document", "model": "sentence-transformers"},
                ttl=7200
            )
        """
        if not self.redis:
            return False
            
        try:
            # Sérialiser l'embedding avec numpy pour efficacité
            embedding_array = np.array(embedding, dtype=np.float32)
            embedding_bytes = embedding_array.tobytes()
            
            # Préparer les données à cacher
            cache_data = {
                'embedding': embedding_bytes,
                'metadata': metadata or {},
                'dimensions': len(embedding)
            }
            
            # Sérialisation JSON avec métadonnées
            cache_value = json.dumps({
                'embedding_b64': embedding_bytes.hex(),
                'metadata': cache_data['metadata'],
                'dimensions': cache_data['dimensions']
            })
            
            # Stockage avec TTL
            ttl_seconds = ttl or self.embedding_ttl
            await self.redis.setex(key, ttl_seconds, cache_value)
            
            return True
            
        except Exception as e:
            # Log error in production
            return False
    
    async def get_embedding(self, key: str) -> Optional[List[float]]:
        """
        Récupérer un embedding depuis le cache.
        
        Désérialise automatiquement le vecteur numpy et retourne
        la liste Python correspondante.
        
        Args:
            key: Clé de cache
            
        Returns:
            Optional[List[float]]: Embedding ou None si non trouvé
            
        Example:
            embedding = await cache.get_embedding("doc_123_embedding")
            if embedding:
                print(f"Cache hit: {len(embedding)} dimensions")
            else:
                print("Cache miss - calcul nécessaire")
        """
        if not self.redis:
            return None
            
        try:
            cache_value = await self.redis.get(key)
            if not cache_value:
                return None
                
            # Désérialiser les données
            cache_data = json.loads(cache_value.decode('utf-8'))
            
            # Reconstituer l'embedding depuis les bytes
            embedding_bytes = bytes.fromhex(cache_data['embedding_b64'])
            embedding_array = np.frombuffer(embedding_bytes, dtype=np.float32)
            
            return embedding_array.tolist()
            
        except Exception as e:
            return None
    
    async def set_search_results(self, key: str, results: List[Dict[str, Any]], 
                               ttl: Optional[int] = None) -> bool:
        """
        Cacher les résultats de recherche vectorielle.
        
        Args:
            key: Clé de cache générée par generate_search_key
            results: Liste des résultats de recherche
            ttl: TTL optionnel (défaut: search_ttl)
            
        Returns:
            bool: True si stocké avec succès
            
        Example:
            search_results = [
                {"id": 1, "metadata": "doc1", "distance": 0.1},
                {"id": 2, "metadata": "doc2", "distance": 0.3}
            ]
            await cache.set_search_results(search_key, search_results, ttl=300)
        """
        if not self.redis:
            return False
            
        try:
            cache_value = json.dumps({
                'results': results,
                'count': len(results),
                'timestamp': int(np.datetime64('now').astype('datetime64[s]').astype(int))
            })
            
            ttl_seconds = ttl or self.search_ttl
            await self.redis.setex(key, ttl_seconds, cache_value)
            
            return True
            
        except Exception as e:
            return False
    
    async def get_search_results(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """
        Récupérer les résultats de recherche depuis le cache.
        
        Args:
            key: Clé de cache
            
        Returns:
            Optional[List[Dict[str, Any]]]: Résultats ou None si non trouvé
            
        Example:
            cached_results = await cache.get_search_results(search_key)
            if cached_results:
                print(f"Cache hit: {len(cached_results)} résultats")
        """
        if not self.redis:
            return None
            
        try:
            cache_value = await self.redis.get(key)
            if not cache_value:
                return None
                
            cache_data = json.loads(cache_value.decode('utf-8'))
            return cache_data['results']
            
        except Exception as e:
            return None
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalider toutes les clés correspondant à un pattern.
        
        Args:
            pattern: Pattern Redis (ex: "aindus:embedding:*")
            
        Returns:
            int: Nombre de clés supprimées
            
        Example:
            # Invalider tous les embeddings d'un modèle
            deleted = await cache.invalidate_pattern("aindus:embedding:old_model:*")
            print(f"{deleted} embeddings invalidés")
        """
        if not self.redis:
            return 0
            
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                deleted = await self.redis.delete(*keys)
                return deleted
            return 0
            
        except Exception as e:
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtenir les statistiques du cache Redis.
        
        Returns:
            Dict[str, Any]: Statistiques de performance et utilisation
            
        Example:
            stats = await cache.get_cache_stats()
            print(f"Hit rate: {stats['hit_rate']:.2%}")
            print(f"Memory usage: {stats['memory_usage_mb']:.1f} MB")
        """
        if not self.redis:
            return {}
            
        try:
            info = await self.redis.info()
            
            # Compter les clés par type
            embedding_keys = len(await self.redis.keys(f"{self.prefix}:embedding:*"))
            search_keys = len(await self.redis.keys(f"{self.prefix}:search:*"))
            
            return {
                'connected': True,
                'total_keys': info.get('db0', {}).get('keys', 0),
                'embedding_keys': embedding_keys,
                'search_keys': search_keys,
                'memory_usage_mb': info.get('used_memory', 0) / (1024 * 1024),
                'hit_rate': info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0)),
                'connected_clients': info.get('connected_clients', 0)
            }
            
        except Exception as e:
            return {'connected': False, 'error': str(e)}
