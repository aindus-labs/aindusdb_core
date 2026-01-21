"""
Tests unitaires pour les routers API AindusDB Core
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from fastapi import HTTPException

from app.main import app
from app.models.health import HealthResponse, StatusResponse
from app.models.vector import VectorSearchResponse, VectorResponse


@pytest.mark.asyncio
class TestHealthRouter:
    """Tests pour le router health"""

    async def test_root_endpoint(self, client: AsyncClient):
        """Test endpoint racine"""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "AindusDB Core API - Docker Deployment"
        assert data["status"] == "running"
        assert data["version"] == "1.0.0"

    @patch("app.routers.health.HealthService")
    async def test_health_check_success(self, mock_health_service, client: AsyncClient):
        """Test health check - succès"""
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_health_service.return_value = mock_service_instance
        
        mock_health_response = HealthResponse(
            status="healthy",
            database="connected",
            pgvector="0.5.1",
            deployment="docker",
            api_version="1.0.0"
        )
        mock_service_instance.health_check.return_value = mock_health_response
        
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["pgvector"] == "0.5.1"
        assert data["deployment"] == "docker"
        assert data["api_version"] == "1.0.0"

    @patch("app.routers.health.HealthService")
    async def test_health_check_failure(self, mock_health_service, client: AsyncClient):
        """Test health check - échec"""
        # Mock du service qui lève une exception
        mock_service_instance = AsyncMock()
        mock_health_service.return_value = mock_service_instance
        mock_service_instance.health_check.side_effect = Exception("Database connection failed")
        
        response = await client.get("/health")
        
        assert response.status_code == 503
        data = response.json()
        assert "Database connection failed" in data["detail"]

    @patch("app.routers.health.HealthService")
    async def test_deployment_status_success(self, mock_health_service, client: AsyncClient):
        """Test status de déploiement - succès"""
        mock_service_instance = AsyncMock()
        mock_health_service.return_value = mock_service_instance
        
        mock_status_response = StatusResponse(
            deployment={"orchestrator": "Docker Compose"},
            database={"status": "connected"},
            api={"title": "AindusDB Core API"},
            vector_operations={"embedding_model": "test-model"}
        )
        mock_service_instance.get_system_status.return_value = mock_status_response
        
        response = await client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["deployment"]["orchestrator"] == "Docker Compose"
        assert data["database"]["status"] == "connected"
        assert data["api"]["title"] == "AindusDB Core API"

    @patch("app.routers.health.HealthService")
    async def test_deployment_status_failure(self, mock_health_service, client: AsyncClient):
        """Test status de déploiement - échec"""
        mock_service_instance = AsyncMock()
        mock_health_service.return_value = mock_service_instance
        mock_service_instance.get_system_status.side_effect = Exception("Status error")
        
        response = await client.get("/status")
        
        assert response.status_code == 500
        data = response.json()
        assert "Status check failed: Status error" in data["detail"]

    async def test_metrics_endpoint(self, client: AsyncClient):
        """Test endpoint de métriques"""
        response = await client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert data["metrics"] == "available"
        assert data["deployment"] == "docker"


@pytest.mark.asyncio
class TestVectorsRouter:
    """Tests pour le router vectors"""

    @patch("app.routers.vectors.VectorService")
    async def test_test_vector_operations_success(self, mock_vector_service, client: AsyncClient):
        """Test opérations vectorielles - succès"""
        mock_service_instance = AsyncMock()
        mock_vector_service.return_value = mock_service_instance
        
        mock_response = VectorSearchResponse(
            status="success",
            message="Vector operations working",
            results=[VectorResponse(id=1, metadata="test", distance=0.0)],
            count=1
        )
        mock_service_instance.test_vector_operations.return_value = mock_response
        
        response = await client.post("/vectors/test")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "Vector operations working" in data["message"]
        assert len(data["results"]) == 1
        assert data["count"] == 1

    @patch("app.routers.vectors.VectorService")
    async def test_test_vector_operations_failure(self, mock_vector_service, client: AsyncClient):
        """Test opérations vectorielles - échec"""
        mock_service_instance = AsyncMock()
        mock_vector_service.return_value = mock_service_instance
        mock_service_instance.test_vector_operations.side_effect = Exception("Vector error")
        
        response = await client.post("/vectors/test")
        
        assert response.status_code == 500
        data = response.json()
        assert "Vector operation failed: Vector error" in data["detail"]

    @patch("app.routers.vectors.VectorService")
    async def test_create_vector_success(self, mock_vector_service, client: AsyncClient):
        """Test création de vecteur - succès"""
        mock_service_instance = AsyncMock()
        mock_vector_service.return_value = mock_service_instance
        mock_service_instance.create_vector.return_value = 42
        
        vector_data = {
            "embedding": [1.0, 2.0, 3.0],
            "metadata": "test-vector"
        }
        
        response = await client.post("/vectors/", json=vector_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["message"] == "Vector created successfully"
        assert data["id"] == 42

    @patch("app.routers.vectors.VectorService")
    async def test_create_vector_failure(self, mock_vector_service, client: AsyncClient):
        """Test création de vecteur - échec"""
        mock_service_instance = AsyncMock()
        mock_vector_service.return_value = mock_service_instance
        mock_service_instance.create_vector.side_effect = Exception("Creation failed")
        
        vector_data = {
            "embedding": [1.0, 2.0, 3.0],
            "metadata": "test-vector"
        }
        
        response = await client.post("/vectors/", json=vector_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Vector creation failed: Creation failed" in data["detail"]

    async def test_create_vector_invalid_data(self, client: AsyncClient):
        """Test création de vecteur avec données invalides"""
        invalid_data = {
            "embedding": "invalid",  # Doit être une liste
            "metadata": "test"
        }
        
        response = await client.post("/vectors/", json=invalid_data)
        
        assert response.status_code == 422  # Validation error

    @patch("app.routers.vectors.VectorService")
    async def test_search_vectors_success(self, mock_vector_service, client: AsyncClient):
        """Test recherche de vecteurs - succès"""
        mock_service_instance = AsyncMock()
        mock_vector_service.return_value = mock_service_instance
        
        mock_response = VectorSearchResponse(
            status="success",
            message="Found 2 similar vectors",
            results=[
                VectorResponse(id=1, metadata="similar-1", distance=0.1),
                VectorResponse(id=2, metadata="similar-2", distance=0.3)
            ],
            count=2
        )
        mock_service_instance.search_vectors.return_value = mock_response
        
        search_data = {
            "query_vector": [1.0, 2.0, 3.0],
            "limit": 10,
            "threshold": 0.5
        }
        
        response = await client.post("/vectors/search", json=search_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "Found 2 similar vectors" in data["message"]
        assert len(data["results"]) == 2
        assert data["count"] == 2

    @patch("app.routers.vectors.VectorService")
    async def test_search_vectors_failure(self, mock_vector_service, client: AsyncClient):
        """Test recherche de vecteurs - échec"""
        mock_service_instance = AsyncMock()
        mock_vector_service.return_value = mock_service_instance
        mock_service_instance.search_vectors.side_effect = Exception("Search failed")
        
        search_data = {
            "query_vector": [1.0, 2.0, 3.0],
            "limit": 5
        }
        
        response = await client.post("/vectors/search", json=search_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Vector search failed: Search failed" in data["detail"]

    async def test_search_vectors_invalid_limit(self, client: AsyncClient):
        """Test recherche avec limite invalide"""
        invalid_search = {
            "query_vector": [1.0, 2.0, 3.0],
            "limit": 0  # Invalide
        }
        
        response = await client.post("/vectors/search", json=invalid_search)
        
        assert response.status_code == 422  # Validation error

    async def test_get_vector_not_implemented(self, client: AsyncClient):
        """Test récupération vecteur par ID (non implémenté)"""
        response = await client.get("/vectors/1")
        
        assert response.status_code == 501
        data = response.json()
        assert "Not implemented yet" in data["detail"]

    async def test_delete_vector_not_implemented(self, client: AsyncClient):
        """Test suppression vecteur par ID (non implémenté)"""
        response = await client.delete("/vectors/1")
        
        assert response.status_code == 501
        data = response.json()
        assert "Not implemented yet" in data["detail"]


@pytest.mark.asyncio
class TestRouterIntegration:
    """Tests d'intégration des routers"""

    async def test_cors_headers(self, client: AsyncClient):
        """Test présence des headers CORS"""
        response = await client.options("/health")
        
        # L'app devrait gérer les OPTIONS requests pour CORS
        # Note: AsyncClient pourrait ne pas simuler exactement CORS

    async def test_404_endpoint(self, client: AsyncClient):
        """Test endpoint inexistant"""
        response = await client.get("/nonexistent")
        
        assert response.status_code == 404

    async def test_method_not_allowed(self, client: AsyncClient):
        """Test méthode HTTP non autorisée"""
        response = await client.patch("/health")  # PATCH non supporté
        
        assert response.status_code == 405

    @patch("app.routers.health.get_database")
    async def test_database_dependency_injection(self, mock_get_db, client: AsyncClient):
        """Test injection de dépendance database"""
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Simuler une réponse health avec DB mockée
        with patch("app.services.health_service.HealthService") as mock_service:
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            
            mock_response = HealthResponse(
                status="healthy",
                database="connected",
                deployment="docker",
                api_version="1.0.0"
            )
            mock_service_instance.health_check.return_value = mock_response
            
            response = await client.get("/health")
            
            assert response.status_code == 200
            # Vérifier que le service a été instancié avec la DB mockée
            mock_service.assert_called_once_with(mock_db)
