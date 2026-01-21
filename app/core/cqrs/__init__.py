"""
CQRS (Command Query Responsibility Segregation) Pattern pour AindusDB Core.

Ce module implémente le pattern CQRS pour séparer les opérations de lecture
et d'écriture, permettant une optimisation et une scalabilité indépendantes.

Architecture CQRS:
- Commands: Opérations d'écriture (CREATE, UPDATE, DELETE)  
- Queries: Opérations de lecture (SELECT, SEARCH)
- Handlers: Gestionnaires spécialisés pour chaque type d'opération
- Event Store: Stockage des événements pour audit complet

Example:
    from app.core.cqrs import CommandBus, QueryBus
    
    # Opérations d'écriture
    command_bus = CommandBus()
    await command_bus.execute(CreateVectorCommand(data))
    
    # Opérations de lecture  
    query_bus = QueryBus()
    results = await query_bus.execute(SearchVectorsQuery(query))
"""

from .command_bus import CommandBus
from .query_bus import QueryBus
from .commands import Command, CommandHandler
from .queries import Query, QueryHandler
from .events import Event, EventStore
from .cqrs_coordinator import CQRSCoordinator

__all__ = [
    "CommandBus",
    "QueryBus", 
    "Command",
    "CommandHandler",
    "Query",
    "QueryHandler",
    "Event",
    "EventStore",
    "CQRSCoordinator"
]
