# 🚀 GETTING STARTED - AINDUSDB CORE

**Version** : 1.0.0  
**Niveau** : Développeur Enterprise  
**Date** : 21 janvier 2026  

---

## 🎯 **INTRODUCTION**

Guide complet pour démarrer rapidement avec AindusDB Core - base de données vectorielle de niveau FAANG avec architecture enterprise.

### **🏆 PRÉREQUIS**
- **Python 3.11+** : Runtime principal
- **PostgreSQL 14+** : Base de données avec pgvector
- **Redis 7+** : Cache (optionnel mais recommandé)
- **Docker & Docker Compose** : Déploiement conteneurisé
- **Git** : Gestion version

---

## ⚡ **INSTALLATION RAPIDE (5 minutes)**

### **🐳 Option 1 : Docker Compose (Recommandé)**
```bash
# 1. Clone repository
git clone https://github.com/aindusdb/aindusdb_core.git
cd aindusdb_core

# 2. Configuration environnement
cp .env.template .env
# Éditer .env avec vos configurations

# 3. Démarrage complet
docker-compose up -d

# 4. Vérification installation
curl http://localhost:8000/health
```

### **💻 Option 2 : Installation Manuelle**
```bash
# 1. Installation Python
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Installation dépendances
pip install -r requirements.txt

# 3. Configuration base de données
# PostgreSQL avec pgvector installé
createdb aindusdb_core

# 4. Migration base de données
alembic upgrade head

# 5. Démarrage API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🔧 **CONFIGURATION ENVIRONNEMENT**

### **📋 Variables Essentielles**
```bash
# .env - Configuration minimale
# =================================
DATABASE_URL=postgresql://aindusdb:password@localhost:5432/aindusdb_core
JWT_SECRET_KEY=votre_clé_secrète_256_bits_minimum
REDIS_URL=redis://localhost:6379/0

# Configuration API
API_HOST=0.0.0.0
API_PORT=8000
API_TITLE=AindusDB Core API

# Sécurité
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Performance
MAX_BATCH_SIZE=100
SEARCH_RESULTS_LIMIT=1000
CACHE_TTL=3600

# Monitoring
METRICS_ENABLED=true
LOG_LEVEL=INFO
```

### **🔐 Génération Secrets Sécurisés**
```bash
# Génération JWT Secret (256 bits)
openssl rand -hex 32

# Génération mot de passe PostgreSQL
openssl rand -base64 32

# Génération clé Redis (optionnel)
openssl rand -hex 16
```

---

## 🌐 **PREMIERS PAS**

### **📚 Documentation API**
```bash
# Swagger UI (interactif)
http://localhost:8000/docs

# ReDoc (documentation)
http://localhost:8000/redoc

# OpenAPI JSON
http://localhost:8000/openapi.json
```

### **🏥 Health Checks**
```bash
# Santé système complète
curl http://localhost:8000/health

# Readiness (Kubernetes)
curl http://localhost:8000/ready

# Liveness (Kubernetes)
curl http://localhost:8000/live

# Métriques Prometheus
curl http://localhost:8000/metrics
```

### **🔑 Authentification**
```bash
# Création utilisateur admin
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@aindusdb.io",
    "password": "SecurePassword123!",
    "role": "admin"
  }'

# Login et récupération token
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@aindusdb.io",
    "password": "SecurePassword123!"
  }'
```

---

## 📊 **OPÉRATIONS VECTEURS**

### **➕ Création Vecteur**
```python
import requests

# Créer vecteur avec embedding
vector_data = {
    "content": "Ceci est un document test",
    "metadata": {
        "source": "test",
        "category": "example",
        "language": "fr"
    },
    "content_type": "text"
}

headers = {
    "Authorization": "Bearer YOUR_JWT_TOKEN",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8000/vectors",
    json=vector_data,
    headers=headers
)

vector = response.json()
print(f"Vecteur créé: {vector['id']}")
```

### **🔍 Recherche Sémantique**
```python
# Recherche par similarité
search_query = {
    "query": "documents techniques",
    "limit": 10,
    "threshold": 0.7,
    "filters": {
        "content_type": "text"
    }
}

response = requests.post(
    "http://localhost:8000/vectors/search",
    json=search_query,
    headers=headers
}

results = response.json()
for result in results['results']:
    print(f"Score: {result['score']:.4f} - {result['content'][:100]}...")
```

### **📈 Recherche Hybride**
```python
# Combinaison sémantique + mots-clés
hybrid_search = {
    "query": "base de données vectorielle",
    "keywords": ["vector", "database", "embedding"],
    "limit": 20,
    "weights": {
        "semantic": 0.7,
        "keywords": 0.3
    }
}

