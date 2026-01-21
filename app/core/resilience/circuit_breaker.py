"""
Circuit Breaker Pattern pour protection contre défaillances en cascade.

Le Circuit Breaker surveille les appels vers des services externes ou
des composants potentiellement défaillants et "ouvre le circuit" quand
un seuil de défaillances est atteint, empêchant les cascades de pannes.

States:
- CLOSED: Circuit fermé, appels normaux
- OPEN: Circuit ouvert, appels bloqués
- HALF_OPEN: Test si service est récupéré

Example:
    breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=Exception
    )
    
    @breaker.protect
    async def risky_operation():
        # Code potentiellement défaillant
        return await external_service.call()
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Optional, Type, Union, Dict, List
from datetime import datetime, timezone, timedelta
from functools import wraps
import inspect

from ...core.logging import get_logger
from ...core.metrics import metrics_service


class CircuitBreakerState(Enum):
    """États possibles du Circuit Breaker."""
    CLOSED = "closed"        # Circuit fermé - appels normaux
    OPEN = "open"           # Circuit ouvert - appels bloqués
    HALF_OPEN = "half_open" # Test de récupération


class CircuitBreakerError(Exception):
    """Exception levée quand le circuit breaker est ouvert."""
    
    def __init__(self, message: str, next_attempt_time: datetime):
        super().__init__(message)
        self.next_attempt_time = next_attempt_time


class CircuitBreaker:
    """
    Circuit Breaker Pattern avec monitoring et métriques intégrés.
    
    Le Circuit Breaker surveille automatiquement les défaillances d'un
    service et protège l'application contre les cascades de pannes en
    "ouvrant le circuit" quand trop d'échecs consécutifs sont détectés.
    
    Features:
    - États CLOSED/OPEN/HALF_OPEN avec transitions automatiques
    - Seuils configurables de défaillances
    - Timeout de récupération adaptatif  
    - Support async/await natif
    - Métriques Prometheus intégrées
    - Callbacks pour événements d'état
    - Protection contre les exceptions spécifiques
    
    Architecture:
    ┌─────────────┐    Success    ┌─────────────┐
    │   CLOSED    │──────────────▶│   CLOSED    │
    │             │               │             │
    │ Fail Count: │◀──────────────│ Fail Count: │
    │      X      │    Timeout    │      0      │
    └──────┬──────┘               └─────────────┘
           │ Threshold
           │ Exceeded
           ▼
    ┌─────────────┐    Timeout    ┌─────────────┐
    │    OPEN     │──────────────▶│ HALF_OPEN   │
    │             │               │             │
    │ Reject All  │◀──────────────│ Test Call   │
    │   Calls     │    Fail       │             │
    └─────────────┘               └─────────────┘
    
    Example:
        # Configuration basique
        db_breaker = CircuitBreaker(
            name="database",
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=DatabaseError
        )
        
        @db_breaker.protect
        async def get_user(user_id: str):
            return await database.fetch_user(user_id)
        
        # Configuration avancée
        api_breaker = CircuitBreaker(
            name="external_api",
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=2,
            timeout=10,
            expected_exception=(TimeoutError, ConnectionError),
            on_state_change=lambda old, new: logger.info(f"API breaker: {old} -> {new}")
        )
    """
    
    def __init__(self,
                 name: str = "default",
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 success_threshold: int = 1,
                 timeout: Optional[float] = None,
                 expected_exception: Union[Type[Exception], tuple] = Exception,
                 on_state_change: Optional[Callable] = None,
                 enable_metrics: bool = True):
        """
        Initialiser le Circuit Breaker.
        
        Args:
            name: Nom pour identification et métriques
            failure_threshold: Nombre d'échecs avant ouverture
            recovery_timeout: Temps avant test de récupération (secondes)
            success_threshold: Succès requis pour fermeture en HALF_OPEN
            timeout: Timeout individuel des appels (secondes)
            expected_exception: Exception(s) comptées comme échecs
            on_state_change: Callback changement d'état
            enable_metrics: Activer métriques Prometheus
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.on_state_change = on_state_change
        self.enable_metrics = enable_metrics
        
        # État du circuit
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._next_attempt_time: Optional[float] = None
        
        # Statistiques
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._total_rejected = 0
        self._state_changes = 0
        
        # Lock pour thread safety
        self._lock = asyncio.Lock()
        
        self.logger = get_logger(f"aindusdb.resilience.circuit_breaker.{name}")
        
        self.logger.info(f"Circuit breaker '{name}' initialized",
                        extra={
                            "failure_threshold": failure_threshold,
                            "recovery_timeout": recovery_timeout,
                            "success_threshold": success_threshold
                        })
    
    @property
    def state(self) -> CircuitBreakerState:
        """État actuel du circuit breaker."""
        return self._state
    
    @property
    def failure_count(self) -> int:
        """Nombre d'échecs consécutifs."""
        return self._failure_count
    
    @property
    def is_closed(self) -> bool:
        """Circuit fermé (appels autorisés)."""
        return self._state == CircuitBreakerState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Circuit ouvert (appels rejetés)."""
        return self._state == CircuitBreakerState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Circuit en test de récupération."""
        return self._state == CircuitBreakerState.HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Exécuter une fonction protégée par le circuit breaker.
        
        Args:
            func: Fonction à exécuter
            *args: Arguments de la fonction
            **kwargs: Arguments nommés de la fonction
            
        Returns:
            Any: Résultat de la fonction
            
        Raises:
            CircuitBreakerError: Si circuit ouvert
            Exception: Erreurs de la fonction appelée
        """
        async with self._lock:
            # Vérifier état et mettre à jour si nécessaire
            await self._update_state()
            
            # Rejeter si circuit ouvert
            if self._state == CircuitBreakerState.OPEN:
                self._total_rejected += 1
                await self._record_metrics("rejected")
                
                next_attempt = datetime.fromtimestamp(
                    self._next_attempt_time, 
                    timezone.utc
                ) if self._next_attempt_time else datetime.now(timezone.utc)
                
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. Next attempt at {next_attempt}",
                    next_attempt
                )
        
        # Exécuter l'appel (en dehors du lock pour éviter blocage)
        self._total_calls += 1
        start_time = time.time()
        
        try:
            # Appliquer timeout si configuré
            if self.timeout:
                if inspect.iscoroutinefunction(func):
                    result = await asyncio.wait_for(
                        func(*args, **kwargs), 
                        timeout=self.timeout
                    )
                else:
                    # Pour fonctions synchrones, les rendre async
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, func, *args, **kwargs
                        ),
                        timeout=self.timeout
                    )
            else:
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
            
            # Succès - mettre à jour état
            execution_time = (time.time() - start_time) * 1000
            async with self._lock:
                await self._record_success(execution_time)
            
            return result
            
        except Exception as e:
            # Échec - vérifier si c'est une exception attendue
            execution_time = (time.time() - start_time) * 1000
            
            if isinstance(e, self.expected_exception):
                async with self._lock:
                    await self._record_failure(e, execution_time)
                    
            await self._record_metrics("error", execution_time)
            raise
    
    def protect(self, func: Callable) -> Callable:
        """
        Décorateur pour protéger une fonction avec le circuit breaker.
        
        Args:
            func: Fonction à protéger
            
        Returns:
            Callable: Fonction protégée
            
        Example:
            @breaker.protect
            async def risky_operation():
                return await external_service.call()
        """
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.call(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            async def sync_wrapper(*args, **kwargs):
                return await self.call(func, *args, **kwargs)
            return sync_wrapper
    
    async def _update_state(self):
        """Mettre à jour l'état du circuit breaker selon les conditions."""
        current_time = time.time()
        
        if self._state == CircuitBreakerState.OPEN:
            # Vérifier si temps de récupération écoulé
            if (self._next_attempt_time and 
                current_time >= self._next_attempt_time):
                await self._transition_to(CircuitBreakerState.HALF_OPEN)
    
    async def _record_success(self, execution_time: float):
        """
        Enregistrer un succès et mettre à jour l'état.
        
        Args:
            execution_time: Temps d'exécution en ms
        """
        self._total_successes += 1
        await self._record_metrics("success", execution_time)
        
        if self._state == CircuitBreakerState.CLOSED:
            # Reset compteur d'échecs
            if self._failure_count > 0:
                self.logger.debug(f"Resetting failure count from {self._failure_count} to 0")
                self._failure_count = 0
                
        elif self._state == CircuitBreakerState.HALF_OPEN:
            # Incrémenter compteur de succès
            self._success_count += 1
            self.logger.debug(f"Half-open success count: {self._success_count}/{self.success_threshold}")
            
            # Fermer circuit si seuil de succès atteint
            if self._success_count >= self.success_threshold:
                await self._transition_to(CircuitBreakerState.CLOSED)
    
    async def _record_failure(self, exception: Exception, execution_time: float):
        """
        Enregistrer un échec et mettre à jour l'état.
        
        Args:
            exception: Exception qui a causé l'échec
            execution_time: Temps d'exécution avant échec
        """
        self._total_failures += 1
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        self.logger.warning(f"Circuit breaker failure recorded: {exception}",
                          extra={
                              "failure_count": self._failure_count,
                              "threshold": self.failure_threshold,
                              "execution_time_ms": execution_time
                          })
        
        if self._state == CircuitBreakerState.CLOSED:
            # Ouvrir circuit si seuil atteint
            if self._failure_count >= self.failure_threshold:
                await self._transition_to(CircuitBreakerState.OPEN)
                
        elif self._state == CircuitBreakerState.HALF_OPEN:
            # Retour à OPEN en cas d'échec pendant test
            await self._transition_to(CircuitBreakerState.OPEN)
    
    async def _transition_to(self, new_state: CircuitBreakerState):
        """
        Effectuer transition vers nouvel état.
        
        Args:
            new_state: Nouvel état du circuit
        """
        old_state = self._state
        self._state = new_state
        self._state_changes += 1
        
        current_time = time.time()
        
        if new_state == CircuitBreakerState.OPEN:
            # Calculer temps de prochaine tentative
            self._next_attempt_time = current_time + self.recovery_timeout
            
            self.logger.warning(f"Circuit breaker '{self.name}' OPENED",
                              extra={
                                  "failure_count": self._failure_count,
                                  "recovery_timeout": self.recovery_timeout,
                                  "next_attempt_time": self._next_attempt_time
                              })
        
        elif new_state == CircuitBreakerState.HALF_OPEN:
            # Reset compteurs pour test
            self._success_count = 0
            
            self.logger.info(f"Circuit breaker '{self.name}' HALF-OPEN (testing recovery)",
                           extra={"success_threshold": self.success_threshold})
        
        elif new_state == CircuitBreakerState.CLOSED:
            # Reset tous les compteurs
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._next_attempt_time = None
            
            self.logger.info(f"Circuit breaker '{self.name}' CLOSED (service recovered)")
        
        # Callback utilisateur
        if self.on_state_change:
            try:
                if inspect.iscoroutinefunction(self.on_state_change):
                    await self.on_state_change(old_state, new_state)
                else:
                    self.on_state_change(old_state, new_state)
            except Exception as e:
                self.logger.error(f"Error in state change callback: {e}")
        
        # Métrique de changement d'état
        await self._record_metrics("state_change")
    
    async def _record_metrics(self, event_type: str, execution_time: float = None):
        """
        Enregistrer métriques Prometheus.
        
        Args:
            event_type: Type d'événement (success/error/rejected/state_change)
            execution_time: Temps d'exécution en ms
        """
        if not self.enable_metrics or not metrics_service:
            return
        
        try:
            # Compteur d'événements
            await metrics_service.increment_counter(
                "circuit_breaker_events_total",
                labels={
                    "name": self.name,
                    "event": event_type,
                    "state": self._state.value
                }
            )
            
            # Histogramme des temps d'exécution
            if execution_time is not None and event_type in ["success", "error"]:
                await metrics_service.record_histogram(
                    "circuit_breaker_execution_duration_ms",
                    execution_time,
                    labels={"name": self.name, "result": event_type}
                )
            
            # Gauge de l'état actuel
            state_values = {
                CircuitBreakerState.CLOSED: 0,
                CircuitBreakerState.HALF_OPEN: 1,
                CircuitBreakerState.OPEN: 2
            }
            await metrics_service.set_gauge(
                "circuit_breaker_state",
                state_values[self._state],
                labels={"name": self.name}
            )
            
            # Gauge du nombre d'échecs
            await metrics_service.set_gauge(
                "circuit_breaker_failure_count",
                self._failure_count,
                labels={"name": self.name}
            )
            
        except Exception as e:
            self.logger.debug(f"Failed to record metrics: {e}")
    
    async def reset(self):
        """
        Réinitialiser manuellement le circuit breaker.
        
        Utile pour forcer la récupération ou les tests.
        """
        async with self._lock:
            self.logger.info(f"Circuit breaker '{self.name}' manually reset")
            await self._transition_to(CircuitBreakerState.CLOSED)
    
    async def force_open(self):
        """
        Forcer l'ouverture du circuit breaker.
        
        Utile pour maintenance ou tests.
        """
        async with self._lock:
            self.logger.warning(f"Circuit breaker '{self.name}' manually opened")
            await self._transition_to(CircuitBreakerState.OPEN)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtenir statistiques détaillées du circuit breaker.
        
        Returns:
            Dict: Statistiques complètes
        """
        current_time = time.time()
        
        stats = {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_calls": self._total_calls,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "total_rejected": self._total_rejected,
            "state_changes": self._state_changes,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "success_threshold": self.success_threshold
        }
        
        # Calculs dérivés
        if self._total_calls > 0:
            stats["success_rate"] = self._total_successes / self._total_calls
            stats["failure_rate"] = self._total_failures / self._total_calls
            stats["rejection_rate"] = self._total_rejected / self._total_calls
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0
            stats["rejection_rate"] = 0.0
        
        # Temps jusqu'à prochaine tentative
        if self._next_attempt_time:
            stats["next_attempt_in_seconds"] = max(0, self._next_attempt_time - current_time)
        else:
            stats["next_attempt_in_seconds"] = 0
        
        # Temps depuis dernier échec
        if self._last_failure_time:
            stats["time_since_last_failure"] = current_time - self._last_failure_time
        else:
            stats["time_since_last_failure"] = None
        
        return stats


class CircuitBreakerRegistry:
    """
    Registry centralisé pour gérer multiples Circuit Breakers.
    
    Permet la gestion centralisée de tous les circuit breakers
    de l'application avec monitoring et configuration unifiés.
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self.logger = get_logger("aindusdb.resilience.circuit_breaker.registry")
    
    def register(self, name: str, breaker: CircuitBreaker) -> CircuitBreaker:
        """
        Enregistrer un circuit breaker.
        
        Args:
            name: Nom unique du breaker
            breaker: Instance du circuit breaker
            
        Returns:
            CircuitBreaker: Le breaker enregistré
        """
        self._breakers[name] = breaker
        self.logger.info(f"Circuit breaker registered: {name}")
        return breaker
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Obtenir un circuit breaker par nom."""
        return self._breakers.get(name)
    
    def create(self, name: str, **kwargs) -> CircuitBreaker:
        """
        Créer et enregistrer un nouveau circuit breaker.
        
        Args:
            name: Nom unique du breaker
            **kwargs: Arguments pour CircuitBreaker
            
        Returns:
            CircuitBreaker: Nouveau breaker créé
        """
        breaker = CircuitBreaker(name=name, **kwargs)
        return self.register(name, breaker)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Obtenir statistiques de tous les breakers."""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}
    
    async def reset_all(self):
        """Réinitialiser tous les circuit breakers."""
        for name, breaker in self._breakers.items():
            await breaker.reset()
            self.logger.info(f"Reset circuit breaker: {name}")
    
    def list_names(self) -> List[str]:
        """Lister noms de tous les breakers."""
        return list(self._breakers.keys())


# Instance globale du registry
circuit_breaker_registry = CircuitBreakerRegistry()
