"""
Tests unitaires pour les modèles Pydantic AindusDB Core
"""
import pytest
from pydantic import ValidationError

from app.models.vector import (
    VectorBase, VectorCreate, VectorModel, VectorResponse,
    VectorSearchRequest, VectorSearchResponse
)
from app.models.health import HealthResponse, StatusResponse


class TestVectorModels:
    """Tests pour les modèles vectoriels"""

    def test_vector_base_valid(self):
        """Test VectorBase avec données valides"""
        vector = VectorBase(
            embedding=[1.0, 2.0, 3.0],
            metadata="test-metadata"
        )
        
        assert vector.embedding == [1.0, 2.0, 3.0]
        assert vector.metadata == "test-metadata"

    def test_vector_base_no_metadata(self):
        """Test VectorBase sans métadonnées"""
        vector = VectorBase(embedding=[1.0, 2.0, 3.0])
        
        assert vector.embedding == [1.0, 2.0, 3.0]
        assert vector.metadata is None

    def test_vector_base_invalid_embedding(self):
        """Test VectorBase avec embedding invalide"""
        with pytest.raises(ValidationError):
            VectorBase(embedding="invalid")

    def test_vector_create_valid(self):
        """Test VectorCreate avec données valides"""
        vector = VectorCreate(
            embedding=[4.0, 5.0, 6.0],
            metadata="create-test"
        )
        
        assert isinstance(vector, VectorBase)
        assert vector.embedding == [4.0, 5.0, 6.0]
        assert vector.metadata == "create-test"

    def test_vector_model_valid(self):
        """Test VectorModel avec ID"""
        vector = VectorModel(
            id=42,
            embedding=[7.0, 8.0, 9.0],
            metadata="model-test"
        )
        
        assert vector.id == 42
        assert vector.embedding == [7.0, 8.0, 9.0]
        assert vector.metadata == "model-test"

    def test_vector_model_missing_id(self):
        """Test VectorModel sans ID (doit échouer)"""
        with pytest.raises(ValidationError):
            VectorModel(
                embedding=[1.0, 2.0, 3.0],
                metadata="no-id"
            )

    def test_vector_response_valid(self):
        """Test VectorResponse valide"""
        response = VectorResponse(
            id=1,
            metadata="response-test",
            distance=0.5
        )
        
        assert response.id == 1
        assert response.metadata == "response-test"
        assert response.distance == 0.5

    def test_vector_response_no_metadata(self):
        """Test VectorResponse sans métadonnées"""
        response = VectorResponse(
            id=2,
            metadata=None,
            distance=1.2
        )
        
        assert response.id == 2
        assert response.metadata is None
        assert response.distance == 1.2

    def test_vector_search_request_valid(self):
        """Test VectorSearchRequest valide"""
        request = VectorSearchRequest(
            query_vector=[1.0, 0.5, 2.0],
            limit=10,
            threshold=0.8
        )
        
        assert request.query_vector == [1.0, 0.5, 2.0]
        assert request.limit == 10
        assert request.threshold == 0.8

    def test_vector_search_request_defaults(self):
        """Test VectorSearchRequest avec valeurs par défaut"""
        request = VectorSearchRequest(
            query_vector=[1.0, 2.0, 3.0]
        )
        
        assert request.limit == 5  # Valeur par défaut
        assert request.threshold is None  # Valeur par défaut

    def test_vector_search_request_invalid_limit(self):
        """Test VectorSearchRequest avec limite invalide"""
        with pytest.raises(ValidationError):
            VectorSearchRequest(
                query_vector=[1.0, 2.0, 3.0],
                limit=0  # Doit être >= 1
            )
        
        with pytest.raises(ValidationError):
            VectorSearchRequest(
                query_vector=[1.0, 2.0, 3.0],
                limit=150  # Doit être <= 100
            )

    def test_vector_search_request_invalid_threshold(self):
        """Test VectorSearchRequest avec seuil invalide"""
        with pytest.raises(ValidationError):
            VectorSearchRequest(
                query_vector=[1.0, 2.0, 3.0],
                threshold=-0.1  # Doit être >= 0
            )
        
        with pytest.raises(ValidationError):
            VectorSearchRequest(
                query_vector=[1.0, 2.0, 3.0],
                threshold=3.0  # Doit être <= 2.0
            )

    def test_vector_search_response_valid(self):
        """Test VectorSearchResponse valide"""
        results = [
            VectorResponse(id=1, metadata="test-1", distance=0.1),
            VectorResponse(id=2, metadata="test-2", distance=0.3)
        ]
        
        response = VectorSearchResponse(
            status="success",
            message="Found vectors",
            results=results,
            count=2
        )
        
        assert response.status == "success"
        assert response.message == "Found vectors"
        assert len(response.results) == 2
        assert response.count == 2

    def test_vector_search_response_defaults(self):
        """Test VectorSearchResponse avec valeurs par défaut"""
        response = VectorSearchResponse(
            message="Test message",
            results=[],
            count=0
        )
        
        assert response.status == "success"  # Valeur par défaut


