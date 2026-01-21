"""
Optimisations d'indexation pgvector pour AindusDB Core.

Ce module implémente les stratégies d'indexation avancées pour pgvector :
configuration HNSW et IVFFlat, paramètres adaptatifs, monitoring des performances
et maintenance automatique des index pour optimiser les recherches vectorielles.

Example:
    from app.core.indexing import IndexManager
    
    # Initialiser le gestionnaire d'index
    index_manager = IndexManager(db_manager)
    
    # Créer index HNSW optimisé
    await index_manager.create_hnsw_index(
        table_name="vectors",
        dimensions=384,
        m=32,  # Connexions par noeud
        ef_construction=128  # Paramètre de construction
    )
    
    # Analyser et optimiser automatiquement
    stats = await index_manager.analyze_index_performance("vectors")
"""

from typing import Dict, Any, Optional, List, Tuple
import asyncio
import time
import math

from .database import DatabaseManager


class IndexManager:
    """
    Gestionnaire d'optimisations pgvector avec stratégies d'indexation avancées.
    
    Cette classe implémente les meilleures pratiques pour les index vectoriels :
    - Configuration adaptative HNSW selon la taille des données
    - Optimisation IVFFlat pour cas spécifiques  
    - Monitoring continu des performances
    - Maintenance automatique et re-indexation intelligente
    - Paramètres dynamiques selon les patterns d'usage
    
    Features:
    - Auto-tuning des paramètres HNSW selon dataset size
    - Comparaison performance HNSW vs IVFFlat 
    - Monitoring temps de requête et recall
    - Re-indexation progressive sans downtime
    - Optimisation mémoire et stockage
    
    Attributes:
        db: Gestionnaire de base de données
        index_stats: Cache des statistiques d'index
        
    Example:
        # Configuration automatique selon taille
        await index_manager.auto_configure_indexes(
            table_name="vectors",
            expected_size=1_000_000,
            query_pattern="similarity_search"  
        )
        
        # Monitoring continu
        performance = await index_manager.monitor_query_performance(
            duration_minutes=60
        )
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialiser le gestionnaire d'index pgvector.
        
        Args:
            db_manager: Instance du gestionnaire de base de données
        """
        self.db = db_manager
        self.index_stats = {}
        
    async def create_hnsw_index(self, 
                              table_name: str,
                              column_name: str = "embedding",
                              dimensions: int = 384,
                              m: int = 16,
                              ef_construction: int = 64,
                              distance_function: str = "cosine") -> Dict[str, Any]:
        """
        Créer un index HNSW optimisé avec paramètres adaptatifs.
        
        HNSW (Hierarchical Navigable Small World) est optimal pour la plupart
        des cas d'usage de recherche vectorielle. Cette méthode configure
        automatiquement les paramètres selon la taille prévue du dataset.
        
        Args:
            table_name: Nom de la table à indexer
            column_name: Nom de la colonne vectorielle
            dimensions: Nombre de dimensions des vecteurs
            m: Connexions par noeud (16-64, défaut adaptatif)
            ef_construction: Paramètre de construction (64-512)
            distance_function: "cosine", "l2", ou "inner_product"
            
        Returns:
            Dict[str, Any]: Informations sur l'index créé et temps de création
            
        Raises:
            Exception: Si la création de l'index échoue
            
        Example:
            # Index HNSW pour embeddings text (384D)
            result = await index_manager.create_hnsw_index(
                table_name="document_vectors",
                dimensions=384,
                m=32,  # Plus de connexions pour precision
                ef_construction=128,
                distance_function="cosine"
            )
            
            print(f"Index créé en {result['creation_time_ms']}ms")
            print(f"Estimated memory: {result['memory_estimate_mb']:.1f}MB")
        """
        # Adapter les paramètres selon les dimensions et usage
        optimal_m, optimal_ef = self._calculate_optimal_hnsw_params(dimensions, m, ef_construction)
        
        # Nom de l'index
        index_name = f"idx_{table_name}_{column_name}_hnsw"
        
        # Mappage des fonctions de distance
        distance_ops = {
            "cosine": "vector_cosine_ops",
            "l2": "vector_l2_ops", 
            "inner_product": "vector_ip_ops"
        }
        
        if distance_function not in distance_ops:
            raise ValueError(f"Distance function '{distance_function}' not supported")
            
        ops_class = distance_ops[distance_function]
        
        # SQL pour créer l'index HNSW
        create_index_sql = f"""
        CREATE INDEX CONCURRENTLY {index_name} 
        ON {table_name} 
        USING hnsw ({column_name} {ops_class}) 
        WITH (m = {optimal_m}, ef_construction = {optimal_ef})
        """
        
        try:
            start_time = time.time()
            
            # Créer l'index de manière non-bloquante
            await self.db.execute_query(create_index_sql)
            
            creation_time = (time.time() - start_time) * 1000
            
            # Collecter les statistiques de l'index
            stats = await self._collect_index_statistics(table_name, index_name)
            
            # Estimer l'usage mémoire
            memory_estimate = self._estimate_hnsw_memory_usage(
                stats.get('estimated_rows', 0), 
                dimensions, 
                optimal_m
            )
            
            result = {
                'index_name': index_name,
                'table_name': table_name,
                'index_type': 'hnsw',
                'parameters': {
                    'm': optimal_m,
                    'ef_construction': optimal_ef,
                    'dimensions': dimensions,
                    'distance_function': distance_function
                },
                'creation_time_ms': round(creation_time, 2),
                'memory_estimate_mb': round(memory_estimate, 1),
                'statistics': stats
            }
            
            # Cacher les stats pour monitoring
            self.index_stats[index_name] = result
            
            return result
            
        except Exception as e:
            raise Exception(f"Failed to create HNSW index: {str(e)}")
    
    async def create_ivfflat_index(self,
                                 table_name: str, 
                                 column_name: str = "embedding",
                                 lists: Optional[int] = None,
                                 distance_function: str = "cosine") -> Dict[str, Any]:
        """
        Créer un index IVFFlat pour datasets très larges avec recherche approximative.
        
        IVFFlat est plus efficace en mémoire pour de très gros datasets (>1M vecteurs)
        mais avec une précision légèrement moindre que HNSW. Le paramètre 'lists'
        est calculé automatiquement selon la règle sqrt(rows/1000).
        
        Args:
            table_name: Nom de la table à indexer
            column_name: Nom de la colonne vectorielle
            lists: Nombre de clusters IVF (auto-calculé si None)
            distance_function: Fonction de distance
            
        Returns:
            Dict[str, Any]: Informations sur l'index IVFFlat créé
            
        Example:
            # Index IVFFlat pour gros dataset
            result = await index_manager.create_ivfflat_index(
                table_name="large_vectors",
                lists=1000,  # Pour ~1M de vecteurs
                distance_function="l2"
            )
        """
        # Estimer le nombre optimal de clusters si non spécifié
        if lists is None:
            row_count = await self._estimate_table_rows(table_name)
            lists = max(100, min(int(math.sqrt(row_count / 1000)), 10000))
        
        index_name = f"idx_{table_name}_{column_name}_ivfflat"
        
        distance_ops = {
            "cosine": "vector_cosine_ops",
            "l2": "vector_l2_ops",
            "inner_product": "vector_ip_ops"
        }
        
        ops_class = distance_ops[distance_function]
        
        create_index_sql = f"""
        CREATE INDEX CONCURRENTLY {index_name} 
        ON {table_name} 
        USING ivfflat ({column_name} {ops_class}) 
        WITH (lists = {lists})
        """
        
        try:
            start_time = time.time()
            await self.db.execute_query(create_index_sql)
            creation_time = (time.time() - start_time) * 1000
            
            stats = await self._collect_index_statistics(table_name, index_name)
            
            result = {
                'index_name': index_name,
                'table_name': table_name,
                'index_type': 'ivfflat',
                'parameters': {
                    'lists': lists,
                    'distance_function': distance_function
                },
                'creation_time_ms': round(creation_time, 2),
                'statistics': stats
            }
            
            self.index_stats[index_name] = result
            return result
            
        except Exception as e:
            raise Exception(f"Failed to create IVFFlat index: {str(e)}")
    
    async def optimize_query_parameters(self, 
                                      table_name: str,
                                      target_recall: float = 0.95) -> Dict[str, Any]:
        """
        Optimiser automatiquement les paramètres de requête pour un recall cible.
        
        Ajuste les paramètres ef_search (HNSW) ou probes (IVFFlat) pour atteindre
        le niveau de rappel souhaité avec les meilleures performances possibles.
        
        Args:
            table_name: Nom de la table avec index vectoriel
            target_recall: Niveau de rappel cible (0.9-0.99)
            
        Returns:
            Dict[str, Any]: Paramètres optimaux et métriques
            
        Example:
            # Auto-tuning pour 95% de recall
            optimal = await index_manager.optimize_query_parameters(
                table_name="vectors",
                target_recall=0.95
            )
            
            # Appliquer les paramètres optimaux
            await db.execute_query(f"SET hnsw.ef_search = {optimal['ef_search']}")
        """
        # Identifier le type d'index présent
        index_info = await self._get_table_indexes(table_name)
        
        if not index_info:
            raise Exception(f"No vector indexes found on table {table_name}")
            
        index_type = index_info[0]['type']
        
        if index_type == 'hnsw':
            return await self._optimize_hnsw_parameters(table_name, target_recall)
        elif index_type == 'ivfflat':
            return await self._optimize_ivfflat_parameters(table_name, target_recall)
        else:
            raise Exception(f"Unsupported index type: {index_type}")
    
    async def benchmark_index_performance(self, 
                                        table_name: str,
                                        num_queries: int = 100) -> Dict[str, Any]:
        """
        Benchmark complet des performances d'index avec métriques détaillées.
        
        Exécute une série de requêtes de test pour mesurer la latence,
        le throughput et la qualité des résultats de l'index vectoriel.
        
        Args:
            table_name: Table à benchmarker
            num_queries: Nombre de requêtes de test
            
        Returns:
            Dict[str, Any]: Métriques de performance complètes
            
        Example:
            # Benchmark après création d'index
            perf = await index_manager.benchmark_index_performance("vectors", 200)
            
            print(f"Latence moyenne: {perf['avg_latency_ms']:.2f}ms")
            print(f"QPS max: {perf['max_qps']:.0f}")
            print(f"Recall@10: {perf['recall_at_k'][10]:.3f}")
        """
        # Générer des vecteurs de requête de test
        test_vectors = await self._generate_test_vectors(table_name, num_queries)
        
        # Mesurer les performances
        latencies = []
        recalls = []
        
        start_benchmark = time.time()
        
        for test_vector in test_vectors:
            # Mesurer une requête individuelle
            start_query = time.time()
            
            # Requête avec index (approximative)
            approx_results = await self._execute_vector_search(
                table_name, 
                test_vector,
                limit=10
            )
            
            query_latency = (time.time() - start_query) * 1000
            latencies.append(query_latency)
            
            # Mesurer le recall vs recherche exacte (sur échantillon)
            if len(recalls) < 20:  # Échantillonnage pour éviter surcharge
                exact_results = await self._execute_exact_search(
                    table_name,
                    test_vector, 
                    limit=10
                )
                recall = self._calculate_recall(approx_results, exact_results)
                recalls.append(recall)
        
        total_benchmark_time = time.time() - start_benchmark
        
        # Calculer les métriques
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        p99_latency = sorted(latencies)[int(0.99 * len(latencies))]
        max_qps = num_queries / total_benchmark_time
        avg_recall = sum(recalls) / len(recalls) if recalls else 0
        
        return {
            'table_name': table_name,
            'num_queries': num_queries,
            'total_time_seconds': round(total_benchmark_time, 2),
            'avg_latency_ms': round(avg_latency, 2),
            'p95_latency_ms': round(p95_latency, 2),
            'p99_latency_ms': round(p99_latency, 2),
            'max_qps': round(max_qps, 1),
            'avg_recall': round(avg_recall, 3),
            'performance_grade': self._grade_performance(avg_latency, avg_recall)
        }
    
    async def auto_configure_indexes(self,
                                   table_name: str,
                                   expected_size: int,
                                   query_pattern: str = "mixed") -> Dict[str, Any]:
        """
        Configuration automatique d'index selon la taille et patterns d'usage.
        
        Analyse les besoins et choisit automatiquement entre HNSW et IVFFlat
        avec les paramètres optimaux selon le dataset et usage prévu.
        
        Args:
            table_name: Nom de la table
            expected_size: Taille prévue du dataset
            query_pattern: "similarity_search", "batch_processing", "mixed"
            
        Returns:
            Dict[str, Any]: Configuration appliquée et recommandations
            
        Example:
            # Auto-configuration pour gros dataset
            config = await index_manager.auto_configure_indexes(
                table_name="vectors",
                expected_size=5_000_000,
                query_pattern="similarity_search"
            )
        """
        # Analyser le dataset existant
        current_size = await self._estimate_table_rows(table_name)
        dimensions = await self._detect_vector_dimensions(table_name)
        
        # Choisir la stratégie d'indexation
        if expected_size < 100_000:
            # Petits datasets : HNSW avec paramètres conservateurs
            strategy = "hnsw_small"
            params = {"m": 16, "ef_construction": 64}
        elif expected_size < 1_000_000:
            # Datasets moyens : HNSW optimisé  
            strategy = "hnsw_medium"
            params = {"m": 32, "ef_construction": 128}
        else:
            # Gros datasets : Comparer HNSW vs IVFFlat
            if query_pattern == "similarity_search":
                strategy = "hnsw_large"
                params = {"m": 64, "ef_construction": 256}
            else:
                strategy = "ivfflat_large" 
                lists = max(1000, int(math.sqrt(expected_size / 1000)))
                params = {"lists": lists}
        
        # Appliquer la configuration
        if strategy.startswith("hnsw"):
            result = await self.create_hnsw_index(
                table_name=table_name,
                dimensions=dimensions,
                **params
            )
        else:
            result = await self.create_ivfflat_index(
                table_name=table_name,
                **params
            )
        
        # Optimiser les paramètres de requête
        query_params = await self.optimize_query_parameters(table_name)
        
        return {
            'strategy': strategy,
            'table_name': table_name,
            'expected_size': expected_size,
            'current_size': current_size,
            'dimensions': dimensions,
            'index_config': result,
            'query_params': query_params,
            'recommendations': self._generate_recommendations(
                expected_size, dimensions, query_pattern
            )
        }
    
    # Méthodes utilitaires privées
    
    def _calculate_optimal_hnsw_params(self, dimensions: int, m: int, ef_construction: int) -> Tuple[int, int]:
        """Calculer les paramètres HNSW optimaux selon les dimensions."""
        # Adapter M selon les dimensions
        if dimensions <= 128:
            optimal_m = max(16, m)
        elif dimensions <= 512:
            optimal_m = max(32, m) 
        else:
            optimal_m = max(48, m)
            
        # Adapter ef_construction selon M
        optimal_ef = max(ef_construction, optimal_m * 2)
        
        return optimal_m, optimal_ef
    
    def _estimate_hnsw_memory_usage(self, rows: int, dimensions: int, m: int) -> float:
        """Estimer l'usage mémoire d'un index HNSW en MB."""
        if rows == 0:
            return 0.0
            
        # Formule approximative : (dimensions * 4 + m * 8) * rows / 1024^2
        bytes_per_vector = (dimensions * 4) + (m * 8)  # float32 + connexions
        total_bytes = bytes_per_vector * rows * 1.2  # Facteur overhead
        return total_bytes / (1024 * 1024)
    
    async def _collect_index_statistics(self, table_name: str, index_name: str) -> Dict[str, Any]:
        """Collecter les statistiques d'un index."""
        stats_query = """
        SELECT 
            schemaname, tablename, indexname,
            idx_scan, idx_tup_read, idx_tup_fetch
        FROM pg_stat_user_indexes 
        WHERE indexname = $1
        """
        
        size_query = "SELECT pg_size_pretty(pg_relation_size($1)) as size"
        
        try:
            stats = await self.db.fetchrow_query(stats_query, index_name)
            size_result = await self.db.fetchrow_query(size_query, index_name)
            
            return {
                'index_name': index_name,
                'scans': stats['idx_scan'] if stats else 0,
                'tuples_read': stats['idx_tup_read'] if stats else 0,
                'size': size_result['size'] if size_result else "0 bytes",
                'estimated_rows': await self._estimate_table_rows(table_name)
            }
            
        except Exception:
            return {'index_name': index_name, 'error': 'Could not collect statistics'}
    
    async def _estimate_table_rows(self, table_name: str) -> int:
        """Estimer le nombre de lignes dans une table."""
        query = """
        SELECT reltuples::bigint as estimate 
        FROM pg_class 
        WHERE relname = $1
        """
        
        try:
            result = await self.db.fetchval_query(query, table_name)
            return int(result) if result else 0
        except Exception:
            return 0
    
    async def _detect_vector_dimensions(self, table_name: str) -> int:
        """Détecter le nombre de dimensions des vecteurs."""
        query = f"SELECT array_length(embedding, 1) as dims FROM {table_name} LIMIT 1"
        
        try:
            dims = await self.db.fetchval_query(query)
            return int(dims) if dims else 384  # Default
        except Exception:
            return 384
    
    def _generate_recommendations(self, size: int, dimensions: int, pattern: str) -> List[str]:
        """Générer des recommandations d'optimisation."""
        recommendations = []
        
        if size > 1_000_000:
            recommendations.append("Consider partitioning for datasets > 1M vectors")
            
        if dimensions > 1000:
            recommendations.append("High-dimensional vectors may benefit from dimensionality reduction")
            
        if pattern == "batch_processing":
            recommendations.append("Consider using connection pooling for batch operations")
            
        recommendations.append("Monitor query performance and adjust ef_search/probes accordingly")
        
        return recommendations
    
    def _grade_performance(self, avg_latency: float, avg_recall: float) -> str:
        """Évaluer la performance globale."""
        if avg_latency < 10 and avg_recall > 0.95:
            return "excellent"
        elif avg_latency < 50 and avg_recall > 0.90:
            return "good"  
        elif avg_latency < 100 and avg_recall > 0.85:
            return "acceptable"
        else:
            return "needs_optimization"