response = requests.post(
    "http://localhost:8000/vectors/hybrid-search",
    json=hybrid_search,
    headers=headers
)
```

---

## 🧪 **VÉRITAS PROTOCOL**

### **🔍 Calculs Vérifiables**
```python
# Calcul mathématique avec preuve VERITAS
calculation_request = {
    "query": "Calcule l'aire d'un cercle de rayon 5",
    "enable_proofs": True,
    "verification_level": "high"
}

response = requests.post(
    "http://localhost:8000/veritas/calculate",
    json=calculation_request,
    headers=headers
)

result = response.json()
print(f"Résultat: {result['answer']}")
print(f"Preuve VERITAS: {result['veritas_proof']['proof_id']}")

# Vérification preuve
proof_id = result['veritas_proof']['proof_id']
verification = requests.get(
    f"http://localhost:8000/veritas/verify/{proof_id}",
    headers=headers
)

print(f"Preuve valide: {verification.json()['is_valid']}")
```

### **📋 Audit Trail**
```python
# Historique complet des calculs
audit_response = requests.get(
    "http://localhost:8000/veritas/audit",
    headers=headers,
    params={"limit": 50}
)

for entry in audit_response.json()['calculations']:
    print(f"{entry['timestamp']}: {entry['query']} → {entry['result']}")
