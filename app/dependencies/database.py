"""
Dépendances pour l'accès base de données
"""
from fastapi import Depends
from ..core.database import get_database, DatabaseManager


async def get_db_connection() -> DatabaseManager:
    """Dépendance pour obtenir une connexion base de données"""
    return await get_database()
