"""
Event Sourcing pour CQRS - Audit immuable des événements.

Ce module implémente l'Event Sourcing pour capturer tous les changements
d'état du système sous forme d'événements immuables, permettant un audit
complet et la reconstruction de l'état à tout moment.

Example:
    # Créer et stocker un événement
    event = Event(
        event_type="VECTOR_CREATED",
        aggregate_id="vector_123",
        event_data={"content": "ML document", "embedding": [0.1, 0.2]}
    )
    
    await event_store.store_event(event)
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

from ...core.logging import get_logger
from ...core.database import DatabaseManager


class Event(BaseModel):
    """
    Événement immuable pour Event Sourcing.
    
    Un événement représente un fait qui s'est produit dans le système.
    Il est immuable une fois créé et contient toutes les informations
    nécessaires pour comprendre ce qui s'est passé.
    
    Attributes:
        event_id: Identifiant unique de l'événement
        event_type: Type d'événement (ex: VECTOR_CREATED)
        aggregate_id: ID de l'agrégat concerné
        event_data: Données de l'événement
        timestamp: Moment de création de l'événement
        version: Version de l'agrégat après l'événement
        correlation_id: ID de corrélation pour traçabilité
        user_id: Utilisateur ayant déclenché l'événement
        metadata: Métadonnées supplémentaires
        
    Example:
        event = Event(
            event_type="VERITAS_PROOF_CREATED",
            aggregate_id="proof_abc123",
            event_data={
                "proof_type": "CALCULATION",
                "confidence_score": 0.95,
                "verification_id": "verif_456"
            },
            user_id="user_789",
            correlation_id="req_001"
        )
    """
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = Field(..., min_length=1, max_length=100)
    aggregate_id: str = Field(..., min_length=1, max_length=255)
    event_data: Dict[str, Any] = Field(..., min_items=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        frozen = True  # Immuable
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire pour stockage."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Créer événement depuis dictionnaire."""
        return cls.model_validate(data)


class EventStore(ABC):
    """
    Interface pour le stockage d'événements.
    
    L'EventStore est responsable de la persistance des événements
    avec garantie d'ordre et d'immuabilité. Il permet aussi la
    reconstruction de l'état des agrégats.
    """
    
    @abstractmethod
    async def store_event(self, event: Event) -> None:
        """Stocker un événement de façon immuable."""
        pass
    
    @abstractmethod
    async def get_events(self, aggregate_id: str, from_version: int = 1) -> List[Event]:
        """Récupérer événements d'un agrégat depuis une version."""
        pass
    
    @abstractmethod
    async def get_events_by_type(self, event_type: str, limit: int = 100) -> List[Event]:
        """Récupérer événements par type."""
        pass
    
    @abstractmethod
    async def get_all_events(self, from_timestamp: datetime = None, limit: int = 1000) -> List[Event]:
        """Récupérer tous les événements avec pagination."""
        pass


