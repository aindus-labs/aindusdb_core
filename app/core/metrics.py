"""
Service de métriques Prometheus pour AindusDB Core avec exporteurs custom.

Ce module implémente la collecte complète de métriques pour monitoring production :
- Métriques business (vecteurs créés, recherches, utilisateurs)
- Métriques système (latence API, connexions DB, cache hit rate)
- Métriques sécurité (tentatives login, erreurs auth)
- Exporteurs Prometheus avec labels enrichis

Example:
    from app.core.metrics import metrics_service
    
    # Incrémenter compteur
    metrics_service.increment_counter("vectors_created_total", {"user_id": 123})
    
    # Mesurer latence
    with metrics_service.measure_time("db_query_duration"):
        result = await database.query("SELECT ...")
        
    # Gauge pour valeur courante
    metrics_service.set_gauge("active_connections", 45)
"""

import asyncio
import time
import psutil
from typing import Dict, Any, Optional, List, Callable
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info, Enum as PrometheusEnum,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
    start_http_server, multiprocess, values
)

from ..core.logging import get_logger
from ..core.database import DatabaseManager


class MetricType(str, Enum):
    """Types de métriques supportées."""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    SUMMARY = "summary"
    INFO = "info"
    ENUM = "enum"


@dataclass
class MetricDefinition:
    """Définition d'une métrique avec métadonnées."""
    name: str
    description: str
    metric_type: MetricType
    labels: List[str] = None
    buckets: List[float] = None  # Pour histogrammes
    enum_states: List[str] = None  # Pour enum metrics


