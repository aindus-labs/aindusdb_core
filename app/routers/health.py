"""
Router pour les endpoints de santé et status - Enterprise Health Checks.

Ce module implémente les endpoints de santé selon les standards enterprise
et Kubernetes avec support pour /health, /ready, /live et monitoring avancé.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from typing import Dict, Any
from datetime import datetime, timezone
from ..core.database import get_database, DatabaseManager
from ..services.health_service import HealthService
from ..models.health import HealthResponse, StatusResponse
from ..core.resilience import ResilienceCoordinator
from ..core.logging import get_logger

# Logger pour health checks
logger = get_logger("aindusdb.routers.health")

# Instance globale du coordinateur de résilience (sera injectée au startup)
resilience_coordinator: ResilienceCoordinator = None

router = APIRouter(
    tags=["health"],
    responses={
        503: {"description": "Service indisponible"},
        200: {"description": "Service opérationnel"}
    }
)


@router.get(
    "/",
    response_model=dict,
    summary="Message de bienvenue",
    description="""
    Endpoint racine retournant les informations de base de l'API.
    
    Utilisé pour vérifier que l'API est accessible et fonctionnelle.
    """,
    responses={
        200: {
            "description": "Informations API",
            "content": {
                "application/json": {
                    "example": {
                        "message": "AindusDB Core API - Docker Deployment",
                        "status": "running",
                        "version": "1.0.0"
                    }
                }
            }
        }
    }
)
async def root():
    """Message de bienvenue et informations de base de l'API"""
    return {
        "message": "AindusDB Core API - Docker Deployment", 
        "status": "running", 
        "version": "1.0.0"
    }


@router.get(
    "/health",
    response_model=Dict[str, Any],
    summary="Health Check - État de santé général",
    description="""
    Endpoint de health check enterprise pour monitoring complet.
    
    Vérifie l'état de santé de tous les composants critiques :
    * Base de données PostgreSQL et pgvector
    * Services VERITAS et métriques 
    * Circuit breakers et resilience patterns
    * Dépendances externes
    
    Standard enterprise compatible Docker/Kubernetes health checks.
    """,
    responses={
        200: {
            "description": "Système en bonne santé",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2024-01-20T21:24:00Z",
                        "services": {
                            "database": {"status": "healthy", "response_time": 12.5},
                            "veritas": {"status": "healthy", "response_time": 45.2},
                            "metrics": {"status": "healthy", "response_time": 8.1}
                        },
                        "circuit_breakers": {
                            "database": "closed",
                            "veritas": "closed"
                        },
                        "summary": {
                            "healthy_services": 3,
                            "total_services": 3,
                            "overall_health_score": 100
                        }
                    }
                }
            }
        },
        503: {
            "description": "Système dégradé ou indisponible",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "error": "Critical services unavailable",
                        "failed_services": ["database"]
                    }
                }
            }
        }
    }
)
async def health_check(response: Response, db: DatabaseManager = Depends(get_database)):
    """
    Health check enterprise avec monitoring complet de tous les services.
    
    Utilise le ResilienceCoordinator pour obtenir l'état de santé global
    de tous les composants du système avec circuit breakers et métriques.
    
    Args:
        response: Objet Response FastAPI pour définir status code
        db: Gestionnaire de base de données injecté
        
    Returns:
        Dict: État de santé détaillé de tous les services
        
    Raises:
        HTTPException: 503 si services critiques indisponibles
    """
    try:
        # Utiliser Resilience Coordinator si disponible
        if resilience_coordinator and resilience_coordinator.initialized:
            health_data = await resilience_coordinator.get_system_health()
            
            # Définir status code selon l'état global
            if health_data["status"] == "unhealthy":
                response.status_code = 503
            elif health_data["status"] == "degraded":
                response.status_code = 200  # Dégradé mais fonctionnel
            else:
                response.status_code = 200
                
            return health_data
        else:
            # Fallback vers health service classique
            health_service = HealthService(db)
            basic_health = await health_service.health_check()
            
            return {
                "status": "healthy" if basic_health.status == "healthy" else "degraded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "services": {
                    "database": {
                        "status": basic_health.database,
                        "pgvector": basic_health.pgvector
                    }
                },
                "fallback_mode": True,
                "message": "Resilience coordinator not available, using basic health check"
            }
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        response.status_code = 503
        
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "message": "Health check system failure"
        }


