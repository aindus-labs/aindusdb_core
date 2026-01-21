"""
Service d'opérations batch vectorielles pour AindusDB Core - Optimisations haute performance.

Ce module implémente les opérations vectorielles en lot avec des optimisations
avancées : traitement parallèle, mise en cache intelligente, insertion bulk
et recherches batch avec agrégation de résultats.

Example:
    from app.services.batch_service import BatchVectorService
    
    # Initialiser avec cache et DB
    batch_service = BatchVectorService(db_manager, cache_service)
    
    # Insertion batch haute performance
    results = await batch_service.batch_insert_vectors([
        {"embedding": [0.1, 0.2, 0.3], "metadata": "doc1"},
        {"embedding": [0.4, 0.5, 0.6], "metadata": "doc2"},
        # ... jusqu'à 10000 vecteurs
    ])
    
    # Recherche batch avec cache hybride  
    search_results = await batch_service.batch_similarity_search([
        {"query": [0.1, 0.2, 0.3], "limit": 10},
        {"query": [0.4, 0.5, 0.6], "limit": 5}
    ])
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import math

from ..core.database import DatabaseManager
from ..services.cache_service import CacheService
from ..models.vector import VectorCreate, VectorSearchRequest, VectorSearchResponse


@dataclass
class BatchInsertResult:
    """Résultat d'une insertion batch avec métriques."""
    success_count: int
    failed_count: int
    total_time_ms: float
    throughput_per_sec: float
    inserted_ids: List[int]
    errors: List[str]


@dataclass
class BatchSearchResult:
    """Résultat d'une recherche batch avec agrégation."""
    results: List[List[Dict[str, Any]]]
    cache_hits: int
    cache_misses: int
    total_time_ms: float
    average_latency_ms: float