class TestHealthModels:
    """Tests pour les modèles de santé"""

    def test_health_response_valid(self):
        """Test HealthResponse valide"""
        response = HealthResponse(
            status="healthy",
            database="connected",
            pgvector="0.5.1",
            deployment="docker",
            api_version="1.0.0"
        )
        
        assert response.status == "healthy"
        assert response.database == "connected"
        assert response.pgvector == "0.5.1"
        assert response.deployment == "docker"
        assert response.api_version == "1.0.0"

    def test_health_response_no_pgvector(self):
        """Test HealthResponse sans version pgvector"""
        response = HealthResponse(
            status="healthy",
            database="connected",
            deployment="docker",
            api_version="1.0.0"
        )
        
        assert response.pgvector is None

    def test_health_response_missing_required(self):
        """Test HealthResponse avec champs obligatoires manquants"""
        with pytest.raises(ValidationError):
            HealthResponse(
                status="healthy",
                database="connected"
                # Manque deployment et api_version
            )

    def test_status_response_valid(self):
        """Test StatusResponse valide"""
        response = StatusResponse(
            deployment={
                "orchestrator": "Docker Compose",
                "runtime": "Docker",
                "status": "production-ready"
            },
            database={
                "status": "connected",
                "connected": True,
                "pgvector": "0.5.1"
            },
            api={
                "title": "AindusDB Core API",
                "version": "1.0.0",
                "host": "0.0.0.0",
                "port": 8000
            },
            vector_operations={
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "dimensions": 384,
                "max_batch_size": 100
            }
        )
        
        assert response.deployment["orchestrator"] == "Docker Compose"
        assert response.database["connected"] is True
        assert response.api["port"] == 8000
        assert response.vector_operations["dimensions"] == 384

    def test_status_response_empty_dicts(self):
        """Test StatusResponse avec dictionnaires vides"""
        response = StatusResponse(
            deployment={},
            database={},
            api={},
            vector_operations={}
        )
        
        # Doit pouvoir créer l'objet même avec des dicts vides
        assert isinstance(response.deployment, dict)
        assert isinstance(response.database, dict)
        assert isinstance(response.api, dict)
        assert isinstance(response.vector_operations, dict)


class TestModelSerialization:
    """Tests de sérialisation/désérialisation des modèles"""

    def test_vector_model_json_serialization(self):
        """Test sérialisation JSON VectorModel"""
        vector = VectorModel(
            id=1,
            embedding=[1.0, 2.0, 3.0],
            metadata="json-test"
        )
        
        json_data = vector.model_dump()
        
        expected = {
            "id": 1,
            "embedding": [1.0, 2.0, 3.0],
            "metadata": "json-test"
        }
        
        assert json_data == expected

    def test_vector_model_from_dict(self):
        """Test création VectorModel depuis dictionnaire"""
        data = {
            "id": 5,
            "embedding": [4.0, 5.0, 6.0],
            "metadata": "from-dict"
        }
        
        vector = VectorModel(**data)
        
        assert vector.id == 5
        assert vector.embedding == [4.0, 5.0, 6.0]
        assert vector.metadata == "from-dict"

    def test_health_response_json_serialization(self):
        """Test sérialisation JSON HealthResponse"""
        response = HealthResponse(
            status="healthy",
            database="connected",
            pgvector="0.5.1",
            deployment="docker",
            api_version="1.0.0"
        )
        
        json_data = response.model_dump()
        
        expected = {
            "status": "healthy",
            "database": "connected",
            "pgvector": "0.5.1",
            "deployment": "docker",
            "api_version": "1.0.0"
        }
        
        assert json_data == expected

    def test_vector_search_response_nested_serialization(self):
        """Test sérialisation avec objets imbriqués"""
        results = [
            VectorResponse(id=1, metadata="test", distance=0.1)
        ]
        
        response = VectorSearchResponse(
            message="Test response",
            results=results,
            count=1
        )
        
        json_data = response.model_dump()
        
        assert json_data["status"] == "success"
        assert len(json_data["results"]) == 1
        assert json_data["results"][0]["id"] == 1
        assert json_data["results"][0]["distance"] == 0.1
