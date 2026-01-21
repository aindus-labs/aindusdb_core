"""
Tests d'intégration pour la base de données AindusDB Core
"""
import pytest
import asyncpg
from typing import AsyncGenerator

from app.core.database import DatabaseManager
from app.services.vector_service import VectorService
from app.services.health_service import HealthService


@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Tests d'intégration avec PostgreSQL + pgvector"""

    async def test_database_connection(self, test_db):
        """Test connexion à la base de données"""
        conn = await asyncpg.connect(test_db)
        
        try:
            # Test connexion basique
            result = await conn.fetchval("SELECT 1")
            assert result == 1
            
            # Test version PostgreSQL
            version = await conn.fetchval("SELECT version()")
            assert "PostgreSQL" in version
            
        finally:
            await conn.close()

    async def test_pgvector_extension(self, test_db):
        """Test extension pgvector"""
        conn = await asyncpg.connect(test_db)
        
        try:
            # Vérifier extension pgvector
            extension = await conn.fetchval(
                "SELECT extname FROM pg_extension WHERE extname = 'vector'"
            )
            assert extension == "vector"
            
            # Vérifier version
            version = await conn.fetchval(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            )
            assert version is not None
            
        finally:
            await conn.close()

    async def test_vector_operations_basic(self, clean_db, test_helpers):
        """Test opérations vectorielles de base"""
        # Insert test vector
        vector_id = await test_helpers.insert_test_vector(
            clean_db, "[1,2,3]", "integration-test"
        )
        assert vector_id is not None
        
        # Verify insertion
        count = await test_helpers.count_vectors(clean_db)
        assert count == 1
        
        # Query vector
        result = await clean_db.fetchrow(
            "SELECT id, metadata, embedding FROM test_vectors WHERE id = $1",
            vector_id
        )
        assert result["id"] == vector_id
        assert result["metadata"] == "integration-test"
        assert result["embedding"] == "[1,2,3]"

    async def test_vector_similarity_search(self, clean_db, test_helpers):
        """Test recherche de similarité vectorielle"""
        # Insert multiple test vectors
        await test_helpers.insert_test_vector(clean_db, "[1,2,3]", "vector-1")
        await test_helpers.insert_test_vector(clean_db, "[1,2,4]", "vector-2")
        await test_helpers.insert_test_vector(clean_db, "[5,6,7]", "vector-3")
        
        # Search for similar vectors
        results = await clean_db.fetch("""
            SELECT id, metadata, embedding <-> $1::vector as distance
            FROM test_vectors 
            ORDER BY distance 
            LIMIT 3
        """, "[1,2,3]")
        
        assert len(results) == 3
        
        # First result should be exact match (distance 0)
        assert results[0]["distance"] == 0.0
        assert results[0]["metadata"] == "vector-1"
        
        # Second should be close (distance small)
        assert results[1]["distance"] < results[2]["distance"]
        assert results[1]["metadata"] == "vector-2"

    async def test_vector_index_creation(self, clean_db):
        """Test création d'index vectoriel pour performance"""
        # Créer un index vectoriel
        await clean_db.execute("""
            CREATE INDEX IF NOT EXISTS test_vectors_embedding_idx 
            ON test_vectors USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        
        # Vérifier que l'index existe
        index_exists = await clean_db.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'test_vectors' 
                AND indexname = 'test_vectors_embedding_idx'
            )
        """)
        assert index_exists is True

    async def test_concurrent_vector_operations(self, clean_db, test_helpers):
        """Test opérations vectorielles concurrentes"""
        import asyncio
        
        # Fonction pour insérer des vecteurs
        async def insert_vectors(start_id: int, count: int):
            for i in range(count):
                await test_helpers.insert_test_vector(
                    clean_db, 
                    f"[{start_id + i},{start_id + i + 1},{start_id + i + 2}]",
                    f"concurrent-{start_id}-{i}"
                )
        
        # Lancer insertions concurrentes
        tasks = [
            insert_vectors(1, 5),
            insert_vectors(10, 5),
            insert_vectors(20, 5)
        ]
        
        await asyncio.gather(*tasks)
        
        # Vérifier le nombre total d'insertions
        count = await test_helpers.count_vectors(clean_db)
        assert count == 15

    async def test_large_vector_dimensions(self, clean_db):
        """Test avec des vecteurs de dimensions importantes"""
        # Créer table pour vecteurs 128D
        await clean_db.execute("""
            CREATE TABLE IF NOT EXISTS large_vectors (
                id SERIAL PRIMARY KEY,
                embedding vector(128),
                metadata TEXT
            )
        """)
        
        # Créer vecteur 128D
        large_vector = "[" + ",".join([str(i * 0.1) for i in range(128)]) + "]"
        
        # Insérer et récupérer
        vector_id = await clean_db.fetchval("""
            INSERT INTO large_vectors (embedding, metadata) 
            VALUES ($1::vector, $2) RETURNING id
        """, large_vector, "large-test")
        
        assert vector_id is not None
        
        # Nettoyage
        await clean_db.execute("DROP TABLE IF EXISTS large_vectors")

    async def test_transaction_rollback(self, clean_db, test_helpers):
        """Test rollback de transactions"""
        # Compter vecteurs initiaux
        initial_count = await test_helpers.count_vectors(clean_db)
        
        try:
            async with clean_db.transaction():
                # Insérer des vecteurs dans la transaction
                await test_helpers.insert_test_vector(clean_db, "[1,1,1]", "tx-1")
                await test_helpers.insert_test_vector(clean_db, "[2,2,2]", "tx-2")
                
                # Forcer une erreur pour déclencher rollback
                raise Exception("Force rollback")
                
        except Exception as e:
            assert "Force rollback" in str(e)
        
        # Vérifier que les insertions ont été annulées
        final_count = await test_helpers.count_vectors(clean_db)
        assert final_count == initial_count