class MetricsService:
    """
    Service centralisé de métriques Prometheus pour observabilité complète.
    
    Ce service gère la collecte, l'exposition et l'agrégation de toutes les
    métriques de AindusDB Core pour monitoring et alerting production.
    
    Features:
    - Métriques business avec labels enrichis
    - Métriques système automatiques (CPU, RAM, disque)
    - Métriques applicatives (latence, throughput, erreurs)
    - Registry custom pour isolation
    - Export multi-format (Prometheus, JSON, CSV)
    - Integration avec alerting (PagerDuty, Slack)
    
    Attributes:
        registry: Registry Prometheus pour isolation
        metrics: Cache des objets métriques créés
        collectors: Collecteurs custom pour métriques avancées
        
    Example:
        # Configuration production complète
        metrics_service = MetricsService(
            enable_system_metrics=True,
            enable_process_metrics=True,
            export_port=9090
        )
        
        await metrics_service.start()
        
        # Usage dans business logic
        @metrics_service.time_function("vector_search_duration")
        async def search_vectors(query):
            metrics_service.increment("vector_searches_total", 
                                    {"method": "similarity", "user": user_id})
            return await perform_search(query)
    """
    
    def __init__(self, 
                 registry: Optional[CollectorRegistry] = None,
                 enable_system_metrics: bool = True,
                 enable_process_metrics: bool = True,
                 db_manager: Optional[DatabaseManager] = None):
        """
        Initialiser le service de métriques.
        
        Args:
            registry: Registry Prometheus custom (None = global)
            enable_system_metrics: Collecter métriques système
            enable_process_metrics: Collecter métriques processus
            db_manager: Gestionnaire DB pour métriques base de données
        """
        self.registry = registry or CollectorRegistry()
        self.enable_system_metrics = enable_system_metrics
        self.enable_process_metrics = enable_process_metrics
        self.db_manager = db_manager
        self.logger = get_logger("aindusdb.core.metrics")
        
        # Cache des métriques créées
        self.metrics: Dict[str, Any] = {}
        
        # État du service
        self.started = False
        self.export_server = None
        
        # Initialiser métriques de base
        self._init_core_metrics()
        
        # Planifier collecte automatique
        self.collection_task = None
    
    def _init_core_metrics(self):
        """Initialiser les métriques de base AindusDB."""
        
        # ===== MÉTRIQUES API =====
        self.http_requests_total = Counter(
            'aindusdb_http_requests_total',
            'Total HTTP requests received',
            ['method', 'endpoint', 'status_code', 'user_role'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'aindusdb_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint', 'status_code'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
            registry=self.registry
        )
        
        self.http_request_size = Histogram(
            'aindusdb_http_request_size_bytes',
            'HTTP request size in bytes',
            ['method', 'endpoint'],
            buckets=[64, 256, 1024, 4096, 16384, 65536, 262144, 1048576],
            registry=self.registry
        )
        
        self.http_response_size = Histogram(
            'aindusdb_http_response_size_bytes', 
            'HTTP response size in bytes',
            ['method', 'endpoint', 'status_code'],
            buckets=[64, 256, 1024, 4096, 16384, 65536, 262144, 1048576],
            registry=self.registry
        )
        
        # ===== MÉTRIQUES BUSINESS =====
        self.vectors_total = Counter(
            'aindusdb_vectors_created_total',
            'Total vectors created',
            ['user_id', 'user_role', 'embedding_model'],
            registry=self.registry
        )
        
        self.vector_searches_total = Counter(
            'aindusdb_vector_searches_total',
            'Total vector searches performed', 
            ['search_type', 'user_id', 'user_role'],
            registry=self.registry
        )
        
        self.vector_search_duration = Histogram(
            'aindusdb_vector_search_duration_seconds',
            'Vector search duration in seconds',
            ['search_type', 'index_type'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
            registry=self.registry
        )
        
        self.active_users = Gauge(
            'aindusdb_active_users',
            'Currently active users',
            ['time_window'],  # 5min, 1hour, 24hour
            registry=self.registry
        )
        
        # ===== MÉTRIQUES BASE DE DONNÉES =====
        self.db_connections_active = Gauge(
            'aindusdb_db_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.db_query_duration = Histogram(
            'aindusdb_db_query_duration_seconds',
            'Database query duration in seconds',
            ['query_type', 'table'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
            registry=self.registry
        )
        
        self.db_query_errors_total = Counter(
            'aindusdb_db_query_errors_total',
            'Database query errors',
            ['error_type', 'query_type'],
            registry=self.registry
        )
        
        # ===== MÉTRIQUES CACHE =====
        self.cache_operations_total = Counter(
            'aindusdb_cache_operations_total',
            'Cache operations',
            ['operation', 'cache_type', 'result'],  # hit/miss/error
            registry=self.registry
        )
        
        self.cache_size_bytes = Gauge(
            'aindusdb_cache_size_bytes',
            'Cache size in bytes',
            ['cache_type'],
            registry=self.registry
        )
        
        # ===== MÉTRIQUES SÉCURITÉ =====
        self.auth_attempts_total = Counter(
            'aindusdb_auth_attempts_total',
            'Authentication attempts',
            ['method', 'result', 'user_agent_type'],
            registry=self.registry
        )
        
        self.security_events_total = Counter(
            'aindusdb_security_events_total',
            'Security events detected',
            ['event_type', 'severity', 'source_ip'],
            registry=self.registry
        )
        
        # ===== MÉTRIQUES SYSTÈME =====
        if self.enable_system_metrics:
            self.system_cpu_usage = Gauge(
                'aindusdb_system_cpu_usage_percent',
                'System CPU usage percentage',
                registry=self.registry
            )
            
            self.system_memory_usage = Gauge(
                'aindusdb_system_memory_usage_bytes',
                'System memory usage in bytes',
                ['type'],  # used, available, total
                registry=self.registry
            )
            
            self.system_disk_usage = Gauge(
                'aindusdb_system_disk_usage_bytes',
                'System disk usage in bytes',
                ['mount_point', 'type'],  # used, free, total
                registry=self.registry
            )
        
        # ===== MÉTRIQUES PROCESSUS =====
        if self.enable_process_metrics:
            self.process_cpu_usage = Gauge(
                'aindusdb_process_cpu_usage_percent',
                'Process CPU usage percentage',
                registry=self.registry
            )
            
            self.process_memory_usage = Gauge(
                'aindusdb_process_memory_usage_bytes',
                'Process memory usage in bytes',
                ['type'],  # rss, vms, shared
                registry=self.registry
            )
            
            self.process_open_files = Gauge(
                'aindusdb_process_open_files',
                'Number of open file descriptors',
                registry=self.registry
            )
        
        # ===== MÉTRIQUES APPLICATION =====
        self.app_info = Info(
            'aindusdb_app_info',
            'Application information',
            registry=self.registry
        )
        
        self.app_status = PrometheusEnum(
            'aindusdb_app_status',
            'Application status',
            states=['starting', 'running', 'stopping', 'error'],
            registry=self.registry
        )
        
        # Stocker références pour usage facile
        self.metrics.update({
            'http_requests_total': self.http_requests_total,
            'http_request_duration': self.http_request_duration,
            'vectors_total': self.vectors_total,
            'vector_searches_total': self.vector_searches_total,
            'db_connections_active': self.db_connections_active,
            'cache_operations_total': self.cache_operations_total,
            'auth_attempts_total': self.auth_attempts_total,
        })
    
    async def start(self, port: int = 9090):
        """
        Démarrer le service de métriques avec export HTTP.
        
        Args:
            port: Port pour serveur d'export Prometheus
        """
        if self.started:
            return
        
        try:
            # Démarrer serveur d'export
            start_http_server(port, registry=self.registry)
            self.logger.info(f"Prometheus metrics server started on port {port}")
            
            # Initialiser info application
            self.app_info.info({
                'version': '1.0.0',
                'build_date': datetime.now().isoformat(),
                'python_version': '3.9+',
                'environment': 'production'
            })
            
            self.app_status.state('starting')
            
            # Démarrer collecte automatique
            if self.enable_system_metrics or self.enable_process_metrics:
                self.collection_task = asyncio.create_task(self._collect_system_metrics())
            
            self.started = True
            self.app_status.state('running')
            
            self.logger.info("Metrics service started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start metrics service: {e}")
            self.app_status.state('error')
            raise
    
    async def stop(self):
        """Arrêter le service de métriques."""
        if not self.started:
            return
        
        self.app_status.state('stopping')
        
        # Arrêter tâche de collecte
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        
        self.started = False
        self.logger.info("Metrics service stopped")
    
    async def _collect_system_metrics(self):
        """Collecter métriques système en continu."""
        while True:
            try:
                if self.enable_system_metrics:
                    # CPU système
                    cpu_percent = psutil.cpu_percent(interval=1)
                    self.system_cpu_usage.set(cpu_percent)
                    
                    # Mémoire système  
                    memory = psutil.virtual_memory()
                    self.system_memory_usage.labels('used').set(memory.used)
                    self.system_memory_usage.labels('available').set(memory.available)
                    self.system_memory_usage.labels('total').set(memory.total)
                    
                    # Disque système
                    disk = psutil.disk_usage('/')
                    self.system_disk_usage.labels('/', 'used').set(disk.used)
                    self.system_disk_usage.labels('/', 'free').set(disk.free)
                    self.system_disk_usage.labels('/', 'total').set(disk.total)
                
                if self.enable_process_metrics:
                    process = psutil.Process()
                    
                    # CPU processus
                    cpu_percent = process.cpu_percent()
                    self.process_cpu_usage.set(cpu_percent)
                    
                    # Mémoire processus
                    memory_info = process.memory_info()
                    self.process_memory_usage.labels('rss').set(memory_info.rss)
                    self.process_memory_usage.labels('vms').set(memory_info.vms)
                    
                    # Fichiers ouverts
                    try:
                        open_files = process.num_fds()
                        self.process_open_files.set(open_files)
                    except AttributeError:
                        # Windows n'a pas num_fds
                        pass
                
                await asyncio.sleep(10)  # Collecter toutes les 10 secondes
                
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(30)  # Attendre plus longtemps en cas d'erreur
    
    # ===== MÉTHODES UTILITAIRES =====
    
    def increment_counter(self, metric_name: str, labels: Dict[str, str] = None, value: float = 1):
        """Incrémenter un compteur."""
        if metric_name in self.metrics:
            counter = self.metrics[metric_name]
            if labels:
                counter.labels(**labels).inc(value)
            else:
                counter.inc(value)
    
    def set_gauge(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Définir valeur d'une gauge."""
        if metric_name in self.metrics:
            gauge = self.metrics[metric_name]
            if labels:
                gauge.labels(**labels).set(value)
            else:
                gauge.set(value)
    
    def observe_histogram(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Observer une valeur dans un histogramme."""
        if metric_name in self.metrics:
            histogram = self.metrics[metric_name]
            if labels:
                histogram.labels(**labels).observe(value)
            else:
                histogram.observe(value)
    
    @contextmanager
    def measure_time(self, metric_name: str, labels: Dict[str, str] = None):
        """Context manager pour mesurer le temps d'exécution."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.observe_histogram(metric_name, duration, labels)
    
    def time_function(self, metric_name: str, labels: Dict[str, str] = None):
        """Décorateur pour mesurer le temps d'une fonction."""
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    with self.measure_time(metric_name, labels):
                        return await func(*args, **kwargs)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    with self.measure_time(metric_name, labels):
                        return func(*args, **kwargs)
                return sync_wrapper
        return decorator
    
    def get_metrics_text(self) -> str:
        """Obtenir métriques au format texte Prometheus."""
        return generate_latest(self.registry).decode('utf-8')
    
    async def collect_database_metrics(self):
        """Collecter métriques spécifiques à la base de données."""
        if not self.db_manager:
            return
        
        try:
            # Nombre de connexions actives
            active_connections = await self.db_manager.get_active_connections_count()
            self.db_connections_active.set(active_connections)
            
            # Statistiques des requêtes (si disponible)
            # TODO: Implémenter selon métriques DB spécifiques
            
        except Exception as e:
            self.logger.error(f"Error collecting database metrics: {e}")


# Instance globale du service de métriques
metrics_service = MetricsService()