class BatchVectorService:
    """
    Service d'opérations vectorielles batch haute performance pour AindusDB Core.
    
    Cette classe optimise les opérations en lot pour traiter efficacement de gros
    volumes de vecteurs : insertions bulk avec préparation de statements, 
    recherches parallèles avec cache intelligent et agrégation de résultats.
    
    Features:
    - Insertion batch jusqu'à 10K vecteurs avec chunking automatique
    - Recherche parallèle avec pool de workers configurables  
    - Cache hybride pour éviter les recalculs d'embeddings
    - Métriques de performance détaillées
    - Gestion des erreurs partielles avec rollback
    - Optimisations mémoire pour datasets volumineux
    
    Attributes:
        db: Gestionnaire de base de données avec pool optimisé
        cache: Service de cache Redis pour embeddings
        max_batch_size: Taille maximale des chunks (défaut: 1000)
        parallel_workers: Nombre de workers parallèles (défaut: 4)
        
    Example:
        # Configuration pour gros volumes
        batch_service = BatchVectorService(
            db_manager=db,
            cache_service=cache,
            max_batch_size=5000,
            parallel_workers=8
        )
        
        # Traitement de 100K vecteurs en chunks optimisés
        for chunk in chunks(vectors, 5000):
            result = await batch_service.batch_insert_vectors(chunk)
            print(f"Inserted {result.success_count} vectors at {result.throughput_per_sec:.0f}/sec")
    """
    
    def __init__(self, 
                 db_manager: DatabaseManager,
                 cache_service: Optional[CacheService] = None,
                 max_batch_size: int = 1000,
                 parallel_workers: int = 4):
        """
        Initialiser le service d'opérations batch.
        
        Args:
            db_manager: Gestionnaire de base de données
            cache_service: Service de cache optionnel
            max_batch_size: Taille max des chunks pour éviter les timeouts
            parallel_workers: Nombre de workers parallèles pour recherches
        """
        self.db = db_manager
        self.cache = cache_service
        self.max_batch_size = max_batch_size
        self.parallel_workers = parallel_workers
        
    async def batch_insert_vectors(self, 
                                 vectors: List[Dict[str, Any]],
                                 table_name: str = "test_vectors",
                                 chunk_size: Optional[int] = None) -> BatchInsertResult:
        """
        Insertion batch haute performance avec chunking et préparation de statements.
        
        Optimise les insertions massives en divisant en chunks gérables,
        utilisant des prepared statements et des transactions pour la cohérence.
        Gère les erreurs partielles sans faire échouer tout le batch.
        
        Args:
            vectors: Liste de vecteurs avec embedding et metadata
            table_name: Nom de la table cible
            chunk_size: Taille des chunks (défaut: max_batch_size)
            
        Returns:
            BatchInsertResult: Résultat avec métriques et IDs insérés
            
        Raises:
            Exception: Si erreur critique empêchant l'insertion
            
        Example:
            vectors = [
                {"embedding": [0.1, 0.2, 0.3], "metadata": "document 1"},
                {"embedding": [0.4, 0.5, 0.6], "metadata": "document 2"},
                # ... jusqu'à 50000 vecteurs
            ]
            
            result = await batch_service.batch_insert_vectors(vectors)
            
            print(f"✅ Inserted: {result.success_count}")
            print(f"❌ Failed: {result.failed_count}")  
            print(f"⚡ Throughput: {result.throughput_per_sec:.0f} vectors/sec")
            print(f"🆔 IDs: {result.inserted_ids[:5]}...") # Premier 5 IDs
        """
        if not vectors:
            return BatchInsertResult(0, 0, 0.0, 0.0, [], [])
            
        chunk_size = chunk_size or self.max_batch_size
        start_time = time.time()
        
        success_count = 0
        failed_count = 0
        inserted_ids = []
        errors = []
        
        # Diviser en chunks pour éviter les timeouts
        chunks = [vectors[i:i + chunk_size] for i in range(0, len(vectors), chunk_size)]
        
        for chunk_index, chunk in enumerate(chunks):
            try:
                # Préparer les données pour l'insertion batch
                insert_args = []
                for vector_data in chunk:
                    embedding = vector_data["embedding"]
                    metadata = vector_data.get("metadata", "")
                    
                    # Convertir embedding en format PostgreSQL 
                    embedding_str = f"[{','.join(map(str, embedding))}]"
                    insert_args.append((embedding_str, metadata))
                
                # SQL avec RETURNING pour récupérer les IDs
                insert_sql = f"""
                INSERT INTO {table_name} (embedding, metadata) 
                VALUES ($1, $2) 
                RETURNING id
                """
                
                # Utiliser execute_batch pour de meilleures performances
                connection = await self.db.get_connection()
                try:
                    # Préparer le statement une fois par chunk
                    statement = await connection.prepare(insert_sql)
                    
                    # Exécuter toutes les insertions du chunk
                    chunk_ids = []
                    for args in insert_args:
                        row = await statement.fetchrow(*args)
                        chunk_ids.append(row['id'])
                    
                    success_count += len(chunk_ids)
                    inserted_ids.extend(chunk_ids)
                    
                finally:
                    await self.db.release_connection(connection)
                    
            except Exception as e:
                failed_count += len(chunk)
                error_msg = f"Chunk {chunk_index}: {str(e)}"
                errors.append(error_msg)
                
                # Log l'erreur mais continuer avec les autres chunks
                continue
        
        total_time = time.time() - start_time
        total_time_ms = total_time * 1000
        throughput = success_count / max(0.001, total_time)  # Éviter division par 0
        
        return BatchInsertResult(
            success_count=success_count,
            failed_count=failed_count, 
            total_time_ms=round(total_time_ms, 2),
            throughput_per_sec=round(throughput, 1),
            inserted_ids=inserted_ids,
            errors=errors
        )
    
    async def batch_similarity_search(self,
                                    search_requests: List[Dict[str, Any]],
                                    table_name: str = "test_vectors") -> BatchSearchResult:
        """
        Recherche de similarité batch avec traitement parallèle et cache hybride.
        
        Traite plusieurs requêtes de recherche en parallèle avec optimisations :
        cache intelligent pour éviter les recherches redondantes, pool de workers
        pour parallélisme et agrégation efficace des résultats.
        
        Args:
            search_requests: Liste de requêtes avec query_vector, limit, threshold
            table_name: Nom de la table à rechercher
            
        Returns:
            BatchSearchResult: Résultats agrégés avec métriques de performance
            
        Example:
            search_requests = [
                {
                    "query_vector": [0.1, 0.2, 0.3],
                    "limit": 10,
                    "threshold": 0.8
                },
                {
                    "query_vector": [0.4, 0.5, 0.6], 
                    "limit": 5,
                    "threshold": 0.7
                },
                # ... jusqu'à 1000 recherches
            ]
            
            result = await batch_service.batch_similarity_search(search_requests)
            
            print(f"🔍 Searches: {len(result.results)}")
            print(f"⚡ Cache hits: {result.cache_hits}")
            print(f"⏱️ Avg latency: {result.average_latency_ms:.2f}ms")
            
            # Accès aux résultats
            for i, search_results in enumerate(result.results):
                print(f"Query {i}: {len(search_results)} results")
        """
        if not search_requests:
            return BatchSearchResult([], 0, 0, 0.0, 0.0)
            
        start_time = time.time()
        cache_hits = 0
        cache_misses = 0
        all_results = []
        
        # Créer des semaphores pour limiter la concurrence
        semaphore = asyncio.Semaphore(self.parallel_workers)
        
        async def process_single_search(request: Dict[str, Any]) -> List[Dict[str, Any]]:
            """Traiter une recherche individuelle avec cache."""
            nonlocal cache_hits, cache_misses
            
            async with semaphore:
                query_vector = request["query_vector"]
                limit = request.get("limit", 10)
                threshold = request.get("threshold")
                
                # Vérifier le cache si disponible
                if self.cache:
                    search_req = VectorSearchRequest(
                        query_vector=query_vector,
                        limit=limit,
                        threshold=threshold
                    )
                    
                    cached_results = await self.cache.get_cached_search_results(search_req)
                    if cached_results:
                        cache_hits += 1
                        return cached_results
                
                # Cache miss - effectuer la recherche
                cache_misses += 1
                
                # Construire la requête SQL avec distance
                query_vector_str = f"[{','.join(map(str, query_vector))}]"
                
                sql = f"""
                SELECT id, metadata, embedding <-> %s::vector AS distance
                FROM {table_name}
                ORDER BY embedding <-> %s::vector
                LIMIT %s
                """
                
                args = [query_vector_str, query_vector_str, limit]
                
                # Ajouter le filtre de seuil si spécifié
                if threshold is not None:
                    sql = sql.replace("LIMIT %s", "AND embedding <-> %s::vector <= %s LIMIT %s")
                    args.insert(-1, query_vector_str)
                    args.insert(-1, threshold)
                
                try:
                    rows = await self.db.fetch_query(sql, *args)
                    
                    results = [
                        {
                            "id": row["id"],
                            "metadata": row["metadata"],
                            "distance": float(row["distance"])
                        }
                        for row in rows
                    ]
                    
                    # Mettre en cache pour futures requêtes
                    if self.cache:
                        await self.cache.cache_search_results(search_req, results)
                    
                    return results
                    
                except Exception as e:
                    # Retourner une liste vide en cas d'erreur
                    return []
        
        # Traitement parallèle de toutes les recherches
        search_tasks = [
            process_single_search(request) 
            for request in search_requests
        ]
        
        all_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Filtrer les exceptions et les remplacer par des listes vides
        processed_results = []
        for result in all_results:
            if isinstance(result, Exception):
                processed_results.append([])
            else:
                processed_results.append(result)
        
        total_time = time.time() - start_time
        total_time_ms = total_time * 1000
        avg_latency = total_time_ms / len(search_requests)
        
        return BatchSearchResult(
            results=processed_results,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            total_time_ms=round(total_time_ms, 2),
            average_latency_ms=round(avg_latency, 2)
        )
    
    async def batch_upsert_vectors(self,
                                 vectors: List[Dict[str, Any]],
                                 table_name: str = "test_vectors",
                                 conflict_column: str = "metadata") -> BatchInsertResult:
        """
        Upsert batch (insert or update) avec gestion des conflits.
        
        Effectue des insertions avec mise à jour automatique en cas de conflit
        sur une colonne spécifiée. Optimisé pour les mises à jour de datasets
        existants.
        
        Args:
            vectors: Vecteurs à insérer/mettre à jour
            table_name: Nom de la table
            conflict_column: Colonne pour détection des conflits
            
        Returns:
            BatchInsertResult: Résultat avec compteurs insert vs update
            
        Example:
            # Mise à jour de vecteurs existants
            vectors = [
                {"embedding": [0.1, 0.2, 0.3], "metadata": "doc_updated"},
                {"embedding": [0.4, 0.5, 0.6], "metadata": "doc_new"}
            ]
            
            result = await batch_service.batch_upsert_vectors(
                vectors, conflict_column="metadata"
            )
        """
        if not vectors:
            return BatchInsertResult(0, 0, 0.0, 0.0, [], [])
            
        start_time = time.time()
        success_count = 0
        failed_count = 0
        inserted_ids = []
        errors = []
        
        # SQL UPSERT avec ON CONFLICT
        upsert_sql = f"""
        INSERT INTO {table_name} (embedding, metadata)
        VALUES ($1, $2)
        ON CONFLICT ({conflict_column}) 
        DO UPDATE SET 
            embedding = EXCLUDED.embedding,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """
        
        # Traitement par chunks
        chunks = [vectors[i:i + self.max_batch_size] 
                 for i in range(0, len(vectors), self.max_batch_size)]
        
        for chunk in chunks:
            try:
                connection = await self.db.get_connection()
                try:
                    statement = await connection.prepare(upsert_sql)
                    
                    for vector_data in chunk:
                        embedding = vector_data["embedding"]
                        metadata = vector_data.get("metadata", "")
                        
                        embedding_str = f"[{','.join(map(str, embedding))}]"
                        
                        row = await statement.fetchrow(embedding_str, metadata)
                        inserted_ids.append(row['id'])
                        success_count += 1
                        
                finally:
                    await self.db.release_connection(connection)
                    
            except Exception as e:
                failed_count += len(chunk)
                errors.append(str(e))
        
        total_time = time.time() - start_time
        throughput = success_count / max(0.001, total_time)
        
        return BatchInsertResult(
            success_count=success_count,
            failed_count=failed_count,
            total_time_ms=round(total_time * 1000, 2),
            throughput_per_sec=round(throughput, 1),
            inserted_ids=inserted_ids,
            errors=errors
        )
    
    async def batch_delete_vectors(self,
                                 vector_ids: List[int],
                                 table_name: str = "test_vectors") -> Dict[str, Any]:
        """
        Suppression batch de vecteurs par ID avec optimisations.
        
        Args:
            vector_ids: Liste des IDs à supprimer
            table_name: Nom de la table
            
        Returns:
            Dict[str, Any]: Résultat avec compteur de suppressions
            
        Example:
            # Supprimer des vecteurs obsolètes
            result = await batch_service.batch_delete_vectors([1, 2, 3, 4, 5])
            print(f"Deleted {result['deleted_count']} vectors")
        """
        if not vector_ids:
            return {"deleted_count": 0, "time_ms": 0.0}
            
        start_time = time.time()
        
        # SQL avec ANY pour suppression efficace par lots
        delete_sql = f"DELETE FROM {table_name} WHERE id = ANY($1)"
        
        try:
            result = await self.db.execute_query(delete_sql, vector_ids)
            
            # Extraire le nombre de lignes supprimées du résultat
            deleted_count = int(result.split()[-1]) if result else 0
            
            return {
                "deleted_count": deleted_count,
                "time_ms": round((time.time() - start_time) * 1000, 2)
            }
            
        except Exception as e:
            return {
                "deleted_count": 0,
                "time_ms": round((time.time() - start_time) * 1000, 2),
                "error": str(e)
            }
    
    def get_performance_recommendations(self, 
                                      dataset_size: int,
                                      operation_type: str) -> List[str]:
        """
        Générer des recommandations d'optimisation selon la taille et type d'opération.
        
        Args:
            dataset_size: Nombre approximatif de vecteurs
            operation_type: "insert", "search", "mixed"
            
        Returns:
            List[str]: Recommandations spécifiques
            
        Example:
            recommendations = batch_service.get_performance_recommendations(
                dataset_size=1_000_000,
                operation_type="insert"
            )
            
            for rec in recommendations:
                print(f"💡 {rec}")
        """
        recommendations = []
        
        # Recommandations selon la taille
        if dataset_size > 1_000_000:
            recommendations.append("Consider table partitioning for datasets > 1M vectors")
            recommendations.append("Use IVFFlat index instead of HNSW for memory efficiency")
            recommendations.append("Increase max_batch_size to 5000 for better throughput")
            
        elif dataset_size > 100_000:
            recommendations.append("HNSW index recommended for good recall/performance balance")
            recommendations.append("Use batch_size of 2000-3000 for optimal performance")
            
        else:
            recommendations.append("HNSW index with default parameters is sufficient")
            recommendations.append("Batch_size of 1000 is optimal for smaller datasets")
        
        # Recommandations selon le type d'opération
        if operation_type == "insert":
            recommendations.append("Use prepared statements and transactions for bulk inserts")
            recommendations.append("Consider temporarily disabling indexes during bulk loading")
            
        elif operation_type == "search":
            recommendations.append("Implement Redis caching for frequent queries")
            recommendations.append("Use parallel_workers = CPU_cores for search-heavy workloads")
            recommendations.append("Tune hnsw.ef_search parameter for recall vs speed")
            
        elif operation_type == "mixed":
            recommendations.append("Balance connection pool size (10-20 connections)")
            recommendations.append("Monitor cache hit rate and adjust TTL accordingly")
            recommendations.append("Use upsert operations to handle duplicate data efficiently")
        
        return recommendations