@pytest.mark.asyncio
class TestDatabaseManagerIntegration:
    """Tests d'intégration du DatabaseManager"""

    async def test_database_manager_pool(self, test_db):
        """Test pool de connexions du DatabaseManager"""
        # Créer un DatabaseManager avec URL de test
        db_manager = DatabaseManager()
        db_manager.pool = await asyncpg.create_pool(test_db, min_size=2, max_size=5)
        
        try:
            # Test acquisition de connexion
            conn = await db_manager.get_connection()
            assert conn is not None
            
            # Test requête
            result = await conn.fetchval("SELECT 42")
            assert result == 42
            
            # Libérer connexion
            await db_manager.release_connection(conn)
            
            # Test méthodes utilitaires
            result = await db_manager.fetchval_query("SELECT 'test'")
            assert result == "test"
            
        finally:
            await db_manager.disconnect()

    async def test_database_manager_concurrent_connections(self, test_db):
        """Test connexions concurrentes avec DatabaseManager"""
        import asyncio
        
        db_manager = DatabaseManager()
        db_manager.pool = await asyncpg.create_pool(test_db, min_size=3, max_size=10)
        
        try:
            # Fonction pour utiliser une connexion
            async def use_connection(connection_id: int):
                result = await db_manager.fetchval_query(f"SELECT {connection_id}")
                return result
            
            # Lancer plusieurs connexions simultanées
            tasks = [use_connection(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            
            assert results == [0, 1, 2, 3, 4]
            
        finally:
            await db_manager.disconnect()


@pytest.mark.asyncio
class TestServiceDatabaseIntegration:
    """Tests d'intégration services avec base de données"""

    async def test_vector_service_integration(self, test_db):
        """Test VectorService avec vraie base de données"""
        db_manager = DatabaseManager()
        db_manager.pool = await asyncpg.create_pool(test_db, min_size=1, max_size=3)
        
        try:
            vector_service = VectorService(db_manager)
            
            # Test création table
            await vector_service.create_test_table()
            
            # Test insertion
            vector_id = await vector_service.insert_test_vector("[4,5,6]", "service-test")
            assert vector_id is not None
            
            # Test recherche
            results = await vector_service.search_similar_vectors("[4,5,6]", 3)
            assert len(results) >= 1
            assert results[0].distance == 0.0
            
            # Test opérations complètes
            response = await vector_service.test_vector_operations()
            assert response.status == "success"
            assert len(response.results) >= 1
            
        finally:
            await db_manager.disconnect()

    async def test_health_service_integration(self, test_db):
        """Test HealthService avec vraie base de données"""
        db_manager = DatabaseManager()
        db_manager.pool = await asyncpg.create_pool(test_db, min_size=1, max_size=3)
        
        try:
            health_service = HealthService(db_manager)
            
            # Test connexion DB
            connected, status = await health_service.check_database_connection()
            assert connected is True
            assert status == "connected"
            
            # Test extension pgvector
            version = await health_service.check_pgvector_extension()
            assert version != "not available"
            assert version != "not found"
            
            # Test health check complet
            health_response = await health_service.health_check()
            assert health_response.status == "healthy"
            assert health_response.database == "connected"
            
            # Test system status
            status_response = await health_service.get_system_status()
            assert status_response.database["connected"] is True
            
        finally:
            await db_manager.disconnect()

    async def test_error_handling_integration(self, test_db):
        """Test gestion d'erreurs avec vraie DB"""
        db_manager = DatabaseManager()
        db_manager.pool = await asyncpg.create_pool(test_db, min_size=1, max_size=3)
        
        try:
            # Test requête invalide
            with pytest.raises(Exception):
                await db_manager.execute_query("INVALID SQL QUERY")
            
            # Test table inexistante
            with pytest.raises(Exception):
                await db_manager.fetch_query("SELECT * FROM nonexistent_table")
            
        finally:
            await db_manager.disconnect()


@pytest.mark.asyncio
class TestDatabasePerformance:
    """Tests de performance base de données"""

    async def test_bulk_insert_performance(self, clean_db, test_helpers):
        """Test performance insertion en masse"""
        import time
        
        start_time = time.time()
        
        # Insérer 100 vecteurs
        for i in range(100):
            await test_helpers.insert_test_vector(
                clean_db, 
                f"[{i},{i+1},{i+2}]", 
                f"perf-test-{i}"
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Vérifier insertion
        count = await test_helpers.count_vectors(clean_db)
        assert count == 100
        
        # Performance acceptable (moins de 10 secondes pour 100 insertions)
        assert duration < 10.0, f"Bulk insert took {duration:.2f}s, expected < 10s"

    async def test_search_performance(self, clean_db, test_helpers):
        """Test performance de recherche"""
        import time
        
        # Préparer données de test (50 vecteurs)
        for i in range(50):
            await test_helpers.insert_test_vector(
                clean_db,
                f"[{i*0.1},{i*0.2},{i*0.3}]",
                f"search-test-{i}"
            )
        
        start_time = time.time()
        
        # Effectuer 10 recherches
        for _ in range(10):
            await clean_db.fetch("""
                SELECT id, metadata, embedding <-> $1::vector as distance
                FROM test_vectors 
                ORDER BY distance 
                LIMIT 10
            """, "[0.1,0.2,0.3]")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance acceptable (moins de 2 secondes pour 10 recherches)
        assert duration < 2.0, f"10 searches took {duration:.2f}s, expected < 2s"
