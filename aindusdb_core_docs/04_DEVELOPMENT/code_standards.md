# 📝 CODE STANDARDS - AINDUSDB CORE

**Version** : 1.0.0  
**Niveau** : Standards Code Enterprise  
**Date** : 21 janvier 2026  

---

## 🎯 **INTRODUCTION**

Standards de codage complets pour AindusDB Core assurant consistance, maintenabilité et excellence technique à travers toute la codebase enterprise.

### **🏆 PRINCIPES DE CODAGE**
- **Clarté avant tout** : Code lisible et auto-documenté
- **Consistance stricte** : Standards appliqués uniformément
- **Performance consciente** : Code optimisé sans compromettre clarté
- **Sécurité intégrée** : Meilleures pratiques sécurité à chaque ligne
- **Testabilité** : Code facile à tester et maintenir

---

## 🐍 **PYTHON STANDARDS**

### **📋 Style Guide (PEP 8+)**
```python
# ✅ BON: Style conforme PEP 8 + Black
class VectorService:
    """Service for managing vector operations.
    
    This service handles creation, search, and manipulation of vectors
    with proper validation and optimization.
    
    Attributes:
        database: Database connection manager
        cache: Redis cache manager
        embedding_service: Service for generating embeddings
    """
    
    def __init__(
        self,
        database: DatabaseManager,
        cache: CacheManager,
        embedding_service: EmbeddingService
    ) -> None:
        """Initialize VectorService with dependencies.
        
        Args:
            database: Database manager instance
            cache: Cache manager instance
            embedding_service: Embedding generation service
            
        Raises:
            ConfigurationError: If any dependency is invalid
        """
        self.database = database
        self.cache = cache
        self.embedding_service = embedding_service
        self._validate_configuration()
    
    async def create_vector(
        self,
        vector_data: VectorCreate,
        user_id: UUID
    ) -> VectorResponse:
        """Create a new vector with embedding generation.
        
        Args:
            vector_data: Vector data to create
            user_id: ID of the creating user
            
        Returns:
            VectorResponse: Created vector with embedding
            
        Raises:
            ValidationError: If vector data is invalid
            DatabaseError: If database operation fails
        """
        # Validate input
        self._validate_vector_data(vector_data)
        
        # Generate embedding
        embedding = await self._generate_embedding(vector_data.content)
        
        # Save to database
        vector_record = await self._save_vector(
            vector_data,
            embedding,
            user_id
        )
        
        # Update cache
        await self._update_cache(vector_record)
        
        return VectorResponse.from_orm(vector_record)
    
    def _validate_vector_data(self, vector_data: VectorCreate) -> None:
        """Validate vector data according to business rules.
        
        Args:
            vector_data: Vector data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not vector_data.content or len(vector_data.content.strip()) == 0:
            raise ValidationError("Content cannot be empty")
        
        if len(vector_data.content) > 10000:
            raise ValidationError("Content exceeds maximum length")
        
        # Validate metadata structure
        if vector_data.metadata and not isinstance(vector_data.metadata, dict):
            raise ValidationError("Metadata must be a dictionary")

# ❌ MAUVAIS: Style non conforme
class vectorservice:
    def __init__(self, db, cache):
        self.db = db
        self.cache = cache
    
    def createVector(self, vectorData, userId):
        if not vectorData.content:
            raise Exception("Invalid content")
        # ... implementation sans validation ni documentation
```

