"""
Resilience Coordinator - Orchestration complète des patterns de résilience.

Ce coordinateur unifie tous les patterns de résilience (Circuit Breaker,
Health Monitor, Retry Policies, etc.) pour fournir une interface simple
et cohérente à l'ensemble de l'application.

Example:
    coordinator = ResilienceCoordinator(db_manager=db)
    await coordinator.initialize()
    
    # Circuit breakers automatiques
    @coordinator.with_circuit_breaker("external_api")
    async def call_api():
        return await api_client.call()
    
    # Health checks intégrés  
    health = await coordinator.get_system_health()
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone

from ...core.logging import get_logger, LogContext
from ...core.database import DatabaseManager
from ...core.metrics import metrics_service
from .circuit_breaker import CircuitBreaker, circuit_breaker_registry, CircuitBreakerError
from .health_monitor import HealthMonitor, ServiceStatus


class ResilienceCoordinator:
    """
    Coordinateur de résilience centralisé pour AindusDB Core.
    
    Ce coordinateur unifie et orchestre tous les patterns de résilience
    pour fournir une protection complète contre les défaillances et
    une récupération automatique des services.
    
    Features:
    - Circuit breakers configurés automatiquement
    - Health monitoring de tous les composants
    - Retry policies adaptatives
    - Auto-remédiation des problèmes communs
    - Métriques et alerting intégrés
    - Configuration centralisée
    
    Architecture:
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │ Circuit Breakers│───▶│ Health Monitor  │───▶│ Alert Manager   │
    │ - Database      │    │ - All Services  │    │ - Notifications │
    │ - Redis         │    │ - Dependencies  │    │ - Escalation    │
    │ - External APIs │    │ - Auto Recovery │    │ - Remediation   │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
    
    Example:
        # Initialisation complète
        coordinator = ResilienceCoordinator(
            db_manager=db_manager,
            enable_auto_remediation=True,
            alert_webhook="https://alerts.company.com/webhook"
        )
        await coordinator.initialize()
        
        # Protection automatique d'une fonction
        @coordinator.with_circuit_breaker("payment_service",
                                         failure_threshold=3,
                                         recovery_timeout=60)
        async def process_payment(amount: float):
            return await payment_api.charge(amount)
        
        # Health check global
        health = await coordinator.get_system_health()
        if health["status"] != "healthy":
            await coordinator.trigger_auto_remediation()
    """
    
    def __init__(self, 
                 db_manager: DatabaseManager,
                 enable_auto_remediation: bool = True,
                 health_check_interval: float = 30.0,
                 alert_webhook: Optional[str] = None):
        """
        Initialiser le coordinateur de résilience.
        
        Args:
            db_manager: Gestionnaire de base de données
            enable_auto_remediation: Activer remédiation automatique
            health_check_interval: Intervalle des health checks (secondes)
            alert_webhook: URL webhook pour alertes
        """
        self.db_manager = db_manager
        self.enable_auto_remediation = enable_auto_remediation
        self.health_check_interval = health_check_interval
        self.alert_webhook = alert_webhook
        
        self.logger = get_logger("aindusdb.resilience.coordinator")
        
        # Composants de résilience
        self.health_monitor: Optional[HealthMonitor] = None
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # État
        self.initialized = False
        self.auto_remediation_active = False
        
        # Statistiques
        self.stats = {
            "initialization_time": 0.0,
            "auto_remediations": 0,
            "circuit_breaker_trips": 0,
            "health_incidents": 0,
            "alerts_sent": 0
        }
    
    async def initialize(self) -> None:
        """Initialiser tous les composants de résilience."""
        if self.initialized:
            self.logger.warning("Resilience Coordinator already initialized")
            return
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.logger.info("Initializing Resilience Coordinator")
            
            # 1. Initialiser Health Monitor
            self.health_monitor = HealthMonitor(
                check_interval=self.health_check_interval,
                enable_auto_remediation=self.enable_auto_remediation,
                alert_callback=self._handle_health_alert
            )
            
            # 2. Enregistrer health checks par défaut
            await self._register_default_health_checks()
            
            # 3. Démarrer monitoring
            await self.health_monitor.start_monitoring()
            
            # 4. Configurer circuit breakers par défaut
            await self._setup_default_circuit_breakers()
            
            # 5. Finaliser initialisation
            self.initialized = True
            initialization_time = asyncio.get_event_loop().time() - start_time
            self.stats["initialization_time"] = initialization_time
            
            self.logger.info(f"✅ Resilience Coordinator initialized in {initialization_time:.2f}s",
                           extra={
                               "auto_remediation": self.enable_auto_remediation,
                               "health_checks": len(self.health_monitor._health_checks) if self.health_monitor else 0,
                               "circuit_breakers": len(self.circuit_breakers)
                           })
                           
        except Exception as e:
            self.logger.error(f"Failed to initialize Resilience Coordinator: {e}")
            raise
    
    async def _register_default_health_checks(self):
        """Enregistrer les health checks par défaut."""
        
        # Health check base de données
        async def database_health_check() -> bool:
            try:
                async with self.db_manager.get_connection() as conn:
                    await conn.fetchval("SELECT 1")
                return True
            except Exception:
                return False
        
        self.health_monitor.register_service(
            name="database",
            check_function=database_health_check,
            interval=30.0,
            timeout=5.0,
            failure_threshold=2,
            critical=True,
            metadata={"type": "postgresql", "component": "core"}
        )
        
        # Health check métriques
        async def metrics_health_check() -> bool:
            try:
                if not metrics_service:
                    return False
                # Vérifier que le service métriques répond
                return metrics_service.is_healthy()  # À implémenter
            except Exception:
                return False
        
        self.health_monitor.register_service(
            name="metrics",
            check_function=metrics_health_check,
            interval=60.0,
            timeout=3.0,
            failure_threshold=3,
            critical=False,
            metadata={"type": "prometheus", "component": "monitoring"}
        )
        
        # Health check VERITAS service
        async def veritas_health_check() -> bool:
            try:
                # TODO: Implémenter vérification VERITAS
                return True
            except Exception:
                return False
        
        self.health_monitor.register_service(
            name="veritas",
            check_function=veritas_health_check,
            interval=45.0,
            timeout=10.0,
            failure_threshold=2,
            critical=True,
            dependencies=["database"],
            metadata={"type": "ai_service", "component": "veritas"}
        )
        
        self.logger.info("Default health checks registered")
    
    async def _setup_default_circuit_breakers(self):
        """Configurer les circuit breakers par défaut."""
        
        # Circuit breaker base de données
        db_breaker = CircuitBreaker(
            name="database",
            failure_threshold=3,
            recovery_timeout=30.0,
            success_threshold=2,
            timeout=10.0,
            expected_exception=Exception,
            on_state_change=self._handle_circuit_breaker_state_change
        )
        self.circuit_breakers["database"] = db_breaker
        circuit_breaker_registry.register("database", db_breaker)
        
        # Circuit breaker services externes (exemple)
        external_api_breaker = CircuitBreaker(
            name="external_api",
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=2,
            timeout=15.0,
            expected_exception=(ConnectionError, TimeoutError),
            on_state_change=self._handle_circuit_breaker_state_change
        )
        self.circuit_breakers["external_api"] = external_api_breaker
        circuit_breaker_registry.register("external_api", external_api_breaker)
        
        # Circuit breaker VERITAS
        veritas_breaker = CircuitBreaker(
            name="veritas",
            failure_threshold=4,
            recovery_timeout=45.0,
            success_threshold=1,
            timeout=30.0,
            expected_exception=Exception,
            on_state_change=self._handle_circuit_breaker_state_change
        )
        self.circuit_breakers["veritas"] = veritas_breaker
        circuit_breaker_registry.register("veritas", veritas_breaker)
        
        self.logger.info(f"Default circuit breakers configured: {list(self.circuit_breakers.keys())}")
    
    async def _handle_health_alert(self, 
                                  service_name: str,
                                  old_status: ServiceStatus,
                                  new_status: ServiceStatus,
                                  error_message: str = None):
        """
        Gérer les alertes de santé des services.
        
        Args:
            service_name: Service concerné
            old_status: Ancien statut
            new_status: Nouveau statut
            error_message: Message d'erreur
        """
        with LogContext(
            operation="health_alert",
            service=service_name,
            old_status=old_status.value,
            new_status=new_status.value
        ):
            self.stats["health_incidents"] += 1
            
            alert_level = "warning"
            if new_status == ServiceStatus.UNHEALTHY:
                alert_level = "critical"
            elif new_status == ServiceStatus.DEGRADED:
                alert_level = "warning"
            
            self.logger.log(
                40 if alert_level == "critical" else 30,  # ERROR or WARNING
                f"Health alert: {service_name} {old_status.value} -> {new_status.value}",
                extra={
                    "service": service_name,
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                    "error_message": error_message,
                    "alert_level": alert_level
                }
            )
            
            # Envoyer alerte webhook si configuré
            if self.alert_webhook:
                await self._send_webhook_alert(service_name, old_status, new_status, error_message, alert_level)
            
            # Déclencher auto-remédiation si nécessaire
            if (self.enable_auto_remediation and 
                new_status == ServiceStatus.UNHEALTHY):
                await self._trigger_service_remediation(service_name)
    
    async def _handle_circuit_breaker_state_change(self, old_state, new_state):
        """Gérer les changements d'état des circuit breakers."""
        self.stats["circuit_breaker_trips"] += 1
        
        self.logger.warning(f"Circuit breaker state change: {old_state.value} -> {new_state.value}")
        
        # Alerter si circuit s'ouvre
        if new_state.value == "open":
            if self.alert_webhook:
                await self._send_webhook_alert(
                    "circuit_breaker",
                    old_state,
                    new_state,
                    f"Circuit breaker opened due to failures",
                    "critical"
                )
    
    async def _send_webhook_alert(self, 
                                service_name: str,
                                old_status,
                                new_status,
                                error_message: str,
                                alert_level: str):
        """
        Envoyer alerte via webhook.
        
        Args:
            service_name: Service concerné
            old_status: Ancien statut  
            new_status: Nouveau statut
            error_message: Message d'erreur
            alert_level: Niveau d'alerte
        """
        try:
            import aiohttp
            
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": service_name,
                "old_status": str(old_status),
                "new_status": str(new_status),
                "error_message": error_message,
                "alert_level": alert_level,
                "source": "aindusdb_resilience"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.alert_webhook,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        self.stats["alerts_sent"] += 1
                        self.logger.debug(f"Alert sent successfully: {service_name}")
                    else:
                        self.logger.warning(f"Failed to send alert: HTTP {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Error sending webhook alert: {e}")
    
    async def _trigger_service_remediation(self, service_name: str):
        """
        Déclencher remédiation automatique pour un service.
        
        Args:
            service_name: Service à réparer
        """
        if not self.enable_auto_remediation:
            return
        
        with LogContext(operation="auto_remediation", service=service_name):
            self.logger.info(f"Triggering auto-remediation for: {service_name}")
            self.stats["auto_remediations"] += 1
            
            try:
                if service_name == "database":
                    await self._remediate_database()
                elif service_name == "metrics":
                    await self._remediate_metrics()
                elif service_name == "veritas":
                    await self._remediate_veritas()
                else:
                    # Remédiation générique
                    await self._remediate_generic_service(service_name)
                
                self.logger.info(f"Auto-remediation completed for: {service_name}")
                
            except Exception as e:
                self.logger.error(f"Auto-remediation failed for {service_name}: {e}")
    
    async def _remediate_database(self):
        """Remédiation spécifique à la base de données."""
        # Tenter reconnexion
        try:
            await self.db_manager.disconnect()
            await asyncio.sleep(5)
            await self.db_manager.connect()
            self.logger.info("Database reconnection successful")
        except Exception as e:
            self.logger.error(f"Database remediation failed: {e}")
    
    async def _remediate_metrics(self):
        """Remédiation spécifique au service métriques."""
        # Redémarrer service métriques
        try:
            if metrics_service:
                await metrics_service.restart()
                self.logger.info("Metrics service restart successful")
        except Exception as e:
            self.logger.error(f"Metrics remediation failed: {e}")
    
    async def _remediate_veritas(self):
        """Remédiation spécifique au service VERITAS."""
        # Vider caches, redémarrer composants
        try:
            # TODO: Implémenter remédiation VERITAS spécifique
            self.logger.info("VERITAS service remediation attempted")
        except Exception as e:
            self.logger.error(f"VERITAS remediation failed: {e}")
    
    async def _remediate_generic_service(self, service_name: str):
        """Remédiation générique pour services inconnus."""
        # Attendre et re-tester
        await asyncio.sleep(10)
        self.logger.info(f"Generic remediation applied to: {service_name}")
    
    def with_circuit_breaker(self, 
                           name: str,
                           failure_threshold: int = 5,
                           recovery_timeout: float = 60.0,
                           **kwargs) -> CircuitBreaker:
        """
        Obtenir ou créer circuit breaker pour protection de fonction.
        
        Args:
            name: Nom du circuit breaker
            failure_threshold: Seuil d'échecs
            recovery_timeout: Temps de récupération
            **kwargs: Arguments supplémentaires pour CircuitBreaker
            
        Returns:
            CircuitBreaker: Circuit breaker configuré
            
        Example:
            @coordinator.with_circuit_breaker("payment_api", failure_threshold=3)
            async def process_payment():
                return await payment_service.charge()
        """
        if name not in self.circuit_breakers:
            # Créer nouveau circuit breaker
            breaker = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                on_state_change=self._handle_circuit_breaker_state_change,
                **kwargs
            )
            self.circuit_breakers[name] = breaker
            circuit_breaker_registry.register(name, breaker)
            
            self.logger.info(f"Created circuit breaker: {name}")
        
        return self.circuit_breakers[name]
    
    async def get_system_health(self) -> Dict[str, Any]:
        """
        Obtenir l'état de santé global du système.
        
        Returns:
            Dict: État de santé complet
        """
        if not self.health_monitor:
            return {"status": "unknown", "error": "Health monitor not initialized"}
        
        # Santé des services
        overall_health = await self.health_monitor.get_overall_health()
        
        # État des circuit breakers
        circuit_breaker_stats = {}
        for name, breaker in self.circuit_breakers.items():
            circuit_breaker_stats[name] = {
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "success_rate": breaker.get_stats()["success_rate"]
            }
        
        # Statistiques du coordinateur
        coordinator_stats = self.get_stats()
        
        return {
            **overall_health,
            "circuit_breakers": circuit_breaker_stats,
            "resilience_coordinator": coordinator_stats
        }
    
    async def trigger_auto_remediation(self) -> Dict[str, Any]:
        """
        Déclencher remédiation automatique de tous les services dégradés.
        
        Returns:
            Dict: Résultats de la remédiation
        """
        if not self.health_monitor:
            return {"error": "Health monitor not initialized"}
        
        overall_health = await self.health_monitor.get_overall_health()
        
        remediation_results = {}
        
        for service_name, service_info in overall_health["services"].items():
            if service_info["status"] in ["degraded", "unhealthy"]:
                try:
                    await self._trigger_service_remediation(service_name)
                    remediation_results[service_name] = "success"
                except Exception as e:
                    remediation_results[service_name] = f"failed: {e}"
        
        return {
            "remediation_triggered": len(remediation_results),
            "results": remediation_results
        }
    
    async def reset_all_circuit_breakers(self):
        """Réinitialiser tous les circuit breakers."""
        for name, breaker in self.circuit_breakers.items():
            await breaker.reset()
            self.logger.info(f"Reset circuit breaker: {name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtenir statistiques du coordinateur de résilience.
        
        Returns:
            Dict: Statistiques complètes
        """
        return {
            "initialized": self.initialized,
            "auto_remediation_active": self.enable_auto_remediation,
            "health_monitor_active": self.health_monitor._monitoring_active if self.health_monitor else False,
            "registered_circuit_breakers": len(self.circuit_breakers),
            "registered_health_checks": len(self.health_monitor._health_checks) if self.health_monitor else 0,
            **self.stats
        }
    
    async def shutdown(self):
        """Arrêter proprement le coordinateur de résilience."""
        if not self.initialized:
            return
        
        try:
            self.logger.info("Shutting down Resilience Coordinator")
            
            # Arrêter health monitor
            if self.health_monitor:
                await self.health_monitor.stop_monitoring()
            
            # Reset circuit breakers
            await self.reset_all_circuit_breakers()
            
            self.initialized = False
            self.logger.info("✅ Resilience Coordinator shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error during Resilience Coordinator shutdown: {e}")


# Factory pour simplifier l'utilisation
class ResilienceFactory:
    """Factory pour créer et configurer le coordinateur de résilience."""
    
    @staticmethod
    async def create_coordinator(db_manager: DatabaseManager, 
                               **kwargs) -> ResilienceCoordinator:
        """
        Créer et initialiser coordinateur de résilience.
        
        Args:
            db_manager: Gestionnaire de base de données
            **kwargs: Options de configuration
            
        Returns:
            ResilienceCoordinator: Coordinateur prêt à l'emploi
        """
        coordinator = ResilienceCoordinator(db_manager=db_manager, **kwargs)
        await coordinator.initialize()
        return coordinator
