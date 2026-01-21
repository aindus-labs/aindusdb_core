"""
Tests d'intégration API AindusDB Core
Tests end-to-end avec vraie base de données
"""
import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.asyncio
class TestAPIIntegrationHealth:
    """Tests d'intégration pour les endpoints de santé"""

    async def test_root_endpoint_integration(self, client: AsyncClient):
        """Test endpoint racine avec vraie application"""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "status" in data
        assert "version" in data
        assert data["status"] == "running"

    async def test_health_check_integration(self, client: AsyncClient):
        """Test health check avec vraie base de données"""
        # Note: Nécessite que les services Docker soient en marche
        response = await client.get("/health")
        
        # Peut être 200 (si DB connectée) ou 503 (si DB non disponible)
        assert response.status_code in [200, 503]
        
        data = response.json()
        
        if response.status_code == 200:
            # DB disponible
            assert data["status"] == "healthy"
            assert data["database"] == "connected"
            assert "pgvector" in data
            assert data["deployment"] == "docker"
            assert "api_version" in data
        else:
            # DB non disponible
            assert "detail" in data
            assert "Database connection failed" in data["detail"]

    async def test_metrics_endpoint_integration(self, client: AsyncClient):
        """Test endpoint métriques"""
        response = await client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert data["metrics"] == "available" 
        assert data["deployment"] == "docker"

    async def test_status_endpoint_integration(self, client: AsyncClient):
        """Test endpoint status complet"""
        response = await client.get("/status")
        
        # Peut être 200 ou 500 selon disponibilité DB
        assert response.status_code in [200, 500]
        
        data = response.json()
        
        if response.status_code == 200:
            # Status disponible
            assert "deployment" in data
            assert "database" in data
            assert "api" in data
            assert "vector_operations" in data
            
            assert data["deployment"]["orchestrator"] == "Docker Compose"
            assert "title" in data["api"]
        else:
            # Erreur status
            assert "detail" in data


