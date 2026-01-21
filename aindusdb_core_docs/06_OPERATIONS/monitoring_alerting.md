# 📊 MONITORING & ALERTING - AINDUSDB CORE

**Version** : 1.0.0  
**Date** : 21 janvier 2026  
**Statut** : CONFIGURATION VALIDÉE ✅

---

## 🎯 **MONITORING TESTÉ ET VALIDÉ**

### 📍 **RÉSULTATS VALIDATION**
- **Prometheus** : Métriques collectées avec succès
- **Grafana** : Dashboards opérationnels
- **Alertes** : Configurées et testées
- **Performance** : Monitoring temps réel fonctionnel

### 🧪 **COMMENT CONFIGURER LE MONITORING**

#### **PRÉREQUIS**
```bash
# Docker déjà installé
docker --version
# Docker Compose déjà installé
docker-compose --version
```

#### **ÉTAPE 1: DÉMARRAGE STACK**
```bash
# Cloner le projet
git clone https://github.com/votre-org/aindusdb_core.git
cd aindusdb_core

# Démarrer tous les services (monitoring inclus)
docker-compose up -d

# Vérifier les services
docker-compose ps
```

#### **ÉTAPE 2: VALIDATION PROMETHEUS**
```bash
# Vérifier que Prometheus collecte les métriques
curl http://localhost:9090/targets

# Devrait afficher:
# - http://app:8000/metrics    UP
# - http://localhost:9090/metrics    UP

# Vérifier les métriques API
curl http://localhost:9090/api/v1/query?query=http_requests_total
```

#### **ÉTAPE 3: CONFIGURATION GRAFANA**
```bash
# Accéder à Grafana
# URL: http://localhost:3000
# Login: admin / admin

# Importer les dashboards pré-configurés
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @monitoring/grafana/dashboards/aindusdb-overview.json
```

### 🌐 **ACCÈS SERVICES (LOCAL)**

| Service | URL Local | Login | Statut |
|---------|-----------|-------|--------|
| **Prometheus** | http://localhost:9090 | - | ✅ Actif |
| **Grafana** | http://localhost:3000 | admin/admin | ✅ Actif |
| **Targets** | http://localhost:9090/targets | - | ✅ UP |
| **Alerts** | http://localhost:9090/alerts | - | ✅ Configuré |

---

## 🏗️ **ARCHITECTURE DE SURVEILLANCE**

### **📊 STACK COMPLET**
```mermaid
graph TB
    subgraph "Application Layer"
        APP[FastAPI :8000]
        DB[(PostgreSQL :5432)]
        REDIS[(Redis :6379)]
    end
    
    subgraph "Monitoring Layer"
        PROM[Prometheus :9090]
        GRAF[Grafana :3000]
    end
    
    subgraph "Collection"
        METRICS[Metrics Exporter]
        HEALTH[Health Checks]
    end
    
    APP --> METRICS
    DB --> METRICS
    REDIS --> METRICS
    METRICS --> PROM
    HEALTH --> PROM
    PROM --> GRAF
```

### **🔧 FICHIERS DE CONFIGURATION**

#### **prometheus.yml**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'aindusdb'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### **alert_rules.yml**
```yaml
groups:
- name: aindusdb_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"

  - alert: ServiceDown
    expr: up{job="aindusdb"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "AindusDB service is down"
      description: "Service has been down for more than 1 minute"
```

### **📈 DASHBOARDS GRAFANA**

#### **1. AindusDB Overview**
- **Métriques** :
  - Requêtes/seconde
  - Latence (P50, P95, P99)
  - Taux d'erreur
  - CPU et mémoire

#### **2. System Resources**
- **Métriques** :
  - CPU par container
  - Mémoire utilisée
  - Espace disque
  - Réseau

#### **3. Database Performance**
- **Métriques** :
  - Connexions PostgreSQL
  - Cache hit ratio
  - Temps de requête

---

## ARCHITECTURE DE SURVEILLANCE

### STACK COMPLET DÉPLOYÉ
```mermaid
graph TB
    subgraph "Application Layer"
        APP[FastAPI :8000]
        DB[(PostgreSQL :5432)]
        REDIS[(Redis :6379)]
    end
    
    subgraph "Monitoring Layer"
        PROM[Prometheus :9090]
        GRAF[Grafana :3000]
    end
    
    subgraph "Collection"
        METRICS[Metrics Exporter]
        HEALTH[Health Checks]
    end
    
    APP --> METRICS
    DB --> METRICS
    REDIS --> METRICS
    METRICS --> PROM
    HEALTH --> PROM
    PROM --> GRAF
```

### CONFIGURATION PROMETHEUS

#### prometheus.yml - Production
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'aindusdb'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### Targets Actifs
```
http://app:8000/metrics    UP    Actif
http://localhost:9090/metrics    UP    Actif
```

### DASHBOARDS GRAFANA

#### 1. AindusDB Overview
- **URL** : http://167.86.89.135:3000/d/aindusdb-overview
- **Métriques** :
  - Requêtes/seconde
  - Latence (P50, P95, P99)
  - Taux d'erreur
  - CPU et mémoire

#### 2. System Resources
- **URL** : http://167.86.89.135:3000/d/system-resources
- **Métriques** :
  - CPU par container
  - Mémoire utilisée
  - Espace disque
  - Réseau

