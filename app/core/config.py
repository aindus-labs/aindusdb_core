"""
Configuration centralisée pour AindusDB Core.

Ce module contient toutes les configurations de l'application AindusDB Core,
incluant les paramètres de base de données, API, sécurité, performance et monitoring.
Les configurations sont chargées à partir des variables d'environnement et du fichier .env.

Example:
    from app.core.config import settings
    
    # Accès aux configurations
    db_url = settings.database_url
    api_port = settings.api_port
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration centralisée de l'application AindusDB Core.
    
    Cette classe utilise Pydantic Settings pour charger et valider
    automatiquement les variables d'environnement. Toutes les valeurs
    ont des defaults raisonnables pour le développement.
    
    Attributes:
        database_url: URL de connexion PostgreSQL avec pgvector
        api_host: Adresse IP d'écoute de l'API (0.0.0.0 pour toutes)
        api_port: Port d'écoute de l'API FastAPI
        api_workers: Nombre de workers Uvicorn pour production
        api_title: Titre de l'API affiché dans la documentation
        api_version: Version de l'API pour OpenAPI
        jwt_secret_key: Clé secrète pour signer les tokens JWT
        access_token_expire_minutes: Durée de vie des tokens en minutes
        cors_origins: Origines autorisées pour CORS (séparées par virgules)
        cors_allow_credentials: Autoriser l'envoi de credentials via CORS
        embedding_model_text: Nom du modèle Sentence Transformers pour le texte
        embedding_dimensions_text: Dimensions des embeddings texte
        max_document_size: Taille maximale des documents en octets
        max_batch_size: Nombre maximum d'éléments par batch
        search_results_limit: Limite maximale de résultats de recherche
        redis_url: URL de connexion Redis pour le cache
        cache_ttl: Durée de vie du cache Redis en secondes
        metrics_enabled: Activer la collecte de métriques
        log_level: Niveau de logging (DEBUG, INFO, WARNING, ERROR)
    
    Example:
        # Charger les configurations
        settings = Settings()
        
        # Utiliser dans l'application
        app = FastAPI(title=settings.api_title, version=settings.api_version)
        
        # Connexion à la base de données
        engine = create_async_engine(settings.database_url)
    """
    
    # Database - SÉCURITÉ : Pas de default pour secrets
    database_url: str = os.getenv("DATABASE_URL")
    
    # API Configuration
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    api_workers: int = int(os.getenv("API_WORKERS", "4"))
    api_title: str = os.getenv("API_TITLE", "AindusDB Core API")
    api_version: str = os.getenv("API_VERSION", "1.0.0")
    
    # Security - SÉCURITÉ : Pas de default pour JWT secret
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # CORS
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
    cors_allow_credentials: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    
    # Embeddings
    embedding_model_text: str = os.getenv("EMBEDDING_MODEL_TEXT", "sentence-transformers/all-MiniLM-L6-v2")
    embedding_dimensions_text: int = int(os.getenv("EMBEDDING_DIMENSIONS_TEXT", "384"))
    
    # Performance
    max_document_size: int = int(os.getenv("MAX_DOCUMENT_SIZE", "10485760"))
    max_batch_size: int = int(os.getenv("MAX_BATCH_SIZE", "100"))
    search_results_limit: int = int(os.getenv("SEARCH_RESULTS_LIMIT", "1000"))
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_ttl: int = int(os.getenv("CACHE_TTL", "3600"))
    
    # Monitoring
    metrics_enabled: bool = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        extra = "allow"
    
    def __post_init__(self):
        """Validation sécurité des variables critiques obligatoires."""
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is REQUIRED for security. "
                "Set: export DATABASE_URL='postgresql://user:pass@host:5432/db'"
            )
        
        if not self.jwt_secret_key:
            raise ValueError(
                "JWT_SECRET_KEY is REQUIRED for security. "
                "Generate: openssl rand -hex 32"
            )
        
        # Validation longueur JWT secret (minimum 32 caractères)
        if len(self.jwt_secret_key) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters for security. "
                "Current length: " + str(len(self.jwt_secret_key))
            )
    
    def model_post_init(self, __context):
        """Validation post-initialization avec Pydantic v2."""
        self.__post_init__()


# Instance globale des settings avec validation sécurité
settings = Settings()
