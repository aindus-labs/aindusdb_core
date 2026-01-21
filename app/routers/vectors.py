"""
Router pour les opérations vectorielles
"""
from fastapi import APIRouter, Depends, HTTPException
from ..core.database import get_database, DatabaseManager
from ..services.vector_service import VectorService
from ..models.vector import (
    VectorCreate, 
    VectorResponse, 
    VectorSearchRequest, 
    VectorSearchResponse
)

router = APIRouter(
    prefix="/vectors", 
    tags=["vectors"],
    responses={
        500: {"description": "Erreur serveur interne"},
        422: {"description": "Erreur de validation des données"}
    }
)


@router.post(
    "/test",
    response_model=VectorSearchResponse,
    summary="Test des opérations vectorielles",
    description="""
    Endpoint de test pour valider le fonctionnement des opérations vectorielles.
    
    Effectue automatiquement :
    * Création d'une table de test
    * Insertion d'un vecteur de test [1,2,3]
    * Recherche de similarité
    * Retourne les résultats
    
    Utilisé pour valider l'installation et la configuration de pgvector.
    """,
    responses={
        200: {
            "description": "Test réussi avec résultats",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Vector operations working with Docker deployment",
                        "results": [
                            {
                                "id": 1,
                                "metadata": "test-docker-deployment",
                                "distance": 0.0
                            }
                        ],
                        "count": 1
                    }
                }
            }
        },
        500: {
            "description": "Échec du test vectoriel",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Vector operation failed: table creation error"
                    }
                }
            }
        }
    }
)
async def test_vector_operations(db: DatabaseManager = Depends(get_database)):
    """
    Test des opérations vectorielles pour valider pgvector.
    
    Exécute un test complet des fonctionnalités vectorielles :
    - Création de table avec colonnes vector
    - Insertion de données vectorielles
    - Recherche par similarité cosinus
    
    Args:
        db: Gestionnaire de base de données injecté
        
    Returns:
        VectorSearchResponse: Résultats du test avec vecteurs trouvés
        
    Raises:
        HTTPException: 500 si les opérations vectorielles échouent
    """
    try:
        vector_service = VectorService(db)
        return await vector_service.test_vector_operations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector operation failed: {str(e)}")


@router.post(
    "/",
    response_model=dict,
    summary="Créer un nouveau vecteur",
    description="""
    Crée et stocke un nouveau vecteur dans la base de données.
    
    Le vecteur est stocké avec ses métadonnées associées.
    Les dimensions du vecteur doivent correspondre à la configuration
    de la table (par défaut 3D pour les tests).
    """,
    responses={
        200: {
            "description": "Vecteur créé avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Vector created successfully",
                        "id": 42
                    }
                }
            }
        },
        422: {
            "description": "Données invalides",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["embedding"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "description": "Erreur lors de la création",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Vector creation failed: dimension mismatch"
                    }
                }
            }
        }
    }
)
async def create_vector(
    vector: VectorCreate, 
    db: DatabaseManager = Depends(get_database)
):
    """
    Créer un nouveau vecteur.
    
    Stocke un vecteur avec ses métadonnées dans la base de données.
    Le vecteur sera automatiquement indexé pour les recherches de similarité.
    
    Args:
        vector: Données du vecteur à créer (embedding + métadonnées)
        db: Gestionnaire de base de données injecté
        
    Returns:
        dict: Confirmation avec l'ID du vecteur créé
        
    Raises:
        HTTPException: 422 pour données invalides, 500 pour erreurs serveur
    """
    try:
        vector_service = VectorService(db)
        vector_id = await vector_service.create_vector(vector)
        return {
            "status": "success",
            "message": "Vector created successfully",
            "id": vector_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector creation failed: {str(e)}")


@router.post(
    "/search",
    response_model=VectorSearchResponse,
    summary="Recherche de vecteurs similaires",
    description="""
    Effectue une recherche de similarité vectorielle.
    
    Utilise la distance cosinus pour trouver les vecteurs les plus similaires
    au vecteur de requête fourni.
    
    Paramètres de recherche :
    * **query_vector** : Vecteur de référence pour la recherche
    * **limit** : Nombre maximum de résultats (1-100)
    * **threshold** : Seuil de distance optionnel (0.0-2.0)
    """,
    responses={
        200: {
            "description": "Résultats de recherche",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Found 2 similar vectors",
                        "results": [
                            {
                                "id": 1,
                                "metadata": "similar-document-1",
                                "distance": 0.1
                            },
                            {
                                "id": 3,
                                "metadata": "similar-document-2", 
                                "distance": 0.3
                            }
                        ],
                        "count": 2
                    }
                }
            }
        },
        422: {
            "description": "Paramètres de recherche invalides",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["limit"],
                                "msg": "ensure this value is greater than 0",
                                "type": "value_error.number.not_gt"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def search_vectors(
    search_request: VectorSearchRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    Rechercher des vecteurs similaires.
    
    Effectue une recherche de similarité basée sur la distance cosinus.
    Les résultats sont triés par distance croissante (plus similaire en premier).
    
    Args:
        search_request: Paramètres de recherche (vecteur, limite, seuil)
        db: Gestionnaire de base de données injecté
        
    Returns:
        VectorSearchResponse: Liste des vecteurs similaires avec leurs distances
        
    Raises:
        HTTPException: 422 pour paramètres invalides, 500 pour erreurs serveur
    """
    try:
        vector_service = VectorService(db)
        return await vector_service.search_vectors(search_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector search failed: {str(e)}")


@router.get(
    "/{vector_id}",
    response_model=VectorResponse,
    summary="Récupérer un vecteur par ID",
    description="""
    Récupère un vecteur spécifique par son identifiant.
    
    **Note** : Cette fonctionnalité n'est pas encore implémentée.
    Sera disponible dans une version future.
    """,
    responses={
        501: {
            "description": "Fonctionnalité non implémentée",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not implemented yet"
                    }
                }
            }
        }
    }
)
async def get_vector(
    vector_id: int,
    db: DatabaseManager = Depends(get_database)
):
    """
    Récupérer un vecteur par ID.
    
    Args:
        vector_id: Identifiant unique du vecteur
        db: Gestionnaire de base de données injecté
        
    Returns:
        VectorResponse: Données du vecteur demandé
        
    Raises:
        HTTPException: 501 car non implémenté pour le moment
    """
    try:
        # TODO: Implémenter la récupération d'un vecteur par ID
        raise HTTPException(status_code=501, detail="Not implemented yet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector retrieval failed: {str(e)}")


@router.delete(
    "/{vector_id}",
    response_model=dict,
    summary="Supprimer un vecteur par ID",
    description="""
    Supprime un vecteur spécifique par son identifiant.
    
    **Note** : Cette fonctionnalité n'est pas encore implémentée.
    Sera disponible dans une version future.
    """,
    responses={
        501: {
            "description": "Fonctionnalité non implémentée",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not implemented yet"
                    }
                }
            }
        }
    }
)
async def delete_vector(
    vector_id: int,
    db: DatabaseManager = Depends(get_database)
):
    """
    Supprimer un vecteur par ID.
    
    Args:
        vector_id: Identifiant unique du vecteur à supprimer
        db: Gestionnaire de base de données injecté
        
    Returns:
        dict: Confirmation de suppression
        
    Raises:
        HTTPException: 501 car non implémenté pour le moment
    """
    try:
        # TODO: Implémenter la suppression d'un vecteur par ID
        raise HTTPException(status_code=501, detail="Not implemented yet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector deletion failed: {str(e)}")