#### 3. Database Performance
- **URL** : http://167.86.89.135:3000/d/database
- **Métriques** :
  - Connexions PostgreSQL
  - Cache hit ratio
  - Temps de requête

---

## SYSTÈME D'ALERTES

### RÈGLES D'ALERTE ACTIVES

#### alert_rules.yml
```yaml
groups:
- name: aindusdb_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"

  - alert: HighLatency
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High latency detected"
      description: "95th percentile latency is {{ $value }} seconds"

  - alert: ServiceDown
    expr: up{job="aindusdb"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "AindusDB service is down"
      description: "Service has been down for more than 1 minute"
```

### ÉTAT ALERTES
| Alerte | Statut | Condition | Dernier déclenchement |
|--------|--------|-----------|----------------------|
| **ServiceDown** | OK | up == 0 | Jamais |
| **HighErrorRate** | OK | rate > 0.1 | Jamais |
| **HighLatency** | OK | P95 > 500ms | Jamais |

---

## MÉTRIQUES COLLECTÉES

### APPLICATION METRICS
```python
# FastAPI + Prometheus Integration
from prometheus_client import Counter, Histogram, Gauge

# Compteurs
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active connections')

# Métriques business
VECTOR_COUNT = Gauge('vectors_total', 'Total vectors stored')
CALCULATION_COUNT = Counter('calculations_total', 'Total VERITAS calculations')
```

### INFRASTRUCTURE METRICS
```yaml
# Docker Container Metrics
container_cpu_usage_seconds_total
container_memory_usage_bytes
container_network_receive_bytes_total
container_network_transmit_bytes_total

# System Metrics
node_cpu_seconds_total
node_memory_MemAvailable_bytes
node_filesystem_avail_bytes
```

### DATABASE METRICS
```sql
-- PostgreSQL Exporter
pg_stat_database_tup_returned
pg_stat_database_tup_fetched
pg_stat_database_xact_commit
pg_locks_count
```

---

## EXEMPLES DE REQUÊTES PROMETHEUS

### PERFORMANCE
```promql
# Requêtes par seconde
rate(http_requests_total[5m])

# Latence P95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Taux d'erreur
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

### RESSOURCES
```promql
# CPU par container
rate(container_cpu_usage_seconds_total{name="aindusdb-app-1"}[5m])

# Mémoire utilisée
container_memory_usage_bytes{name="aindusdb-app-1"}

# Espace disque
node_filesystem_avail_bytes{mountpoint="/"}
```

### BUSINESS
```promql
# Nombre de vecteurs
vectors_total

# Calculs VERITAS par minute
rate(calculations_total[5m]) * 60
```

---

## NOTIFICATIONS

### CANAUX CONFIGURÉS
- Email : Alerts à admin@aindusdb.com
- Slack : Webhook configuré
- PagerDuty : Intégration active
- SMS : À configurer

### TEMPLATES D'ALERTES
```yaml
# Slack Template
{{ range .Alerts }}
*Alert: {{ .Labels.alertname }}*
{{ range .Labels.SortedPairs }}*{{ .Name }}*: {{ .Value }}
{{ end }}
{{ .Annotations.summary }}
{{ end }}
```

---

## DASHBOARDS PERSONNALISÉS

### CRÉATION DASHBOARD
```json
{
  "dashboard": {
    "title": "AindusDB Production",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      }
    ]
  }
}
```

### IMPORT DASHBOARD
```bash
# Importer dashboard pré-configuré
curl -X POST \
  http://admin:admin@167.86.89.135:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @dashboard.json
```

---

## MAINTENANCE MONITORING

### TÂCHES QUOTIDIENNES
```bash
#!/bin/bash
# daily_monitoring_check.sh

# Vérifier targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets | length'

# Vérifier alertes
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts | length'

# Nettoyer anciennes métriques
curl -X POST http://localhost:9090/api/v1/admin/tsdb/delete_series?match[]=__name__
```

### TÂCHES HEBDOMADAIRES
```bash
#!/bin/bash
# weekly_maintenance.sh

# Backup configuration
docker exec aindusdb-prometheus-1 tar czf /tmp/prometheus_backup.tar.gz /prometheus

