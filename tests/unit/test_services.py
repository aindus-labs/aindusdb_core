"""
Tests unitaires pour les services AindusDB Core
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncpg

from app.services.vector_service import VectorService
from app.services.health_service import HealthService
from app.models.vector import VectorCreate, VectorSearchRequest


class TestVectorService:
    """Tests pour VectorService"""

    @pytest.fixture
    def mock_db_manager(self):
        """Mock du gestionnaire de base de données"""
        mock_db = AsyncMock()
        mock_db.execute_query = AsyncMock()
        mock_db.fetchval_query = AsyncMock()
        mock_db.fetch_query = AsyncMock()
        return mock_db

    @pytest.fixture
    def vector_service(self, mock_db_manager):
        """Instance du service vectoriel avec DB mockée"""
        return VectorService(mock_db_manager)

    @pytest.mark.asyncio
    async def test_create_test_table(self, vector_service, mock_db_manager):
        """Test création table de test"""
        await vector_service.create_test_table()
        
        mock_db_manager.execute_query.assert_called_once()
        call_args = mock_db_manager.execute_query.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS test_vectors" in call_args
        assert "embedding vector(3)" in call_args

    @pytest.mark.asyncio
    async def test_insert_test_vector(self, vector_service, mock_db_manager):
        """Test insertion vecteur de test"""
        mock_db_manager.fetchval_query.return_value = 42
        
        result = await vector_service.insert_test_vector("[1,2,3]", "test-metadata")
        
        assert result == 42
        mock_db_manager.fetchval_query.assert_called_once_with(
            """
            INSERT INTO test_vectors (embedding, metadata) 
            VALUES ($1::vector, $2)
            RETURNING id
        """, "[1,2,3]", "test-metadata"
        )

    @pytest.mark.asyncio
    async def test_search_similar_vectors(self, vector_service, mock_db_manager):
        """Test recherche de vecteurs similaires"""
        # Mock des résultats de la requête
        mock_results = [
            {"id": 1, "metadata": "test-1", "distance": 0.1},
            {"id": 2, "metadata": "test-2", "distance": 0.2}
        ]
        mock_db_manager.fetch_query.return_value = mock_results
        
        results = await vector_service.search_similar_vectors("[1,2,3]", 5)
        
        assert len(results) == 2
        assert results[0].id == 1
        assert results[0].metadata == "test-1"
        assert results[0].distance == 0.1
        
        mock_db_manager.fetch_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_vector_operations_success(self, vector_service, mock_db_manager):
        """Test opérations vectorielles complètes - succès"""
        # Mock des retours
        mock_db_manager.fetchval_query.return_value = 1
        mock_db_manager.fetch_query.return_value = [
            {"id": 1, "metadata": "test-docker-deployment", "distance": 0.0}
        ]
        
        result = await vector_service.test_vector_operations()
        
        assert result.status == "success"
        assert "Vector operations working" in result.message
        assert len(result.results) == 1
        assert result.count == 1

    @pytest.mark.asyncio
    async def test_test_vector_operations_failure(self, vector_service, mock_db_manager):
        """Test opérations vectorielles - échec"""
        mock_db_manager.execute_query.side_effect = Exception("DB Error")
        
        with pytest.raises(Exception) as exc_info:
            await vector_service.test_vector_operations()
        
        assert "Vector operation failed: DB Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_vector(self, vector_service, mock_db_manager):
        """Test création d'un vecteur"""
        mock_db_manager.fetchval_query.return_value = 5
        
        vector_create = VectorCreate(
            embedding=[1.0, 2.0, 3.0],
            metadata="test-vector"
        )
        
        result = await vector_service.create_vector(vector_create)
        
        assert result == 5
        mock_db_manager.fetchval_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_vectors(self, vector_service, mock_db_manager):
        """Test recherche de vecteurs"""
        mock_db_manager.fetch_query.return_value = [
            {"id": 1, "metadata": "similar", "distance": 0.1}
        ]
        
        search_request = VectorSearchRequest(
            query_vector=[1.0, 2.0, 3.0],
            limit=10
        )
        
        result = await vector_service.search_vectors(search_request)
        
        assert result.status == "success"
        assert "Found 1 similar vectors" in result.message
        assert len(result.results) == 1

    @pytest.mark.asyncio
    async def test_search_vectors_with_threshold(self, vector_service, mock_db_manager):
        """Test recherche avec seuil de distance"""
        mock_db_manager.fetch_query.return_value = [
            {"id": 1, "metadata": "close", "distance": 0.1},
            {"id": 2, "metadata": "far", "distance": 0.9}
        ]
        
        search_request = VectorSearchRequest(
            query_vector=[1.0, 2.0, 3.0],
            limit=10,
            threshold=0.5
        )
        
        result = await vector_service.search_vectors(search_request)
        
        # Seul le vecteur avec distance 0.1 doit être retourné
        assert len(result.results) == 1
        assert result.results[0].distance == 0.1