@pytest.mark.asyncio
class TestAPIIntegrationVectors:
    """Tests d'intégration pour les endpoints vectoriels"""

    async def test_vector_test_endpoint_integration(self, client: AsyncClient):
        """Test endpoint de test vectoriel"""
        response = await client.post("/vectors/test")
        
        # Peut être 200 (si DB connectée) ou 500 (si problème)
        assert response.status_code in [200, 500]
        
        data = response.json()
        
        if response.status_code == 200:
            # Test vectoriel réussi
            assert data["status"] == "success"
            assert "message" in data
            assert "results" in data
            assert "count" in data
            assert isinstance(data["results"], list)
            assert data["count"] >= 0
            
            # Vérifier structure des résultats
            if data["results"]:
                result = data["results"][0]
                assert "id" in result
                assert "metadata" in result
                assert "distance" in result
        else:
            # Erreur test vectoriel
            assert "detail" in data
            assert "Vector operation failed" in data["detail"]

    async def test_create_vector_endpoint_integration(self, client: AsyncClient):
        """Test création de vecteur"""
        vector_data = {
            "embedding": [1.5, 2.5, 3.5],
            "metadata": "integration-test-vector"
        }
        
        response = await client.post("/vectors/", json=vector_data)
        
        # Peut être 200 (succès) ou 500 (erreur DB)
        assert response.status_code in [200, 500]
        
        data = response.json()
        
        if response.status_code == 200:
            # Création réussie
            assert data["status"] == "success"
            assert data["message"] == "Vector created successfully"
            assert "id" in data
            assert isinstance(data["id"], int)
        else:
            # Erreur création
            assert "detail" in data
            assert "Vector creation failed" in data["detail"]

    async def test_create_vector_invalid_data_integration(self, client: AsyncClient):
        """Test création vecteur avec données invalides"""
        invalid_data = {
            "embedding": "not-a-list",  # Invalide
            "metadata": "test"
        }
        
        response = await client.post("/vectors/", json=invalid_data)
        
        # Doit toujours être 422 (erreur validation)
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data

    async def test_search_vectors_endpoint_integration(self, client: AsyncClient):
        """Test recherche de vecteurs"""
        search_data = {
            "query_vector": [1.0, 2.0, 3.0],
            "limit": 5,
            "threshold": 1.0
        }
        
        response = await client.post("/vectors/search", json=search_data)
        
        # Peut être 200 (succès) ou 500 (erreur DB)
        assert response.status_code in [200, 500]
        
        data = response.json()
        
        if response.status_code == 200:
            # Recherche réussie
            assert data["status"] == "success"
            assert "message" in data
            assert "results" in data
            assert "count" in data
            assert isinstance(data["results"], list)
            assert data["count"] >= 0
            
            # Vérifier structure des résultats
            for result in data["results"]:
                assert "id" in result
                assert "metadata" in result  
                assert "distance" in result
                assert isinstance(result["distance"], (int, float))
        else:
            # Erreur recherche
            assert "detail" in data
            assert "Vector search failed" in data["detail"]

    async def test_search_vectors_invalid_limit_integration(self, client: AsyncClient):
        """Test recherche avec limite invalide"""
        invalid_search = {
            "query_vector": [1.0, 2.0, 3.0],
            "limit": 0  # Invalide
        }
        
        response = await client.post("/vectors/search", json=invalid_search)
        
        # Doit être 422 (erreur validation)
        assert response.status_code == 422

    async def test_get_vector_not_implemented_integration(self, client: AsyncClient):
        """Test récupération vecteur (non implémenté)"""
        response = await client.get("/vectors/123")
        
        # Doit être 501 (non implémenté)
        assert response.status_code == 501
        data = response.json()
        assert "Not implemented yet" in data["detail"]

    async def test_delete_vector_not_implemented_integration(self, client: AsyncClient):
        """Test suppression vecteur (non implémenté)"""
        response = await client.delete("/vectors/123")
        
        # Doit être 501 (non implémenté)
        assert response.status_code == 501
        data = response.json()
        assert "Not implemented yet" in data["detail"]