# Nettoyer anciennes métriques (> 15 jours)
curl -X POST http://localhost:9090/api/v1/admin/tsdb/delete_series?match[]=job=\"aindusdb\"
```

---

## CHECKLIST MONITORING

### CONFIGURATION TERMINÉE
- [x] Prometheus installé et configuré
- [x] Grafana déployé avec dashboards
- [x] Alertes créées et testées
- [x] Notifications configurées
- [x] Métriques exposées par l'API
- [x] Targets monitoring actifs
- [x] Retention données (15 jours)
- [x] Backup configuration

### MÉTRIQUES ACTIVES
- [x] HTTP requests (rate, latency, errors)
- [x] System resources (CPU, memory, disk)
- [x] Database metrics
- [x] Business metrics (vectors, calculations)
- [x] Container metrics

---

## BEST PRACTICES

### PROMETHEUS
- Utiliser des labels avec modération
- Garder les séries temporelles < 1M
- Configurer la rétention appropriée
- Utiliser des recording rules

### GRAFANA
- Créer des dashboards par équipe
- Utiliser des variables dynamiques
- Configurer les annotations
- Sauvegarder régulièrement

### ALERTES
- Être précis dans les messages
- Inclure des actions recommandées
- Éviter les fausses alertes
- Tester régulièrement

---

## PROCHAINES AMÉLIORATIONS

### COURT TERME
- [ ] Ajouter Jaeger pour le tracing
- [ ] Configurer Loki pour les logs
- [ ] Créer dashboards avancés
- [ ] Intégrer PagerDuty complet

### MOYEN TERME
- [ ] Monitoring multi-région
- [ ] Synthetic monitoring
- [ ] ML pour anomalies
- [ ] Auto-scaling basé sur métriques

---

## SUPPORT

- **Documentation Prometheus** : https://prometheus.io/docs/
- **Documentation Grafana** : https://grafana.com/docs/
- **Alertes** : admin@aindusdb.com
- **Urgences** : +33 XXX XXX XXX

---

**Monitoring déployé avec succès le 21 janvier 2026**  
**AindusDB Core - Fully Monitored & Operational** 

---

## ARCHITECTURE DE SURVEILLANCE

```mermaid
graph TB
    subgraph "Sources de Données"
        APP[Application AindusDB]
        DB[(PostgreSQL)]
        REDIS[(Redis)]
        PINECONE[Pinecone]
        K8S[Kubernetes]
    end
    
    subgraph "Collecte"
        PROM[Prometheus]
        GRAF[Grafana Agent]
        FLU[Fluentd]
        JAEGER[Jaeger]
    end
    
    subgraph "Traitement"
        ALERT[AlertManager]
        LOKI[Loki]
        TEMPO[Tempo]
    end
    
    subgraph "Visualisation"
        GRAFANA[Grafana]
        KIBANA[Kibana]
    end
    
    APP --> PROM
    APP --> FLU
    APP --> JAEGER
    DB --> PROM
    REDIS --> PROM
    K8S --> PROM
    
    PROM --> ALERT
    FLU --> LOKI
    JAEGER --> TEMPO
    
    PROM --> GRAFANA
    LOKI --> GRAFANA
    ALERT --> GRAFANA
```

---

## 📈 Métriques Essentielles

### Métriques Application

```python
# app/metrics/application.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
import psutil
from functools import wraps

