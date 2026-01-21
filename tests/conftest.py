"""
Configuration globale pour les tests AindusDB Core
"""
import pytest
import asyncio
import asyncpg
from typing import AsyncGenerator
from httpx import AsyncClient

from app.main import app
from app.core.config import settings
from app.core.database import db_manager


# Configuration de base pour les tests
@pytest.fixture(scope="session")
def event_loop():
    """Créer un event loop pour toute la session de tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Configuration base de données de test
TEST_DATABASE_URL = "postgresql://aindusdb:aindusdb_secure_2026_change_me@localhost:5432/aindusdb_test"


@pytest.fixture(scope="session")
async def test_db():
    """Créer et configurer la base de données de test"""
    # Créer la DB de test
    conn = await asyncpg.connect("postgresql://aindusdb:aindusdb_secure_2026_change_me@localhost:5432/postgres")
    try:
        await conn.execute("DROP DATABASE IF EXISTS aindusdb_test")
        await conn.execute("CREATE DATABASE aindusdb_test")
    finally:
        await conn.close()
    
    # Configurer la DB de test
    test_conn = await asyncpg.connect(TEST_DATABASE_URL)
    try:
        # Créer extension pgvector
        await test_conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # Créer tables de test
        await test_conn.execute("""
            CREATE TABLE IF NOT EXISTS test_vectors (
                id SERIAL PRIMARY KEY,
                embedding vector(3),
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        yield TEST_DATABASE_URL
        
    finally:
        await test_conn.close()
    
    # Nettoyage
    cleanup_conn = await asyncpg.connect("postgresql://aindusdb:aindusdb_secure_2026_change_me@localhost:5432/postgres")
    try:
        await cleanup_conn.execute("DROP DATABASE IF EXISTS aindusdb_test")
    finally:
        await cleanup_conn.close()


@pytest.fixture
async def db_connection(test_db):
    """Fournir une connexion DB pour les tests"""
    conn = await asyncpg.connect(test_db)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture
async def clean_db(db_connection):
    """Nettoyer la DB avant chaque test"""
    await db_connection.execute("TRUNCATE test_vectors RESTART IDENTITY")
    yield db_connection
    # Nettoyage après test
    await db_connection.execute("TRUNCATE test_vectors RESTART IDENTITY")


@pytest.fixture
async def client():
    """Client HTTP pour tester l'API"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def sample_vectors():
    """Données de test - vecteurs d'exemple"""
    return [
        {
            "embedding": [1.0, 2.0, 3.0],
            "metadata": "test-vector-1"
        },
        {
            "embedding": [4.0, 5.0, 6.0],
            "metadata": "test-vector-2"
        },
        {
            "embedding": [7.0, 8.0, 9.0],
            "metadata": "test-vector-3"
        }
    ]


@pytest.fixture
def mock_settings():
    """Settings de test"""
    return {
        "database_url": TEST_DATABASE_URL,
        "api_title": "AindusDB Test API",
        "api_version": "1.0.0-test",
        "log_level": "DEBUG"
    }


# Helpers pour les tests
class TestHelpers:
    """Utilitaires pour les tests"""
    
    @staticmethod
    async def insert_test_vector(conn, embedding: str, metadata: str) -> int:
        """Insérer un vecteur de test"""
        result = await conn.fetchval(
            "INSERT INTO test_vectors (embedding, metadata) VALUES ($1::vector, $2) RETURNING id",
            embedding, metadata
        )
        return result
    
    @staticmethod
    async def count_vectors(conn) -> int:
        """Compter les vecteurs en DB"""
        return await conn.fetchval("SELECT COUNT(*) FROM test_vectors")
    
    @staticmethod
    def vector_to_string(vector: list) -> str:
        """Convertir liste en string pour PostgreSQL"""
        return f"[{','.join(map(str, vector))}]"


@pytest.fixture
def test_helpers():
    """Fournir les helpers de test"""
    return TestHelpers
