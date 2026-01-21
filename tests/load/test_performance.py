"""
Tests de charge et performance pour AindusDB Core
"""
import pytest
import asyncio
import time
import statistics
from httpx import AsyncClient
import asyncpg
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

from app.core.database import DatabaseManager
from app.services.vector_service import VectorService


@pytest.mark.asyncio
@pytest.mark.slow
class TestAPIPerformance:
    """Tests de performance API"""

    async def test_health_endpoint_performance(self, client: AsyncClient):
        """Test performance endpoint /health"""
        response_times = []
        
        # Effectuer 50 requêtes
        for _ in range(50):
            start_time = time.time()
            response = await client.get("/health")
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            # Chaque requête doit réussir ou échouer proprement
            assert response.status_code in [200, 503]
        
        # Analyser les performances
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        print(f"\nHealth endpoint performance:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Max: {max_time:.3f}s") 
        print(f"  Min: {min_time:.3f}s")
        
        # Critères de performance
        assert avg_time < 0.1, f"Average response time {avg_time:.3f}s too slow"
        assert max_time < 0.5, f"Max response time {max_time:.3f}s too slow"

    async def test_vector_operations_performance(self, client: AsyncClient):
        """Test performance opérations vectorielles"""
        response_times = []
        
        # Effectuer 20 tests vectoriels (plus lourds)
        for _ in range(20):
            start_time = time.time()
            response = await client.post("/vectors/test")
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            # Peut être 200 (succès) ou 500 (DB indisponible)
            assert response.status_code in [200, 500]
        
        if response_times:
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            
            print(f"\nVector operations performance:")
            print(f"  Average: {avg_time:.3f}s")
            print(f"  Max: {max_time:.3f}s")
            
            # Critères pour opérations vectorielles (plus permissifs)
            assert avg_time < 2.0, f"Average vector operation {avg_time:.3f}s too slow"
            assert max_time < 5.0, f"Max vector operation {max_time:.3f}s too slow"

    async def test_concurrent_api_requests(self, client: AsyncClient):
        """Test requêtes API concurrentes"""
        async def make_request(endpoint: str) -> Dict[str, Any]:
            start_time = time.time()
            response = await client.get(endpoint)
            end_time = time.time()
            
            return {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response_time": end_time - start_time
            }
        
        # Créer 30 requêtes concurrentes sur différents endpoints
        tasks = []
        endpoints = ["/", "/health", "/metrics"] * 10  # 10 de chaque
        
        for endpoint in endpoints:
            tasks.append(make_request(endpoint))
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        print(f"\nConcurrent requests performance:")
        print(f"  Total time for {len(tasks)} requests: {total_time:.3f}s")
        print(f"  Average per request: {total_time/len(tasks):.3f}s")
        
        # Analyser les résultats
        success_count = sum(1 for r in results if r["status_code"] == 200)
        error_count = len(results) - success_count
        
        print(f"  Successful requests: {success_count}/{len(results)}")
        print(f"  Failed requests: {error_count}")
        
        # Critères de performance concurrente
        assert total_time < 10.0, f"30 concurrent requests took {total_time:.3f}s"
        assert success_count >= len(results) * 0.8, "Too many failed requests"

    async def test_api_memory_stress(self, client: AsyncClient):
        """Test stress mémoire API"""
        # Effectuer beaucoup de requêtes rapidement
        request_count = 100
        
        start_time = time.time()
        
        for i in range(request_count):
            response = await client.get("/")
            assert response.status_code == 200
            
            # Petit délai pour éviter de surcharger
            if i % 20 == 0:
                await asyncio.sleep(0.01)
        
        total_time = time.time() - start_time
        
        print(f"\nMemory stress test:")
        print(f"  {request_count} requests in {total_time:.3f}s")
        print(f"  Rate: {request_count/total_time:.1f} req/s")
        
        # Vérifier performance acceptable
        assert total_time < 30.0, f"Memory stress test too slow: {total_time:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