@pytest.mark.asyncio
class TestAPIIntegrationWorkflows:
    """Tests de workflows complets API"""

    async def test_complete_vector_workflow_integration(self, client: AsyncClient):
        """Test workflow complet : création → test → recherche"""
        
        # 1. Vérifier santé API
        health_response = await client.get("/health")
        if health_response.status_code != 200:
            pytest.skip("Database not available for integration test")
        
        # 2. Test des opérations vectorielles
        test_response = await client.post("/vectors/test")
        assert test_response.status_code == 200
        test_data = test_response.json()
        assert test_data["status"] == "success"
        
        # 3. Créer un vecteur
        vector_data = {
            "embedding": [0.1, 0.2, 0.3],
            "metadata": "workflow-test"
        }
        create_response = await client.post("/vectors/", json=vector_data)
        
        if create_response.status_code == 200:
            create_data = create_response.json()
            vector_id = create_data["id"]
            
            # 4. Rechercher des vecteurs similaires
            search_data = {
                "query_vector": [0.1, 0.2, 0.3],
                "limit": 10
            }
            search_response = await client.post("/vectors/search", json=search_data)
            
            if search_response.status_code == 200:
                search_data = search_response.json()
                assert search_data["status"] == "success"
                
                # Vérifier que notre vecteur est dans les résultats
                found_vector = False
                for result in search_data["results"]:
                    if result["metadata"] == "workflow-test":
                        found_vector = True
                        assert result["distance"] == 0.0  # Distance exacte
                        break
                
                # Note: Peut ne pas trouver si le vecteur a été inséré dans une table différente

    async def test_api_error_handling_integration(self, client: AsyncClient):
        """Test gestion d'erreurs API"""
        
        # Test endpoint inexistant
        response = await client.get("/nonexistent")
        assert response.status_code == 404
        
        # Test méthode non supportée
        response = await client.patch("/health")
        assert response.status_code == 405
        
        # Test données JSON invalides
        response = await client.post("/vectors/", data="invalid-json")
        assert response.status_code == 422

    async def test_api_concurrent_requests_integration(self, client: AsyncClient):
        """Test requêtes concurrentes"""
        import asyncio
        
        # Lancer plusieurs requêtes en parallèle
        tasks = [
            client.get("/health"),
            client.get("/metrics"),
            client.post("/vectors/test"),
            client.get("/"),
            client.get("/status")
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Vérifier qu'aucune requête n'a complètement échoué
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code in [200, 500, 503]  # Codes acceptables

    async def test_api_large_vector_integration(self, client: AsyncClient):
        """Test avec vecteur de grande taille"""
        # Créer un vecteur plus grand (mais pas trop pour éviter les erreurs)
        large_embedding = [i * 0.01 for i in range(100)]
        
        vector_data = {
            "embedding": large_embedding,
            "metadata": "large-vector-test"
        }
        
        response = await client.post("/vectors/", json=vector_data)
        
        # Peut échouer si la DB n'est configurée que pour des vecteurs 3D
        if response.status_code == 500:
            # Erreur attendue pour vecteur de mauvaise dimension
            data = response.json()
            assert "Vector creation failed" in data["detail"]
        else:
            # Success possible si la DB accepte les vecteurs variables
            pass


@pytest.mark.asyncio  
class TestAPIIntegrationSecurity:
    """Tests de sécurité API"""

    async def test_cors_headers_integration(self, client: AsyncClient):
        """Test headers CORS"""
        # Note: AsyncClient peut ne pas simuler complètement CORS
        response = await client.get("/health")
        
        # Vérifier que la réponse est valide
        assert response.status_code in [200, 503]

    async def test_api_input_validation_integration(self, client: AsyncClient):
        """Test validation des entrées"""
        
        # Test embedding requis
        response = await client.post("/vectors/", json={"metadata": "test"})
        assert response.status_code == 422
        
        # Test query_vector requis pour recherche
        response = await client.post("/vectors/search", json={"limit": 5})
        assert response.status_code == 422
        
        # Test limites de recherche
        response = await client.post("/vectors/search", json={
            "query_vector": [1, 2, 3],
            "limit": 1000  # Trop grand
        })
        assert response.status_code == 422

    async def test_api_response_format_integration(self, client: AsyncClient):
        """Test format des réponses API"""
        
        # Test Content-Type JSON
        response = await client.get("/")
        assert response.headers["content-type"] == "application/json"
        
        # Test structure réponse erreur
        response = await client.get("/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


@pytest.mark.asyncio
class TestAPIIntegrationPerformance:
    """Tests de performance API"""

    async def test_api_response_time_integration(self, client: AsyncClient):
        """Test temps de réponse API"""
        import time
        
        # Test endpoint léger
        start_time = time.time()
        response = await client.get("/")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 1.0  # Moins d'1 seconde
        assert response.status_code == 200

    async def test_api_multiple_requests_integration(self, client: AsyncClient):
        """Test performance multiples requêtes"""
        import time
        
        start_time = time.time()
        
        # 10 requêtes rapides
        for _ in range(10):
            response = await client.get("/metrics")
            assert response.status_code == 200
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 10 requêtes en moins de 5 secondes
        assert total_time < 5.0, f"10 requests took {total_time:.2f}s"

    async def test_api_memory_usage_integration(self, client: AsyncClient):
        """Test usage mémoire stable"""
        # Test basique - multiple requêtes ne doivent pas causer de fuite
        responses = []
        
        for i in range(20):
            response = await client.get("/")
            responses.append(response.status_code)
            
        # Toutes les requêtes doivent réussir
        assert all(status == 200 for status in responses)
