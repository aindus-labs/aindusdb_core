"""
Command Pattern pour CQRS - Opérations d'écriture.

Ce module définit les commandes (opérations d'écriture) et leurs handlers
pour le pattern CQRS. Chaque commande représente une intention d'action
qui modifie l'état du système.

Example:
    # Définir une commande
    class CreateVectorCommand(Command):
        content: str
        embedding: List[float]
        metadata: Dict[str, Any]
    
    # Handler associé
    class CreateVectorHandler(CommandHandler[CreateVectorCommand]):
        async def handle(self, command: CreateVectorCommand) -> str:
            vector_id = await self.db.create_vector(...)
            return vector_id
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field

from ...core.logging import get_logger


# Types génériques pour CQRS
TCommand = TypeVar('TCommand', bound='Command')
TResult = TypeVar('TResult')


class Command(BaseModel):
    """
    Classe de base pour toutes les commandes CQRS.
    
    Une commande représente une intention d'action qui modifie l'état
    du système. Elle contient toutes les données nécessaires pour
    exécuter l'opération d'écriture.
    
    Attributes:
        command_id: Identifiant unique de la commande
        timestamp: Moment de création de la commande
        user_id: Utilisateur qui a initié la commande
        correlation_id: ID de corrélation pour traçabilité
        
    Example:
        class UpdateVectorCommand(Command):
            vector_id: str
            new_content: str
            metadata: Dict[str, Any]
    """
    
    command_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    class Config:
        extra = "allow"


class CommandHandler(ABC, Generic[TCommand, TResult]):
    """
    Classe de base pour les handlers de commandes.
    
    Chaque handler est responsable d'exécuter une seule type de commande
    selon le principe Single Responsibility. Il contient la logique
    métier pour transformer l'intention en action concrète.
    
    Example:
        class CreateVectorHandler(CommandHandler[CreateVectorCommand, str]):
            def __init__(self, db_manager: DatabaseManager):
                self.db = db_manager
                self.logger = get_logger("commands.create_vector")
            
            async def handle(self, command: CreateVectorCommand) -> str:
                # Logique de création du vecteur
                return vector_id
    """
    
    def __init__(self):
        self.logger = get_logger(f"commands.{self.__class__.__name__.lower()}")
    
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        """
        Exécuter la commande et retourner le résultat.
        
        Args:
            command: Commande à exécuter
            
        Returns:
            TResult: Résultat de l'exécution
        """
        pass
    
    async def validate(self, command: TCommand) -> None:
        """
        Valider la commande avant exécution.
        
        Args:
            command: Commande à valider
            
        Raises:
            ValueError: Si la commande est invalide
        """
        # Validation de base - peut être surchargée
        if not command.command_id:
            raise ValueError("Command ID is required")


# ===== COMMANDES VECTORIELLES =====

class CreateVectorCommand(Command):
    """Commande pour créer un nouveau vecteur."""
    content: str = Field(..., min_length=1, max_length=10000)
    embedding: List[float] = Field(..., min_items=1, max_items=2048)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_type: str = "manual"
    quality_score: float = Field(default=0.8, ge=0.0, le=1.0)


class UpdateVectorCommand(Command):
    """Commande pour mettre à jour un vecteur existant."""
    vector_id: str = Field(..., min_length=1)
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    embedding: Optional[List[float]] = Field(None, min_items=1, max_items=2048)
    metadata: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class DeleteVectorCommand(Command):
    """Commande pour supprimer un vecteur."""
    vector_id: str = Field(..., min_length=1)
    soft_delete: bool = True
    reason: Optional[str] = None


# ===== COMMANDES VERITAS =====

class CreateVeritasProofCommand(Command):
    """Commande pour créer une preuve VERITAS."""
    verification_id: str = Field(..., min_length=1)
    proof_data: Dict[str, Any] = Field(..., min_items=1)
    proof_type: str = Field(..., min_length=1)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    verifier_system: str = Field(..., min_length=1)


class UpdateVeritasProofCommand(Command):
    """Commande pour mettre à jour une preuve VERITAS."""
    proof_id: str = Field(..., min_length=1)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    verification_status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ===== COMMANDES BATCH =====

class BatchCreateVectorsCommand(Command):
    """Commande pour création de vecteurs en batch."""
    vectors_data: List[Dict[str, Any]] = Field(..., min_items=1, max_items=1000)
    batch_size: int = Field(default=100, ge=1, le=1000)
    parallel_processing: bool = True
    fail_on_error: bool = False


class BatchUpdateVectorsCommand(Command):
    """Commande pour mise à jour de vecteurs en batch."""
    updates: List[Dict[str, Any]] = Field(..., min_items=1, max_items=1000)
    batch_size: int = Field(default=100, ge=1, le=1000)
    parallel_processing: bool = True


# ===== COMMANDES AUDIT =====

class LogAuditEventCommand(Command):
    """Commande pour enregistrer un événement d'audit."""
    event_type: str = Field(..., min_length=1)
    resource_id: str = Field(..., min_length=1)
    resource_type: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


# ===== COMMANDES MÉTRIQUES =====

class RecordMetricCommand(Command):
    """Commande pour enregistrer une métrique."""
    metric_name: str = Field(..., min_length=1)
    metric_value: float = Field(...)
    metric_type: str = Field(..., pattern="^(counter|gauge|histogram|summary)$")
    labels: Dict[str, str] = Field(default_factory=dict)
    unit: Optional[str] = None


# ===== COMMANDES CACHE =====

class InvalidateCacheCommand(Command):
    """Commande pour invalider le cache."""
    cache_key: Optional[str] = None
    cache_pattern: Optional[str] = None
    cache_type: str = Field(default="redis", pattern="^(redis|memory|all)$")
    reason: Optional[str] = None


class WarmupCacheCommand(Command):
    """Commande pour réchauffer le cache."""
    cache_keys: List[str] = Field(..., min_items=1)
    priority: int = Field(default=1, ge=1, le=10)
    async_mode: bool = True


# ===== FACTORY PATTERN =====

class CommandFactory:
    """Factory pour créer des commandes avec validation."""
    
    @staticmethod
    def create_vector_command(
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any] = None,
        user_id: str = None
    ) -> CreateVectorCommand:
        """
        Créer une commande de création de vecteur validée.
        
        Args:
            content: Contenu textuel du vecteur
            embedding: Vecteur d'embedding
            metadata: Métadonnées optionnelles
            user_id: Utilisateur initiateur
            
        Returns:
            CreateVectorCommand: Commande validée
        """
        return CreateVectorCommand(
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            user_id=user_id,
            correlation_id=str(uuid.uuid4())
        )
    
    @staticmethod
    def create_veritas_proof_command(
        verification_id: str,
        proof_data: Dict[str, Any],
        proof_type: str,
        confidence_score: float,
        user_id: str = None
    ) -> CreateVeritasProofCommand:
        """
        Créer une commande de preuve VERITAS validée.
        
        Args:
            verification_id: ID de vérification
            proof_data: Données de la preuve
            proof_type: Type de preuve
            confidence_score: Score de confiance
            user_id: Utilisateur initiateur
            
        Returns:
            CreateVeritasProofCommand: Commande validée
        """
        return CreateVeritasProofCommand(
            verification_id=verification_id,
            proof_data=proof_data,
            proof_type=proof_type,
            confidence_score=confidence_score,
            verifier_system="cqrs_v1",
            user_id=user_id,
            correlation_id=str(uuid.uuid4())
        )