class TestDatabasePerformance:
    """Tests de performance base de données"""

    async def test_database_connection_pool_performance(self, test_db):
        """Test performance pool de connexions"""
        db_manager = DatabaseManager()
        db_manager.pool = await asyncpg.create_pool(
            test_db, 
            min_size=5, 
            max_size=20,
            command_timeout=60
        )
        
        try:
            async def db_operation(operation_id: int) -> Dict[str, Any]:
                start_time = time.time()
                
                try:
                    result = await db_manager.fetchval_query(f"SELECT {operation_id}")
                    success = True
                    error = None
                except Exception as e:
                    result = None
                    success = False
                    error = str(e)
                
                return {
                    "operation_id": operation_id,
                    "success": success,
                    "result": result,
                    "error": error,
                    "duration": time.time() - start_time
                }
            
            # Lancer 50 opérations concurrentes
            tasks = [db_operation(i) for i in range(50)]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            # Analyser résultats
            successful = [r for r in results if r["success"]]
            failed = [r for r in results if not r["success"]]
            
            if successful:
                avg_duration = statistics.mean([r["duration"] for r in successful])
                max_duration = max([r["duration"] for r in successful])
                
                print(f"\nDatabase pool performance:")
                print(f"  Total time: {total_time:.3f}s")
                print(f"  Successful operations: {len(successful)}/50")
                print(f"  Average operation time: {avg_duration:.3f}s")
                print(f"  Max operation time: {max_duration:.3f}s")
                
                # Critères de performance
                assert len(successful) >= 45, "Too many failed DB operations"
                assert avg_duration < 0.1, f"Average DB operation too slow: {avg_duration:.3f}s"
                assert total_time < 5.0, f"50 concurrent DB ops too slow: {total_time:.3f}s"
            
            if failed:
                print(f"  Failed operations: {len(failed)}")
                for fail in failed[:3]:  # Montrer les 3 premières erreurs
                    print(f"    {fail['operation_id']}: {fail['error']}")
        
        finally:
            await db_manager.disconnect()

    async def test_vector_bulk_insert_performance(self, test_db, test_helpers):
        """Test performance insertion en masse de vecteurs"""
        conn = await asyncpg.connect(test_db)
        
        try:
            # Préparer données de test
            vector_count = 200
            vectors_data = [
                (f"[{i},{i+1},{i+2}]", f"bulk-test-{i}")
                for i in range(vector_count)
            ]
            
            # Test insertion séquentielle
            start_time = time.time()
            
            for vector_str, metadata in vectors_data:
                await test_helpers.insert_test_vector(conn, vector_str, metadata)
            
            sequential_time = time.time() - start_time
            
            # Nettoyer
            await conn.execute("TRUNCATE test_vectors")
            
            # Test insertion par batch
            start_time = time.time()
            
            # Insérer par batch de 50
            batch_size = 50
            for i in range(0, len(vectors_data), batch_size):
                batch = vectors_data[i:i + batch_size]
                
                # Préparer requête batch
                values = []
                params = []
                for j, (vector_str, metadata) in enumerate(batch):
                    idx = j * 2
                    values.append(f"(${idx + 1}::vector, ${idx + 2})")
                    params.extend([vector_str, metadata])
                
                query = f"""
                    INSERT INTO test_vectors (embedding, metadata) 
                    VALUES {','.join(values)}
                """
                
                await conn.execute(query, *params)
            
            batch_time = time.time() - start_time
            
            print(f"\nBulk insert performance ({vector_count} vectors):")
            print(f"  Sequential: {sequential_time:.3f}s ({vector_count/sequential_time:.1f} vec/s)")
            print(f"  Batch: {batch_time:.3f}s ({vector_count/batch_time:.1f} vec/s)")
            print(f"  Speedup: {sequential_time/batch_time:.1f}x")
            
            # Vérifier que batch est plus rapide
            assert batch_time < sequential_time, "Batch insert should be faster"
            
            # Critères de performance
            assert sequential_time < 30.0, f"Sequential insert too slow: {sequential_time:.3f}s"
            assert batch_time < 10.0, f"Batch insert too slow: {batch_time:.3f}s"
            
            # Vérifier que tous les vecteurs ont été insérés
            final_count = await test_helpers.count_vectors(conn)
            assert final_count == vector_count
        
        finally:
            await conn.close()

    async def test_vector_search_performance(self, test_db, test_helpers):
        """Test performance recherche vectorielle"""
        conn = await asyncpg.connect(test_db)
        
        try:
            # Préparer base de données avec vecteurs de test
            vector_count = 100
            
            for i in range(vector_count):
                await test_helpers.insert_test_vector(
                    conn,
                    f"[{i*0.1},{i*0.2},{i*0.3}]",
                    f"search-perf-{i}"
                )
            
            # Test recherches multiples
            search_times = []
            query_vector = "[0.5,1.0,1.5]"
            
            for _ in range(20):
                start_time = time.time()
                
                results = await conn.fetch("""
                    SELECT id, metadata, embedding <-> $1::vector as distance
                    FROM test_vectors 
                    ORDER BY distance 
                    LIMIT 10
                """, query_vector)
                
                search_time = time.time() - start_time
                search_times.append(search_time)
                
                # Vérifier résultats
                assert len(results) == 10
                assert results[0]["distance"] <= results[-1]["distance"]
            
            # Analyser performance
            avg_search_time = statistics.mean(search_times)
            max_search_time = max(search_times)
            min_search_time = min(search_times)
            
            print(f"\nVector search performance ({vector_count} vectors):")
            print(f"  Average search: {avg_search_time:.3f}s")
            print(f"  Max search: {max_search_time:.3f}s")
            print(f"  Min search: {min_search_time:.3f}s")
            
            # Critères de performance
            assert avg_search_time < 0.5, f"Average search too slow: {avg_search_time:.3f}s"
            assert max_search_time < 1.0, f"Max search too slow: {max_search_time:.3f}s"
        
        finally:
            await conn.close()


