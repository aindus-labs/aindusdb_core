"""
Dépendances FastAPI pour AindusDB Core
"""
from .database import get_db_connection

__all__ = [
    "get_db_connection"
]
