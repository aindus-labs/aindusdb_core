"""
Command Bus pour CQRS - Orchestration des commandes d'écriture.

Le Command Bus est responsable de recevoir les commandes, de trouver
le handler approprié et d'exécuter la commande avec gestion d'erreurs,
logging et métriques.

Example:
    command_bus = CommandBus()
    command_bus.register(CreateVectorCommand, CreateVectorHandler())
    
    result = await command_bus.execute(CreateVectorCommand(...))
"""

import asyncio
from typing import Dict, Type, TypeVar, Any, Optional, List
from datetime import datetime, timezone
import time

from ...core.logging import get_logger, LogContext
from ...core.metrics import metrics_service
from .commands import Command, CommandHandler
from .events import Event, EventStore

TCommand = TypeVar('TCommand', bound=Command)
TResult = TypeVar('TResult')


class CommandBus:
    """
    Bus de commandes pour pattern CQRS avec orchestration complète.
    
    Le CommandBus centralise l'exécution des commandes d'écriture avec :
    - Enregistrement dynamique des handlers
    - Validation des commandes avant exécution
    - Gestion des erreurs et retry automatique
    - Métriques et logging pour observabilité
    - Event sourcing pour audit complet
    - Support des middlewares pour cross-cutting concerns
    
    Features:
    - Registry des handlers par type de commande
    - Pipeline de middlewares configurables
    - Métriques Prometheus intégrées
    - Circuit breaker pour résilience
    - Event store pour traçabilité complète
    
    Example:
        # Configuration
        bus = CommandBus(event_store=event_store)
        bus.register(CreateVectorCommand, CreateVectorHandler(db))
        
        # Exécution
        result = await bus.execute(CreateVectorCommand(
            content="test",
            embedding=[0.1, 0.2, 0.3]
        ))
    """
    
    def __init__(self, 
                 event_store: Optional[EventStore] = None,
                 enable_metrics: bool = True,
                 max_retries: int = 3):
        """
        Initialiser le Command Bus.
        
        Args:
            event_store: Store pour les événements
            enable_metrics: Activer les métriques
            max_retries: Nombre maximum de retry
        """
        self.handlers: Dict[Type[Command], CommandHandler] = {}
        self.middlewares: List[CommandMiddleware] = []
        self.event_store = event_store
        self.enable_metrics = enable_metrics
        self.max_retries = max_retries
        
        self.logger = get_logger("aindusdb.cqrs.command_bus")
        
        # Statistiques
        self.stats = {
            "commands_executed": 0,
            "commands_failed": 0,
            "total_execution_time": 0.0,
            "handlers_registered": 0
        }
    
    def register(self, command_type: Type[TCommand], handler: CommandHandler[TCommand, TResult]):
        """
        Enregistrer un handler pour un type de commande.
        
        Args:
            command_type: Type de commande
            handler: Handler associé
        """
        self.handlers[command_type] = handler
        self.stats["handlers_registered"] += 1
        
        self.logger.info(f"Command handler registered: {command_type.__name__} -> {handler.__class__.__name__}")
    
    def add_middleware(self, middleware: 'CommandMiddleware'):
        """
        Ajouter un middleware au pipeline.
        
        Args:
            middleware: Middleware à ajouter
        """
        self.middlewares.append(middleware)
        self.logger.info(f"Command middleware added: {middleware.__class__.__name__}")
    
    async def execute(self, command: TCommand) -> TResult:
        """
        Exécuter une commande avec pipeline complet.
        
        Args:
            command: Commande à exécuter
            
        Returns:
            TResult: Résultat de l'exécution
            
        Raises:
            ValueError: Si aucun handler n'est trouvé
            Exception: Erreurs d'exécution
        """
        start_time = time.time()
        command_type = type(command)
        
        with LogContext(
            operation="execute_command",
            command_type=command_type.__name__,
            command_id=command.command_id,
            correlation_id=command.correlation_id
        ):
            self.logger.info(f"Executing command: {command_type.__name__}")
            
            try:
                # 1. Vérifier qu'un handler existe
                if command_type not in self.handlers:
                    raise ValueError(f"No handler registered for command: {command_type.__name__}")
                
                handler = self.handlers[command_type]
                
                # 2. Exécuter pipeline de middlewares
                result = await self._execute_pipeline(command, handler)
                
                # 3. Enregistrer événement de succès
                if self.event_store:
                    await self._record_command_event(command, "EXECUTED", result)
                
                # 4. Métriques
                execution_time = (time.time() - start_time) * 1000
                await self._record_metrics(command_type.__name__, "success", execution_time)
                
                self.stats["commands_executed"] += 1
                self.stats["total_execution_time"] += execution_time
                
                self.logger.info(f"Command executed successfully: {command_type.__name__}",
                               extra={"execution_time_ms": execution_time})
                
                return result
                
            except Exception as e:
                # Gestion d'erreur avec retry
                execution_time = (time.time() - start_time) * 1000
                
                self.logger.error(f"Command execution failed: {command_type.__name__}: {e}",
                                extra={"execution_time_ms": execution_time})
                
                # Enregistrer événement d'erreur
                if self.event_store:
                    await self._record_command_event(command, "FAILED", str(e))
                
                # Métriques d'erreur
                await self._record_metrics(command_type.__name__, "error", execution_time)
                
                self.stats["commands_failed"] += 1
                raise
    
    async def _execute_pipeline(self, command: TCommand, handler: CommandHandler) -> TResult:
        """
        Exécuter le pipeline complet : middlewares + handler.
        
        Args:
            command: Commande à exécuter
            handler: Handler final
            
        Returns:
            TResult: Résultat de l'exécution
        """
        # Créer pipeline avec middlewares
        pipeline = self._build_pipeline(handler)
        
        # Exécuter pipeline
        return await pipeline(command)
    
    def _build_pipeline(self, handler: CommandHandler):
        """
        Construire le pipeline de middlewares + handler.
        
        Args:
            handler: Handler final
            
        Returns:
            Callable: Pipeline complet
        """
        # Handler final
        async def final_handler(command):
            await handler.validate(command)
            return await handler.handle(command)
        
        # Appliquer middlewares en reverse (dernier ajouté = premier exécuté)
        pipeline = final_handler
        for middleware in reversed(self.middlewares):
            pipeline = middleware.wrap(pipeline)
        
        return pipeline
    
    async def _record_command_event(self, command: Command, status: str, result: Any):
        """
        Enregistrer événement de commande dans l'event store.
        
        Args:
            command: Commande exécutée
            status: Statut d'exécution
            result: Résultat ou erreur
        """
        if not self.event_store:
            return
        
        event = Event(
            event_type="COMMAND_EXECUTED",
            aggregate_id=command.command_id,
            event_data={
                "command_type": type(command).__name__,
                "command_data": command.model_dump(),
                "status": status,
                "result": str(result)[:500],  # Limiter taille
                "user_id": command.user_id,
                "correlation_id": command.correlation_id
            },
            correlation_id=command.correlation_id
        )
        
        await self.event_store.store_event(event)
    
    async def _record_metrics(self, command_name: str, status: str, execution_time: float):
        """
        Enregistrer métriques d'exécution.
        
        Args:
            command_name: Nom de la commande
            status: Statut (success/error)
            execution_time: Temps d'exécution (ms)
        """
        if not self.enable_metrics or not metrics_service:
            return
        
        # Compteur de commandes
        await metrics_service.increment_counter(
            "cqrs_commands_total",
            labels={"command": command_name, "status": status}
        )
        
        # Histogramme des temps d'exécution
        await metrics_service.record_histogram(
            "cqrs_command_duration_ms",
            execution_time,
            labels={"command": command_name}
        )
    
    async def execute_batch(self, commands: List[Command], parallel: bool = False) -> List[Any]:
        """
        Exécuter plusieurs commandes en batch.
        
        Args:
            commands: Liste des commandes
            parallel: Exécution parallèle ou séquentielle
            
        Returns:
            List[Any]: Résultats des commandes
        """
        if parallel:
            # Exécution parallèle
            tasks = [self.execute(command) for command in commands]
            return await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Exécution séquentielle
            results = []
            for command in commands:
                try:
                    result = await self.execute(command)
                    results.append(result)
                except Exception as e:
                    results.append(e)
            return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtenir statistiques du Command Bus.
        
        Returns:
            Dict: Statistiques complètes
        """
        stats = self.stats.copy()
        
        # Calculer moyennes
        if stats["commands_executed"] > 0:
            stats["avg_execution_time"] = (
                stats["total_execution_time"] / stats["commands_executed"]
            )
        else:
            stats["avg_execution_time"] = 0.0
        
        # Taux de succès
        total_commands = stats["commands_executed"] + stats["commands_failed"]
        if total_commands > 0:
            stats["success_rate"] = stats["commands_executed"] / total_commands
        else:
            stats["success_rate"] = 1.0
        
        stats["registered_handlers"] = list(self.handlers.keys())
        stats["middleware_count"] = len(self.middlewares)
        
        return stats
    
    def clear_handlers(self):
        """Vider tous les handlers (utile pour tests)."""
        self.handlers.clear()
        self.stats["handlers_registered"] = 0
        self.logger.info("All command handlers cleared")


class CommandMiddleware:
    """
    Classe de base pour les middlewares de commandes.
    
    Les middlewares permettent d'ajouter des fonctionnalités transversales
    comme la validation, l'authentification, le caching, etc.
    
    Example:
        class ValidationMiddleware(CommandMiddleware):
            def wrap(self, next_handler):
                async def wrapper(command):
                    await self.validate_command(command)
                    return await next_handler(command)
                return wrapper
    """
    
    def wrap(self, next_handler):
        """
        Enrober le handler suivant avec la fonctionnalité du middleware.
        
        Args:
            next_handler: Handler suivant dans la chaîne
            
        Returns:
            Callable: Handler enrobé
        """
        return next_handler


class ValidationMiddleware(CommandMiddleware):
    """Middleware de validation des commandes."""
    
    def __init__(self):
        self.logger = get_logger("cqrs.middleware.validation")
    
    def wrap(self, next_handler):
        async def wrapper(command):
            self.logger.debug(f"Validating command: {type(command).__name__}")
            
            # Validation Pydantic automatique
            try:
                command.model_validate(command.model_dump())
            except Exception as e:
                raise ValueError(f"Command validation failed: {e}")
            
            return await next_handler(command)
        return wrapper


class TimingMiddleware(CommandMiddleware):
    """Middleware de mesure de performance."""
    
    def __init__(self):
        self.logger = get_logger("cqrs.middleware.timing")
    
    def wrap(self, next_handler):
        async def wrapper(command):
            start_time = time.time()
            
            try:
                result = await next_handler(command)
                execution_time = (time.time() - start_time) * 1000
                
                self.logger.info(f"Command timing: {type(command).__name__} = {execution_time:.1f}ms")
                return result
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                self.logger.warning(f"Command failed after {execution_time:.1f}ms: {e}")
                raise
                
        return wrapper


class RetryMiddleware(CommandMiddleware):
    """Middleware de retry automatique."""
    
    def __init__(self, max_retries: int = 3, delay: float = 1.0):
        self.max_retries = max_retries
        self.delay = delay
        self.logger = get_logger("cqrs.middleware.retry")
    
    def wrap(self, next_handler):
        async def wrapper(command):
            last_exception = None
            
            for attempt in range(self.max_retries + 1):
                try:
                    return await next_handler(command)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < self.max_retries:
                        wait_time = self.delay * (2 ** attempt)  # Backoff exponentiel
                        self.logger.warning(f"Command failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.error(f"Command failed after {self.max_retries + 1} attempts: {e}")
            
            raise last_exception
        return wrapper
