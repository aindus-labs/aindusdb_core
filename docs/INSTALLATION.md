# 📦 Guide d'Installation AindusDB Core

Ce guide couvre toutes les méthodes d'installation et de déploiement d'AindusDB Core.

## 📋 Prérequis

### **Système**
- **OS** : Windows 10+, Linux (Ubuntu 20.04+), macOS 12+
- **RAM** : 4GB minimum, 8GB recommandé
- **Stockage** : 10GB espace libre minimum
- **Réseau** : Accès Internet pour télécharger les images Docker

### **Logiciels requis**

#### **🐳 Docker (Méthode recommandée)**
```bash
# Vérifier installation Docker
docker --version
# → Docker version 20.10.0+

docker-compose --version  
# → docker-compose version 1.29.0+

# Test Docker
docker run hello-world
```

#### **🛠️ Installation manuelle**
```bash
# PostgreSQL 15+ avec pgvector
psql --version
# → PostgreSQL 15.0+

# Python 3.11+
python --version
# → Python 3.11.0+

# Git
git --version
# → git version 2.30.0+
```

---

## 🚀 Installation rapide (Docker)

### **Étape 1 : Clonage du projet**
```bash
# Cloner le repository
git clone https://github.com/aindus-labs/aindusdb_core.git
cd AindusDB_Core

# Vérifier les fichiers
ls -la
# → docker-compose.yml, .env.template, etc.
```

### **Étape 2 : Configuration environnement**
```bash
# Copier le template de configuration
cp .env.template .env

# Éditer la configuration (optionnel)
nano .env  # ou votre éditeur préféré
```

**Variables importantes à configurer :**
```bash
# Mot de passe PostgreSQL (IMPORTANT : changer en production)
POSTGRES_PASSWORD=aindusdb_secure_2026_change_me

# Port de l'API (par défaut 8000)
API_PORT=8000

# Niveau de logs
LOG_LEVEL=INFO
```

### **Étape 3 : Démarrage des services**
```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier le statut
docker-compose ps
```

**Sortie attendue :**
```
Name                    Command               State           Ports
------------------------------------------------------------------------
aindusdb_api_1         uvicorn app.main:app --ho...   Up      0.0.0.0:8000->8000/tcp
aindusdb_postgres_1    docker-entrypoint.sh postgres Up      0.0.0.0:5432->5432/tcp
aindusdb_redis_1       docker-entrypoint.sh redis... Up      6379/tcp
```

### **Étape 4 : Validation de l'installation**
```bash
# Test API principale
curl http://localhost:8000/
# → {"message": "AindusDB Core API - Docker Deployment", "status": "running"}

# Test santé système
curl http://localhost:8000/health
# → {"status": "healthy", "database": "connected", "pgvector": "0.5.1"}

# Test opérations vectorielles
curl -X POST http://localhost:8000/vectors/test
# → {"status": "success", "results": [...]}
```

**🎉 Installation terminée ! Votre AindusDB Core est opérationnel.**

---

## 🛠️ Installation manuelle (Développement)

### **Étape 1 : Installation PostgreSQL + pgvector**

#### **Ubuntu/Debian**
```bash
# Installation PostgreSQL 15
sudo apt update
sudo apt install postgresql-15 postgresql-client-15

# Installation build tools pour pgvector
sudo apt install build-essential postgresql-server-dev-15

# Installation pgvector
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Démarrer PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### **macOS**
```bash
# Avec Homebrew
brew install postgresql@15
brew services start postgresql@15

# Installation pgvector
brew install pgvector
```

#### **Windows**
```powershell
# Télécharger PostgreSQL depuis https://www.postgresql.org/download/windows/
# Installer manuellement

# Pour pgvector, utiliser WSL2 ou Docker (recommandé)
```

### **Étape 2 : Configuration PostgreSQL**
```bash
# Se connecter à PostgreSQL
sudo -u postgres psql

# Créer base de données et utilisateur
CREATE DATABASE aindusdb_core;
CREATE USER aindusdb WITH PASSWORD 'aindusdb_secure_2026_change_me';
GRANT ALL PRIVILEGES ON DATABASE aindusdb_core TO aindusdb;

# Installer extension pgvector
\c aindusdb_core
CREATE EXTENSION vector;

# Vérifier installation
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
# → vector | 0.5.1

\q
```

### **Étape 3 : Installation Python et dépendances**
```bash
# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows

# Installer dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Vérifier installation
python -c "import fastapi, asyncpg, pydantic; print('✅ Dépendances OK')"
```

### **Étape 4 : Configuration application**
```bash
# Copier configuration
cp .env.template .env

# Configurer URL de base de données
export DATABASE_URL="postgresql://aindusdb:aindusdb_secure_2026_change_me@localhost:5432/aindusdb_core"
# ou éditer .env
```

### **Étape 5 : Démarrage de l'application**
```bash
# Démarrer l'API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Dans un autre terminal, tester
curl http://localhost:8000/health
```

---

## 🏗️ Installation pour production

### **🐳 Docker avec optimisations production**

**Fichier `docker-compose.prod.yml` :**
```yaml
version: '3.8'
services:
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: aindusdb_core
      POSTGRES_USER: aindusdb
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgresql.prod.conf:/etc/postgresql/postgresql.conf:ro
    ports:
      - "5432:5432"
    restart: unless-stopped
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aindusdb -d aindusdb_core"]
      interval: 30s
      timeout: 10s
      retries: 3

  api:
    image: aindusdb/core:latest
    environment:
      DATABASE_URL: postgresql://aindusdb:${POSTGRES_PASSWORD}@postgres:5432/aindusdb_core
      API_WORKERS: 4
      LOG_LEVEL: INFO
      CORS_ORIGINS: "https://yourdomain.com"
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  postgres_data:
    driver: local