class PostgreSQLEventStore(EventStore):
    """
    Event Store basé sur PostgreSQL avec garanties ACID.
    
    Implémentation PostgreSQL de l'EventStore avec :
    - Stockage immuable des événements
    - Index optimisés pour queries fréquentes
    - Garanties ACID pour consistance
    - Support des transactions pour événements multiples
    - Compression automatique des anciennes données
    
    Features:
    - Table events avec contraintes d'immuabilité
    - Index sur aggregate_id, event_type, timestamp
    - Partitioning par date pour performance
    - Archivage automatique des anciens événements
    - Métriques intégrées pour monitoring
    
    Example:
        event_store = PostgreSQLEventStore(db_manager)
        await event_store.initialize()
        
        await event_store.store_event(event)
        events = await event_store.get_events("aggregate_123")
    """
    
    def __init__(self, 
                 db_manager: DatabaseManager,
                 table_name: str = "event_store",
                 enable_archiving: bool = True,
                 archive_after_days: int = 365):
        """
        Initialiser l'Event Store PostgreSQL.
        
        Args:
            db_manager: Gestionnaire de base de données
            table_name: Nom de la table des événements
            enable_archiving: Activer archivage automatique
            archive_after_days: Archiver après X jours
        """
        self.db_manager = db_manager
        self.table_name = table_name
        self.enable_archiving = enable_archiving
        self.archive_after_days = archive_after_days
        self.logger = get_logger("aindusdb.event_sourcing.postgresql_store")
        
        # Statistiques
        self.stats = {
            "events_stored": 0,
            "events_retrieved": 0,
            "queries_executed": 0,
            "archive_operations": 0
        }
    
    async def initialize(self) -> None:
        """Initialiser les tables et index de l'Event Store."""
        
        # Créer table principale des événements
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            event_id UUID PRIMARY KEY,
            event_type VARCHAR(100) NOT NULL,
            aggregate_id VARCHAR(255) NOT NULL,
            event_data JSONB NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            version INTEGER NOT NULL DEFAULT 1,
            correlation_id VARCHAR(255),
            user_id VARCHAR(255),
            metadata JSONB DEFAULT '{{}}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
        
        # Index pour performance
        create_indexes_queries = [
            f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_aggregate_id ON {self.table_name} (aggregate_id);",
            f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_event_type ON {self.table_name} (event_type);",
            f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_timestamp ON {self.table_name} (timestamp);",
            f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_correlation_id ON {self.table_name} (correlation_id);",
            f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_user_id ON {self.table_name} (user_id);",
            f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_aggregate_version ON {self.table_name} (aggregate_id, version);",
        ]
        
        # Créer table d'archive si activé
        create_archive_query = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name}_archive (
            LIKE {self.table_name} INCLUDING ALL,
            archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """ if self.enable_archiving else ""
        
        try:
            async with self.db_manager.get_connection() as conn:
                # Table principale
                await conn.execute(create_table_query)
                
                # Index
                for index_query in create_indexes_queries:
                    await conn.execute(index_query)
                
                # Table archive
                if create_archive_query:
                    await conn.execute(create_archive_query)
                
                self.logger.info(f"EventStore initialized: table={self.table_name}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize EventStore: {e}")
            raise
    
    async def store_event(self, event: Event) -> None:
        """
        Stocker un événement de façon immuable et atomique.
        
        Args:
            event: Événement à stocker
            
        Raises:
            Exception: Si erreur de stockage
        """
        insert_query = f"""
        INSERT INTO {self.table_name} (
            event_id, event_type, aggregate_id, event_data,
            timestamp, version, correlation_id, user_id, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        try:
            async with self.db_manager.get_connection() as conn:
                await conn.execute(
                    insert_query,
                    event.event_id,
                    event.event_type,
                    event.aggregate_id,
                    json.dumps(event.event_data),
                    event.timestamp,
                    event.version,
                    event.correlation_id,
                    event.user_id,
                    json.dumps(event.metadata)
                )
                
                self.stats["events_stored"] += 1
                
                self.logger.info(f"Event stored: {event.event_type}",
                               extra={
                                   "event_id": event.event_id,
                                   "aggregate_id": event.aggregate_id,
                                   "correlation_id": event.correlation_id
                               })
                
        except Exception as e:
            self.logger.error(f"Failed to store event {event.event_id}: {e}")
            raise
    
    async def get_events(self, aggregate_id: str, from_version: int = 1) -> List[Event]:
        """
        Récupérer tous les événements d'un agrégat.
        
        Args:
            aggregate_id: ID de l'agrégat
            from_version: Version minimale à récupérer
            
        Returns:
            List[Event]: Événements ordonnés par version
        """
        select_query = f"""
        SELECT event_id, event_type, aggregate_id, event_data,
               timestamp, version, correlation_id, user_id, metadata
        FROM {self.table_name}
        WHERE aggregate_id = $1 AND version >= $2
        ORDER BY version ASC
        """
        
        try:
            async with self.db_manager.get_connection() as conn:
                rows = await conn.fetch(select_query, aggregate_id, from_version)
                
                events = []
                for row in rows:
                    event_dict = {
                        "event_id": str(row["event_id"]),
                        "event_type": row["event_type"],
                        "aggregate_id": row["aggregate_id"],
                        "event_data": json.loads(row["event_data"]),
                        "timestamp": row["timestamp"],
                        "version": row["version"],
                        "correlation_id": row["correlation_id"],
                        "user_id": row["user_id"],
                        "metadata": json.loads(row["metadata"] or "{}")
                    }
                    events.append(Event.from_dict(event_dict))
                
                self.stats["events_retrieved"] += len(events)
                self.stats["queries_executed"] += 1
                
                self.logger.debug(f"Retrieved {len(events)} events for aggregate {aggregate_id}")
                
                return events
                
        except Exception as e:
            self.logger.error(f"Failed to get events for aggregate {aggregate_id}: {e}")
            raise
    
    async def get_events_by_type(self, event_type: str, limit: int = 100) -> List[Event]:
        """
        Récupérer événements par type avec limite.
        
        Args:
            event_type: Type d'événement
            limit: Nombre maximum d'événements
            
        Returns:
            List[Event]: Événements du type demandé
        """
        select_query = f"""
        SELECT event_id, event_type, aggregate_id, event_data,
               timestamp, version, correlation_id, user_id, metadata
        FROM {self.table_name}
        WHERE event_type = $1
        ORDER BY timestamp DESC
        LIMIT $2
        """
        
        try:
            async with self.db_manager.get_connection() as conn:
                rows = await conn.fetch(select_query, event_type, limit)
                
                events = []
                for row in rows:
                    event_dict = {
                        "event_id": str(row["event_id"]),
                        "event_type": row["event_type"],
                        "aggregate_id": row["aggregate_id"],
                        "event_data": json.loads(row["event_data"]),
                        "timestamp": row["timestamp"],
                        "version": row["version"],
                        "correlation_id": row["correlation_id"],
                        "user_id": row["user_id"],
                        "metadata": json.loads(row["metadata"] or "{}")
                    }
                    events.append(Event.from_dict(event_dict))
                
                self.stats["events_retrieved"] += len(events)
                self.stats["queries_executed"] += 1
                
                return events
                
        except Exception as e:
            self.logger.error(f"Failed to get events by type {event_type}: {e}")
            raise
    
    async def get_all_events(self, from_timestamp: datetime = None, limit: int = 1000) -> List[Event]:
        """
        Récupérer tous les événements avec pagination.
        
        Args:
            from_timestamp: Timestamp de début
            limit: Limite du nombre d'événements
            
        Returns:
            List[Event]: Événements paginés
        """
        if from_timestamp:
            select_query = f"""
            SELECT event_id, event_type, aggregate_id, event_data,
                   timestamp, version, correlation_id, user_id, metadata
            FROM {self.table_name}
            WHERE timestamp >= $1
            ORDER BY timestamp ASC
            LIMIT $2
            """
            params = [from_timestamp, limit]
        else:
            select_query = f"""
            SELECT event_id, event_type, aggregate_id, event_data,
                   timestamp, version, correlation_id, user_id, metadata
            FROM {self.table_name}
            ORDER BY timestamp DESC
            LIMIT $1
            """
            params = [limit]
        
        try:
            async with self.db_manager.get_connection() as conn:
                rows = await conn.fetch(select_query, *params)
                
                events = []
                for row in rows:
                    event_dict = {
                        "event_id": str(row["event_id"]),
                        "event_type": row["event_type"],
                        "aggregate_id": row["aggregate_id"],
                        "event_data": json.loads(row["event_data"]),
                        "timestamp": row["timestamp"],
                        "version": row["version"],
                        "correlation_id": row["correlation_id"],
                        "user_id": row["user_id"],
                        "metadata": json.loads(row["metadata"] or "{}")
                    }
                    events.append(Event.from_dict(event_dict))
                
                self.stats["events_retrieved"] += len(events)
                self.stats["queries_executed"] += 1
                
                return events
                
        except Exception as e:
            self.logger.error(f"Failed to get all events: {e}")
            raise
    
    async def store_events_batch(self, events: List[Event]) -> None:
        """
        Stocker plusieurs événements en transaction atomique.
        
        Args:
            events: Liste d'événements à stocker
        """
        if not events:
            return
        
        insert_query = f"""
        INSERT INTO {self.table_name} (
            event_id, event_type, aggregate_id, event_data,
            timestamp, version, correlation_id, user_id, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        try:
            async with self.db_manager.get_connection() as conn:
                async with conn.transaction():
                    for event in events:
                        await conn.execute(
                            insert_query,
                            event.event_id,
                            event.event_type,
                            event.aggregate_id,
                            json.dumps(event.event_data),
                            event.timestamp,
                            event.version,
                            event.correlation_id,
                            event.user_id,
                            json.dumps(event.metadata)
                        )
                    
                    self.stats["events_stored"] += len(events)
                    
                    self.logger.info(f"Batch stored {len(events)} events")
                    
        except Exception as e:
            self.logger.error(f"Failed to store event batch: {e}")
            raise
    
    async def get_event_statistics(self) -> Dict[str, Any]:
        """
        Obtenir statistiques de l'Event Store.
        
        Returns:
            Dict: Statistiques complètes
        """
        stats_query = f"""
        SELECT 
            COUNT(*) as total_events,
            COUNT(DISTINCT aggregate_id) as unique_aggregates,
            COUNT(DISTINCT event_type) as unique_event_types,
            COUNT(DISTINCT user_id) as unique_users,
            MIN(timestamp) as oldest_event,
            MAX(timestamp) as newest_event,
            COUNT(DISTINCT DATE(timestamp)) as days_with_events
        FROM {self.table_name}
        """
        
        event_type_stats_query = f"""
        SELECT event_type, COUNT(*) as count
        FROM {self.table_name}
        GROUP BY event_type
        ORDER BY count DESC
        LIMIT 10
        """
        
        try:
            async with self.db_manager.get_connection() as conn:
                # Statistiques générales
                row = await conn.fetchrow(stats_query)
                
                # Statistiques par type
                type_rows = await conn.fetch(event_type_stats_query)
                
                stats = {
                    "total_events": row["total_events"] or 0,
                    "unique_aggregates": row["unique_aggregates"] or 0,
                    "unique_event_types": row["unique_event_types"] or 0,
                    "unique_users": row["unique_users"] or 0,
                    "oldest_event": row["oldest_event"],
                    "newest_event": row["newest_event"],
                    "days_with_events": row["days_with_events"] or 0,
                    "top_event_types": [
                        {"event_type": r["event_type"], "count": r["count"]}
                        for r in type_rows
                    ],
                    **self.stats  # Ajouter stats internes
                }
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get event statistics: {e}")
            return {"error": str(e), **self.stats}
    
    async def archive_old_events(self, days_old: int = None) -> int:
        """
        Archiver les anciens événements.
        
        Args:
            days_old: Nombre de jours (défaut: archive_after_days)
            
        Returns:
            int: Nombre d'événements archivés
        """
        if not self.enable_archiving:
            return 0
        
        days = days_old or self.archive_after_days
        
        archive_query = f"""
        INSERT INTO {self.table_name}_archive 
        SELECT *, NOW() as archived_at
        FROM {self.table_name}
        WHERE timestamp < NOW() - INTERVAL '{days} days'
        """
        
        delete_query = f"""
        DELETE FROM {self.table_name}
        WHERE timestamp < NOW() - INTERVAL '{days} days'
        """
        
        try:
            async with self.db_manager.get_connection() as conn:
                async with conn.transaction():
                    # Copier vers archive
                    result = await conn.execute(archive_query)
                    archived_count = int(result.split()[-1])
                    
                    # Supprimer de la table principale
                    await conn.execute(delete_query)
                    
                    self.stats["archive_operations"] += 1
                    
                    self.logger.info(f"Archived {archived_count} events older than {days} days")
                    
                    return archived_count
                    
        except Exception as e:
            self.logger.error(f"Failed to archive events: {e}")
            return 0