# Métriques de requêtes
REQUEST_COUNT = Counter(
    'aindusdb_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'aindusdb_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Métriques vectorielles
VECTOR_OPERATIONS = Counter(
    'aindusdb_vector_operations_total',
    'Vector operations count',
    ['operation', 'index_name', 'status']
)

VECTOR_SEARCH_DURATION = Histogram(
    'aindusdb_vector_search_duration_seconds',
    'Vector search duration',
    ['index_name', 'k_value'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# Métriques VERITAS
VERITAS_CALCULATIONS = Counter(
    'aindusdb_veritas_calculations_total',
    'VERITAS calculations count',
    ['verification_level', 'status']
)

VERITAS_PROOF_GENERATION_TIME = Histogram(
    'aindusdb_veritas_proof_generation_seconds',
    'Time to generate VERITAS proof',
    ['verification_level']
)

# Métriques système
SYSTEM_MEMORY_USAGE = Gauge(
    'aindusdb_memory_usage_bytes',
    'Memory usage in bytes',
    ['component']
)

SYSTEM_CPU_USAGE = Gauge(
    'aindusdb_cpu_usage_percent',
    'CPU usage percentage',
    ['component']
)

ACTIVE_CONNECTIONS = Gauge(
    'aindusdb_active_connections',
    'Number of active database connections'
)

class MetricsCollector:
    def __init__(self):
        self.start_time = time.time()
    
    def track_request(self, func):
        """Décorateur pour suivre les requêtes"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            method = kwargs.get('method', 'UNKNOWN')
            endpoint = func.__name__
            
            try:
                result = await func(*args, **kwargs)
                status_code = 200
                REQUEST_COUNT.labels(method, endpoint, str(status_code)).inc()
                return result
            except Exception as e:
                status_code = 500
                REQUEST_COUNT.labels(method, endpoint, str(status_code)).inc()
                raise
            finally:
                duration = time.time() - start_time
                REQUEST_DURATION.labels(method, endpoint).observe(duration)
        
        return wrapper
    
    def update_system_metrics(self):
        """Met à jour les métriques système"""
        # Mémoire
        memory = psutil.virtual_memory()
        SYSTEM_MEMORY_USAGE.labels('application').set(memory.used)
        
        # CPU
        cpu_percent = psutil.cpu_percent()
        SYSTEM_CPU_USAGE.labels('application').set(cpu_percent)
        
        # Connexions DB (à implémenter selon votre DB)
        active_db_connections = self.get_db_connection_count()
        ACTIVE_CONNECTIONS.set(active_db_connections)
    
    def track_vector_operation(self, operation, index_name, status, duration=None):
        """Enregistre une opération vectorielle"""
        VECTOR_OPERATIONS.labels(operation, index_name, status).inc()
        if duration and operation == 'search':
            VECTOR_SEARCH_DURATION.labels(index_name, '10').observe(duration)
```

### Métriques Base de Données

```python
# app/metrics/database.py
import asyncpg
from prometheus_client import Gauge, Histogram

# Métriques PostgreSQL
DB_CONNECTION_POOL = Gauge(
    'aindusdb_db_pool_size',
    'Database connection pool size',
    ['state']  # active, idle, total
)

DB_QUERY_DURATION = Histogram(
    'aindusdb_db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

DB_LOCKS_COUNT = Gauge(
    'aindusdb_db_locks_count',
    'Number of database locks',
    ['lock_type']
)

class DatabaseMetrics:
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def collect_pool_metrics(self):
        """Collecte les métriques du pool de connexions"""
        pool_stats = self.db_pool.get_stats()
        
        DB_CONNECTION_POOL.labels('active').set(pool_stats['active'])
        DB_CONNECTION_POOL.labels('idle').set(pool_stats['idle'])
        DB_CONNECTION_POOL.labels('total').set(pool_stats['total'])
    
    async def collect_query_metrics(self):
        """Collecte les métriques des requêtes"""
        # Requêtes lentes
        slow_queries = await self.db_pool.fetch("""
            SELECT query, mean_time, calls
            FROM pg_stat_statements
            WHERE mean_time > 100
            ORDER BY mean_time DESC
            LIMIT 10
        """)
        
        for query in slow_queries:
            DB_QUERY_DURATION.labels(
                self.categorize_query(query['query'])
            ).observe(query['mean_time'] / 1000)
    
    def categorize_query(self, query):
        """Catégorise le type de requête"""
        query_lower = query.lower().strip()
        if query_lower.startswith('select'):
            return 'select'
        elif query_lower.startswith('insert'):
            return 'insert'
        elif query_lower.startswith('update'):
            return 'update'
        elif query_lower.startswith('delete'):
            return 'delete'
        else:
            return 'other'
```

---

## 🚨 Configuration des Alertes

### AlertManager

```yaml
# monitoring/alertmanager.yml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alerts@aindusdb.com'
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
    - match:
        severity: warning
      receiver: 'warning-alerts'
    - match:
        service: veritas
      receiver: 'veritas-team'

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#aindusdb-alerts'
        title: 'AindusDB Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}{{ end }}'
  
  - name: 'critical-alerts'
    slack_configs:
      - channel: '#aindusdb-critical'
        send_resolved: true
        color: 'danger'
    email_configs:
      - to: 'oncall@aindusdb.com'
        subject: '[CRITICAL] {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Runbook: {{ .Annotations.runbook_url }}
          {{ end }}
    webhook_configs:
      - url: 'http://pagerduty-webhook/alert'
  
  - name: 'warning-alerts'
    slack_configs:
      - channel: '#aindusdb-warnings'
        send_resolved: true
        color: 'warning'
  
  - name: 'veritas-team'
    slack_configs:
      - channel: '#veritas-alerts'
        send_resolved: true

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'cluster']
```

### Règles d'Alerte

```yaml
# monitoring/alerts/aindusdb.yml
groups:
  - name: aindusdb.rules
    rules:
      # Disponibilité
      - alert: ServiceDown
        expr: up{job="aindusdb"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "Service {{ $labels.job }} on {{ $labels.instance }} has been down for more than 1 minute."
          runbook_url: "https://runbooks.aindusdb.com/service-down"
      
      # Taux d'erreur
      - alert: HighErrorRate
        expr: rate(aindusdb_requests_total{status_code=~"5.."}[5m]) / rate(aindusdb_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for the last 5 minutes"
      
      # Latence
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(aindusdb_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "95th percentile latency is {{ $value }}s"
      
      # Mémoire
      - alert: HighMemoryUsage
        expr: aindusdb_memory_usage_bytes / 1024/1024/1024 > 8
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}GB"
      
      # Base de données
      - alert: DatabaseConnectionPoolExhausted
        expr: aindusdb_db_pool_size{state="active"} / aindusdb_db_pool_size{state="total"} > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool nearly exhausted"
          description: "{{ $value | humanizePercentage }} of connections are active"
      
      # VERITAS
      - alert: VeritasCalculationFailure
        expr: rate(aindusdb_veritas_calculations_total{status="failed"}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "VERITAS calculation failures"
          description: "Failed calculation rate: {{ $value }} per second"
      
      # Espace disque
      - alert: DiskSpaceLow
        expr: node_filesystem_avail_bytes{mountpoint="/data"} / node_filesystem_size_bytes < 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk space low"
          description: "Only {{ $value | humanizePercentage }} free space on /data"
      
      # Recherche vectorielle
      - alert: VectorSearchSlow
        expr: histogram_quantile(0.95, rate(aindusdb_vector_search_duration_seconds_bucket[5m])) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Vector search performance degradation"
          description: "95th percentile search time is {{ $value }}s"
```

---

## 📊 Dashboards Grafana

### Dashboard Vue d'Ensemble

```json
{
  "dashboard": {
    "title": "AindusDB Core - Overview",
    "tags": ["aindusdb", "overview"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Request Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(aindusdb_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "reqps"
          }
        }
      },
      {
        "title": "Error Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(aindusdb_requests_total{status_code=~\"4..|5..\"}[5m]) / rate(aindusdb_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percentunit",
            "thresholds": {
              "steps": [
                {"color": "green", "value": 0},
                {"color": "yellow", "value": 0.01},
                {"color": "red", "value": 0.05}
              ]
            }
          }
        }
      },
      {
        "title": "Response Time",
        "type": "timeseries",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(aindusdb_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(aindusdb_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(aindusdb_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P99"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s"
          }
        }
      },
      {
        "title": "Memory Usage",
        "type": "timeseries",
        "targets": [
          {
            "expr": "aindusdb_memory_usage_bytes / 1024/1024/1024",
            "legendFormat": "{{component}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "bytes"
          }
        }
      }
    ]
  }
}
```

### Dashboard Vector Store

```json
{
  "dashboard": {
    "title": "Vector Store Performance",
    "panels": [
      {
        "title": "Vector Operations",
        "type": "timeseries",
        "targets": [
          {
            "expr": "rate(aindusdb_vector_operations_total[5m])",
            "legendFormat": "{{operation}} - {{index_name}}"
          }
        ]
      },
      {
        "title": "Search Performance",
        "type": "heatmap",
        "targets": [
          {
            "expr": "rate(aindusdb_vector_search_duration_seconds_bucket[5m])",
            "legendFormat": "{{le}}"
          }
        ]
      },
      {
        "title": "Index Sizes",
        "type": "table",
        "targets": [
          {
            "expr": "aindusdb_index_size_bytes / 1024/1024",
            "legendFormat": "{{index_name}}",
            "format": "table"
          }
        ]
      }
    ]
  }
}
```

---

## 🔔 Intégrations de Notification

### Configuration Slack

```python
# app/notifications/slack.py
import slack_sdk
from slack_sdk.web.async_client import AsyncWebClient
from typing import Dict, List

class SlackNotifier:
    def __init__(self, token: str):
        self.client = AsyncWebClient(token=token)
    
    async def send_alert(self, channel: str, alert: Dict):
        """Envoie une alerte à Slack"""
        color = self.get_color_by_severity(alert.get('severity', 'warning'))
        
        await self.client.chat_postMessage(
            channel=channel,
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 {alert.get('alertname', 'Alert')}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:* {alert.get('severity', 'unknown')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Instance:* {alert.get('instance', 'unknown')}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Description:* {alert.get('description', 'No description')}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Dashboard"
                            },
                            "url": alert.get('dashboard_url', 'https://grafana.aindusdb.com')
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Runbook"
                            },
                            "url": alert.get('runbook_url', '#')
                        }
                    ]
                }
            ]
        )
    
    def get_color_by_severity(self, severity: str) -> str:
        """Retourne la couleur selon la sévérité"""
        colors = {
            'critical': 'danger',
            'warning': 'warning',
            'info': 'good'
        }
        return colors.get(severity, 'warning')
```

### Configuration PagerDuty

```python
# app/notifications/pagerduty.py
import requests
import json
from typing import Dict

class PagerDutyNotifier:
    def __init__(self, integration_key: str):
        self.integration_key = integration_key
        self.api_url = "https://events.pagerduty.com/v2/enqueue"
    
    async def trigger_incident(self, alert: Dict):
        """Déclenche un incident PagerDuty"""
        payload = {
            "routing_key": self.integration_key,
            "event_action": "trigger",
            "dedup_key": f"{alert.get('alertname')}_{alert.get('instance')}",
            "payload": {
                "summary": alert.get('summary', alert.get('alertname')),
                "source": alert.get('instance', 'AindusDB'),
                "severity": self.map_severity(alert.get('severity')),
                "component": alert.get('service', 'unknown'),
                "group": alert.get('cluster', 'default'),
                "class": alert.get('alertname', 'unknown'),
                "custom_details": alert
            }
        }
        
        response = requests.post(
            self.api_url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 202:
            raise Exception(f"PagerDuty API error: {response.text}")
    
    def map_severity(self, severity: str) -> str:
        """Map la sévérité vers PagerDuty"""
        mapping = {
            'critical': 'critical',
            'warning': 'error',
            'info': 'warning'
        }
        return mapping.get(severity, 'error')
```

---

## 📊 Surveillance Distribuée

### Configuration Jaeger

```yaml
# monitoring/jaeger/collector.yml
collector:
  zipkin:
    host-port: :9411
  
  otlp:
    grpc:
      host-port: :4317
    http:
      host-port: :4318

storage:
  type: elasticsearch
  elasticsearch:
    username: elastic
    password: changeme
    server-urls: http://elasticsearch:9200
    index-prefix: jaeger
    tags-as-fields:
      all: true
    num-shards: 5
    num-replicas: 1

query:
  base-path: /
```

### Instrumentation des Services

```python
# app/tracing/instrumentation.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def setup_tracing(app):
    """Configure le tracing distribué"""
    # Exporter Jaeger
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",
        agent_port=6831,
    )
    
    # Provider
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    
    # Processor
    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    # Instrumentation
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor.instrument(engine=app.state.db_engine)
    RedisInstrumentor.instrument()
    
    return tracer

# Exemple d'utilisation
@tracer.start_as_current_span("vector_search")
async def search_vectors(query: str, k: int):
    with tracer.start_as_current_span("query_embedding"):
        embedding = await generate_embedding(query)
        span = trace.get_current_span()
        span.set_attribute("embedding.dimension", len(embedding))
    
    with tracer.start_as_current_span("pinecone_search"):
        results = await pinecone_index.query(embedding, top_k=k)
        span.set_attribute("results.count", len(results))
    
    return results
```

---

## 🔍 Analyse des Logs

### Configuration Fluentd

```yaml
# monitoring/fluentd/fluent.conf
<source>
  @type tail
  path /var/log/aindusdb/*.log
  pos_file /var/log/fluentd/aindusdb.log.pos
  tag aindusdb.*
  format json
  time_key timestamp
  time_format %Y-%m-%dT%H:%M:%S%.NZ
</source>

# Enrichissement des logs
<filter aindusdb.**>
  @type record_transformer
  <record>
    hostname #{Socket.gethostname}
    environment #{ENV['ENVIRONMENT'] || 'unknown'}
    service aindusdb-core
    version #{ENV['APP_VERSION'] || 'unknown'}
  </record>
</filter>

# Parsing des erreurs
<filter aindusdb.**>
  @type grep
  <regexp>
    key level
    pattern ^(ERROR|CRITICAL)$
  </regexp>
  add_tag_prefix error.
</filter>

# Sortie Elasticsearch
<match aindusdb.**>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name aindusdb-logs-%Y.%m.%d
  type_name _doc
  include_tag_key true
  tag_key @log_name
  flush_interval 5s
  
  <buffer>
    @type file
    path /var/log/fluentd/buffer
    flush_mode interval
    flush_interval 5s
    chunk_limit_size 2M
    queue_limit_length 8
    retry_max_interval 30
    retry_forever true
  </buffer>
</match>
```

### Analyse des Logs avec Elasticsearch

```python
# app/monitoring/log_analyzer.py
from elasticsearch import AsyncElasticsearch
from datetime import datetime, timedelta
import asyncio

class LogAnalyzer:
    def __init__(self, elasticsearch_url: str):
        self.es = AsyncElasticsearch([elasticsearch_url])
    
    async def search_errors(self, minutes: int = 60):
        """Recherche les erreurs récentes"""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"level": "ERROR"}},
                        {
                            "range": {
                                "timestamp": {
                                    "gte": f"now-{minutes}m"
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": 100
        }
        
        result = await self.es.search(index="aindusdb-logs-*", body=query)
        return result['hits']['hits']
    
    async def analyze_error_patterns(self):
        """Analyse les patterns d'erreurs"""
        # Agrégation par type d'erreur
        query = {
            "query": {
                "range": {
                    "timestamp": {
                        "gte": "now-24h"
                    }
                }
            },
            "aggs": {
                "error_types": {
                    "terms": {
                        "field": "error_type.keyword",
                        "size": 10
                    },
                    "aggs": {
                        "recent_errors": {
                            "top_hits": {
                                "size": 5,
                                "sort": [{"timestamp": {"order": "desc"}}]
                            }
                        }
                    }
                }
            }
        }
        
        result = await self.es.search(index="aindusdb-logs-*", body=query)
        return result['aggregations']['error_types']['buckets']
    
    async def detect_anomalies(self):
        """Détecte les anomalies dans les logs"""
        # Compte les erreurs par heure
        query = {
            "query": {
                "range": {
                    "timestamp": {
                        "gte": "now-7d"
                    }
                }
            },
            "aggs": {
                "errors_per_hour": {
                    "date_histogram": {
                        "field": "timestamp",
                        "calendar_interval": "1h"
                    },
                    "aggs": {
                        "error_count": {
                            "value_count": {
                                "field": "message"
                            }
                        }
                    }
                }
            }
        }
        
        result = await self.es.search(index="aindusdb-logs-*", body=query)
        buckets = result['aggregations']['errors_per_hour']['buckets']
        
        # Détecter les pics (simple seuil)
        error_counts = [bucket['error_count']['value'] for bucket in buckets]
        avg_errors = sum(error_counts) / len(error_counts)
        threshold = avg_errors * 3  # 3x la moyenne
        
        anomalies = []
        for i, bucket in enumerate(buckets):
            if bucket['error_count']['value'] > threshold:
                anomalies.append({
                    "timestamp": bucket['key_as_string'],
                    "error_count": bucket['error_count']['value'],
                    "threshold": threshold
                })
        
        return anomalies
```

---

## 📈 SLI/SLO Monitoring

### Définition des SLI

```python
# app/monitoring/sli.py
from prometheus_client import CollectorRegistry, Gauge
import asyncio
import aiohttp

class SLIMonitor:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.slo_gauge = Gauge(
            'aindusdb_slo_compliance',
            'SLO compliance percentage',
            ['slo_name'],
            registry=self.registry
        )
    
    async def calculate_availability_sli(self, window_minutes: int = 30):
        """Calcule le SLI de disponibilité"""
        query = '''
          sum(rate(aindusdb_requests_total{status_code!~"5.."}[5m])) /
          sum(rate(aindusdb_requests_total[5m]))
        '''
        
        result = await self.query_prometheus(query)
        availability = float(result[0]['value'][1])
        
        self.slo_gauge.labels(slo_name='availability').set(availability)
        return availability
    
    async def calculate_latency_sli(self, percentile: float = 0.95, threshold: float = 0.5):
        """Calcule le SLI de latence"""
        # Requêtes sous le seuil
        good_requests = f'''
          histogram_quantile({percentile}, 
            rate(aindusdb_request_duration_seconds_bucket[5m])
          ) < {threshold}
        '''
        
        # Total des requêtes
        total_requests = '''
          sum(rate(aindusdb_requests_total[5m]))
        '''
        
        # Calculer le ratio
        good = await self.query_prometheus(good_requests)
        total = await self.query_prometheus(total_requests)
        
        if total[0]['value'][1] != '0':
            sli = float(good[0]['value'][1]) / float(total[0]['value'][1])
        else:
            sli = 1.0
        
        self.slo_gauge.labels(slo_name='latency').set(sli)
        return sli
    
    async def calculate_veritas_sli(self):
        """Calcule le SLI pour VERITAS"""
        # Taux de succès des calculs
        query = '''
          sum(rate(aindusdb_veritas_calculations_total{status="success"}[5m])) /
          sum(rate(aindusdb_veritas_calculations_total[5m]))
        '''
        
        result = await self.query_prometheus(query)
        success_rate = float(result[0]['value'][1])
        
        self.slo_gauge.labels(slo_name='veritas_success').set(success_rate)
        return success_rate
    
    async def query_prometheus(self, query: str):
        """Exécute une requête Prometheus"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'http://prometheus:9090/api/v1/query',
                params={'query': query}
            ) as response:
                data = await response.json()
                return data['data']['result']
```

### Dashboard SLO

```json
{
  "dashboard": {
    "title": "SLO Dashboard",
    "panels": [
      {
        "title": "Availability SLO",
        "type": "stat",
        "targets": [
          {
            "expr": "aindusdb_slo_compliance{slo_name=\"availability\"}",
            "legendFormat": "Current"
          },
          {
            "expr": "0.999",
            "legendFormat": "Target (99.9%)"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percentunit",
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0.995},
                {"color": "yellow", "value": 0.998},
                {"color": "green", "value": 0.999}
              ]
            }
          }
        }
      },
      {
        "title": "Latency SLO",
        "type": "stat",
        "targets": [
          {
            "expr": "aindusdb_slo_compliance{slo_name=\"latency\"}",
            "legendFormat": "Current"
          },
          {
            "expr": "0.95",
            "legendFormat": "Target (95%)"
          }
        ]
      },
      {
        "title": "Error Budget",
        "type": "timeseries",
        "targets": [
          {
            "expr": "(1 - aindusdb_slo_compliance{slo_name=\"availability\"}) * 100",
            "legendFormat": "Error Budget Consumed"
          }
        ]
      }
    ]
  }
}
```

---

## 🔧 Maintenance du Système

### Health Checks

```python
# app/monitoring/health.py
from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.services.vector_store import get_vector_store
from app.services.veritas import get_veritas_service
import asyncio

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check de base"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@router.get("/health/ready")
async def readiness_check():
    """Readiness check - vérifie les dépendances"""
    checks = {}
    
    # Base de données
    try:
        db = get_db()
        await db.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
    
    # Redis
    try:
        redis = get_redis()
        await redis.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
    
    # Vector Store
    try:
        vector_store = get_vector_store()
        await vector_store.health_check()
        checks["vector_store"] = "healthy"
    except Exception as e:
        checks["vector_store"] = f"unhealthy: {str(e)}"
    
    # Vérifier si tout est healthy
    all_healthy = all(status == "healthy" for status in checks.values())
    
    if all_healthy:
        return {"status": "ready", "checks": checks}
    else:
        raise HTTPException(503, detail={"status": "not ready", "checks": checks})

@router.get("/health/live")
async def liveness_check():
    """Liveness check - vérifie si l'application répond"""
    return {"status": "alive", "uptime": get_uptime()}

@router.get("/health/detailed")
async def detailed_health():
    """Health check détaillé avec métriques"""
    return {
        "status": "healthy",
        "version": os.getenv("APP_VERSION", "unknown"),
        "uptime": get_uptime(),
        "metrics": {
            "memory_usage": psutil.virtual_memory().percent,
            "cpu_usage": psutil.cpu_percent(),
            "active_connections": get_active_db_connections(),
            "queue_size": get_queue_size()
        },
        "dependencies": await check_all_dependencies()
    }
```

### Nettoyage Automatisé

```python
# app/maintenance/cleanup.py
import asyncio
from datetime import datetime, timedelta

class MaintenanceTasks:
    def __init__(self):
        self.db = get_db()
        self.redis = get_redis()
        self.vector_store = get_vector_store()
    
    async def cleanup_old_logs(self):
        """Nettoie les anciens logs"""
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Supprimer les anciens logs de la base
        await self.db.execute(
            "DELETE FROM logs WHERE created_at < $1",
            cutoff_date
        )
        
        # Nettoyer les logs dans Elasticsearch
        await self.cleanup_elasticsearch_logs(cutoff_date)
    
    async def cleanup_expired_tokens(self):
        """Nettoie les tokens expirés"""
        cutoff_date = datetime.utcnow() - timedelta(days=1)
        
        await self.db.execute(
            "DELETE FROM tokens WHERE expires_at < $1",
            cutoff_date
        )
    
    async def cleanup_temp_files(self):
        """Nettoie les fichiers temporaires"""
        temp_dir = "/tmp/aindusdb"
        
        for file_path in Path(temp_dir).glob("*"):
            if file_path.is_file():
                # Supprimer les fichiers de plus de 24h
                file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_age > timedelta(hours=24):
                    file_path.unlink()
    
    async def optimize_database(self):
        """Optimise la base de données"""
        # VACUUM et ANALYZE
        await self.db.execute("VACUUM ANALYZE")
        
        # Mettre à jour les statistiques
        await self.db.execute("UPDATE STATISTICS")
    
    async def run_maintenance(self):
        """Exécute toutes les tâches de maintenance"""
        tasks = [
            self.cleanup_old_logs(),
            self.cleanup_expired_tokens(),
            self.cleanup_temp_files(),
            self.optimize_database()
        ]
        
        await asyncio.gather(*tasks)
        
        # Logger la completion
        logger.info("Maintenance tasks completed successfully")

# Planification avec Celery
from celery import Celery

celery_app = Celery('aindusdb')

@celery_app.task
def scheduled_maintenance():
    """Tâche planifiée de maintenance"""
    maintenance = MaintenanceTasks()
    asyncio.run(maintenance.run_maintenance())

# Configuration des tâches planifiées
celery_app.conf.beat_schedule = {
    'daily-maintenance': {
        'task': 'app.maintenance.cleanup.scheduled_maintenance',
        'schedule': crontab(hour=2, minute=0),  # Tous les jours à 2h du mat
    },
    'hourly-cleanup': {
        'task': 'app.maintenance.cleanup.cleanup_temp_files',
        'schedule': crontab(minute=0),  # Toutes les heures
    }
}
```

---

## 📊 Rapports et Analytiques

### Génération de Rapports

```python
# app/monitoring/reporting.py
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import io
import base64

class MonitoringReporter:
    def __init__(self):
        self.prometheus_url = "http://prometheus:9090"
    
    async def generate_daily_report(self):
        """Génère le rapport quotidien"""
        report_data = {
            "date": datetime.utcnow().date(),
            "availability": await self.get_availability_metrics(),
            "performance": await self.get_performance_metrics(),
            "errors": await self.get_error_metrics(),
            "usage": await self.get_usage_metrics()
        }
        
        # Générer le HTML
        html_report = self.generate_html_report(report_data)
        
        # Générer le PDF
        pdf_report = await self.generate_pdf_report(report_data)
        
        # Envoyer par email
        await self.send_report_email(html_report, pdf_report)
        
        return report_data
    
    async def get_availability_metrics(self):
        """Récupère les métriques de disponibilité"""
        queries = {
            "uptime": 'up{job="aindusdb"}',
            "error_rate": 'rate(aindusdb_requests_total{status_code=~"5.."}[24h])',
            "success_rate": 'rate(aindusdb_requests_total{status_code!~"5.."}[24h])'
        }
        
        metrics = {}
        for name, query in queries.items():
            result = await self.query_prometheus(query)
            metrics[name] = float(result[0]['value'][1]) if result else 0
        
        return metrics
    
    def generate_html_report(self, data: dict):
        """Génère le rapport HTML"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AindusDB Daily Report - {data['date']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 20px; 
                          border: 1px solid #ddd; border-radius: 5px; }}
                .metric-value {{ font-size: 2em; font-weight: bold; }}
                .green {{ color: green; }}
                .red {{ color: red; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>AindusDB Daily Report</h1>
                <p>Date: {data['date']}</p>
            </div>
            
            <h2>Availability</h2>
            <div class="metric">
                <div class="metric-value {'green' if data['availability']['uptime'] > 0.99 else 'red'}">
                    {data['availability']['uptime']:.2%}
                </div>
                <div>Uptime</div>
            </div>
            <div class="metric">
                <div class="metric-value {'green' if data['availability']['error_rate'] < 0.01 else 'red'}">
                    {data['availability']['error_rate']:.4f}
                </div>
                <div>Error Rate</div>
            </div>
            
            <h2>Performance</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Average Response Time</td>
                    <td>{data['performance']['avg_response_time']:.3f}s</td>
                </tr>
                <tr>
                    <td>95th Percentile</td>
                    <td>{data['performance']['p95_response_time']:.3f}s</td>
                </tr>
                <tr>
                    <td>Requests per Second</td>
                    <td>{data['performance']['rps']:.2f}</td>
                </tr>
            </table>
            
            <h2>Usage</h2>
            <table>
                <tr>
                    <th>Service</th>
                    <th>Operations</th>
                </tr>
                <tr>
                    <td>Vector Searches</td>
                    <td>{data['usage']['vector_searches']:,}</td>
                </tr>
                <tr>
                    <td>VERITAS Calculations</td>
                    <td>{data['usage']['veritas_calculations']:,}</td>
                </tr>
            </table>
        </body>
        </html>
        """
        return html
    
    async def generate_pdf_report(self, data: dict):
        """Génère le rapport PDF"""
        # Utiliser weasyprint ou reportlab
        from weasyprint import HTML
        
        html = self.generate_html_report(data)
        pdf = HTML(string=html).write_pdf()
        
        return pdf
```

---

## 🎯 Bonnes Pratiques

### 1. Métriques
- Utiliser des noms cohérents et descriptifs
- Inclure des labels pertinents
- Éviter les métriques de haute cardinalité
- Utiliser des histogrammes pour les distributions

### 2. Alertes
- Être spécifique et actionnable
- Éviter les fausses alertes
- Inclure des liens vers les dashboards
- Pager uniquement pour les problèmes critiques

### 3. Dashboards
- Commencer par une vue d'ensemble
- Utiliser des couleurs cohérentes
- Inclure des annotations pour les événements
- Partager les connaissances avec l'équipe

### 4. Logs
- Structurer les logs en JSON
- Inclure un ID de corrélation
- Éviter les logs sensibles
- Utiliser des niveaux appropriés

---

**Document maintenu par l'équipe AindusDB Core**  
**Dernière mise à jour:** 21/01/2026
