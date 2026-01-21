"""
Query Pattern pour CQRS - Opérations de lecture.

Ce module définit les queries (opérations de lecture) et leurs handlers
pour le pattern CQRS. Chaque query représente une demande d'information
sans modifier l'état du système.

Example:
    # Définir une query
    class SearchVectorsQuery(Query):
        query_text: str
        limit: int = 50
        filters: Dict[str, Any] = {}
    
    # Handler associé
    class SearchVectorsHandler(QueryHandler[SearchVectorsQuery]):
        async def handle(self, query: SearchVectorsQuery) -> List[Vector]:
            return await self.db.search_vectors(...)
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field

from ...core.logging import get_logger


# Types génériques pour CQRS
TQuery = TypeVar('TQuery', bound='Query')
TResult = TypeVar('TResult')


class Query(BaseModel):
    """
    Classe de base pour toutes les queries CQRS.
    
    Une query représente une demande d'information sans modification
    d'état. Elle contient tous les paramètres nécessaires pour
    récupérer les données demandées.
    
    Attributes:
        query_id: Identifiant unique de la query
        timestamp: Moment de création de la query
        user_id: Utilisateur qui a initié la query
        correlation_id: ID de corrélation pour traçabilité
        
    Example:
        class GetVectorByIdQuery(Query):
            vector_id: str
            include_metadata: bool = True
    """
    
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    class Config:
        extra = "allow"


class QueryHandler(ABC, Generic[TQuery, TResult]):
    """
    Classe de base pour les handlers de queries.
    
    Chaque handler est responsable d'exécuter une seule type de query
    selon le principe Single Responsibility. Il contient la logique
    optimisée pour la lecture des données.
    
    Example:
        class SearchVectorsHandler(QueryHandler[SearchVectorsQuery, List[Vector]]):
            def __init__(self, db_manager: DatabaseManager):
                self.db = db_manager
                self.logger = get_logger("queries.search_vectors")
            
            async def handle(self, query: SearchVectorsQuery) -> List[Vector]:
                # Logique de recherche optimisée
                return vectors
    """
    
    def __init__(self):
        self.logger = get_logger(f"queries.{self.__class__.__name__.lower()}")
    
    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """
        Exécuter la query et retourner le résultat.
        
        Args:
            query: Query à exécuter
            
        Returns:
            TResult: Résultat de la query
        """
        pass
    
    async def validate(self, query: TQuery) -> None:
        """
        Valider la query avant exécution.
        
        Args:
            query: Query à valider
            
        Raises:
            ValueError: Si la query est invalide
        """
        # Validation de base - peut être surchargée
        if not query.query_id:
            raise ValueError("Query ID is required")


# ===== QUERIES VECTORIELLES =====

class GetVectorByIdQuery(Query):
    """Query pour récupérer un vecteur par son ID."""
    vector_id: str = Field(..., min_length=1)
    include_metadata: bool = True
    include_embedding: bool = False


class SearchVectorsQuery(Query):
    """Query pour recherche sémantique de vecteurs."""
    query_text: Optional[str] = None
    query_embedding: Optional[List[float]] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    filters: Dict[str, Any] = Field(default_factory=dict)
    include_metadata: bool = True
    include_embeddings: bool = False
    sort_by: str = "similarity"
    order: str = Field(default="desc", regex="^(asc|desc)$")


class ListVectorsQuery(Query):
    """Query pour lister les vecteurs avec pagination."""
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    filters: Dict[str, Any] = Field(default_factory=dict)
    include_metadata: bool = True
    include_embeddings: bool = False
    sort_by: str = "created_at"
    order: str = Field(default="desc", regex="^(asc|desc)$")


class CountVectorsQuery(Query):
    """Query pour compter les vecteurs selon des critères."""
    filters: Dict[str, Any] = Field(default_factory=dict)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ===== QUERIES VERITAS =====

class GetVeritasProofByIdQuery(Query):
    """Query pour récupérer une preuve VERITAS par ID."""
    proof_id: str = Field(..., min_length=1)
    include_computation_steps: bool = True
    include_metadata: bool = True


class SearchVeritasProofsQuery(Query):
    """Query pour rechercher des preuves VERITAS."""
    verification_id: Optional[str] = None
    proof_type: Optional[str] = None
    verification_status: Optional[str] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    verifier_system: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    sort_by: str = "confidence_score"
    order: str = Field(default="desc", regex="^(asc|desc)$")


class GetVeritasStatsQuery(Query):
    """Query pour obtenir statistiques VERITAS."""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    group_by: str = Field(default="day", regex="^(hour|day|week|month)$")
    include_distribution: bool = True
    include_trends: bool = True


# ===== QUERIES ANALYTICS =====

class GetVectorAnalyticsQuery(Query):
    """Query pour analytics des vecteurs."""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    metrics: List[str] = Field(default_factory=lambda: ["count", "avg_quality", "source_distribution"])
    group_by: str = Field(default="day", regex="^(hour|day|week|month)$")
    filters: Dict[str, Any] = Field(default_factory=dict)


class GetPerformanceMetricsQuery(Query):
    """Query pour métriques de performance."""
    metric_names: List[str] = Field(default_factory=list)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    aggregation: str = Field(default="avg", regex="^(avg|sum|min|max|count)$")
    resolution: str = Field(default="5m", regex="^(1m|5m|15m|1h|1d)$")


class GetSystemHealthQuery(Query):
    """Query pour l'état de santé du système."""
    include_database: bool = True
    include_redis: bool = True
    include_services: bool = True
    include_metrics: bool = True
    deep_check: bool = False


