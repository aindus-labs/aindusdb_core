"""
Service de vérification de santé et de monitoring pour AindusDB Core.

Ce module implémente tous les checks de santé système : vérification de la
connectivité PostgreSQL, status de l'extension pgvector, métriques système
et diagnostics complets. Il fournit les données pour les endpoints de monitoring.

Example:
    from app.services.health_service import HealthService
    from app.core.database import db_manager
    
    # Initialiser le service
    health_service = HealthService(db_manager)
    
    # Vérifier la santé générale
    health = await health_service.health_check()
    
    # Obtenir le statut détaillé
    status = await health_service.get_system_status()
"""
from ..core.database import DatabaseManager
from ..core.config import settings
from ..models.health import HealthResponse, StatusResponse


class HealthService:
    """
    Service centralisé pour les vérifications de santé et le monitoring d'AindusDB Core.
    
    Cette classe gère toutes les vérifications de santé système : connectivité
    base de données, status des extensions, métriques de performance et diagnostics
    détaillés. Elle fournit les données structurées pour les endpoints de monitoring.
    
    Le service effectue des checks non-intrusifs et rapides pour minimiser l'impact
    sur les performances tout en fournissant des informations précises sur l'état
    du système.
    
    Attributes:
        db: Instance du gestionnaire de base de données pour les vérifications
        
    Example:
        # Utilisation avec dependency injection FastAPI
        @router.get("/health")
        async def health_endpoint(
            health_service: HealthService = Depends(get_health_service)
        ):
            return await health_service.health_check()
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialiser le service de santé avec un gestionnaire de base de données.
        
        Args:
            db_manager: Instance du DatabaseManager pour les vérifications DB
        """
        self.db = db_manager
    
    async def check_database_connection(self) -> tuple[bool, str]:
        """
        Vérifier la connectivité à la base de données PostgreSQL.
        
        Exécute une requête simple pour tester si PostgreSQL est accessible
        et répond correctement. Utilise une requête légère (SELECT 1) pour
        minimiser l'impact sur les performances.
        
        Returns:
            tuple[bool, str]: (connecté, message de statut)
            - bool: True si connecté, False sinon
            - str: "connected" si OK, message d'erreur sinon
            
        Example:
            connected, status = await health_service.check_database_connection()
            if connected:
                print(f"Database OK: {status}")
            else:
                print(f"Database error: {status}")
        """
        try:
            await self.db.fetchval_query("SELECT 1")
            return True, "connected"
        except Exception as e:
            return False, f"connection failed: {str(e)}"
    
    async def check_pgvector_extension(self) -> str:
        """
        Vérifier la disponibilité et la version de l'extension pgvector.
        
        Interroge le catalogue système PostgreSQL pour déterminer si
        l'extension pgvector est installée et récupérer sa version.
        Cette information est cruciale pour les opérations vectorielles.
        
        Returns:
            str: Version de pgvector si installée, "not found" ou "not available" sinon
            
        Example:
            version = await health_service.check_pgvector_extension()
            if version.startswith("0."):
                print(f"pgvector version {version} disponible")
            else:
                print(f"pgvector non disponible: {version}")
        """
        try:
            version = await self.db.fetchval_query(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            )
            return version or "not found"
        except Exception:
            return "not available"
    
    async def health_check(self) -> HealthResponse:
        """
        Effectuer une vérification de santé complète du système.
        
        Exécute tous les checks essentiels (base de données, pgvector)
        et retourne un résumé structuré de l'état du système.
        Utilisé par l'endpoint GET /health pour le monitoring.
        
        Returns:
            HealthResponse: Réponse structurée avec statut global et détails
            
        Raises:
            Exception: Si la base de données n'est pas accessible
            
        Example:
            health = await health_service.health_check()
            
            if health.status == "healthy":
                print("Système opérationnel")
                print(f"Database: {health.database}")
                print(f"pgvector: {health.pgvector}")
            else:
                print(f"Problème détecté: {health.status}")
        """
        db_connected, db_status = await self.check_database_connection()
        
        if not db_connected:
            raise Exception(f"Database connection failed: {db_status}")
        
        pgvector_version = await self.check_pgvector_extension()
        
        return HealthResponse(
            status="healthy",
            database=db_status,
            pgvector=pgvector_version,
            deployment="docker",
            api_version=settings.api_version
        )
    
    async def get_system_status(self) -> StatusResponse:
        """
        Obtenir le statut détaillé complet de tous les composants système.
        
        Collecte des informations exhaustives sur le déploiement,
        la base de données, l'API et les opérations vectorielles.
        Utilisé par l'endpoint GET /status pour le diagnostic approfondi.
        
        Contrairement à health_check(), cette méthode retourne des
        détails techniques complets même si certains composants ne
        fonctionnent pas parfaitement.
        
        Returns:
            StatusResponse: Informations détaillées sur tous les composants
            
        Example:
            status = await health_service.get_system_status()
            
            print(f"Déploiement: {status.deployment['orchestrator']}")
            print(f"Database: {status.database['status']}")
            print(f"API version: {status.api['version']}")
            print(f"Max batch: {status.vector_operations['max_batch_size']}")
        """
        db_connected, db_status = await self.check_database_connection()
        pgvector_version = await self.check_pgvector_extension()
        
        return StatusResponse(
            deployment={
                "orchestrator": "Docker Compose",
                "runtime": "Docker",
                "status": "production-ready"
            },
            database={
                "status": db_status,
                "connected": db_connected,
                "url": settings.database_url.replace(settings.database_url.split('@')[0].split('//')[1], "****"),
                "pgvector": pgvector_version
            },
            api={
                "title": settings.api_title,
                "version": settings.api_version,
                "host": settings.api_host,
                "port": settings.api_port
            },
            vector_operations={
                "embedding_model": settings.embedding_model_text,
                "dimensions": settings.embedding_dimensions_text,
                "max_batch_size": settings.max_batch_size,
                "search_limit": settings.search_results_limit
            }
        )
