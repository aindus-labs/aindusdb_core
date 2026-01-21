"""
Modèles Pydantic pour les opérations vectorielles dans AindusDB Core.

Ce module définit tous les modèles de données utilisés pour les opérations
vectorielles : création, recherche, réponses API. Les modèles utilisent
Pydantic pour la validation automatique des données et la génération
de documentation OpenAPI.

Example:
    from app.models.vector import VectorCreate, VectorSearchRequest
    
    # Création d'un nouveau vecteur
    new_vector = VectorCreate(
        embedding=[0.1, 0.2, 0.3],
        metadata="Document d'exemple"
    )
    
    # Recherche vectorielle
    search_req = VectorSearchRequest(
        query_vector=[0.15, 0.25, 0.35],
        limit=10
    )
"""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, validator, model_validator, field_validator
from .veritas import ContentType, QualityMetadata, SourceMetadata


class VectorBase(BaseModel):
    """
    Modèle de base pour tous les types de vecteurs avec support VERITAS.
    
    Classe parente contenant les champs communs à tous les modèles
    de vecteurs. Définit la structure fondamentale d'un vecteur
    avec son embedding et ses métadonnées, enrichie pour VERITAS.
    
    Attributes:
        embedding: Liste de nombres flottants représentant le vecteur
        metadata: Métadonnées textuelles optionnelles associées au vecteur
        content_type: Type de contenu (markdown, latex, etc.)
        source_hash: Hash SHA-256 du document source pour traçabilité VERITAS
        quality_metadata: Métadonnées de qualité pour vérification
        latex_content: Version LaTeX du contenu pour équations
        veritas_compatible: Compatible avec protocole VERITAS
        
    Example:
        # Vecteur avec support VERITAS
        vector = VectorBase(
            embedding=[0.1, 0.2, 0.3],
            metadata="Newton's second law",
            content_type=ContentType.LATEX,
            source_hash="abc123...",
            veritas_compatible=True
        )
    """
    embedding: List[float] = Field(
        ..., 
        description="Vecteur d'embedding sous forme de liste de nombres flottants",
        min_items=1,
        max_items=10000,
        example=[0.1, 0.2, 0.3, 0.4, 0.5]
    )
    metadata: Optional[str] = Field(
        None, 
        description="Métadonnées textuelles associées au vecteur",
        max_length=5000
    )
    
    # Nouveaux champs VERITAS
    content_type: Optional[ContentType] = Field(
        default=ContentType.MARKDOWN,
        description="Type de contenu du document source"
    )
    source_hash: Optional[str] = Field(
        None,
        pattern=r"^[a-f0-9]{64}$",
        description="Hash SHA-256 du document source pour traçabilité VERITAS"
    )
    quality_metadata: Optional[QualityMetadata] = Field(
        None,
        description="Métadonnées de qualité pour vérification VERITAS"
    )
    latex_content: Optional[str] = Field(
        None,
        max_length=10000,
        description="Version LaTeX du contenu pour équations et formules"
    )
    veritas_compatible: Optional[bool] = Field(
        default=False,
        description="Document compatible avec protocole VERITAS"
    )

    @field_validator('embedding')
    def validate_embedding(cls, v):
        """
        Valider que l'embedding est correct.
        
        Vérifie que tous les éléments sont des nombres finis
        et que la liste n'est pas vide.
        """
        if not v:
            raise ValueError("L'embedding ne peut pas être vide")
        
        for i, val in enumerate(v):
            if not isinstance(val, (int, float)):
                raise ValueError(f"Élément {i} doit être un nombre")
            if not (-1e10 < val < 1e10):
                raise ValueError(f"Élément {i} doit être un nombre fini")
        
        return v


class VectorCreate(VectorBase):
    """
    Modèle pour la création de nouveaux vecteurs.
    
    Utilisé dans les requêtes POST pour créer de nouveaux vecteurs
    dans la base de données. Hérite de VectorBase sans ajout de champs
    supplémentaires.
    
    Example:
        # Créer un vecteur via l'API
        vector_data = VectorCreate(
            embedding=[0.1, 0.2, 0.3],
            metadata="Premier document"
        )
        
        response = requests.post(
            "http://localhost:8000/vectors/",
            json=vector_data.dict()
        )
    """
    pass


class VectorModel(VectorBase):
    """
    Modèle complet d'un vecteur avec identifiant de base de données.
    
    Représente un vecteur tel qu'il est stocké en base de données,
    incluant l'ID auto-généré. Utilisé pour les réponses API qui
    retournent des vecteurs existants.
    
    Attributes:
        id: Identifiant unique auto-généré par PostgreSQL
        embedding: Hérité de VectorBase
        metadata: Hérité de VectorBase
        
    Example:
        # Vecteur récupéré de la base de données
        stored_vector = VectorModel(
            id=42,
            embedding=[0.1, 0.2, 0.3],
            metadata="Document stocké"
        )
    """
    id: int = Field(
        ..., 
        description="Identifiant unique du vecteur en base de données",
        gt=0,
        example=42
    )
    
    class Config:
        from_attributes = True