@pytest.mark.asyncio
@pytest.mark.slow
class TestServicePerformance:
    """Tests de performance des services"""

    async def test_vector_service_performance(self, test_db):
        """Test performance VectorService"""
        db_manager = DatabaseManager()
        db_manager.pool = await asyncpg.create_pool(test_db, min_size=3, max_size=10)
        
        try:
            vector_service = VectorService(db_manager)
            
            # Test création table (une seule fois)
            start_time = time.time()
            await vector_service.create_test_table()
            table_creation_time = time.time() - start_time
            
            print(f"\nVector service performance:")
            print(f"  Table creation: {table_creation_time:.3f}s")
            
            # Test insertions multiples
            insert_times = []
            
            for i in range(20):
                start_time = time.time()
                await vector_service.insert_test_vector(
                    f"[{i},{i+1},{i+2}]", 
                    f"service-perf-{i}"
                )
                insert_time = time.time() - start_time
                insert_times.append(insert_time)
            
            avg_insert_time = statistics.mean(insert_times)
            print(f"  Average insert: {avg_insert_time:.3f}s")
            
            # Test recherches multiples
            search_times = []
            
            for i in range(10):
                start_time = time.time()
                results = await vector_service.search_similar_vectors("[1,2,3]", 5)
                search_time = time.time() - start_time
                search_times.append(search_time)
                
                assert len(results) >= 1
            
            avg_search_time = statistics.mean(search_times)
            print(f"  Average search: {avg_search_time:.3f}s")
            
            # Test opération complète
            start_time = time.time()
            response = await vector_service.test_vector_operations()
            complete_op_time = time.time() - start_time
            
            print(f"  Complete operation: {complete_op_time:.3f}s")
            
            assert response.status == "success"
            
            # Critères de performance
            assert avg_insert_time < 0.2, f"Insert too slow: {avg_insert_time:.3f}s"
            assert avg_search_time < 0.1, f"Search too slow: {avg_search_time:.3f}s"
            assert complete_op_time < 1.0, f"Complete operation too slow: {complete_op_time:.3f}s"
        
        finally:
            await db_manager.disconnect()

    async def test_health_service_performance(self, test_db):
        """Test performance HealthService"""
        db_manager = DatabaseManager()
        db_manager.pool = await asyncpg.create_pool(test_db, min_size=2, max_size=5)
        
        try:
            from app.services.health_service import HealthService
            health_service = HealthService(db_manager)
            
            # Test checks multiples
            check_times = []
            
            for _ in range(30):
                start_time = time.time()
                
                # Test tous les checks
                connected, status = await health_service.check_database_connection()
                pgvector_version = await health_service.check_pgvector_extension()
                
                check_time = time.time() - start_time
                check_times.append(check_time)
                
                assert connected is True
                assert status == "connected"
            
            avg_check_time = statistics.mean(check_times)
            max_check_time = max(check_times)
            
            print(f"\nHealth service performance:")
            print(f"  Average health check: {avg_check_time:.3f}s")
            print(f"  Max health check: {max_check_time:.3f}s")
            
            # Test health check complet
            start_time = time.time()
            health_response = await health_service.health_check()
            complete_health_time = time.time() - start_time
            
            print(f"  Complete health check: {complete_health_time:.3f}s")
            
            assert health_response.status == "healthy"
            
            # Critères de performance
            assert avg_check_time < 0.05, f"Health check too slow: {avg_check_time:.3f}s"
            assert complete_health_time < 0.1, f"Complete health check too slow: {complete_health_time:.3f}s"
        
        finally:
            await db_manager.disconnect()


