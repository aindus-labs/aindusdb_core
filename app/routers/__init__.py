"""
Routers API pour AindusDB Core
"""
from .health import router as health_router
from .vectors import router as vectors_router

__all__ = [
    "health_router",
    "vectors_router"
]