### **📝 Documentation et Docstrings**
```python
# Google Style Docstrings (recommandé)
def calculate_similarity(
    vector1: List[float],
    vector2: List[float],
    metric: str = "cosine",
    normalize: bool = True
) -> float:
    """Calculate similarity between two vectors.
    
    This function computes similarity using various metrics with optional
    normalization for improved numerical stability.
    
    Args:
        vector1: First vector of floats
        vector2: Second vector of floats
        metric: Similarity metric to use ("cosine", "euclidean", "dotproduct")
        normalize: Whether to normalize vectors before calculation
        
    Returns:
        Similarity score between 0.0 and 1.0
        
    Raises:
        ValueError: If vectors have different dimensions or metric is invalid
        
    Example:
        >>> v1 = [1.0, 0.0, 0.0]
        >>> v2 = [0.0, 1.0, 0.0]
        >>> similarity = calculate_similarity(v1, v2, "cosine")
        >>> print(f"Similarity: {similarity:.3f}")
        Similarity: 0.000
        
    Note:
        Cosine similarity is recommended for high-dimensional vectors.
        Euclidean distance is inversely proportional to similarity.
    """
    if len(vector1) != len(vector2):
        raise ValueError("Vectors must have same dimension")
    
    if metric not in ["cosine", "euclidean", "dotproduct"]:
        raise ValueError(f"Unknown metric: {metric}")
    
    if normalize:
        vector1 = self._normalize_vector(vector1)
        vector2 = self._normalize_vector(vector2)
    
    if metric == "cosine":
        return self._cosine_similarity(vector1, vector2)
    elif metric == "euclidean":
        return self._euclidean_similarity(vector1, vector2)
    else:  # dotproduct
        return self._dot_product_similarity(vector1, vector2)


# Type hints complets
from typing import (
    List,
    Dict,
    Optional,
    Union,
    Callable,
    AsyncGenerator,
    TypeVar,
    Generic
)

T = TypeVar('T')

class DataProcessor(Generic[T]):
    """Generic data processor with type safety."""
    
    def __init__(
        self,
        processor_func: Callable[[T], T],
        validator_func: Optional[Callable[[T], bool]] = None
    ) -> None:
        self.processor_func = processor_func
        self.validator_func = validator_func
    
    async def process_batch(
        self,
        items: List[T]
    ) -> AsyncGenerator[T, None]:
        """Process items with validation and error handling."""
        for item in items:
            if self.validator_func and not self.validator_func(item):
                continue
            
            try:
                processed = self.processor_func(item)
                yield processed
            except Exception as e:
                logger.error(f"Processing failed for item {item}: {e}")
                continue
```

### **🔧 Naming Conventions**
```python
# ✅ BON: Noms clairs et descriptifs
class VectorEmbeddingService:
    """Service for generating and managing vector embeddings."""
    
    def __init__(self) -> None:
        self._embedding_cache: Dict[str, List[float]] = {}
        self._model_version: str = "text-embedding-ada-002"
    
    async def generate_embedding_for_text(
        self,
        text_content: str,
        use_cache: bool = True
    ) -> List[float]:
        """Generate embedding for text content."""
        cache_key = self._generate_cache_key(text_content)
        
        if use_cache and cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        embedding = await self._call_embedding_api(text_content)
        
        if use_cache:
            self._embedding_cache[cache_key] = embedding
        
        return embedding
    
    def _generate_cache_key(self, text: str) -> str:
        """Generate deterministic cache key for text."""
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()[:16]

# ❌ MAUVAIS: Noms ambigus ou abrégés
class VES:
    def __init__(self):
        self.cache = {}
        self.ver = "v2"
    
    def gen_emb(self, txt, use_c=True):
        k = self.mk_key(txt)
        if use_c and k in self.cache:
            return self.cache[k]
        emb = self.call_api(txt)
        if use_c:
            self.cache[k] = emb
        return emb
```

---

## 🏗️ **ARCHITECTURE PATTERNS**