```

---

## 🏗️ **ARCHITECTURE TECHNIQUE**

### **📋 Structure Projet Complète**
```
aindusdb_core/
├── app/                          # Application principale
│   ├── core/                     # Services centraux (13 fichiers)
│   │   ├── config.py            # Configuration Pydantic
│   │   ├── database.py          # Gestion PostgreSQL + pool
│   │   ├── security.py          # Authentification JWT/MFA
│   │   ├── security_config.py   # Configuration sécurité
│   │   ├── metrics.py           # Métriques Prometheus
│   │   ├── logging.py           # Logging structuré
│   │   ├── secure_logging.py    # Logging sécurisé filtré
│   │   ├── cache.py             # Cache multi-niveau
│   │   ├── indexing.py          # Indexation vectorielle
│   │   ├── safe_math.py         # Calculs mathématiques sécurisés
│   │   ├── cqrs/                # Pattern CQRS (7 fichiers)
│   │   │   ├── command_bus.py   # Bus de commandes
│   │   │   ├── commands.py      # Définition commandes
│   │   │   ├── query_bus.py     # Bus de queries
│   │   │   ├── queries.py       # Définition queries
│   │   │   ├── events.py        # Event Sourcing
│   │   │   └── cqrs_coordinator.py  # Orchestration CQRS
│   │   └── resilience/          # Patterns résilience (4 fichiers)
│   │       ├── circuit_breaker.py   # Circuit Breaker pattern
│   │       ├── health_monitor.py    # Surveillance santé
│   │       └── resilience_coordinator.py  # Coordination résilience
│   │
│   ├── models/                   # Modèles Pydantic (7 fichiers)
│   │   ├── vector.py            # Modèles vecteurs
│   │   ├── auth.py              # Modèles authentification/user
│   │   ├── veritas.py           # Modèles VERITAS complets
│   │   ├── secure_veritas.py    # VERITAS sécurisé
│   │   ├── secure_schemas.py    # Schémas sécurité
│   │   └── health.py            # Modèles health checks
│   │
│   ├── services/                 # Logique métier (14 fichiers)
│   │   ├── vector_service.py    # Service vecteurs
│   │   ├── auth_service.py      # Service authentification
│   │   ├── user_service.py      # Service utilisateurs
│   │   ├── mfa_service.py       # Service MFA/2FA
│   │   ├── rbac_service.py      # Service contrôle accès
│   │   ├── audit_service.py     # Service audit & logging
│   │   ├── cache_service.py     # Service cache Redis
│   │   ├── health_service.py    # Service health checks
│   │   ├── batch_service.py     # Service opérations batch
│   │   ├── batch_operations.py  # Opérations batch optimisées
│   │   ├── typst_service.py     # Service Typst rendering
│   │   ├── ai_typst_generator.py # Génération IA Typst
│   │   ├── veritas_service.py   # Service VERITAS principal
│   │   └── veritas/             # Services VERITAS spécialisés (5 fichiers)
│   │       ├── veritas_verifier.py      # Vérification calculs
│   │       ├── veritas_generator.py     # Génération preuves
│   │       ├── veritas_proof_manager.py # Gestion preuves
│   │       └── veritas_orchestrator.py  # Orchestration VERITAS
│   │
│   ├── routers/                  # Endpoints API (7 fichiers)
│   │   ├── vectors.py           # Routes vecteurs
│   │   ├── auth.py              # Routes authentification
│   │   ├── veritas.py           # Routes VERITAS
│   │   ├── health.py            # Routes health checks
│   │   ├── security_monitoring.py # Routes monitoring sécurité
│   │   └── typst_native.py      # Routes Typst rendering
│   │
│   ├── middleware/               # Middlewares (7 fichiers)
│   │   ├── security_headers.py  # Headers sécurité OWASP
│   │   ├── security_validation.py # Validation sécurité requêtes
│   │   ├── advanced_rate_limiting.py # Rate limiting avancé
│   │   ├── auth.py              # Middleware authentification
│   │   ├── logging_middleware.py # Middleware logging
│   │   ├── metrics_middleware.py # Middleware métriques
│   │   └── veritas_middleware.py # Middleware VERITAS
│   │
│   ├── dependencies/             # Injection dépendances FastAPI
│   │   ├── __init__.py
│   │   └── database.py          # Providers database
│   │
│   └── main.py                  # Point d'entrée FastAPI
│
├── tests/                        # Tests complets
│   ├── unit/                    # Tests unitaires
│   ├── integration/             # Tests intégration
│   ├── load/                    # Tests performance
│   ├── conftest.py              # Configuration pytest
│   ├── test_security_suite.py   # Suite tests sécurité
│   ├── test_safe_math.py        # Tests calculs sécurisés
│   ├── test_rate_limiting.py    # Tests rate limiting
│   └── penetration_test_framework.py # Framework pentesting
│
├── docs/                         # Documentation
│   ├── INSTALLATION.md          # Guide installation
│   ├── CONTRIBUTING.md          # Guide contribution
│   ├── SECURITY.md              # Guide sécurité
│   ├── API_EXAMPLES.md          # Exemples API
│   └── conf.py                  # Configuration Sphinx
│
├── scripts/                      # Scripts utilitaires (26 scripts)
│   ├── setup_mfa.sh/bat         # Setup MFA
│   ├── run_security_tests.sh/bat # Tests sécurité
│   ├── vulnerability_scan.sh/bat # Scan vulnérabilités
│   └── secure_deployment.sh     # Déploiement sécurisé
│
├── migrations/                   # Migrations base de données
│   └── *.sql                    # Scripts SQL migration
│
├── monitoring/                   # Configuration monitoring
│   ├── prometheus.yml           # Configuration Prometheus
│   └── grafana.ini              # Configuration Grafana
│
├── security_reports/             # Rapports sécurité
│   └── vulnerability_scan.json  # Résultats scans
│
├── aindusdb_core_docs/           # Documentation mondiale
│   ├── 01_ARCHITECTURE/         # Architecture enterprise
│   ├── 02_SECURITY/             # Sécurité & conformité
│   ├── 03_DEPLOYMENT/           # Déploiement production
│   ├── 04_DEVELOPMENT/          # Guides développement
│   ├── 05_PERFORMANCE/          # Performance & optimisation
│   ├── 06_OPERATIONS/           # Opérations & maintenance
│   ├── 07_COMPLIANCE/           # Conformité internationale
│   └── 08_REFERENCE/            # Référence technique
│
├── .github/                      # GitHub Actions workflows
├── docker-compose.yml            # Orchestration Docker
├── Dockerfile                    # Image Docker production
├── requirements.txt              # Dépendances Python
├── pytest.ini                    # Configuration pytest
└── README.md                     # Documentation principale
```

### **🔄 Flux Données**
```mermaid
graph TB
    A[Client Request] --> B[FastAPI Router]
    B --> C[Authentication]
    C --> D[Service Layer]
    D --> E[Business Logic]
    E --> F[PostgreSQL + pgvector]
    E --> G[Redis Cache]
    F --> H[Vector Operations]
    G --> I[Cached Results]
    H --> J[Response]
    I --> J
```

---

## 🧪 **DÉVELOPPEMENT LOCAL**

### **🔧 Setup Développement**
```bash
# Environnement virtuel
python -m venv venv
source venv/bin/activate

# Installation dépendances dev
pip install -r requirements.txt
pip install pytest pytest-asyncio black isort

# Pre-commit hooks
pre-commit install
```

### **🧪 Tests**
```bash
# Tests complets
pytest

# Tests avec coverage
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/test_vectors.py -v

# Tests async
pytest -k "async" --asyncio-mode=auto
```

### **🔍 Debug**
```python
# Debug mode
uvicorn app.main:app --reload --log-level debug

# Breakpoints Python
import pdb; pdb.set_trace()

