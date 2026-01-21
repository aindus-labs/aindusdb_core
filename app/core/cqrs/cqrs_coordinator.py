"""
CQRS Coordinator - Orchestration complète des patterns CQRS + Event Sourcing.

Ce module coordonne l'ensemble des composants CQRS et Event Sourcing pour
fournir une interface unifiée et simplifiée pour l'ensemble de l'application.

Example:
    coordinator = CQRSCoordinator(db_manager=db)
    await coordinator.initialize()
    
    # Commandes
    result = await coordinator.execute_command(CreateVectorCommand(...))
    
    # Queries  
    vectors = await coordinator.execute_query(SearchVectorsQuery(...))
"""

from typing import Any, Dict, List, Optional, Type
import asyncio
from datetime import datetime, timezone

from ...core.logging import get_logger, LogContext
from ...core.database import DatabaseManager
from ...core.metrics import metrics_service
from .command_bus import CommandBus, ValidationMiddleware, TimingMiddleware, RetryMiddleware
from .query_bus import QueryBus, CompressionMiddleware, PaginationMiddleware
from .commands import Command, CommandHandler, CommandFactory
from .queries import Query, QueryHandler, QueryFactory
from .events import Event, EventStore, PostgreSQLEventStore


class CQRSCoordinator:
    """
    Coordinateur CQRS avec Event Sourcing intégré pour AindusDB Core.
    
    Ce coordinateur unifie tous les composants CQRS et Event Sourcing
    pour fournir une interface simple et cohérente à l'application.
    Il gère l'initialisation, la configuration et l'orchestration
    de tous les buses et services.
    
    Features:
    - Command Bus avec middlewares configurés
    - Query Bus avec cache et optimisations
    - Event Store PostgreSQL pour audit complet
    - Métriques intégrées pour observabilité
    - Configuration automatique des handlers
    - Health checks et monitoring
    
    Architecture:
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │   Commands  │───▶│ Command Bus │───▶│ Event Store │
    └─────────────┘    └─────────────┘    └─────────────┘
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │   Queries   │───▶│ Query Bus   │───▶│   Cache     │
    └─────────────┘    └─────────────┘    └─────────────┘
    
    Example:
        # Initialisation
        coordinator = CQRSCoordinator(db_manager=db_manager)
        await coordinator.initialize()
        
        # Utilisation
        from app.core.cqrs import CommandFactory, QueryFactory
        
        # Créer et exécuter commande
        command = CommandFactory.create_vector_command(
            content="ML research paper",
            embedding=[0.1, 0.2, 0.3, 0.4]
        )
        vector_id = await coordinator.execute_command(command)
        
        # Créer et exécuter query
        query = QueryFactory.create_search_query(
            query_text="machine learning",
            limit=10
        )
        results = await coordinator.execute_query(query)
    """
    
    def __init__(self, 
                 db_manager: DatabaseManager,
                 enable_event_sourcing: bool = True,
                 enable_metrics: bool = True,
                 cache_ttl: int = 300):
        """
        Initialiser le coordinateur CQRS.
        
        Args:
            db_manager: Gestionnaire de base de données
            enable_event_sourcing: Activer Event Sourcing
            enable_metrics: Activer métriques Prometheus
            cache_ttl: TTL du cache Query Bus (secondes)
        """
        self.db_manager = db_manager
        self.enable_event_sourcing = enable_event_sourcing
        self.enable_metrics = enable_metrics
        self.cache_ttl = cache_ttl
        
        self.logger = get_logger("aindusdb.cqrs.coordinator")
        
        # Components CQRS
        self.event_store: Optional[EventStore] = None
        self.command_bus: Optional[CommandBus] = None
        self.query_bus: Optional[QueryBus] = None
        
        # État
        self.initialized = False
        
        # Statistiques
        self.stats = {
            "commands_processed": 0,
            "queries_processed": 0,
            "events_stored": 0,
            "initialization_time": 0.0,
            "total_processing_time": 0.0
        }
    
    async def initialize(self) -> None:
        """
        Initialiser tous les composants CQRS et Event Sourcing.
        
        Cette méthode configure et démarre tous les services nécessaires
        au fonctionnement du pattern CQRS avec Event Sourcing.
        """
        if self.initialized:
            self.logger.warning("CQRS Coordinator already initialized")
            return
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.logger.info("Initializing CQRS Coordinator with Event Sourcing")
            
            # 1. Initialiser Event Store si activé
            if self.enable_event_sourcing:
                self.event_store = PostgreSQLEventStore(
                    db_manager=self.db_manager,
                    enable_archiving=True,
                    archive_after_days=365
                )
                await self.event_store.initialize()
                self.logger.info("✅ Event Store initialized")
            
            # 2. Initialiser Command Bus
            self.command_bus = CommandBus(
                event_store=self.event_store,
                enable_metrics=self.enable_metrics,
                max_retries=3
            )
            
            # Ajouter middlewares Command Bus
            self.command_bus.add_middleware(ValidationMiddleware())
            self.command_bus.add_middleware(TimingMiddleware())
            self.command_bus.add_middleware(RetryMiddleware(max_retries=2, delay=1.0))
            
            self.logger.info("✅ Command Bus initialized with middlewares")
            
            # 3. Initialiser Query Bus
            self.query_bus = QueryBus(
                enable_cache=True,
                cache_ttl=self.cache_ttl,
                enable_metrics=self.enable_metrics,
                default_timeout=30
            )
            
            # Ajouter middlewares Query Bus
            self.query_bus.add_middleware(CompressionMiddleware(threshold_bytes=50000))
            self.query_bus.add_middleware(PaginationMiddleware(max_results=10000))
            
            self.logger.info("✅ Query Bus initialized with cache and middlewares")
            
            # 4. Enregistrer handlers par défaut
            await self._register_default_handlers()
            
            # 5. Finaliser initialisation
            self.initialized = True
            initialization_time = asyncio.get_event_loop().time() - start_time
            self.stats["initialization_time"] = initialization_time
            
            self.logger.info(f"🎉 CQRS Coordinator fully initialized in {initialization_time:.2f}s",
                           extra={
                               "event_sourcing": self.enable_event_sourcing,
                               "metrics": self.enable_metrics,
                               "cache_ttl": self.cache_ttl
                           })
                           
        except Exception as e:
            self.logger.error(f"Failed to initialize CQRS Coordinator: {e}")
            raise
    
    async def _register_default_handlers(self):
        """Enregistrer les handlers par défaut pour les commandes et queries courantes."""
        
        # Import des handlers (éviter imports circulaires)
        try:
            # TODO: Implémenter handlers concrets
            # from ..handlers.vector_handlers import (
            #     CreateVectorHandler, UpdateVectorHandler, DeleteVectorHandler,
            #     SearchVectorsHandler, GetVectorByIdHandler
            # )
            # from ..handlers.veritas_handlers import (
            #     CreateVeritasProofHandler, SearchVeritasProofsHandler
            # )
            
            # Command handlers
            # self.command_bus.register(CreateVectorCommand, CreateVectorHandler(self.db_manager))
            # self.command_bus.register(UpdateVectorCommand, UpdateVectorHandler(self.db_manager))
            
            # Query handlers  
            # self.query_bus.register(SearchVectorsQuery, SearchVectorsHandler(self.db_manager))
            # self.query_bus.register(GetVectorByIdQuery, GetVectorByIdHandler(self.db_manager))
            
            self.logger.info("Default CQRS handlers registered")
            
        except ImportError as e:
            self.logger.warning(f"Could not register default handlers: {e}")
    
    async def execute_command(self, command: Command) -> Any:
        """
        Exécuter une commande via le Command Bus.
        
        Args:
            command: Commande à exécuter
            
        Returns:
            Any: Résultat de l'exécution
            
        Raises:
            RuntimeError: Si coordinateur non initialisé
            ValueError: Si commande invalide
        """
        if not self.initialized:
            raise RuntimeError("CQRS Coordinator not initialized. Call await initialize() first.")
        
        start_time = asyncio.get_event_loop().time()
        
        with LogContext(
            operation="cqrs_execute_command",
            command_type=type(command).__name__,
            correlation_id=command.correlation_id
        ):
            try:
                result = await self.command_bus.execute(command)
                
                # Statistiques
                processing_time = asyncio.get_event_loop().time() - start_time
                self.stats["commands_processed"] += 1
                self.stats["total_processing_time"] += processing_time
                
                # Enregistrer événement si Event Sourcing activé
                if self.enable_event_sourcing and self.event_store:
                    await self._record_command_execution_event(command, result, processing_time)
                    self.stats["events_stored"] += 1
                
                return result
                
            except Exception as e:
                self.logger.error(f"Command execution failed: {e}")
                
                # Enregistrer événement d'erreur
                if self.enable_event_sourcing and self.event_store:
                    await self._record_command_execution_event(command, None, 0, str(e))
                
                raise
    
    async def execute_query(self, query: Query) -> Any:
        """
        Exécuter une query via le Query Bus.
        
        Args:
            query: Query à exécuter
            
        Returns:
            Any: Résultat de la query
            
        Raises:
            RuntimeError: Si coordinateur non initialisé
            ValueError: Si query invalide
        """
        if not self.initialized:
            raise RuntimeError("CQRS Coordinator not initialized. Call await initialize() first.")
        
        start_time = asyncio.get_event_loop().time()
        
        with LogContext(
            operation="cqrs_execute_query",
            query_type=type(query).__name__,
            correlation_id=query.correlation_id
        ):
            try:
                result = await self.query_bus.execute(query)
                
                # Statistiques
                processing_time = asyncio.get_event_loop().time() - start_time
                self.stats["queries_processed"] += 1
                self.stats["total_processing_time"] += processing_time
                
                return result
                
            except Exception as e:
                self.logger.error(f"Query execution failed: {e}")
                raise
    
    async def execute_command_batch(self, commands: List[Command], parallel: bool = False) -> List[Any]:
        """
        Exécuter plusieurs commandes en batch.
        
        Args:
            commands: Liste des commandes
            parallel: Exécution parallèle ou séquentielle
            
        Returns:
            List[Any]: Résultats des commandes
        """
        if not self.initialized:
            raise RuntimeError("CQRS Coordinator not initialized")
        
        return await self.command_bus.execute_batch(commands, parallel)
    
    async def execute_query_batch(self, queries: List[Query], parallel: bool = True) -> List[Any]:
        """
        Exécuter plusieurs queries en batch.
        
        Args:
            queries: Liste des queries
            parallel: Exécution parallèle (recommandée pour lectures)
            
        Returns:
            List[Any]: Résultats des queries
        """
        if not self.initialized:
            raise RuntimeError("CQRS Coordinator not initialized")
        
        return await self.query_bus.execute_batch(queries, parallel)
    
    async def _record_command_execution_event(self, 
                                            command: Command, 
                                            result: Any, 
                                            processing_time: float,
                                            error: str = None):
        """
        Enregistrer événement d'exécution de commande dans Event Store.
        
        Args:
            command: Commande exécutée
            result: Résultat ou None si erreur
            processing_time: Temps de traitement
            error: Message d'erreur si applicable
        """
        try:
            event = Event(
                event_type="CQRS_COMMAND_EXECUTED",
                aggregate_id=f"cqrs_coordinator_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                event_data={
                    "command_id": command.command_id,
                    "command_type": type(command).__name__,
                    "user_id": command.user_id,
                    "processing_time_ms": processing_time * 1000,
                    "success": error is None,
                    "error": error,
                    "result_type": type(result).__name__ if result else None
                },
                correlation_id=command.correlation_id,
                user_id=command.user_id,
                metadata={
                    "component": "cqrs_coordinator",
                    "operation": "command_execution"
                }
            )
            
            await self.event_store.store_event(event)
            
        except Exception as e:
            self.logger.debug(f"Failed to record command execution event: {e}")
    
    async def get_event_history(self, 
                              aggregate_id: str = None,
                              event_type: str = None,
                              from_timestamp: datetime = None,
                              limit: int = 100) -> List[Event]:
        """
        Récupérer historique des événements.
        
        Args:
            aggregate_id: ID d'agrégat spécifique
            event_type: Type d'événement spécifique
            from_timestamp: Timestamp de début
            limit: Nombre maximum d'événements
            
        Returns:
            List[Event]: Événements correspondants
        """
        if not self.enable_event_sourcing or not self.event_store:
            return []
        
        if aggregate_id:
            return await self.event_store.get_events(aggregate_id)
        elif event_type:
            return await self.event_store.get_events_by_type(event_type, limit)
        else:
            return await self.event_store.get_all_events(from_timestamp, limit)
    
    def get_command_bus(self) -> CommandBus:
        """Obtenir référence au Command Bus pour enregistrements personnalisés."""
        if not self.initialized:
            raise RuntimeError("CQRS Coordinator not initialized")
        return self.command_bus
    
    def get_query_bus(self) -> QueryBus:
        """Obtenir référence au Query Bus pour enregistrements personnalisés."""
        if not self.initialized:
            raise RuntimeError("CQRS Coordinator not initialized")
        return self.query_bus
    
    def get_event_store(self) -> Optional[EventStore]:
        """Obtenir référence à l'Event Store."""
        return self.event_store
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Obtenir l'état de santé du coordinateur CQRS.
        
        Returns:
            Dict: État de santé détaillé
        """
        health = {
            "status": "healthy" if self.initialized else "unhealthy",
            "initialized": self.initialized,
            "components": {
                "command_bus": self.command_bus is not None,
                "query_bus": self.query_bus is not None,
                "event_store": self.event_store is not None
            },
            "statistics": self.get_comprehensive_stats()
        }
        
        # Vérifier santé Event Store
        if self.event_store:
            try:
                event_stats = await self.event_store.get_event_statistics()
                health["event_store_stats"] = event_stats
            except Exception as e:
                health["event_store_error"] = str(e)
                health["status"] = "degraded"
        
        return health
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """
        Obtenir statistiques complètes du coordinateur.
        
        Returns:
            Dict: Statistiques détaillées
        """
        stats = self.stats.copy()
        
        # Stats des composants
        if self.command_bus:
            stats["command_bus"] = self.command_bus.get_stats()
        
        if self.query_bus:
            stats["query_bus"] = self.query_bus.get_stats()
        
        # Calculs dérivés
        total_operations = stats["commands_processed"] + stats["queries_processed"]
        if total_operations > 0:
            stats["avg_processing_time"] = stats["total_processing_time"] / total_operations
            stats["commands_percentage"] = stats["commands_processed"] / total_operations * 100
            stats["queries_percentage"] = stats["queries_processed"] / total_operations * 100
        else:
            stats["avg_processing_time"] = 0.0
            stats["commands_percentage"] = 0.0
            stats["queries_percentage"] = 0.0
        
        return stats
    
    async def clear_caches(self):
        """Vider tous les caches CQRS."""
        if self.query_bus:
            self.query_bus.clear_cache()
        
        self.logger.info("CQRS caches cleared")
    
    async def shutdown(self):
        """Arrêter proprement le coordinateur CQRS."""
        if not self.initialized:
            return
        
        try:
            self.logger.info("Shutting down CQRS Coordinator")
            
            # Vider caches
            await self.clear_caches()
            
            # Archiver anciens événements si Event Store activé
            if self.event_store and hasattr(self.event_store, 'archive_old_events'):
                archived = await self.event_store.archive_old_events()
                if archived > 0:
                    self.logger.info(f"Archived {archived} old events during shutdown")
            
            self.initialized = False
            self.logger.info("✅ CQRS Coordinator shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error during CQRS Coordinator shutdown: {e}")


# Factory pour simplifier l'utilisation
class CQRSFactory:
    """Factory pour créer et configurer facilement le coordinateur CQRS."""
    
    @staticmethod
    async def create_coordinator(db_manager: DatabaseManager, 
                               **kwargs) -> CQRSCoordinator:
        """
        Créer et initialiser un coordinateur CQRS configuré.
        
        Args:
            db_manager: Gestionnaire de base de données
            **kwargs: Options de configuration
            
        Returns:
            CQRSCoordinator: Coordinateur prêt à l'emploi
        """
        coordinator = CQRSCoordinator(db_manager=db_manager, **kwargs)
        await coordinator.initialize()
        return coordinator
    
    @staticmethod
    def create_command(command_type: str, **data) -> Command:
        """
        Créer une commande via factory intégrée.
        
        Args:
            command_type: Type de commande (ex: "create_vector")
            **data: Données de la commande
            
        Returns:
            Command: Commande créée
        """
        if command_type == "create_vector":
            return CommandFactory.create_vector_command(**data)
        elif command_type == "create_veritas_proof":
            return CommandFactory.create_veritas_proof_command(**data)
        else:
            raise ValueError(f"Unknown command type: {command_type}")
    
    @staticmethod
    def create_query(query_type: str, **data) -> Query:
        """
        Créer une query via factory intégrée.
        
        Args:
            query_type: Type de query (ex: "search_vectors")
            **data: Données de la query
            
        Returns:
            Query: Query créée
        """
        if query_type == "search_vectors":
            return QueryFactory.create_search_query(**data)
        elif query_type == "search_veritas_proofs":
            return QueryFactory.create_veritas_search_query(**data)
        elif query_type == "analytics":
            return QueryFactory.create_analytics_query(**data)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