### **🔄 Dependency Injection**
```python
# ✅ BON: Injection explicite avec FastAPI
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Provider functions
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session with proper cleanup."""
    async with database.get_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_vector_service(
    session: AsyncSession = Depends(get_database_session),
    redis: Redis = Depends(get_redis_client)
) -> VectorService:
    """Provide VectorService with dependencies."""
    return VectorService(
        database=session,
        cache=redis,
        embedding_service=EmbeddingService()
    )

# Usage in endpoints
@router.post("/vectors")
async def create_vector(
    vector_data: VectorCreate,
    vector_service: VectorService = Depends(get_vector_service),
    current_user: User = Depends(get_current_user)
) -> VectorResponse:
    """Create vector with injected dependencies."""
    return await vector_service.create_vector(vector_data, current_user.id)

# ❌ MAUVAIS: Dépendances hardcodées
class VectorService:
    def __init__(self):
        self.database = PostgreSQL()  # Hardcoded
        self.cache = Redis()          # Hardcoded
        self.embeddings = OpenAI()    # Hardcoded
```

### **🎯 Error Handling Patterns**
```python
# ✅ BON: Error handling structuré avec exceptions personnalisées
# Custom exceptions
class AindusDBException(Exception):
    """Base exception for AindusDB."""
    pass

class ValidationError(AindusDBException):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: Optional[str] = None):
        self.field = field
        super().__init__(message)

class DatabaseError(AindusDBException):
    """Raised when database operation fails."""
    def __init__(self, message: str, query: Optional[str] = None):
        self.query = query
        super().__init__(message)

class VectorService:
    async def create_vector(self, vector_data: VectorCreate) -> VectorResponse:
        """Create vector with comprehensive error handling."""
        try:
            # Validate input
            self._validate_vector_data(vector_data)
            
            # Generate embedding
            embedding = await self._generate_embedding(vector_data.content)
            
            # Save to database
            vector_record = await self._save_to_database(vector_data, embedding)
            
            return VectorResponse.from_orm(vector_record)
            
        except ValidationError:
            # Re-raise validation errors
            raise
            
        except DatabaseError as e:
            # Log database errors with context
            logger.error(f"Database error creating vector: {e}")
            raise DatabaseError("Failed to save vector to database")
            
        except Exception as e:
            # Catch-all for unexpected errors
            logger.exception(f"Unexpected error creating vector: {e}")
            raise AindusDBException("Internal server error")
    
    def _validate_vector_data(self, vector_data: VectorCreate) -> None:
        """Validate vector data with detailed errors."""
        if not vector_data.content:
            raise ValidationError("Content is required", field="content")
        
        if len(vector_data.content) > 10000:
            raise ValidationError(
                f"Content too long (max 10000 chars, got {len(vector_data.content)})",
                field="content"
            )

# ❌ MAUVAIS: Error handling générique
async def create_vector(self, vector_data):
    try:
        # ... implementation
        pass
    except Exception as e:
        print(f"Error: {e}")  # Pas de logging structuré
        return None  # Pas d'exception informative
```

---

## 🔒 **SECURITY STANDARDS**

### **🛡️ Input Validation and Sanitization**
```python
# ✅ BON: Validation complète avec Pydantic
from pydantic import BaseModel, validator, Field
import bleach
import re

class VectorCreate(BaseModel):
    """Vector creation model with comprehensive validation."""
    
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Text content to vectorize"
    )
    
    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom metadata key-value pairs"
    )
    
    content_type: str = Field(
        default="text",
        regex="^(text|image|audio|video)$",
        description="Type of content"
    )
    
    @validator('content')
    def sanitize_content(cls, v: str) -> str:
        """Sanitize content to prevent XSS and injection."""
        # Remove HTML tags
        sanitized = bleach.clean(v, tags=[], strip=True)
        
        # Check for dangerous patterns
        dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'eval\(',
            r'exec\(',
            r'\$\{.*\}'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise ValueError("Content contains potentially dangerous code")
        
        return sanitized.strip()
    
    @validator('metadata')
    def validate_metadata(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate metadata structure and values."""
        if len(v) > 50:  # Limit metadata size
            raise ValueError("Too many metadata fields")
        
        for key, value in v.items():
            if len(key) > 100 or len(value) > 500:
                raise ValueError("Metadata key or value too long")
            
            # Sanitize metadata values
            v[key] = bleach.clean(value, tags=[], strip=True)
        
        return v

# ✅ BON: Validation SQL avec paramètres
class UserRepository:
    async def get_user_vectors(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Vector]:
        """Get user vectors with safe SQL parameters."""
        query = """
            SELECT id, content, metadata, created_at
            FROM vectors
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        
        try:
            results = await self.db.fetch_all(
                query,
                user_id,  # Parameter 1
                limit,    # Parameter 2
                offset    # Parameter 3
            )
            return [Vector.from_db_row(row) for row in results]
            
        except DatabaseError as e:
            logger.error(f"Database error fetching vectors: {e}")
            raise DatabaseError("Failed to fetch user vectors")

# ❌ MAUVAIS: Vulnérabilités SQL injection
async def get_user_vectors(self, user_id, limit=10):
    query = f"SELECT * FROM vectors WHERE user_id = '{user_id}' LIMIT {limit}"
    # ⚠️ Vulnérable à SQL injection!
    return await self.db.execute(query)
```