class VectorResponse(BaseModel):
    """
    Modèle de réponse pour les résultats de recherche vectorielle.
    
    Utilisé dans les réponses de recherche de similarité pour retourner
    un vecteur avec sa distance par rapport à la requête. Plus léger
    que VectorModel car ne contient pas l'embedding complet.
    
    Attributes:
        id: Identifiant du vecteur trouvé
        metadata: Métadonnées du vecteur pour contexte
        distance: Distance calculée entre le vecteur de requête et ce résultat
        
    Example:
        # Résultat de recherche
        result = VectorResponse(
            id=123,
            metadata="Document pertinent",
            distance=0.25
        )
    """
    id: int = Field(
        ..., 
        description="Identifiant unique du vecteur",
        example=123
    )
    metadata: Optional[str] = Field(
        None, 
        description="Métadonnées associées au vecteur",
        example="Document sur les bases de données vectorielles"
    )
    distance: float = Field(
        ..., 
        description="Distance entre le vecteur de requête et ce résultat",
        ge=0.0,
        example=0.25
    )
    
    class Config:
        from_attributes = True


class VectorSearchRequest(BaseModel):
    """
    Modèle de requête pour la recherche de similarité vectorielle.
    
    Définit les paramètres d'une recherche vectorielle : le vecteur
    de requête, le nombre de résultats souhaités et un seuil de
    distance optionnel pour filtrer les résultats.
    
    Attributes:
        query_vector: Vecteur pour lequel chercher des similarités
        limit: Nombre maximum de résultats à retourner (1-100)
        threshold: Seuil de distance maximum pour inclure un résultat
        
    Example:
        # Recherche de 10 vecteurs similaires
        search = VectorSearchRequest(
            query_vector=[0.1, 0.2, 0.3],
            limit=10,
            threshold=0.5
        )
        
        # Utiliser dans une requête API
        response = requests.post(
            "http://localhost:8000/vectors/search",
            json=search.dict()
        )
    """
    query_vector: List[float] = Field(
        ..., 
        description="Vecteur de recherche pour trouver des similarités",
        min_items=1,
        max_items=10000,
        example=[0.1, 0.2, 0.3, 0.4, 0.5]
    )
    limit: int = Field(
        5, 
        ge=1, 
        le=100, 
        description="Nombre maximum de résultats à retourner",
        example=10
    )
    threshold: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=2.0, 
        description="Seuil de distance maximum (seuls les résultats avec distance <= threshold sont inclus)",
        example=0.5
    )

    @field_validator('query_vector')
    def validate_query_vector(cls, v):
        """
        Valider le vecteur de recherche.
        
        Applique les mêmes validations que VectorBase.embedding
        pour garantir la cohérence.
        """
        if not v:
            raise ValueError("Le vecteur de recherche ne peut pas être vide")
        
        for i, val in enumerate(v):
            if not isinstance(val, (int, float)):
                raise ValueError(f"Élément {i} doit être un nombre")
            if not (-1e10 < val < 1e10):
                raise ValueError(f"Élément {i} doit être un nombre fini")
        
        return v


class VectorSearchResponse(BaseModel):
    """
    Modèle de réponse pour les opérations de recherche vectorielle.
    
    Structure standardisée pour toutes les réponses de recherche,
    incluant le statut, un message descriptif, les résultats trouvés
    et le nombre total de résultats.
    
    Attributes:
        status: Statut de l'opération ("success" ou "error")
        message: Message descriptif de l'opération
        results: Liste des vecteurs trouvés avec leurs distances
        count: Nombre total de résultats retournés
        
    Example:
        # Réponse de recherche réussie
        response = VectorSearchResponse(
            status="success",
            message="Trouvé 3 vecteurs similaires",
            results=[
                VectorResponse(id=1, metadata="Doc 1", distance=0.1),
                VectorResponse(id=2, metadata="Doc 2", distance=0.2)
            ],
            count=2
        )
        
        # Réponse d'erreur
        error_response = VectorSearchResponse(
            status="error", 
            message="Vecteur de recherche invalide",
            results=[],
            count=0
        )
    """
    status: str = Field(
        "success",
        description="Statut de l'opération",
        pattern="^(success|error)$",
        example="success"
    )
    message: str = Field(
        ...,
        description="Message descriptif de l'opération",
        example="Trouvé 5 vecteurs similaires en 12ms"
    )
    results: List[VectorResponse] = Field(
        ...,
        description="Liste des vecteurs trouvés avec leurs distances",
        example=[]
    )
    count: int = Field(
        ...,
        description="Nombre total de résultats retournés", 
        ge=0,
        example=5
    )
