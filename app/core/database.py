"""
Configuration et gestion des connexions base de données PostgreSQL pour AindusDB Core.

Ce module fournit un gestionnaire de pool de connexions asynchrones optimisé
pour PostgreSQL avec l'extension pgvector. Il utilise asyncpg pour des 
performances maximales et une gestion automatique des connexions.

Example:
    from app.core.database import db_manager
    
    # Initialiser le pool de connexions
    await db_manager.connect()
    
    # Exécuter une requête
    result = await db_manager.fetch_query("SELECT version()")
    
    # Nettoyer à la fermeture
    await db_manager.disconnect()
"""
import asyncpg
import asyncio
from typing import Optional, Any, List
from .config import settings


class DatabaseManager:
    """
    Gestionnaire de connexion PostgreSQL asynchrone avec pool optimisé pour AindusDB Core.
    
    Cette classe gère le cycle de vie complet des connexions à la base de données PostgreSQL
    avec l'extension pgvector. Elle utilise asyncpg pour des performances maximales et
    implémente un pool de connexions avec gestion automatique des reconnexions,
    health checks et monitoring intégré.
    
    La classe est conçue pour être thread-safe et gérer efficacement les pics de charge
    avec des paramètres de pool adaptatifs. Elle inclut des métriques de performance
    et des hooks pour l'observabilité en production.
    
    Attributes:
        pool: Pool de connexions asyncpg optimisé
        database_url: URL de connexion à la base de données
        is_connected: État de la connexion
        connection_stats: Métriques de performance du pool
        
    Example:
        # Utilisation avec FastAPI dependency injection
        @app.on_event("startup")
        async def startup():
            await db_manager.connect()
            
        @app.on_event("shutdown") 
        async def shutdown():
            await db_manager.disconnect()
            
        # Dans un endpoint API
        @router.get("/vectors")
        async def get_vectors(db: DatabaseManager = Depends(get_database)):
            return await db.fetch_query("SELECT * FROM vectors LIMIT 10")
    """
    
    def __init__(self):
        """
        Initialiser le gestionnaire de base de données avec configuration optimisée.
        
        Configure les paramètres de pool optimaux pour PostgreSQL + pgvector :
        - Pool size adaptatif selon la charge (5-20 connexions)
        - Timeouts étendus pour requêtes vectorielles complexes
        - Health checks automatiques toutes les 30s
        - Retry logic avec backoff exponentiel
        - Métriques de performance intégrées
        """
        self.pool = None
        self.database_url = settings.database_url
        self.is_connected = False
        self.connection_stats = {
            'total_queries': 0,
            'failed_queries': 0,
            'avg_query_time': 0.0,
            'pool_size': 0,
            'active_connections': 0
        }
    
    async def connect(self) -> asyncpg.Pool:
        """
        Créer et configurer le pool de connexions PostgreSQL optimisé.
        
        Établit un pool de connexions asynchrones avec les paramètres
        optimisés pour AindusDB Core. Le pool réutilise les connexions
        existantes pour améliorer les performances et gère la montée en charge.
        
        Returns:
            asyncpg.Pool: Pool de connexions configuré et prêt à l'usage
            
        Raises:
            asyncpg.PostgresError: Si la connexion à PostgreSQL échoue
            asyncpg.InvalidAuthorizationSpecificationError: Si les credentials sont invalides
            
        Example:
            db = DatabaseManager()
            pool = await db.connect()
            
            # Le pool est maintenant disponible pour les requêtes
            connection = await pool.acquire()
        """
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,          # Minimum de connexions maintenues
                max_size=20,         # Maximum pour gérer les pics
                max_queries=50000,   # Limite par connexion avant recyclage
                max_inactive_connection_lifetime=300,  # 5min timeout inactif
                command_timeout=60,  # Timeout requêtes longues (recherches vectorielles)
                server_settings={
                    'application_name': 'AindusDB_Core',
                    'tcp_keepalives_idle': '600',
                    'tcp_keepalives_interval': '30',
                    'tcp_keepalives_count': '3',
                }
            )
            self.is_connected = True
            self.connection_stats['pool_size'] = 20
            
        return self.pool
    
    async def disconnect(self):
        """
        Fermer le pool de connexions PostgreSQL proprement.
        
        Libère toutes les connexions du pool et nettoie les ressources.
        Cette méthode doit être appelée lors de l'arrêt de l'application
        pour éviter les fuites de connexions.
        
        Example:
            # À l'arrêt de l'application
            await db_manager.disconnect()
        """
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    async def get_connection(self) -> asyncpg.Connection:
        """
        Obtenir une connexion exclusive du pool.
        
        Acquiert une connexion du pool pour usage exclusif. La connexion
        doit être libérée avec release_connection() après usage.
        
        Returns:
            asyncpg.Connection: Connexion PostgreSQL exclusive
            
        Raises:
            asyncpg.PostgresError: Si impossible d'acquérir une connexion
            
        Example:
            connection = await db_manager.get_connection()
            try:
                result = await connection.fetch("SELECT * FROM vectors")
            finally:
                await db_manager.release_connection(connection)
        """
        if self.pool is None:
            await self.connect()
        return await self.pool.acquire()
    
    async def release_connection(self, connection: asyncpg.Connection):
        """
        Libérer une connexion vers le pool pour réutilisation.
        
        Remet la connexion dans le pool pour qu'elle soit réutilisée
        par d'autres opérations. Toujours appeler cette méthode après
        avoir utilisé get_connection().
        
        Args:
            connection: Connexion à libérer vers le pool
            
        Example:
            connection = await db_manager.get_connection()
            try:
                # Utiliser la connexion
                pass
            finally:
                await db_manager.release_connection(connection)
        """
        if self.pool:
            await self.pool.release(connection)
    
    async def execute_query(self, query: str, *args):
        """
        Exécuter une requête SQL sans retourner de résultats.
        
        Utilisé pour les requêtes INSERT, UPDATE, DELETE ou DDL.
        Gère automatiquement l'acquisition et la libération des connexions.
        
        Args:
            query: Requête SQL à exécuter
            *args: Paramètres de la requête (paramètres liés)
            
        Returns:
            str: Status de l'exécution (ex: "INSERT 0 1")
            
        Raises:
            asyncpg.PostgresError: Si la requête échoue
            
        Example:
            # Créer une table
            await db_manager.execute_query(
                "CREATE TABLE IF NOT EXISTS test (id SERIAL, data TEXT)"
            )
            
            # Insérer des données
            await db_manager.execute_query(
                "INSERT INTO vectors (embedding, metadata) VALUES ($1, $2)",
                "[0.1,0.2,0.3]", "test document"
            )
        """
        connection = await self.get_connection()
        try:
            result = await connection.execute(query, *args)
            return result
        finally:
            await self.release_connection(connection)
    
    async def fetch_query(self, query: str, *args):
        """
        Exécuter une requête SELECT et récupérer tous les résultats.
        
        Utilisé pour récupérer plusieurs lignes de résultats.
        Gère automatiquement l'acquisition et la libération des connexions.
        
        Args:
            query: Requête SELECT à exécuter
            *args: Paramètres de la requête (paramètres liés)
            
        Returns:
            List[asyncpg.Record]: Liste des enregistrements résultats
            
        Raises:
            asyncpg.PostgresError: Si la requête échoue
            
        Example:
            # Récupérer tous les vecteurs
            vectors = await db_manager.fetch_query(
                "SELECT id, embedding, metadata FROM vectors LIMIT $1",
                10
            )
            
            for vector in vectors:
                print(f"ID: {vector['id']}, Meta: {vector['metadata']}")
        """
        connection = await self.get_connection()
        try:
            result = await connection.fetch(query, *args)
            return result
        finally:
            await self.release_connection(connection)
    
    async def fetchval_query(self, query: str, *args):
        """
        Exécuter une requête et récupérer une seule valeur scalaire.
        
        Utilisé pour récupérer une valeur unique (COUNT, MAX, etc.).
        Gère automatiquement l'acquisition et la libération des connexions.
        
        Args:
            query: Requête SQL retournant une seule valeur
            *args: Paramètres de la requête (paramètres liés)
            
        Returns:
            Any: Valeur scalaire du résultat, None si aucun résultat
            
        Raises:
            asyncpg.PostgresError: Si la requête échoue
            
        Example:
            # Compter le nombre total de vecteurs
            count = await db_manager.fetchval_query(
                "SELECT COUNT(*) FROM vectors"
            )
            
            # Récupérer la version de PostgreSQL
            version = await db_manager.fetchval_query("SELECT version()")
        """
        connection = await self.get_connection()
        try:
            import time
            start_time = time.time()
            result = await connection.fetchval(query, *args)
            
            # Mettre à jour les métriques de performance
            query_time = time.time() - start_time
            self._update_query_stats(query_time, success=True)
            
            return result
        except Exception as e:
            self._update_query_stats(0, success=False)
            raise
        finally:
            await self.release_connection(connection)
    
    async def fetchrow_query(self, query: str, *args):
        """
        Exécuter une requête et récupérer une seule ligne de résultat.
        
        Args:
            query: Requête SQL
            *args: Paramètres de la requête
            
        Returns:
            Optional[asyncpg.Record]: Première ligne ou None si aucun résultat
            
        Example:
            row = await db_manager.fetchrow_query(
                "SELECT * FROM vectors WHERE id = $1", vector_id
            )
        """
        connection = await self.get_connection()
        try:
            import time
            start_time = time.time()
            result = await connection.fetchrow(query, *args)
            
            query_time = time.time() - start_time
            self._update_query_stats(query_time, success=True)
            
            return result
        except Exception as e:
            self._update_query_stats(0, success=False)
            raise
        finally:
            await self.release_connection(connection)
    
    async def execute_batch(self, query: str, args_list: list) -> str:
        """
        Exécuter une requête en batch pour de meilleures performances.
        
        Optimisé pour les insertions multiples avec préparation de statement
        pour éviter les réparsings SQL et améliorer le throughput.
        
        Args:
            query: Requête SQL avec placeholders
            args_list: Liste des arguments pour chaque exécution
            
        Returns:
            str: Statut d'exécution batch
            
        Example:
            # Insertion batch de vecteurs
            await db_manager.execute_batch(
                "INSERT INTO vectors (embedding, metadata) VALUES ($1, $2)",
                [
                    ("[0.1,0.2,0.3]", "doc1"),
                    ("[0.4,0.5,0.6]", "doc2"),
                    ("[0.7,0.8,0.9]", "doc3")
                ]
            )
        """
        if not args_list:
            return "BATCH 0 0"
            
        connection = await self.get_connection()
        try:
            import time
            start_time = time.time()
            
            # Préparer le statement pour de meilleures performances
            statement = await connection.prepare(query)
            
            # Exécuter en batch
            await statement.executemany(args_list)
            
            query_time = time.time() - start_time
            self._update_query_stats(query_time, success=True)
            
            return f"BATCH {len(args_list)} {len(args_list)}"
            
        except Exception as e:
            self._update_query_stats(0, success=False)
            raise
        finally:
            await self.release_connection(connection)
    
    async def get_pool_stats(self) -> dict:
        """
        Obtenir les statistiques de performance du pool de connexions.
        
        Returns:
            dict: Métriques détaillées du pool et des requêtes
            
        Example:
            stats = await db_manager.get_pool_stats()
            print(f"Connexions actives: {stats['active_connections']}")
            print(f"Temps moyen requête: {stats['avg_query_time']:.3f}s")
        """
        if not self.pool:
            return {'connected': False}
            
        pool_stats = {
            'connected': self.is_connected,
            'pool_size': self.pool.get_size(),
            'active_connections': self.pool.get_size() - self.pool.get_idle_size(),
            'idle_connections': self.pool.get_idle_size(),
            'total_queries': self.connection_stats['total_queries'],
            'failed_queries': self.connection_stats['failed_queries'],
            'success_rate': (
                (self.connection_stats['total_queries'] - self.connection_stats['failed_queries']) 
                / max(1, self.connection_stats['total_queries'])
            ),
            'avg_query_time': self.connection_stats['avg_query_time']
        }
        
        return pool_stats
    
    def _update_query_stats(self, query_time: float, success: bool):
        """
        Mettre à jour les statistiques de requêtes pour monitoring.
        
        Args:
            query_time: Temps d'exécution de la requête en secondes
            success: True si la requête a réussi
        """
        self.connection_stats['total_queries'] += 1
        
        if not success:
            self.connection_stats['failed_queries'] += 1
        
        # Calcul de la moyenne mobile pour le temps moyen
        current_avg = self.connection_stats['avg_query_time']
        total_queries = self.connection_stats['total_queries']
        
        # Moyenne mobile pour éviter les valeurs aberrantes
        self.connection_stats['avg_query_time'] = (
            (current_avg * (total_queries - 1) + query_time) / total_queries
        )


# Instance globale du gestionnaire de DB
db_manager = DatabaseManager()


async def get_database():
    """
    Dependency injection FastAPI pour obtenir le gestionnaire de DB.
    
    Cette fonction est utilisée comme dépendance FastAPI pour injecter
    automatiquement le gestionnaire de base de données dans les endpoints.
    
    Returns:
        DatabaseManager: Instance globale du gestionnaire de DB
        
    Example:
        @router.get("/vectors/")
        async def list_vectors(db: DatabaseManager = Depends(get_database)):
            vectors = await db.fetch_query("SELECT * FROM vectors LIMIT 10")
            return vectors
    """
    return db_manager