### **🔐 Authentication and Authorization**
```python
# ✅ BON: Authentification sécurisée avec JWT
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

class SecurityService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = settings.jwt_secret_key
        self.algorithm = "HS256"
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash with secure comparison."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate secure password hash."""
        return self.pwd_context.hash(password)
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token with expiration."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        return encoded_jwt
    
    async def get_current_user(
        self,
        token: str = Depends(oauth2_scheme)
    ) -> User:
        """Get current user from JWT token."""
        credentials_exception = HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            user_id: str = payload.get("sub")
            
            if user_id is None:
                raise credentials_exception
                
        except JWTError:
            raise credentials_exception
        
        user = await self.get_user(user_id)
        if user is None:
            raise credentials_exception
            
        return user

# ✅ BON: Authorization avec RBAC
class Permission(Enum):
    """User permissions."""
    READ_VECTORS = "read:vectors"
    WRITE_VECTORS = "write:vectors"
    DELETE_VECTORS = "delete:vectors"
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"

class RBACService:
    def __init__(self):
        self.role_permissions = {
            "user": [Permission.READ_VECTORS, Permission.WRITE_VECTORS],
            "admin": [Permission.DELETE_VECTORS, Permission.ADMIN_USERS],
            "super_admin": [Permission.ADMIN_SYSTEM]
        }
    
    def has_permission(
        self,
        user: User,
        required_permission: Permission
    ) -> bool:
        """Check if user has required permission."""
        user_permissions = self.role_permissions.get(user.role, [])
        return required_permission in user_permissions
    
    def require_permission(self, permission: Permission):
        """Decorator to require specific permission."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user from request/state
                current_user = kwargs.get('current_user')
                if not current_user:
                    raise HTTPException(status_code=401, detail="Not authenticated")
                
                if not self.has_permission(current_user, permission):
                    raise HTTPException(
                        status_code=403,
                        detail="Insufficient permissions"
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator

# Usage
@router.delete("/vectors/{vector_id}")
@rbac.require_permission(Permission.DELETE_VECTORS)
async def delete_vector(
    vector_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete vector with permission check."""
    # ... implementation
```

---

## ⚡ **PERFORMANCE STANDARDS**