# Logging détaillé
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📊 **MONITORING LOCAL**

### **📈 Métriques**
```bash
# Prometheus local
docker run -p 9090:9090 prom/prometheus

# Grafana local
docker run -p 3000:3000 grafana/grafana

# Accès métriques API
curl http://localhost:8000/metrics | grep http_requests
```

### **📝 Logs**
```python
# Configuration logging
import structlog

logger = structlog.get_logger()
logger.info("Processing vector", vector_id="123", operation="search")

# Logs structurés
{
  "event": "Processing vector",
  "vector_id": "123", 
  "operation": "search",
  "timestamp": "2026-01-21T12:00:00Z"
}
```

---

## 🚀 **DÉPLOIEMENT**

### **🐳 Docker Production**
```bash
# Build image optimisée
docker build -t aindusdb/core:latest .

# Run avec configuration production
docker run -d \
  --name aindusdb-prod \
  -p 8000:8000 \
  -e DATABASE_URL=$DATABASE_URL \
  -e JWT_SECRET_KEY=$JWT_SECRET_KEY \
  aindusdb/core:latest
```

### **☸️ Kubernetes**
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aindusdb-core
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aindusdb-core
  template:
    spec:
      containers:
      - name: aindusdb
        image: aindusdb/core:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: aindusdb-secrets
              key: database-url
```

---

## 🔧 **CONFIGURATION AVANCÉE**

### **⚡ Performance**
```python
# Configuration PostgreSQL optimisée
DATABASE_URL = "postgresql://user:pass@host:5432/db?pool_size=20&max_overflow=30"

# Configuration Redis
REDIS_URL = "redis://localhost:6379/0?max_connections=100"

# Configuration API
UVICORN_WORKERS = 4
UVICORN_WORKER_CONNECTIONS = 1000
```

### **🛡️ Sécurité**
```python
# Headers sécurité
MIDDLEWARE = [
    SecurityHeadersMiddleware,
    CORSMiddleware,
    RateLimitMiddleware,
    AuditMiddleware
]

# Rate limiting
RATE_LIMIT = "100/minute"
RATE_LIMIT_BURST = 200
```

---

## 📚 **RESSOURCES**

### **📖 Documentation**
- **API Reference** : `/docs` (Swagger UI)
- **Architecture Guide** : `docs/ARCHITECTURE.md`
- **Security Guide** : `docs/SECURITY.md`
- **Deployment Guide** : `docs/DEPLOYMENT.md`

### **🧪 Exemples Code**
- **Basic Usage** : `examples/basic_usage.py`
- **Advanced Search** : `examples/advanced_search.py`
- **VERITAS Protocol** : `examples/veritas_examples.py`
- **Batch Operations** : `examples/batch_operations.py`

### **🔧 Outils**
- **CLI Tool** : `aindusdb-cli`
- **Python SDK** : `aindusdb-sdk`
- **Migration Tool** : `aindusdb-migrate`
- **Performance Monitor** : `aindusdb-monitor`

---

## 🆘 **SUPPORT**

### **🐛 Problèmes Communs**
```bash
# Problème connexion base
psql $DATABASE_URL -c "SELECT version();"

# Problème Redis
redis-cli ping

# Problème permissions
chmod +x scripts/*.sh

# Problème dépendances
pip install --upgrade -r requirements.txt
```

### **💬 Communauté**
- **GitHub Issues** : https://github.com/aindusdb/aindusdb_core/issues
- **Discord** : https://discord.gg/aindusdb
- **Stack Overflow** : `aindusdb` tag
- **Documentation** : https://docs.aindusdb.io

---

## 🏆 **PROCHAINES ÉTAPES**

### **📯 Apprentissage**
1. **Compléter tutoriels** : Exemples et guides
2. **Explorer API** : Documentation interactive
3. **Configurer monitoring** : Prometheus + Grafana
4. **Déployer production** : Docker/Kubernetes

### **🚀 Développement**
1. **Fork repository** : Contribuer au projet
2. **Créer features** : Extensions personnalisées
3. **Partager exemples** : Cas d'usage réels
4. **Rejoindre communauté** : Échanges techniques

---

## ✅ **CONCLUSION**

**AindusDB Core est prêt !** 🎉

Vous avez maintenant :
- ✅ Installation fonctionnelle
- ✅ API disponible
- ✅ Base de données configurée
- ✅ Monitoring actif
- ✅ Documentation complète

**Prochaine étape** : Explorer les fonctionnalités avancées et commencer à développer !

---

*Bienvenue dans l'écosystème AindusDB - Base de données vectorielle de niveau mondial*  

*Getting Started Guide - 21 janvier 2026*
