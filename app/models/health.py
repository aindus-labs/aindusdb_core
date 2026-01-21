"""
Modèles Pydantic pour les vérifications de santé et de statut d'AindusDB Core.

Ce module définit les modèles de données pour les endpoints de monitoring
et de diagnostic : health checks, statut système, métriques de performance.
Ces modèles permettent de surveiller l'état de l'API, de la base de données
et des opérations vectorielles.

Example:
    from app.models.health import HealthResponse, StatusResponse
    
    # Réponse de health check
    health = HealthResponse(
        status="healthy",
        database="connected",
        pgvector="0.5.1",
        deployment="docker",
        api_version="1.0.0"
    )
    
    # Réponse de statut détaillé
    status = StatusResponse(
        deployment={"orchestrator": "docker-compose"},
        database={"status": "connected"},
        api={"uptime": "2h 15m"},
        vector_operations={"last_test": "success"}
    )
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class HealthResponse(BaseModel):
    """
    Modèle de réponse pour les vérifications de santé système.
    
    Utilisé par l'endpoint GET /health pour indiquer l'état global
    du système AindusDB Core. Fournit des informations essentielles
    sur la connectivité de la base de données, l'extension pgvector,
    le type de déploiement et la version de l'API.
    
    Attributes:
        status: État global du système ("healthy", "degraded", "unhealthy")
        database: État de la connexion PostgreSQL ("connected", "disconnected", "error")
        pgvector: Version de l'extension pgvector si disponible
        deployment: Type de déploiement ("docker", "kubernetes", "manual")
        api_version: Version de l'API AindusDB Core
        
    Example:
        # Système en bonne santé
        healthy_response = HealthResponse(
            status="healthy",
            database="connected", 
            pgvector="0.5.1",
            deployment="docker",
            api_version="1.0.0"
        )
        
        # Système avec problèmes
        degraded_response = HealthResponse(
            status="degraded",
            database="connected",
            pgvector=None,  # Extension non disponible
            deployment="manual", 
            api_version="1.0.0"
        )
    """
    status: str = Field(
        ...,
        description="État global du système",
        pattern="^(healthy|degraded|unhealthy)$",
        example="healthy"
    )
    database: str = Field(
        ...,
        description="État de la connexion PostgreSQL",
        pattern="^(connected|disconnected|error)$",
        example="connected"
    )
    pgvector: Optional[str] = Field(
        None,
        description="Version de l'extension pgvector si disponible",
        example="0.5.1"
    )
    deployment: str = Field(
        ...,
        description="Type de déploiement détecté",
        example="docker"
    )
    api_version: str = Field(
        ...,
        description="Version actuelle de l'API AindusDB Core",
        example="1.0.0"
    )


class StatusResponse(BaseModel):
    """
    Modèle de réponse pour le statut détaillé du système.
    
    Utilisé par l'endpoint GET /status pour fournir des informations
    complètes sur tous les composants du système : déploiement,
    base de données, API et opérations vectorielles. Plus détaillé
    que HealthResponse pour le diagnostic approfondi.
    
    Attributes:
        deployment: Informations sur l'environnement de déploiement
        database: Détails sur la base de données PostgreSQL
        api: Métriques et informations sur l'API FastAPI
        vector_operations: État des opérations vectorielles pgvector
        
    Example:
        # Statut complet du système
        detailed_status = StatusResponse(
            deployment={
                "orchestrator": "docker-compose",
                "environment": "development",
                "started_at": "2026-01-15T10:30:00Z"
            },
            database={
                "status": "connected",
                "version": "PostgreSQL 15.1",
                "active_connections": 5,
                "max_connections": 20
            },
            api={
                "uptime": "2h 15m 30s",
                "requests_total": 1247,
                "requests_per_second": 0.18,
                "memory_usage": "128MB"
            },
            vector_operations={
                "last_test": "success",
                "test_duration": "0.023s",
                "pgvector_version": "0.5.1",
                "index_type": "hnsw"
            }
        )
    """
    deployment: Dict[str, Any] = Field(
        ...,
        description="Informations détaillées sur l'environnement de déploiement",
        example={
            "orchestrator": "docker-compose",
            "environment": "development",
            "container_id": "abc123def456",
            "started_at": "2026-01-15T10:30:00Z"
        }
    )
    database: Dict[str, Any] = Field(
        ...,
        description="Détails complets sur la base de données PostgreSQL",
        example={
            "status": "connected",
            "version": "PostgreSQL 15.1 on x86_64-pc-linux-gnu",
            "active_connections": 5,
            "max_connections": 20,
            "database_size": "15MB"
        }
    )
    api: Dict[str, Any] = Field(
        ...,
        description="Métriques et informations sur l'API FastAPI",
        example={
            "uptime": "2h 15m 30s",
            "requests_total": 1247,
            "requests_per_second": 0.18,
            "memory_usage": "128MB",
            "workers": 4
        }
    )
    vector_operations: Dict[str, Any] = Field(
        ...,
        description="État détaillé des opérations vectorielles pgvector",
        example={
            "last_test": "success",
            "test_duration": "0.023s", 
            "pgvector_version": "0.5.1",
            "vectors_count": 42,
            "last_insertion": "2026-01-15T12:45:00Z"
        }
    )


class MetricsResponse(BaseModel):
    """
    Modèle de réponse pour les métriques de performance système.
    
    Utilisé par l'endpoint GET /metrics pour exposer des métriques
    détaillées compatible avec les systèmes de monitoring comme
    Prometheus. Fournit des données quantitatives sur les performances.
    
    Attributes:
        timestamp: Horodatage de la collecte des métriques
        api_metrics: Métriques liées à l'API (requêtes, latence, etc.)
        database_metrics: Métriques de la base de données
        vector_metrics: Métriques spécifiques aux opérations vectorielles
        system_metrics: Métriques système (CPU, mémoire, etc.)
        
    Example:
        # Métriques système complètes
        metrics = MetricsResponse(
            timestamp="2026-01-15T14:30:00Z",
            api_metrics={
                "requests_total": 5000,
                "requests_per_second_avg": 2.5,
                "response_time_p50": "0.012s",
                "response_time_p95": "0.045s",
                "error_rate": 0.001
            },
            database_metrics={
                "connections_active": 8,
                "connections_max": 20,
                "query_duration_avg": "0.008s",
                "cache_hit_ratio": 0.95
            },
            vector_metrics={
                "vectors_total": 10000,
                "searches_per_second": 15.2,
                "insertion_rate": 100.5,
                "index_size": "250MB"
            },
            system_metrics={
                "cpu_usage": 0.15,
                "memory_usage": 0.45,
                "disk_usage": 0.30
            }
        )
    """
    timestamp: str = Field(
        ...,
        description="Horodatage ISO 8601 de la collecte des métriques",
        example="2026-01-15T14:30:00Z"
    )
    api_metrics: Dict[str, Any] = Field(
        ...,
        description="Métriques de performance de l'API FastAPI",
        example={
            "requests_total": 5000,
            "requests_per_second": 2.5,
            "response_time_avg": "0.025s",
            "error_rate": 0.001
        }
    )
    database_metrics: Dict[str, Any] = Field(
        ...,
        description="Métriques de performance PostgreSQL",
        example={
            "connections_active": 8,
            "query_duration_avg": "0.008s", 
            "cache_hit_ratio": 0.95,
            "transactions_per_second": 45.2
        }
    )
    vector_metrics: Dict[str, Any] = Field(
        ...,
        description="Métriques spécifiques aux opérations vectorielles",
        example={
            "vectors_total": 10000,
            "searches_per_second": 15.2,
            "insertion_rate": 100.5,
            "average_search_time": "0.015s"
        }
    )
    system_metrics: Dict[str, Any] = Field(
        ...,
        description="Métriques système générales",
        example={
            "cpu_usage": 0.15,
            "memory_usage": 0.45,
            "disk_usage": 0.30,
            "uptime": "3d 2h 15m"
        }
    )