### **🚀 Async/Await Patterns**
```python
# ✅ BON: Async patterns optimisés
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

class VectorService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def process_vector_batch(
        self,
        vectors: List[VectorCreate]
    ) -> List[VectorResponse]:
        """Process vector batch with concurrent execution."""
        # Create tasks for concurrent processing
        tasks = [
            self.create_vector(vector)
            for vector in vectors
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Vector processing failed: {result}")
                continue
            processed_results.append(result)
        
        return processed_results
    
    async def generate_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently."""
        # Batch API calls when possible
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Run blocking call in thread pool
            embeddings = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._generate_embeddings_sync,
                batch
            )
            
            all_embeddings.extend(embeddings)
        
        return all_embeddings
    
    def _generate_embeddings_sync(self, texts: List[str]) -> List[List[float]]:
        """Synchronous embedding generation for thread pool."""
        # This would be a blocking API call
        return [self._generate_single_embedding(text) for text in texts]

# ✅ BON: Cache patterns avec TTL
from functools import lru_cache
import time

class CacheManager:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._local_cache: Dict[str, Tuple[Any, float]] = {}
    
    async def get_with_fallback(
        self,
        key: str,
        fallback_func: Callable[[], Awaitable[Any]],
        ttl: int = 300
    ) -> Any:
        """Get value with multi-level cache fallback."""
        # Level 1: Local memory cache
        if key in self._local_cache:
            value, timestamp = self._local_cache[key]
            if time.time() - timestamp < ttl:
                return value
        
        # Level 2: Redis cache
        cached_value = await self.redis.get(key)
        if cached_value:
            value = json.loads(cached_value)
            self._local_cache[key] = (value, time.time())
            return value
        
        # Level 3: Generate and cache
        value = await fallback_func()
        await self.redis.setex(key, ttl, json.dumps(value))
        self._local_cache[key] = (value, time.time())
        
        return value

# ❌ MAUVAIS: Code synchrone bloquant
class VectorService:
    def create_vector(self, vector_data):
        # ⚠️ Appels bloquants sans async
        embedding = self.embedding_api.generate(vector_data.content)
        result = self.database.save(vector_data, embedding)
        return result
```

### **📊 Memory Management**
```python
# ✅ BON: Gestion mémoire optimisée
import gc
import psutil
from typing import Iterator

class BatchProcessor:
    """Process large datasets with memory efficiency."""
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        self.process = psutil.Process()
    
    def process_large_dataset(
        self,
        data_source: Iterator[Dict[str, Any]]
    ) -> Iterator[List[ProcessedItem]]:
        """Process large dataset in memory-efficient batches."""
        batch = []
        
        for item in data_source:
            batch.append(item)
            
            # Process batch when it reaches size limit
            if len(batch) >= self.batch_size:
                processed = self._process_batch(batch)
                yield processed
                
                # Clear batch and force garbage collection
                batch.clear()
                gc.collect()
                
                # Monitor memory usage
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                if memory_mb > 1000:  # 1GB limit
                    logger.warning(f"High memory usage: {memory_mb:.1f}MB")
        
        # Process remaining items
        if batch:
            yield self._process_batch(batch)
    
    def _process_batch(self, batch: List[Dict[str, Any]]) -> List[ProcessedItem]:
        """Process a single batch of items."""
        # Implementation optimized for batch size
        return [self._process_item(item) for item in batch]

# ✅ BON: Resource management avec context managers
class DatabaseConnection:
    """Database connection with proper resource management."""
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.connection = await self._create_connection()
        return self.connection
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        if self.connection:
            await self.connection.close()
        
        if exc_type:
            logger.error(f"Database error: {exc_val}")

# Usage
async def process_vectors():
    """Process vectors with proper resource management."""
    async with DatabaseConnection() as conn:
        cursor = await conn.cursor()
        
        # Process with memory-efficient streaming
        async for batch in BatchProcessor().process_large_dataset(
            cursor.fetch_many(size=1000)
        ):
            await process_batch(batch)
```

---

## 🧪 **TESTING STANDARDS**