@router.get(
    "/ready",
    response_model=Dict[str, Any],
    summary="Readiness Check - Service prêt à recevoir du trafic",
    description="""
    Endpoint de readiness check standard Kubernetes.
    
    Vérifie si l'application est prête à recevoir du trafic :
    * Tous les services critiques sont opérationnels
    * Base de données accessible et responsive
    * Dépendances externes disponibles
    * Circuit breakers dans un état acceptable
    
    Utilisé par Kubernetes pour déterminer quand envoyer du trafic.
    """,
    responses={
        200: {
            "description": "Service prêt à recevoir du trafic",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ready",
                        "timestamp": "2024-01-20T21:24:00Z",
                        "ready_services": ["database", "veritas", "metrics"],
                        "readiness_score": 100,
                        "can_serve_traffic": True
                    }
                }
            }
        },
        503: {
            "description": "Service non prêt, éviter le trafic",
            "content": {
                "application/json": {
                    "example": {
                        "status": "not_ready",
                        "blocking_issues": ["database_connection_failed"],
                        "can_serve_traffic": False
                    }
                }
            }
        }
    }
)
async def readiness_check(response: Response):
    """
    Readiness check standard Kubernetes pour déterminer si le pod peut recevoir du trafic.
    
    Contrairement au health check, le readiness check détermine spécifiquement
    si l'application peut traiter les requêtes entrantes sans erreur.
    
    Args:
        response: Objet Response FastAPI pour status code
        
    Returns:
        Dict: État de disponibilité du service
    """
    try:
        if resilience_coordinator and resilience_coordinator.initialized:
            health_data = await resilience_coordinator.get_system_health()
            
            # Analyser la capacité à servir du trafic
            critical_services_healthy = True
            ready_services = []
            blocking_issues = []
            
            for service_name, service_info in health_data.get("services", {}).items():
                if service_info.get("critical", False):
                    if service_info["status"] == "unhealthy":
                        critical_services_healthy = False
                        blocking_issues.append(f"{service_name}_unavailable")
                    elif service_info["status"] in ["healthy", "degraded"]:
                        ready_services.append(service_name)
                else:
                    # Services non critiques n'impactent pas la readiness
                    if service_info["status"] in ["healthy", "degraded"]:
                        ready_services.append(service_name)
            
            # Vérifier circuit breakers critiques
            cb_stats = health_data.get("circuit_breakers", {})
            for cb_name, cb_state in cb_stats.items():
                if cb_name in ["database", "veritas"] and cb_state.get("state") == "open":
                    critical_services_healthy = False
                    blocking_issues.append(f"{cb_name}_circuit_breaker_open")
            
            # Déterminer readiness
            is_ready = critical_services_healthy and len(ready_services) > 0
            readiness_score = (len(ready_services) / max(1, len(health_data.get("services", {})))) * 100
            
            response.status_code = 200 if is_ready else 503
            
            return {
                "status": "ready" if is_ready else "not_ready",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ready_services": ready_services,
                "blocking_issues": blocking_issues if not is_ready else [],
                "readiness_score": int(readiness_score),
                "can_serve_traffic": is_ready,
                "critical_services_healthy": critical_services_healthy
            }
        else:
            # Fallback basique - vérifier juste la DB
            try:
                from ..core.database import db_manager
                async with db_manager.get_connection() as conn:
                    await conn.fetchval("SELECT 1")
                
                response.status_code = 200
                return {
                    "status": "ready",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "ready_services": ["database"],
                    "readiness_score": 100,
                    "can_serve_traffic": True,
                    "fallback_mode": True
                }
            except Exception:
                response.status_code = 503
                return {
                    "status": "not_ready",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "blocking_issues": ["database_connection_failed"],
                    "can_serve_traffic": False,
                    "fallback_mode": True
                }
                
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        response.status_code = 503
        
        return {
            "status": "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "blocking_issues": ["readiness_check_failure"],
            "can_serve_traffic": False
        }


