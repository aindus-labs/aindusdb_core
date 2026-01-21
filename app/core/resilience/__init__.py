"""
Resilience Patterns pour AindusDB Core - Circuit Breaker, Retry, Timeout.

Ce module implémente des patterns de résilience pour protéger l'application
contre les défaillances en cascade et améliorer la robustesse générale.

Components:
- CircuitBreaker: Protection contre défaillances répétées
- RetryPolicy: Gestion des retry avec backoff
- TimeoutManager: Gestion des timeouts avec escalade
- BulkheadPattern: Isolation des ressources
- HealthMonitor: Surveillance continue des services

Example:
    from app.core.resilience import CircuitBreaker, RetryPolicy
    
    # Circuit breaker pour service externe
    breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=Exception
    )
    
    @breaker.protect
    async def call_external_service():
        # Code potentiellement défaillant
        return await external_api.call()
"""

from .circuit_breaker import CircuitBreaker, CircuitBreakerState
from .retry_policy import RetryPolicy, BackoffStrategy
from .timeout_manager import TimeoutManager, TimeoutError
from .bulkhead_pattern import BulkheadPattern, ResourcePool
from .health_monitor import HealthMonitor, ServiceStatus
from .resilience_coordinator import ResilienceCoordinator

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerState",
    "RetryPolicy",
    "BackoffStrategy",
    "TimeoutManager",
    "TimeoutError",
    "BulkheadPattern",
    "ResourcePool",
    "HealthMonitor",
    "ServiceStatus",
    "ResilienceCoordinator"
]