### **✅ Test Structure and Naming**
```python
# ✅ BON: Tests bien structurés et nommés
class TestVectorService:
    """Test suite for VectorService."""
    
    @pytest.fixture
    def vector_service(self, mock_db, mock_cache):
        """Create VectorService with mocked dependencies."""
        return VectorService(
            database=mock_db,
            cache=mock_cache,
            embedding_service=MockEmbeddingService()
        )
    
    @pytest.fixture
    def sample_vector_data(self):
        """Sample vector data for testing."""
        return VectorCreate(
            content="Test vector content",
            metadata={"category": "test"},
            content_type="text"
        )
    
    @pytest.mark.asyncio
    async def test_create_vector_success(
        self,
        vector_service,
        sample_vector_data
    ):
        """Test successful vector creation."""
        # Arrange
        user_id = uuid4()
        expected_embedding = [0.1, 0.2, 0.3] * 512
        
        # Act
        result = await vector_service.create_vector(
            sample_vector_data,
            user_id
        )
        
        # Assert
        assert isinstance(result, VectorResponse)
        assert result.content == sample_vector_data.content
        assert result.metadata == sample_vector_data.metadata
        assert result.embedding == expected_embedding
    
    @pytest.mark.asyncio
    async def test_create_vector_validation_error(
        self,
        vector_service
    ):
        """Test vector creation with invalid data."""
        # Arrange
        invalid_data = VectorCreate(content="")  # Empty content
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await vector_service.create_vector(invalid_data, uuid4())
        
        assert "Content is required" in str(exc_info.value)
    
    @pytest.mark.parametrize("content,expected_length", [
        ("short", 1),
        ("medium length content", 3),
        ("very long content with many words", 5)
    ])
    async def test_embedding_generation_various_lengths(
        self,
        vector_service,
        content,
        expected_length
    ):
        """Test embedding generation with various content lengths."""
        # Arrange
        vector_data = VectorCreate(content=content)
        
        # Act
        result = await vector_service.create_vector(vector_data, uuid4())
        
        # Assert
        assert len(result.embedding) == 1536  # Standard embedding size

# ✅ BON: Tests d'intégration avec fixtures
@pytest.mark.integration
class TestVectorIntegration:
    """Integration tests for vector operations."""
    
    @pytest.fixture(scope="class")
    async def test_database(self):
        """Create test database with proper cleanup."""
        db = TestDatabase()
        await db.setup()
        yield db
        await db.cleanup()
    
    @pytest.fixture
    async def populated_database(self, test_database):
        """Database populated with test data."""
        await test_database.create_test_vectors(100)
        return test_database
```

---

## 📊 **MONITORING AND LOGGING**

### **📝 Structured Logging**
```python
# ✅ BON: Logging structuré avec context
import structlog
from contextlib import contextmanager

logger = structlog.get_logger()

class VectorService:
    async def create_vector(self, vector_data: VectorCreate, user_id: UUID):
        """Create vector with comprehensive logging."""
        # Add context to logger
        log = logger.bind(
            operation="create_vector",
            user_id=str(user_id),
            content_length=len(vector_data.content)
        )
        
        log.info("Starting vector creation")
        
        try:
            # Generate embedding
            log.debug("Generating embedding")
            embedding = await self._generate_embedding(vector_data.content)
            log.info("Embedding generated", embedding_length=len(embedding))
            
            # Save to database
            log.debug("Saving to database")
            vector_record = await self._save_vector(vector_data, embedding, user_id)
            log.info("Vector saved successfully", vector_id=str(vector_record.id))
            
            return VectorResponse.from_orm(vector_record)
            
        except ValidationError as e:
            log.warning("Validation failed", error=str(e), field=e.field)
            raise
            
        except DatabaseError as e:
            log.error("Database operation failed", error=str(e), query=e.query)
            raise
            
        except Exception as e:
            log.exception("Unexpected error during vector creation")
            raise
    
    @contextmanager
    def operation_timer(self, operation_name: str):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            logger.info(
                "Operation completed",
                operation=operation_name,
                duration_ms=duration * 1000
            )

# Usage
async def create_vector(self, vector_data: VectorCreate, user_id: UUID):
    with self.operation_timer("create_vector"):
        # ... implementation
        pass
```