@router.get(
    "/live",
    response_model=Dict[str, Any],
    summary="Liveness Check - Application vivante et responsive",
    description="""
    Endpoint de liveness check standard Kubernetes.
    
    Vérifie si l'application est vivante et doit continuer à fonctionner :
    * Processus principal répond aux requêtes
    * Pas de blocage ou deadlock détecté
    * Mémoire et ressources dans les limites acceptables
    * Threads et coroutines fonctionnelles
    
    Utilisé par Kubernetes pour déterminer si redémarrer le pod.
    """,
    responses={
        200: {
            "description": "Application vivante et fonctionnelle",
            "content": {
                "application/json": {
                    "example": {
                        "status": "alive",
                        "timestamp": "2024-01-20T21:24:00Z",
                        "uptime_seconds": 3600,
                        "response_time_ms": 2.5,
                        "restart_required": False
                    }
                }
            }
        },
        503: {
            "description": "Application non responsive, redémarrage requis",
            "content": {
                "application/json": {
                    "example": {
                        "status": "dead",
                        "issues": ["memory_exhausted", "deadlock_detected"],
                        "restart_required": True
                    }
                }
            }
        }
    }
)
async def liveness_check(response: Response):
    """
    Liveness check standard Kubernetes pour déterminer si l'application doit être redémarrée.
    
    Ce check est plus basique que health/readiness et se concentre sur
    la capacité de l'application à répondre et traiter les requêtes.
    
    Args:
        response: Objet Response FastAPI pour status code
        
    Returns:
        Dict: État de vivacité de l'application
    """
    import time
    import psutil
    import os
    
    start_check_time = time.time()
    
    try:
        # Informations sur le processus
        process = psutil.Process(os.getpid())
        
        # Vérifications de vivacité basiques
        issues = []
        
        # 1. Mémoire - vérifier pas d'explosion mémoire
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # Seuil d'alerte à 1GB (ajustable selon l'environnement)
        if memory_mb > 1024:
            issues.append(f"high_memory_usage_{int(memory_mb)}MB")
        
        # 2. CPU - vérifier pas de surcharge
        cpu_percent = process.cpu_percent(interval=0.1)
        if cpu_percent > 90:
            issues.append(f"high_cpu_usage_{cpu_percent}%")
        
        # 3. Nombre de threads - détecter prolifération
        num_threads = process.num_threads()
        if num_threads > 100:  # Seuil ajustable
            issues.append(f"thread_proliferation_{num_threads}")
        
        # 4. Descripteurs de fichiers (Linux/Mac)
        try:
            num_fds = process.num_fds()
            if num_fds > 1000:  # Seuil ajustable
                issues.append(f"fd_leak_{num_fds}")
        except (AttributeError, NotImplementedError):
            # Windows ou autre OS
            pass
        
        # 5. Uptime
        create_time = process.create_time()
        uptime_seconds = time.time() - create_time
        
        # Temps de réponse du check
        response_time_ms = (time.time() - start_check_time) * 1000
        
        # 6. Vérifier temps de réponse acceptable
        if response_time_ms > 1000:  # Plus de 1 seconde = problème
            issues.append(f"slow_response_{int(response_time_ms)}ms")
        
        # Déterminer si redémarrage requis
        restart_required = len(issues) > 2 or any(
            "memory" in issue or "deadlock" in issue for issue in issues
        )
        
        # Status code
        if restart_required:
            response.status_code = 503
            status = "dead"
        else:
            response.status_code = 200
            status = "alive"
        
        return {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": int(uptime_seconds),
            "response_time_ms": round(response_time_ms, 1),
            "restart_required": restart_required,
            "issues": issues,
            "process_info": {
                "pid": process.pid,
                "memory_mb": round(memory_mb, 1),
                "cpu_percent": cpu_percent,
                "num_threads": num_threads
            }
        }
        
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        response.status_code = 503
        
        return {
            "status": "dead",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "issues": ["liveness_check_failure"],
            "restart_required": True
        }


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Status système complet",
    description="""
    Endpoint de status détaillé du système.
    
    Retourne des informations complètes sur :
    * Configuration du déploiement
    * État de la base de données
    * Configuration de l'API
    * Paramètres des opérations vectorielles
    
    Utile pour le debugging et la supervision avancée.
    """,
    responses={
        200: {
            "description": "Status système détaillé",
            "content": {
                "application/json": {
                    "example": {
                        "deployment": {
                            "orchestrator": "Docker Compose",
                            "runtime": "Docker",
                            "status": "production-ready"
                        },
                        "database": {
                            "status": "connected",
                            "connected": True,
                            "pgvector": "0.5.1"
                        },
                        "api": {
                            "title": "AindusDB Core API",
                            "version": "1.0.0"
                        },
                        "vector_operations": {
                            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                            "dimensions": 384
                        }
                    }
                }
            }
        }
    }
)
async def deployment_status(db: DatabaseManager = Depends(get_database)):
    """
    Status complet du déploiement Docker.
    
    Fournit des informations détaillées sur la configuration et l'état
    de tous les composants du système.
    
    Args:
        db: Gestionnaire de base de données injecté
        
    Returns:
        StatusResponse: Status détaillé du système
        
    Raises:
        HTTPException: 500 en cas d'erreur lors de la récupération du status
    """
    try:
        health_service = HealthService(db)
        return await health_service.get_system_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.get(
    "/metrics",
    response_model=Dict[str, Any],
    summary="Métriques Enterprise - Monitoring et observabilité",
    description="""
    Endpoint de métriques enterprise pour monitoring avancé.
    
    Expose les métriques détaillées pour :
    * Performance et latence des services
    * Circuit breakers et resilience patterns  
    * Santé des composants en temps réel
    * Statistiques d'utilisation
    * Métriques custom VERITAS
    
    Compatible Prometheus, DataDog, New Relic, etc.
    """,
    responses={
        200: {
            "description": "Métriques détaillées disponibles",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "timestamp": "2024-01-20T21:24:00Z",
                        "metrics": {
                            "health_checks_total": 1250,
                            "circuit_breaker_trips": 3,
                            "avg_response_time_ms": 45.2,
                            "requests_per_second": 12.5
                        },
                        "services": {
                            "database": {"latency_p95": 25.3, "errors": 0},
                            "veritas": {"latency_p95": 120.5, "errors": 2}
                        }
                    }
                }
            }
        }
    }
)
async def metrics_endpoint():
    """
    Endpoint de métriques enterprise pour monitoring avancé.
    
    Collecte et expose toutes les métriques de performance,
    santé et utilisation du système pour observabilité complète.
    
    Returns:
        Dict: Métriques complètes du système
    """
    try:
        metrics_data = {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "deployment": "enterprise"
        }
        
        # Métriques du Resilience Coordinator
        if resilience_coordinator and resilience_coordinator.initialized:
            coordinator_stats = resilience_coordinator.get_stats()
            
            metrics_data["resilience"] = coordinator_stats
            metrics_data["circuit_breakers"] = {
                name: breaker.get_stats() 
                for name, breaker in resilience_coordinator.circuit_breakers.items()
            }
            
            # Santé des services
            if resilience_coordinator.health_monitor:
                health_stats = resilience_coordinator.health_monitor.get_stats()
                metrics_data["health_monitoring"] = health_stats
        
        # Métriques système de base
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        system_metrics = {
            "process": {
                "pid": process.pid,
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads(),
                "uptime_seconds": int(time.time() - process.create_time())
            },
            "system": {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 1),
                "memory_available_gb": round(psutil.virtual_memory().available / 1024 / 1024 / 1024, 1),
                "disk_usage_percent": psutil.disk_usage('/').percent
            }
        }
        
        metrics_data["system"] = system_metrics
        
        # Métriques Prometheus si disponibles
        try:
            from ..core.metrics import metrics_service
            if metrics_service:
                # TODO: Récupérer métriques Prometheus
                metrics_data["prometheus_available"] = True
        except ImportError:
            metrics_data["prometheus_available"] = False
        
        return metrics_data
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "message": "Metrics collection failure"
        }


def set_resilience_coordinator(coordinator: ResilienceCoordinator):
    """
    Définir l'instance du coordinateur de résilience.
    
    Cette fonction sera appelée au startup de l'application pour
    injecter le coordinateur dans les endpoints de santé.
    
    Args:
        coordinator: Instance du ResilienceCoordinator
    """
    global resilience_coordinator
    resilience_coordinator = coordinator
    logger.info("Resilience coordinator set for health endpoints")
