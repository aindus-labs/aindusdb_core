"""
Service de gestion des opérations vectorielles pour AindusDB Core.

Ce module implémente la couche de logique métier pour toutes les opérations
vectorielles : création, recherche, gestion des tables de test. Il fait le lien
entre les modèles Pydantic et la base de données PostgreSQL avec pgvector.

Example:
    from app.services.vector_service import VectorService
    from app.core.database import db_manager
    from app.models.vector import VectorCreate, VectorSearchRequest
    
    # Initialiser le service
    vector_service = VectorService(db_manager)
    
    # Créer un vecteur
    new_vector = VectorCreate(embedding=[0.1, 0.2, 0.3], metadata="test")
    vector_id = await vector_service.create_vector(new_vector)
    
    # Rechercher des vecteurs similaires
    search = VectorSearchRequest(query_vector=[0.1, 0.2, 0.3], limit=10)
    results = await vector_service.search_vectors(search)
"""
from typing import List, Optional
from ..core.database import DatabaseManager
from ..models.vector import VectorCreate, VectorResponse, VectorSearchRequest, VectorSearchResponse


class VectorService:
    """
    Service de gestion des opérations vectorielles avec pgvector.
    
    Cette classe centralise toute la logique métier pour les opérations
    vectorielles dans AindusDB Core. Elle gère la création de vecteurs,
    la recherche de similarité, les tests d'opérations et la communication
    avec PostgreSQL + pgvector.
    
    Le service utilise des requêtes SQL optimisées pour pgvector et gère
    automatiquement la conversion des embeddings Python vers le format
    PostgreSQL vector.
    
    Attributes:
        db: Instance du gestionnaire de base de données pour les requêtes
        
    Example:
        # Utilisation avec dependency injection FastAPI
        @router.post("/vectors/")
        async def create_vector_endpoint(
            vector: VectorCreate,
            vector_service: VectorService = Depends(get_vector_service)
        ):
            vector_id = await vector_service.create_vector(vector)
            return {"id": vector_id, "status": "created"}
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialiser le service vectoriel avec un gestionnaire de base de données.
        
        Args:
            db_manager: Instance du DatabaseManager pour les opérations SQL
        """
        self.db = db_manager
    
    async def create_test_table(self):
        """
        Créer la table de test vectorielle si elle n'existe pas.
        
        Crée une table temporaire `test_vectors` utilisée pour les tests
        d'opérations pgvector. La table contient des vecteurs à 3 dimensions
        pour des tests rapides et cohérents.
        
        Table schema:
            - id: SERIAL PRIMARY KEY (identifiant auto-généré)
            - embedding: vector(3) (vecteur pgvector 3 dimensions)  
            - metadata: TEXT (métadonnées textuelles optionnelles)
            
        Raises:
            Exception: Si la création de table échoue (permissions, SQL invalide)
            
        Example:
            vector_service = VectorService(db_manager)
            await vector_service.create_test_table()
            # Table test_vectors maintenant disponible
        """
        query = """
            CREATE TABLE IF NOT EXISTS test_vectors (
                id SERIAL PRIMARY KEY,
                embedding vector(3),
                metadata TEXT
            )
        """
        await self.db.execute_query(query)
    
    async def insert_test_vector(self, vector_data: str, metadata: str) -> int:
        """
        Insérer un vecteur de test dans la table test_vectors.
        
        Insère un nouveau vecteur dans la table de test avec les données
        d'embedding au format string PostgreSQL et des métadonnées optionnelles.
        Retourne l'ID auto-généré du vecteur créé.
        
        Args:
            vector_data: Vecteur au format string PostgreSQL (ex: "[1,2,3]")
            metadata: Métadonnées textuelles à associer au vecteur
            
        Returns:
            int: ID unique du vecteur inséré (généré par SERIAL)
            
        Raises:
            Exception: Si l'insertion échoue (format invalide, contraintes DB)
            
        Example:
            vector_id = await vector_service.insert_test_vector(
                "[0.1,0.2,0.3]", 
                "Document de test"
            )
            print(f"Vecteur créé avec ID: {vector_id}")
        """
        query = """
            INSERT INTO test_vectors (embedding, metadata) 
            VALUES ($1::vector, $2)
            RETURNING id
        """
        result = await self.db.fetchval_query(query, vector_data, metadata)
        return result
    
    async def search_similar_vectors(self, query_vector: str, limit: int = 5) -> List[VectorResponse]:
        """
        Rechercher les vecteurs les plus similaires à un vecteur de requête.
        
        Utilise l'opérateur de distance cosinus de pgvector (<->) pour trouver
        les vecteurs les plus proches dans l'espace vectoriel. Les résultats
        sont triés par distance croissante (plus proche = distance plus petite).
        
        Args:
            query_vector: Vecteur de recherche au format string PostgreSQL
            limit: Nombre maximum de résultats à retourner (défaut: 5)
            
        Returns:
            List[VectorResponse]: Liste des vecteurs trouvés avec leurs distances
            
        Raises:
            Exception: Si la recherche échoue (format invalide, erreur SQL)
            
        Example:
            # Chercher les 10 vecteurs les plus similaires
            results = await vector_service.search_similar_vectors(
                "[0.1,0.2,0.3]", 
                limit=10
            )
            
            for result in results:
                print(f"ID: {result.id}, Distance: {result.distance}")
        """
        query = """
            SELECT id, metadata, embedding <-> $1::vector as distance
            FROM test_vectors 
            ORDER BY distance 
            LIMIT $2
        """
        results = await self.db.fetch_query(query, query_vector, limit)
        
        return [
            VectorResponse(
                id=row['id'],
                metadata=row['metadata'],
                distance=float(row['distance'])
            )
            for row in results
        ]
    
    async def test_vector_operations(self) -> VectorSearchResponse:
        """
        Exécuter un test complet des opérations vectorielles pgvector.
        
        Teste l'ensemble du pipeline vectoriel : création de table, insertion
        d'un vecteur de test, et recherche de similarité. Utilisé par l'endpoint
        POST /vectors/test pour valider le bon fonctionnement de pgvector.
        
        Le test utilise un vecteur fixe [1,2,3] pour garantir des résultats
        reproductibles et cohérents lors des vérifications système.
        
        Returns:
            VectorSearchResponse: Réponse avec statut et résultats du test
            
        Raises:
            Exception: Si une étape du test échoue (table, insertion, recherche)
            
        Example:
            # Tester les opérations vectorielles
            test_result = await vector_service.test_vector_operations()
            
            if test_result.status == "success":
                print(f"Test réussi: {test_result.message}")
                print(f"Trouvé {test_result.count} résultats")
            else:
                print(f"Test échoué: {test_result.message}")
        """
        try:
            # Créer table test
            await self.create_test_table()
            
            # Insérer vecteur test
            vector_id = await self.insert_test_vector("[1,2,3]", "test-docker-deployment")
            
            # Recherche de similarité
            results = await self.search_similar_vectors("[1,2,3]", 5)
            
            return VectorSearchResponse(
                status="success",
                message="Vector operations working with Docker deployment",
                results=results,
                count=len(results)
            )
        
        except Exception as e:
            raise Exception(f"Vector operation failed: {str(e)}")
    
    async def create_vector(self, vector: VectorCreate) -> int:
        """
        Créer un nouveau vecteur à partir d'un modèle VectorCreate.
        
        Convertit automatiquement l'embedding Python (List[float]) vers
        le format string requis par PostgreSQL et insère le vecteur dans
        la table de test. Méthode de haut niveau pour l'API REST.
        
        Args:
            vector: Modèle VectorCreate contenant embedding et métadonnées
            
        Returns:
            int: ID unique du vecteur créé en base de données
            
        Raises:
            Exception: Si la création échoue (validation, conversion, insertion)
            
        Example:
            from app.models.vector import VectorCreate
            
            # Créer un nouveau vecteur
            new_vector = VectorCreate(
                embedding=[0.1, 0.2, 0.3],
                metadata="Mon document"
            )
            
            vector_id = await vector_service.create_vector(new_vector)
            print(f"Vecteur créé: {vector_id}")
        """
        # Convertir la liste en string pour PostgreSQL
        vector_str = f"[{','.join(map(str, vector.embedding))}]"
        return await self.insert_test_vector(vector_str, vector.metadata)
    
    async def search_vectors(self, search_request: VectorSearchRequest) -> VectorSearchResponse:
        """
        Effectuer une recherche de similarité vectorielle complète.
        
        Méthode de haut niveau qui prend une requête VectorSearchRequest,
        convertit les paramètres au format PostgreSQL, exécute la recherche
        et applique le filtrage par seuil si spécifié.
        
        La recherche utilise la distance cosinus pgvector et peut être limitée
        par un seuil de distance maximum pour exclure les résultats trop éloignés.
        
        Args:
            search_request: Requête contenant vecteur, limite et seuil optionnel
            
        Returns:
            VectorSearchResponse: Réponse structurée avec résultats et métadonnées
            
        Raises:
            Exception: Si la recherche échoue (validation, conversion, SQL)
            
        Example:
            from app.models.vector import VectorSearchRequest
            
            # Recherche avec seuil de distance
            search = VectorSearchRequest(
                query_vector=[0.1, 0.2, 0.3],
                limit=20,
                threshold=0.5  # Seulement les résultats avec distance <= 0.5
            )
            
            results = await vector_service.search_vectors(search)
            print(f"Trouvé {results.count} vecteurs similaires")
            
            for result in results.results:
                print(f"- ID {result.id}: {result.metadata} (distance: {result.distance})")
        """
        # Convertir la liste en string pour PostgreSQL
        query_vector_str = f"[{','.join(map(str, search_request.query_vector))}]"
        
        results = await self.search_similar_vectors(
            query_vector_str, 
            search_request.limit
        )
        
        # Filtrer par seuil si spécifié
        if search_request.threshold is not None:
            results = [r for r in results if r.distance <= search_request.threshold]
        
        return VectorSearchResponse(
            status="success",
            message=f"Found {len(results)} similar vectors",
            results=results,
            count=len(results)
        )