### **📈 Metrics Collection**
```python
# ✅ BON: Métriques Prometheus intégrées
from prometheus_client import Counter, Histogram, Gauge
import time

class MetricsCollector:
    """Centralized metrics collection."""
    
    def __init__(self):
        # Business metrics
        self.vector_operations = Counter(
            'vector_operations_total',
            'Total vector operations',
            ['operation_type', 'status']
        )
        
        self.vector_search_duration = Histogram(
            'vector_search_duration_seconds',
            'Vector search duration',
            ['search_type', 'index_type']
        )
        
        self.active_connections = Gauge(
            'database_connections_active',
            'Active database connections'
        )
        
        self.embedding_cache_size = Gauge(
            'embedding_cache_size',
            'Number of items in embedding cache'
        )
    
    def record_vector_operation(
        self,
        operation_type: str,
        status: str,
        duration_ms: float
    ):
        """Record vector operation metrics."""
        self.vector_operations.labels(
            operation_type=operation_type,
            status=status
        ).inc()
        
        if operation_type == "search":
            self.vector_search_duration.labels(
                search_type="semantic",
                index_type="ivfflat"
            ).observe(duration_ms / 1000)

# Usage dans service
class VectorService:
    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics
    
    async def search_vectors(self, query: str):
        """Search vectors with metrics collection."""
        start_time = time.time()
        
        try:
            results = await self._perform_search(query)
            self.metrics.record_vector_operation(
                "search",
                "success",
                (time.time() - start_time) * 1000
            )
            return results
            
        except Exception as e:
            self.metrics.record_vector_operation(
                "search",
                "error",
                (time.time() - start_time) * 1000
            )
            raise
```

---

## 📋 **CODE REVIEW CHECKLIST**

### **✅ Mandatory Checklist**
```yaml
code_review_checklist:
  functionality:
    - "Code implements requirements correctly"
    - "Edge cases are handled"
    - "Error handling is comprehensive"
    - "Business logic is correct"
  
  code_quality:
    - "Follows PEP 8 and project standards"
    - "Names are clear and descriptive"
    - "Functions are small and focused"
    - "No code duplication (DRY principle)"
    - "Comments explain 'why' not 'what'"
  
  security:
    - "Input validation is implemented"
    - "SQL queries use parameters"
    - "No hardcoded secrets"
    - "Authentication/authorization is proper"
    - "XSS and injection protection"
  
  performance:
    - "Async/await used correctly"
    - "Database queries are optimized"
    - "Caching is implemented where appropriate"
    - "Memory usage is efficient"
    - "No N+1 query problems"
  
  testing:
    - "Unit tests cover new code"
    - "Integration tests are added"
    - "Edge cases are tested"
    - "Error conditions are tested"
    - "Tests are maintainable"
  
  documentation:
    - "Docstrings are complete"
    - "API documentation is updated"
    - "README is updated if needed"
    - "Comments are clear and useful"
    - "Complex logic is explained"
```

---

## 🚀 **AUTOMATION AND TOOLS**

### **🔧 Pre-commit Hooks**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v0.950
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.4
    hooks:
      - id: bandit
        args: [-c, pyproject.toml]

  - repo: https://github.com/pycqa/pydocstyle
    rev: 6.1.1
    hooks:
      - id: pydocstyle
        args: [--convention=google]
```

### **⚙️ Configuration Files**
```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["app"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[tool.pytest.ini_options]
minversion = "6.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
    "security: marks tests as security tests"
]
```

---

## 🎯 **CONCLUSION**

### **✅ Standards Benefits**
- **Consistency** : Code uniforme across équipe
- **Maintainability** : Code facile à maintenir et faire évoluer
- **Quality** : Haute qualité avec reviews et automatisation
- **Security** : Meilleures pratiques sécurité intégrées
- **Performance** : Code optimisé et efficient

### **🚀 Continuous Improvement**
- **Training** : Formation continue équipe standards
- **Tools** : Outils automatisation qualité
- **Monitoring** : Surveillance métriques qualité
- **Evolution** : Standards adaptés avec nouvelles pratiques
- **Community** : Contribution standards open-source

---

*Code Standards - 21 janvier 2026*  
*Enterprise-Grade Development Practices*
