"""
Health Monitor - Surveillance continue des services et composants.

Ce module implémente un système de monitoring de santé en temps réel pour
tous les composants critiques d'AindusDB Core, permettant une détection
proactive des problèmes et une escalation automatique.

Example:
    monitor = HealthMonitor()
    
    # Enregistrer services à surveiller
    monitor.register_service("database", db_health_check)
    monitor.register_service("redis", redis_health_check)
    
    # Démarrer monitoring
    await monitor.start_monitoring()
    
    # Vérifier santé
    health = await monitor.get_overall_health()
"""

import asyncio
import time
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Awaitable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

from ...core.logging import get_logger
from ...core.metrics import metrics_service


class ServiceStatus(Enum):
    """États possibles d'un service."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"


@dataclass
class HealthCheck:
    """Configuration d'un health check."""
    name: str
    check_function: Callable[[], Awaitable[bool]]
    interval: float = 30.0  # secondes
    timeout: float = 10.0   # secondes
    failure_threshold: int = 3
    success_threshold: int = 1
    critical: bool = False
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceHealth:
    """État de santé d'un service."""
    name: str
    status: ServiceStatus
    last_check: datetime
    response_time: float
    error_message: Optional[str] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_checks: int = 0
    total_failures: int = 0
    uptime_percentage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthMonitor:
    """
    Moniteur de santé centralisé pour tous les services AindusDB Core.
    
    Le Health Monitor surveille continuellement l'état de santé de tous
    les composants critiques et fournit une vue d'ensemble en temps réel
    de l'état du système.
    
    Features:
    - Health checks périodiques configurables
    - Détection automatique des dégradations
    - Escalation basée sur criticité
    - Dépendances entre services
    - Métriques et alerting intégrés
    - Support maintenance planifiée
    - Historique des incidents
    
    Architecture:
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │ Health Checks   │───▶│ Status Analysis │───▶│ Alert Manager   │
    │ - Database      │    │ - Thresholds    │    │ - Notifications │
    │ - Redis         │    │ - Dependencies  │    │ - Escalation    │
    │ - External APIs │    │ - Trends        │    │ - Remediation   │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
    
    Example:
        # Configuration
        monitor = HealthMonitor(
            check_interval=30,
            enable_auto_remediation=True
        )
        
        # Enregistrer services
        monitor.register_service("database", db_health_check, critical=True)
        monitor.register_service("redis", redis_health_check)
        monitor.register_service("external_api", api_health_check, 
                               dependencies=["database"])
        
        # Démarrer monitoring
        await monitor.start_monitoring()
        
        # Vérifications
        overall_health = await monitor.get_overall_health()
        service_health = await monitor.get_service_health("database")
    """
    
    def __init__(self, 
                 check_interval: float = 30.0,
                 enable_metrics: bool = True,
                 enable_auto_remediation: bool = False,
                 alert_callback: Optional[Callable] = None):
        """
        Initialiser le Health Monitor.
        
        Args:
            check_interval: Intervalle par défaut des checks (secondes)
            enable_metrics: Activer métriques Prometheus
            enable_auto_remediation: Activer remédiation automatique
            alert_callback: Callback pour alertes
        """
        self.check_interval = check_interval
        self.enable_metrics = enable_metrics
        self.enable_auto_remediation = enable_auto_remediation
        self.alert_callback = alert_callback
        
        # Services enregistrés
        self._health_checks: Dict[str, HealthCheck] = {}
        self._service_health: Dict[str, ServiceHealth] = {}
        
        # Tâches de monitoring
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._monitoring_active = False
        
        # Historique des incidents
        self._incident_history: List[Dict[str, Any]] = []
        
        # Statistiques globales
        self._start_time = time.time()
        self._total_checks = 0
        self._total_failures = 0
        
        self.logger = get_logger("aindusdb.resilience.health_monitor")
        
        self.logger.info("Health Monitor initialized",
                        extra={
                            "check_interval": check_interval,
                            "auto_remediation": enable_auto_remediation
                        })
    
    def register_service(self, 
                        name: str,
                        check_function: Callable[[], Awaitable[bool]],
                        interval: float = None,
                        timeout: float = 10.0,
                        failure_threshold: int = 3,
                        success_threshold: int = 1,
                        critical: bool = False,
                        dependencies: List[str] = None,
                        **metadata) -> None:
        """
        Enregistrer un service à surveiller.
        
        Args:
            name: Nom unique du service
            check_function: Fonction de vérification (async)
            interval: Intervalle de vérification (défaut: check_interval)
            timeout: Timeout pour le check
            failure_threshold: Échecs consécutifs avant UNHEALTHY
            success_threshold: Succès consécutifs pour recovery
            critical: Service critique (impact santé globale)
            dependencies: Services dont dépend ce service
            **metadata: Métadonnées supplémentaires
        """
        if name in self._health_checks:
            self.logger.warning(f"Service '{name}' already registered, updating")
        
        health_check = HealthCheck(
            name=name,
            check_function=check_function,
            interval=interval or self.check_interval,
            timeout=timeout,
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            critical=critical,
            dependencies=dependencies or [],
            metadata=metadata
        )
        
        self._health_checks[name] = health_check
        
        # Initialiser état de santé
        self._service_health[name] = ServiceHealth(
            name=name,
            status=ServiceStatus.UNKNOWN,
            last_check=datetime.now(timezone.utc),
            response_time=0.0,
            metadata=metadata
        )
        
        self.logger.info(f"Service registered: {name}",
                        extra={
                            "critical": critical,
                            "interval": health_check.interval,
                            "dependencies": dependencies or []
                        })
        
        # Démarrer monitoring si actif
        if self._monitoring_active:
            self._start_service_monitoring(name)
    
    async def start_monitoring(self) -> None:
        """Démarrer le monitoring de tous les services enregistrés."""
        if self._monitoring_active:
            self.logger.warning("Health monitoring already active")
            return
        
        self.logger.info(f"Starting health monitoring for {len(self._health_checks)} services")
        
        self._monitoring_active = True
        self._start_time = time.time()
        
        # Démarrer tâche pour chaque service
        for name in self._health_checks:
            self._start_service_monitoring(name)
        
        self.logger.info("✅ Health monitoring started for all services")
    
    def _start_service_monitoring(self, service_name: str) -> None:
        """Démarrer monitoring d'un service spécifique."""
        if service_name in self._monitoring_tasks:
            # Annuler tâche existante
            self._monitoring_tasks[service_name].cancel()
        
        # Créer nouvelle tâche
        task = asyncio.create_task(
            self._monitor_service(service_name),
            name=f"health_monitor_{service_name}"
        )
        self._monitoring_tasks[service_name] = task
        
        self.logger.debug(f"Started monitoring task for service: {service_name}")
    
    async def _monitor_service(self, service_name: str) -> None:
        """
        Boucle de monitoring d'un service.
        
        Args:
            service_name: Nom du service à surveiller
        """
        health_check = self._health_checks[service_name]
        
        self.logger.debug(f"Monitoring service: {service_name}")
        
        while self._monitoring_active:
            try:
                await self._perform_health_check(service_name)
                
                # Attendre avant prochaine vérification
                await asyncio.sleep(health_check.interval)
                
            except asyncio.CancelledError:
                self.logger.debug(f"Monitoring cancelled for service: {service_name}")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop for {service_name}: {e}")
                await asyncio.sleep(min(30, health_check.interval))
    
    async def _perform_health_check(self, service_name: str) -> None:
        """
        Effectuer un health check sur un service.
        
        Args:
            service_name: Nom du service
        """
        health_check = self._health_checks[service_name]
        service_health = self._service_health[service_name]
        
        start_time = time.time()
        check_success = False
        error_message = None
        
        try:
            # Vérifier dépendances d'abord
            if not await self._check_dependencies(service_name):
                error_message = "Dependencies not healthy"
                raise Exception(error_message)
            
            # Effectuer le check avec timeout
            check_success = await asyncio.wait_for(
                health_check.check_function(),
                timeout=health_check.timeout
            )
            
        except asyncio.TimeoutError:
            error_message = f"Health check timeout after {health_check.timeout}s"
        except Exception as e:
            error_message = str(e)
        
        # Calculer temps de réponse
        response_time = (time.time() - start_time) * 1000  # ms
        
        # Mettre à jour statistiques
        service_health.last_check = datetime.now(timezone.utc)
        service_health.response_time = response_time
        service_health.total_checks += 1
        self._total_checks += 1
        
        if check_success:
            # Succès
            service_health.consecutive_failures = 0
            service_health.consecutive_successes += 1
            service_health.error_message = None
            
            # Déterminer nouveau statut
            if service_health.consecutive_successes >= health_check.success_threshold:
                new_status = ServiceStatus.HEALTHY
            else:
                new_status = service_health.status  # Garder statut actuel
            
        else:
            # Échec
            service_health.consecutive_successes = 0
            service_health.consecutive_failures += 1
            service_health.total_failures += 1
            service_health.error_message = error_message
            self._total_failures += 1
            
            # Déterminer nouveau statut
            if service_health.consecutive_failures >= health_check.failure_threshold:
                new_status = ServiceStatus.UNHEALTHY
            elif service_health.consecutive_failures > 1:
                new_status = ServiceStatus.DEGRADED
            else:
                new_status = service_health.status
        
        # Mettre à jour statut si changé
        if service_health.status != new_status:
            await self._update_service_status(service_name, new_status, error_message)
        
        # Calculer uptime
        if service_health.total_checks > 0:
            success_count = service_health.total_checks - service_health.total_failures
            service_health.uptime_percentage = (success_count / service_health.total_checks) * 100
        
        # Métriques
        await self._record_health_metrics(service_name, check_success, response_time)
        
        self.logger.debug(f"Health check completed: {service_name}",
                         extra={
                             "success": check_success,
                             "response_time_ms": response_time,
                             "status": service_health.status.value,
                             "consecutive_failures": service_health.consecutive_failures
                         })
    
    async def _check_dependencies(self, service_name: str) -> bool:
        """
        Vérifier que les dépendances d'un service sont saines.
        
        Args:
            service_name: Nom du service
            
        Returns:
            bool: True si dépendances OK
        """
        health_check = self._health_checks[service_name]
        
        for dependency in health_check.dependencies:
            if dependency not in self._service_health:
                self.logger.warning(f"Unknown dependency: {dependency} for {service_name}")
                return False
            
            dep_health = self._service_health[dependency]
            if dep_health.status == ServiceStatus.UNHEALTHY:
                self.logger.debug(f"Dependency {dependency} is unhealthy for {service_name}")
                return False
        
        return True
    
    async def _update_service_status(self, 
                                   service_name: str, 
                                   new_status: ServiceStatus,
                                   error_message: str = None) -> None:
        """
        Mettre à jour le statut d'un service.
        
        Args:
            service_name: Nom du service
            new_status: Nouveau statut
            error_message: Message d'erreur si applicable
        """
        service_health = self._service_health[service_name]
        old_status = service_health.status
        
        service_health.status = new_status
        
        self.logger.info(f"Service status change: {service_name}",
                        extra={
                            "old_status": old_status.value,
                            "new_status": new_status.value,
                            "error": error_message
                        })
        
        # Enregistrer incident si dégradation
        if new_status in [ServiceStatus.DEGRADED, ServiceStatus.UNHEALTHY]:
            await self._record_incident(service_name, old_status, new_status, error_message)
        
        # Alertes
        if self.alert_callback:
            try:
                await self.alert_callback(service_name, old_status, new_status, error_message)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
        
        # Auto-remédiation
        if (self.enable_auto_remediation and 
            new_status == ServiceStatus.UNHEALTHY and
            service_name in self._health_checks):
            await self._attempt_auto_remediation(service_name)
    
    async def _record_incident(self, 
                              service_name: str,
                              old_status: ServiceStatus,
                              new_status: ServiceStatus,
                              error_message: str = None) -> None:
        """
        Enregistrer un incident de santé.
        
        Args:
            service_name: Service concerné
            old_status: Ancien statut
            new_status: Nouveau statut
            error_message: Détails de l'erreur
        """
        incident = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": service_name,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "error_message": error_message,
            "critical": self._health_checks[service_name].critical
        }
        
        self._incident_history.append(incident)
        
        # Limiter historique (derniers 1000)
        if len(self._incident_history) > 1000:
            self._incident_history = self._incident_history[-1000:]
        
        self.logger.warning(f"Incident recorded: {service_name}",
                           extra=incident)
    
    async def _attempt_auto_remediation(self, service_name: str) -> None:
        """
        Tenter une remédiation automatique.
        
        Args:
            service_name: Service à réparer
        """
        self.logger.info(f"Attempting auto-remediation for: {service_name}")
        
        # TODO: Implémenter logiques de remédiation spécifiques
        # Par exemple:
        # - Redémarrer service
        # - Vider cache
        # - Reconnecter base de données
        # - Etc.
        
        # Pour l'instant, juste attendre et re-tester
        await asyncio.sleep(10)
        await self._perform_health_check(service_name)
    
    async def _record_health_metrics(self, 
                                   service_name: str, 
                                   success: bool, 
                                   response_time: float) -> None:
        """
        Enregistrer métriques de santé.
        
        Args:
            service_name: Nom du service
            success: Succès du check
            response_time: Temps de réponse en ms
        """
        if not self.enable_metrics or not metrics_service:
            return
        
        try:
            # Compteur de checks
            await metrics_service.increment_counter(
                "health_checks_total",
                labels={
                    "service": service_name,
                    "result": "success" if success else "failure"
                }
            )
            
            # Temps de réponse
            await metrics_service.record_histogram(
                "health_check_duration_ms",
                response_time,
                labels={"service": service_name}
            )
            
            # Status gauge
            service_health = self._service_health[service_name]
            status_values = {
                ServiceStatus.HEALTHY: 1,
                ServiceStatus.DEGRADED: 0.5,
                ServiceStatus.UNHEALTHY: 0,
                ServiceStatus.UNKNOWN: -1,
                ServiceStatus.MAINTENANCE: -0.5
            }
            
            await metrics_service.set_gauge(
                "service_health_status",
                status_values[service_health.status],
                labels={"service": service_name}
            )
            
            # Uptime percentage
            await metrics_service.set_gauge(
                "service_uptime_percentage",
                service_health.uptime_percentage,
                labels={"service": service_name}
            )
            
        except Exception as e:
            self.logger.debug(f"Failed to record health metrics: {e}")
    
    async def get_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        """
        Obtenir l'état de santé d'un service.
        
        Args:
            service_name: Nom du service
            
        Returns:
            Optional[ServiceHealth]: État du service ou None
        """
        return self._service_health.get(service_name)
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """
        Obtenir l'état de santé global du système.
        
        Returns:
            Dict: État de santé global
        """
        if not self._service_health:
            return {
                "status": "unknown",
                "message": "No services registered",
                "services": {}
            }
        
        # Analyser états des services
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        critical_unhealthy = False
        
        service_details = {}
        
        for name, health in self._service_health.items():
            service_details[name] = {
                "status": health.status.value,
                "last_check": health.last_check.isoformat(),
                "response_time": health.response_time,
                "uptime_percentage": health.uptime_percentage,
                "error_message": health.error_message,
                "critical": self._health_checks[name].critical
            }
            
            if health.status == ServiceStatus.HEALTHY:
                healthy_count += 1
            elif health.status == ServiceStatus.DEGRADED:
                degraded_count += 1
            elif health.status == ServiceStatus.UNHEALTHY:
                unhealthy_count += 1
                if self._health_checks[name].critical:
                    critical_unhealthy = True
        
        # Déterminer état global
        if critical_unhealthy or unhealthy_count > len(self._service_health) // 2:
            overall_status = "unhealthy"
            message = f"System unhealthy: {unhealthy_count} services down"
        elif degraded_count > 0 or unhealthy_count > 0:
            overall_status = "degraded"
            message = f"System degraded: {degraded_count} degraded, {unhealthy_count} unhealthy"
        elif healthy_count == len(self._service_health):
            overall_status = "healthy"
            message = "All services healthy"
        else:
            overall_status = "unknown"
            message = "System status unknown"
        
        # Statistiques globales
        uptime = time.time() - self._start_time
        success_rate = ((self._total_checks - self._total_failures) / self._total_checks * 100 
                       if self._total_checks > 0 else 0)
        
        return {
            "status": overall_status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": service_details,
            "summary": {
                "total_services": len(self._service_health),
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
                "critical_issues": critical_unhealthy
            },
            "metrics": {
                "uptime_seconds": uptime,
                "total_checks": self._total_checks,
                "total_failures": self._total_failures,
                "success_rate_percentage": success_rate,
                "recent_incidents": len([
                    i for i in self._incident_history 
                    if datetime.fromisoformat(i["timestamp"]) > 
                    datetime.now(timezone.utc) - timedelta(hours=24)
                ])
            }
        }
    
    async def get_incident_history(self, 
                                 service_name: str = None,
                                 hours: int = 24) -> List[Dict[str, Any]]:
        """
        Obtenir historique des incidents.
        
        Args:
            service_name: Filtrer par service (optionnel)
            hours: Nombre d'heures d'historique
            
        Returns:
            List: Liste des incidents
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        incidents = [
            incident for incident in self._incident_history
            if datetime.fromisoformat(incident["timestamp"]) >= since
        ]
        
        if service_name:
            incidents = [i for i in incidents if i["service"] == service_name]
        
        return incidents
    
    async def set_service_maintenance(self, service_name: str, maintenance: bool = True) -> None:
        """
        Mettre un service en maintenance.
        
        Args:
            service_name: Nom du service
            maintenance: True pour activer maintenance
        """
        if service_name not in self._service_health:
            raise ValueError(f"Unknown service: {service_name}")
        
        service_health = self._service_health[service_name]
        
        if maintenance:
            service_health.status = ServiceStatus.MAINTENANCE
            self.logger.info(f"Service set to maintenance: {service_name}")
        else:
            service_health.status = ServiceStatus.UNKNOWN
            # Forcer un check immédiat
            await self._perform_health_check(service_name)
            self.logger.info(f"Service removed from maintenance: {service_name}")
    
    async def stop_monitoring(self) -> None:
        """Arrêter le monitoring de tous les services."""
        if not self._monitoring_active:
            return
        
        self.logger.info("Stopping health monitoring")
        
        self._monitoring_active = False
        
        # Annuler toutes les tâches
        for task in self._monitoring_tasks.values():
            task.cancel()
        
        # Attendre l'arrêt des tâches
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks.values(), return_exceptions=True)
        
        self._monitoring_tasks.clear()
        
        self.logger.info("✅ Health monitoring stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtenir statistiques détaillées du monitor.
        
        Returns:
            Dict: Statistiques complètes
        """
        uptime = time.time() - self._start_time
        
        return {
            "monitoring_active": self._monitoring_active,
            "uptime_seconds": uptime,
            "registered_services": len(self._health_checks),
            "total_checks": self._total_checks,
            "total_failures": self._total_failures,
            "success_rate": (self._total_checks - self._total_failures) / self._total_checks * 100 if self._total_checks > 0 else 0,
            "incident_count": len(self._incident_history),
            "services": {name: health.status.value for name, health in self._service_health.items()}
        }