# ===== QUERIES AUDIT =====

class GetAuditLogsQuery(Query):
    """Query pour récupérer les logs d'audit."""
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
    user_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    include_details: bool = True


class GetUserActivityQuery(Query):
    """Query pour activité utilisateur."""
    user_id: str = Field(..., min_length=1)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    action_types: List[str] = Field(default_factory=list)
    limit: int = Field(default=100, ge=1, le=1000)
    include_details: bool = False


# ===== QUERIES CACHE =====

class GetCacheStatsQuery(Query):
    """Query pour statistiques du cache."""
    cache_type: str = Field(default="all", regex="^(redis|memory|all)$")
    include_keys: bool = False
    include_memory_usage: bool = True


class CheckCacheKeyQuery(Query):
    """Query pour vérifier une clé de cache."""
    cache_key: str = Field(..., min_length=1)
    cache_type: str = Field(default="redis", regex="^(redis|memory)$")
    include_value: bool = False
    include_ttl: bool = True


# ===== QUERIES BATCH =====

class GetBatchOperationStatusQuery(Query):
    """Query pour statut d'opération batch."""
    batch_id: str = Field(..., min_length=1)
    include_details: bool = True
    include_progress: bool = True
    include_errors: bool = True


class ListBatchOperationsQuery(Query):
    """Query pour lister les opérations batch."""
    status: Optional[str] = Field(None, regex="^(pending|running|completed|failed)$")
    operation_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ===== FACTORY PATTERN =====

class QueryFactory:
    """Factory pour créer des queries avec validation."""
    
    @staticmethod
    def create_search_query(
        query_text: str = None,
        query_embedding: List[float] = None,
        limit: int = 50,
        similarity_threshold: float = 0.7,
        user_id: str = None
    ) -> SearchVectorsQuery:
        """
        Créer une query de recherche validée.
        
        Args:
            query_text: Texte de recherche
            query_embedding: Vecteur de recherche
            limit: Nombre de résultats
            similarity_threshold: Seuil de similarité
            user_id: Utilisateur initiateur
            
        Returns:
            SearchVectorsQuery: Query validée
        """
        if not query_text and not query_embedding:
            raise ValueError("Either query_text or query_embedding is required")
        
        return SearchVectorsQuery(
            query_text=query_text,
            query_embedding=query_embedding,
            limit=limit,
            similarity_threshold=similarity_threshold,
            user_id=user_id,
            correlation_id=str(uuid.uuid4())
        )
    
    @staticmethod
    def create_veritas_search_query(
        verification_id: str = None,
        proof_type: str = None,
        min_confidence: float = None,
        limit: int = 50,
        user_id: str = None
    ) -> SearchVeritasProofsQuery:
        """
        Créer une query de recherche VERITAS validée.
        
        Args:
            verification_id: ID de vérification
            proof_type: Type de preuve
            min_confidence: Confiance minimale
            limit: Nombre de résultats
            user_id: Utilisateur initiateur
            
        Returns:
            SearchVeritasProofsQuery: Query validée
        """
        return SearchVeritasProofsQuery(
            verification_id=verification_id,
            proof_type=proof_type,
            min_confidence=min_confidence,
            limit=limit,
            user_id=user_id,
            correlation_id=str(uuid.uuid4())
        )
    
    @staticmethod
    def create_analytics_query(
        date_from: datetime = None,
        date_to: datetime = None,
        metrics: List[str] = None,
        group_by: str = "day",
        user_id: str = None
    ) -> GetVectorAnalyticsQuery:
        """
        Créer une query d'analytics validée.
        
        Args:
            date_from: Date de début
            date_to: Date de fin
            metrics: Métriques à inclure
            group_by: Groupement temporel
            user_id: Utilisateur initiateur
            
        Returns:
            GetVectorAnalyticsQuery: Query validée
        """
        return GetVectorAnalyticsQuery(
            date_from=date_from,
            date_to=date_to,
            metrics=metrics or ["count", "avg_quality"],
            group_by=group_by,
            user_id=user_id,
            correlation_id=str(uuid.uuid4())
        )