@pytest.mark.asyncio
@pytest.mark.slow
class TestLoadTesting:
    """Tests de charge système"""

    async def test_system_load_mixed_operations(self, client: AsyncClient):
        """Test charge système avec opérations mixtes"""
        
        async def worker(worker_id: int, operations: int) -> Dict[str, Any]:
            """Worker pour effectuer des opérations mixtes"""
            results = {
                "worker_id": worker_id,
                "operations": operations,
                "health_checks": 0,
                "vector_tests": 0,
                "errors": 0,
                "total_time": 0
            }
            
            start_time = time.time()
            
            for i in range(operations):
                try:
                    if i % 3 == 0:
                        # Health check
                        response = await client.get("/health")
                        if response.status_code in [200, 503]:
                            results["health_checks"] += 1
                    elif i % 3 == 1:
                        # Vector test
                        response = await client.post("/vectors/test")
                        if response.status_code in [200, 500]:
                            results["vector_tests"] += 1
                    else:
                        # Metrics
                        response = await client.get("/metrics")
                        if response.status_code == 200:
                            pass  # OK
                    
                    # Petit délai entre opérations
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    results["errors"] += 1
            
            results["total_time"] = time.time() - start_time
            return results
        
        # Lancer 5 workers avec 20 opérations chacun
        workers = 5
        operations_per_worker = 20
        
        print(f"\nLoad testing: {workers} workers × {operations_per_worker} operations")
        
        start_time = time.time()
        tasks = [worker(i, operations_per_worker) for i in range(workers)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyser résultats
        total_operations = sum(r["operations"] for r in results)
        total_health_checks = sum(r["health_checks"] for r in results)
        total_vector_tests = sum(r["vector_tests"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Operations: {total_operations}")
        print(f"  Health checks: {total_health_checks}")
        print(f"  Vector tests: {total_vector_tests}")
        print(f"  Errors: {total_errors}")
        print(f"  Operations/sec: {total_operations/total_time:.1f}")
        
        # Critères de réussite
        assert total_time < 30.0, f"Load test took too long: {total_time:.3f}s"
        assert total_errors < total_operations * 0.1, f"Too many errors: {total_errors}"
        assert total_health_checks >= workers * 5, "Not enough health checks completed"


# Configuration pour les tests lents
def pytest_configure(config):
    """Configuration pytest pour marquer les tests lents"""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")


# Utilitaires pour les tests de performance
class PerformanceMonitor:
    """Moniteur de performance pour les tests"""
    
    def __init__(self):
        self.metrics = {}
    
    def start_timer(self, operation: str):
        """Démarrer un timer pour une opération"""
        self.metrics[operation] = {"start": time.time()}
    
    def stop_timer(self, operation: str):
        """Arrêter un timer et calculer la durée"""
        if operation in self.metrics:
            self.metrics[operation]["duration"] = time.time() - self.metrics[operation]["start"]
    
    def get_duration(self, operation: str) -> float:
        """Obtenir la durée d'une opération"""
        return self.metrics.get(operation, {}).get("duration", 0.0)
    
    def report(self):
        """Générer un rapport de performance"""
        print("\nPerformance Report:")
        for op, data in self.metrics.items():
            if "duration" in data:
                print(f"  {op}: {data['duration']:.3f}s")


@pytest.fixture
def perf_monitor():
    """Fixture pour le moniteur de performance"""
    return PerformanceMonitor()