```

**Démarrage production :**
```bash
# Variables d'environnement sécurisées
export POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Démarrage
docker-compose -f docker-compose.prod.yml up -d

# Monitoring
docker-compose -f docker-compose.prod.yml logs -f api
```

### **☸️ Déploiement Kubernetes**

**Namespace et secrets :**
```yaml
# namespace.yml
apiVersion: v1
kind: Namespace
metadata:
  name: aindusdb

---
# secrets.yml
apiVersion: v1
kind: Secret
metadata:
  name: aindusdb-secret
  namespace: aindusdb
type: Opaque
data:
  postgres-password: <base64-encoded-password>
  database-url: <base64-encoded-database-url>
```

**Base de données :**
```yaml
# postgres.yml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: aindusdb
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: ankane/pgvector:latest
        env:
        - name: POSTGRES_DB
          value: aindusdb_core
        - name: POSTGRES_USER
          value: aindusdb
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: aindusdb-secret
              key: postgres-password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
```

**Application API :**
```yaml
# api.yml  
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aindusdb-api
  namespace: aindusdb
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aindusdb-api
  template:
    metadata:
      labels:
        app: aindusdb-api
    spec:
      containers:
      - name: api
        image: aindusdb/core:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: aindusdb-secret
              key: database-url
        - name: API_WORKERS
          value: "4"
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

**Service et Ingress :**
```yaml
# service.yml
apiVersion: v1
kind: Service
metadata:
  name: aindusdb-service
  namespace: aindusdb
spec:
  selector:
    app: aindusdb-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
# ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aindusdb-ingress
  namespace: aindusdb
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: aindusdb-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: aindusdb-service
            port:
              number: 80
```

**Déploiement K8s :**
```bash
# Appliquer les manifests
kubectl apply -f namespace.yml
kubectl apply -f secrets.yml
kubectl apply -f postgres.yml
kubectl apply -f api.yml
kubectl apply -f service.yml
kubectl apply -f ingress.yml

# Vérifier le déploiement
kubectl get pods -n aindusdb
kubectl logs -n aindusdb deployment/aindusdb-api
```

---

## 🔧 Configuration avancée

### **Optimisation PostgreSQL**

**Fichier `postgresql.prod.conf` :**
```ini
# Connexions
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB

# Performance
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB

# Logging
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on

# Extensions
shared_preload_libraries = 'vector'

# Vector-specific
max_parallel_workers_per_gather = 4
```

### **Configuration SSL/TLS**

**Génération certificats :**
```bash
# Certificats auto-signés (développement uniquement)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Configuration nginx reverse proxy
upstream aindusdb_api {
    server localhost:8000;
}

server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://aindusdb_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### **Monitoring avec Prometheus**

**Configuration `docker-compose.monitoring.yml` :**
```yaml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  grafana_data:
```

---

## 🚨 Troubleshooting

### **Problèmes courants Docker**

#### **Port déjà utilisé**
```bash
# Identifier le processus
netstat -tulpn | grep :8000
# ou
lsof -i :8000

# Arrêter le service conflictuel
sudo systemctl stop <service-name>
# ou
sudo kill <PID>
```

#### **Problème de permissions**
```bash
# Linux : ajouter utilisateur au groupe docker
sudo usermod -aG docker $USER
# Redémarrer la session

# Permissions volumes Docker
sudo chown -R $USER:$USER /var/lib/docker/volumes/
```

#### **Extension pgvector manquante**
```bash
# Se connecter au container PostgreSQL
docker exec -it aindusdb_postgres_1 psql -U aindusdb -d aindusdb_core

# Installer extension
CREATE EXTENSION IF NOT EXISTS vector;

# Vérifier
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

### **Problèmes installation manuelle**

#### **Erreur compilation pgvector**
```bash
# Ubuntu : installer build tools manquants
sudo apt install build-essential postgresql-server-dev-all

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install postgresql-devel
```

#### **Erreur connexion PostgreSQL**
```bash
# Vérifier service PostgreSQL
sudo systemctl status postgresql

# Vérifier configuration
sudo -u postgres psql -c "SHOW config_file;"

# Tester connexion
psql -h localhost -U aindusdb -d aindusdb_core -c "SELECT version();"
```

### **Tests de validation**

**Script de validation complète :**
```bash
#!/bin/bash
# validate_installation.sh

echo "🔍 Validation installation AindusDB Core..."

# Test 1: API accessible
if curl -f -s http://localhost:8000/ > /dev/null; then
    echo "✅ API accessible"
else
    echo "❌ API non accessible"
    exit 1
fi

# Test 2: Base de données
if curl -f -s http://localhost:8000/health | grep -q "healthy"; then
    echo "✅ Base de données connectée"
else
    echo "❌ Problème base de données"
    exit 1
fi

# Test 3: Opérations vectorielles
if curl -f -s -X POST http://localhost:8000/vectors/test | grep -q "success"; then
    echo "✅ Opérations vectorielles fonctionnelles"
else
    echo "❌ Problème opérations vectorielles"
    exit 1
fi

echo "🎉 Installation validée avec succès!"
```

```bash
# Rendre exécutable et lancer
chmod +x validate_installation.sh
./validate_installation.sh
```

---

## 📚 Ressources supplémentaires

- **Documentation API** : http://localhost:8000/docs (Swagger)
- **Guide développeur** : [CONTRIBUTING.md](./CONTRIBUTING.md)
- **Configuration** : [Configuration avancée](../README.md#configuration)
- **Support** : [GitHub Issues](https://github.com/aindus-labs/aindusdb_core/issues)

---

*Guide d'installation AindusDB Core - Version 1.0.0*