class TestHealthService:
    """Tests pour HealthService"""

    @pytest.fixture
    def mock_db_manager(self):
        """Mock du gestionnaire de base de données"""
        mock_db = AsyncMock()
        mock_db.fetchval_query = AsyncMock()
        return mock_db

    @pytest.fixture
    def health_service(self, mock_db_manager):
        """Instance du service de santé avec DB mockée"""
        return HealthService(mock_db_manager)

    @pytest.mark.asyncio
    async def test_check_database_connection_success(self, health_service, mock_db_manager):
        """Test connexion DB - succès"""
        mock_db_manager.fetchval_query.return_value = 1
        
        connected, status = await health_service.check_database_connection()
        
        assert connected is True
        assert status == "connected"
        mock_db_manager.fetchval_query.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_check_database_connection_failure(self, health_service, mock_db_manager):
        """Test connexion DB - échec"""
        mock_db_manager.fetchval_query.side_effect = Exception("Connection failed")
        
        connected, status = await health_service.check_database_connection()
        
        assert connected is False
        assert "connection failed: Connection failed" in status

    @pytest.mark.asyncio
    async def test_check_pgvector_extension_found(self, health_service, mock_db_manager):
        """Test extension pgvector - trouvée"""
        mock_db_manager.fetchval_query.return_value = "0.5.1"
        
        version = await health_service.check_pgvector_extension()
        
        assert version == "0.5.1"

    @pytest.mark.asyncio
    async def test_check_pgvector_extension_not_found(self, health_service, mock_db_manager):
        """Test extension pgvector - non trouvée"""
        mock_db_manager.fetchval_query.return_value = None
        
        version = await health_service.check_pgvector_extension()
        
        assert version == "not found"

    @pytest.mark.asyncio
    async def test_check_pgvector_extension_error(self, health_service, mock_db_manager):
        """Test extension pgvector - erreur"""
        mock_db_manager.fetchval_query.side_effect = Exception("Query error")
        
        version = await health_service.check_pgvector_extension()
        
        assert version == "not available"

    @pytest.mark.asyncio
    async def test_health_check_success(self, health_service, mock_db_manager):
        """Test health check complet - succès"""
        mock_db_manager.fetchval_query.side_effect = [1, "0.5.1"]
        
        result = await health_service.health_check()
        
        assert result.status == "healthy"
        assert result.database == "connected"
        assert result.pgvector == "0.5.1"
        assert result.deployment == "docker"

    @pytest.mark.asyncio
    async def test_health_check_db_failure(self, health_service, mock_db_manager):
        """Test health check - échec DB"""
        mock_db_manager.fetchval_query.side_effect = Exception("DB down")
        
        with pytest.raises(Exception) as exc_info:
            await health_service.health_check()
        
        assert "Database connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_system_status(self, health_service, mock_db_manager):
        """Test status système complet"""
        mock_db_manager.fetchval_query.side_effect = [1, "0.5.1"]
        
        result = await health_service.get_system_status()
        
        assert result.deployment["orchestrator"] == "Docker Compose"
        assert result.database["connected"] is True
        assert result.api["title"] == "AindusDB Core API"
        assert result.vector_operations["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
