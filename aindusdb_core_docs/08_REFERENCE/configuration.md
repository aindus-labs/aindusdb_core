# Guide de Configuration - AindusDB Core

**Version:** 1.0  
**Date:** 21/01/2026  
**Auteur:** Équipe AindusDB  
**Statut:** En rédaction  

---

## ⚙️ Vue d'ensemble

Ce guide détaille toutes les options de configuration pour AindusDB Core, depuis les variables d'environnement jusqu'aux paramètres avancés.

---

## 📁 Structure des Fichiers de Configuration

```
aindusdb_core/
├── config/
│   ├── base.yaml           # Configuration de base
│   ├── development.yaml    # Environnement de dev
│   ├── production.yaml     # Environnement de prod
│   └── testing.yaml        # Environnement de test
├── .env                    # Variables d'environnement
├── .env.example           # Exemple de variables
└── config.py              # Chargement de la configuration
```

---

## 🌍 Variables d'Environnement

### Variables Essentielles

```bash
# Base de données
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aindusdb
DB_USER=aindusdb_user
DB_PASSWORD=secure_password
DB_SSL_MODE=require
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Redis (Cache)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password
REDIS_DB=0
REDIS_SSL=true

# Application
APP_NAME=AindusDB Core
APP_VERSION=1.0.0
APP_ENV=production
APP_DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8000
APP_WORKERS=4

# Sécurité
SECRET_KEY=your_super_secret_key_here
JWT_SECRET_KEY=jwt_secret_key_here
JWT_ALGORITHM=RS256
JWT_EXPIRE_MINUTES=60
JWT_REFRESH_EXPIRE_DAYS=30

# Vector Store
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=production
PINECONE_INDEX_PREFIX=aindusdb

# Stockage Object
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=eu-west-1
AWS_S3_BUCKET=aindusdb-storage
AWS_S3_ENCRYPTION=AES256

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
JAEGER_ENDPOINT=http://jaeger:14268/api/traces
SENTRY_DSN=https://your_sentry_dsn

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/aindusdb/app.log
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=10

# Vérification
VERITAS_ENABLED=true
VERITAS_MAX_COMPLEXITY=1000
VERITAS_TIMEOUT_SECONDS=30
VERITAS_CACHE_TTL=3600
```

### Variables Optionnelles

```bash
# Performance
ENABLE_ASYNC=true
MAX_CONCURRENT_REQUESTS=1000
REQUEST_TIMEOUT_SECONDS=30
KEEPALIVE_TIMEOUT_SECONDS=65

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_BURST=100

# CORS
CORS_ORIGINS=["https://app.aindusdb.com", "https://admin.aindusdb.com"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["GET", "POST", "PUT", "DELETE"]
CORS_ALLOW_HEADERS=["*"]

# WebSocket
WEBSOCKET_ENABLED=true
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_MAX_CONNECTIONS=10000

# Background Tasks
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_WORKER_CONCURRENCY=4

# Feature Flags
FEATURE_VECTOR_SEARCH=true
FEATURE_VERITAS_CALCULATIONS=true
FEATURE_BATCH_OPERATIONS=true
FEATURE_REAL_TIME_UPDATES=false
```

---

## 📄 Fichiers de Configuration YAML

### Configuration de Base (base.yaml)

```yaml
# config/base.yaml
app:
  name: "AindusDB Core"
  version: "1.0.0"
  description: "Vector Database with VERITAS computations"
  
database:
  driver: "postgresql"
  echo: false
  pool_pre_ping: true
  pool_recycle: 3600
  
redis:
  decode_responses: true
  socket_timeout: 5
  socket_connect_timeout: 5
  retry_on_timeout: true
  
security:
  password_min_length: 8
  password_require_uppercase: true
  password_require_lowercase: true
  password_require_numbers: true
  password_require_symbols: true
  session_timeout: 3600
  max_login_attempts: 5
  lockout_duration: 900
  
vector_store:
  default_dimension: 1536
  default_metric: "cosine"
  batch_size: 1000
  max_batch_size: 10000
  
veritas:
  enabled: true
  max_expression_depth: 100
  allowed_functions:
    - "sqrt"
    - "pow"
    - "log"
    - "exp"
    - "sin"
    - "cos"
    - "tan"
  cache_enabled: true
  cache_size: 10000
  
monitoring:
  metrics_enabled: true
  tracing_enabled: true
  health_check_interval: 30
  
logging:
  level: "INFO"
  format: "json"
  include_timestamp: true
  include_level: true
  include_logger: true
```

### Configuration Production (production.yaml)

```yaml
# config/production.yaml
app:
  debug: false
  workers: 8
  
database:
  pool_size: 50
  max_overflow: 100
  pool_timeout: 30
  
redis:
  max_connections: 100
  
security:
  require_https: true
  strict_transport_security: true
  content_security_policy: "default-src 'self'"
  
vector_store:
  replication_factor: 3
  consistency_level: "strong"
  
veritas:
  timeout_seconds: 60
  max_concurrent_calculations: 100
  
monitoring:
  prometheus_port: 9090
  jaeger_sampling_rate: 0.1
  
logging:
  level: "WARNING"
  handlers:
    - type: "file"
      filename: "/var/log/aindusdb/app.log"
      max_bytes: 104857600  # 100MB
      backup_count: 10
    - type: "syslog"
      facility: "local0"
```

### Configuration Développement (development.yaml)

```yaml
# config/development.yaml
app:
  debug: true
  reload: true
  workers: 1
  
database:
  echo: true
  pool_size: 5
  max_overflow: 10
  
security:
  require_https: false
  cors_origins: ["*"]
  
vector_store:
  replication_factor: 1
  consistency_level: "eventual"
  
veritas:
  timeout_seconds: 10
  
monitoring:
  prometheus_port: 9091
  jaeger_sampling_rate: 1.0
  
logging:
  level: "DEBUG"
  handlers:
    - type: "console"
      format: "detailed"
```

---

## 🔧 Configuration par Code

### Classe de Configuration (config.py)

```python
# app/core/config.py
from pydantic import BaseSettings, validator
from typing import List, Optional, Dict, Any
import os
from pathlib import Path

class Settings(BaseSettings):
    # Application
    app_name: str = "AindusDB Core"
    app_version: str = "1.0.0"
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_workers: int = 4
    
    # Base de données
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "aindusdb"
    db_user: str = "aindusdb_user"
    db_password: str
    db_ssl_mode: str = "prefer"
    db_pool_size: int = 20
    db_max_overflow: int = 30
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?sslmode={self.db_ssl_mode}"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    redis_ssl: bool = False
    
    @property
    def redis_url(self) -> str:
        protocol = "rediss" if self.redis_ssl else "redis"
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"{protocol}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # Sécurité
    secret_key: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 30
    
    # Vector Store
    pinecone_api_key: str
    pinecone_environment: str = "production"
    pinecone_index_prefix: str = "aindusdb"
    
    # AWS
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "eu-west-1"
    aws_s3_bucket: str = "aindusdb-storage"
    
    # Monitoring
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    jaeger_endpoint: Optional[str] = None
    sentry_dsn: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[str] = None
    log_max_size: str = "100MB"
    log_backup_count: int = 10
    
    # CORS
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 1000
    rate_limit_burst: int = 100
    
    # VERITAS
    veritas_enabled: bool = True
    veritas_max_complexity: int = 1000
    veritas_timeout_seconds: int = 30
    veritas_cache_ttl: int = 3600
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",")]
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    @validator("jwt_algorithm")
    def validate_jwt_algorithm(cls, v):
        valid_algos = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in valid_algos:
            raise ValueError(f"JWT algorithm must be one of {valid_algos}")
        return v

# Instance globale
settings = Settings()
```

### Chargement de Configuration YAML

```python
# app/core/yaml_config.py
import yaml
from pathlib import Path
from typing import Dict, Any
import os

class YAMLConfigLoader:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.environment = os.getenv("APP_ENV", "development")
        self.config = {}
        
    def load(self) -> Dict[str, Any]:
        """Charge la configuration YAML"""
        # Charger la configuration de base
        base_config = self._load_file("base.yaml")
        
        # Charger la configuration spécifique à l'environnement
        env_config = self._load_file(f"{self.environment}.yaml")
        
        # Fusionner les configurations
        self.config = self._merge_configs(base_config, env_config)
        
        # Appliquer les variables d'environnement
        self._apply_env_overrides()
        
        return self.config
    
    def _load_file(self, filename: str) -> Dict[str, Any]:
        """Charge un fichier de configuration YAML"""
        file_path = self.config_dir / filename
        if not file_path.exists():
            return {}
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Fusionne deux configurations"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def _apply_env_overrides(self):
        """Applique les overrides des variables d'environnement"""
        env_mappings = {
            "APP_WORKERS": ["app", "workers"],
            "DB_POOL_SIZE": ["database", "pool_size"],
            "LOG_LEVEL": ["logging", "level"],
            "VERITAS_TIMEOUT_SECONDS": ["veritas", "timeout_seconds"],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(config_path, value)
    
    def _set_nested_value(self, path: List[str], value: Any):
        """Définit une valeur imbriquée dans la configuration"""
        current = self.config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Conversion de type
        if path[-1] in ["workers", "pool_size", "timeout_seconds"]:
            value = int(value)
        elif path[-1] in ["debug", "enabled"]:
            value = value.lower() in ["true", "1", "yes"]
            
        current[path[-1]] = value

# Utilisation
config_loader = YAMLConfigLoader()
yaml_config = config_loader.load()
```

---

## 🚀 Configuration par Ligne de Commande

### Arguments CLI

```python
# app/cli.py
import click
from app.core.config import settings

@click.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--workers", default=4, help="Number of worker processes")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--config", help="Path to config file")
@click.option("--log-level", default="INFO", help="Log level")
def run(host, port, workers, reload, config, log_level):
    """Démarre l'application AindusDB"""
    
    # Override des settings
    if config:
        settings.config_file = config
    if host != "0.0.0.0":
        settings.app_host = host
    if port != 8000:
        settings.app_port = port
    if workers != 4:
        settings.app_workers = workers
    if reload:
        settings.app_debug = True
    if log_level != "INFO":
        settings.log_level = log_level
    
    # Démarrage de l'application
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        workers=settings.app_workers if not reload else 1,
        reload=reload,
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    run()
```

### Exemples d'Utilisation

```bash
# Démarrage avec configuration par défaut
python -m app.cli

# Démarrage avec options personnalisées
python -m app.cli --host 127.0.0.1 --port 8080 --workers 8

# Démarrage avec fichier de configuration personnalisé
python -m app.cli --config /path/to/config.yaml

# Démarrage en mode développement
python -m app.cli --reload --log-level DEBUG
```

---

## 🔐 Configuration de la Sécurité

### Configuration HTTPS/TLS

```yaml
# security/tls.yaml
tls:
  enabled: true
  cert_file: "/etc/ssl/certs/aindusdb.crt"
  key_file: "/etc/ssl/private/aindusdb.key"
  ca_file: "/etc/ssl/certs/ca.crt"
  
  # Protocoles et chiffrements
  min_version: "TLSv1.2"
  ciphers:
    - "TLS_AES_256_GCM_SHA384"
    - "TLS_CHACHA20_POLY1305_SHA256"
    - "TLS_AES_128_GCM_SHA256"
  
  # HSTS
  strict_transport_security:
    enabled: true
    max_age: 31536000
    include_subdomains: true
    preload: true
```

### Configuration OAuth2

```yaml
# security/oauth2.yaml
oauth2:
  providers:
    google:
      client_id: "your_google_client_id"
      client_secret: "your_google_client_secret"
      authorize_url: "https://accounts.google.com/o/oauth2/v2/auth"
      token_url: "https://oauth2.googleapis.com/token"
      userinfo_url: "https://www.googleapis.com/oauth2/v2/userinfo"
      scope: "openid email profile"
      
    github:
      client_id: "your_github_client_id"
      client_secret: "your_github_client_secret"
      authorize_url: "https://github.com/login/oauth/authorize"
      token_url: "https://github.com/login/oauth/access_token"
      userinfo_url: "https://api.github.com/user"
      scope: "user:email"
```

---

## 📊 Configuration du Monitoring

### Prometheus Configuration

```yaml
# monitoring/prometheus.yaml
prometheus:
  enabled: true
  port: 9090
  metrics_path: "/metrics"
  
  # Métriques personnalisées
  custom_metrics:
    - name: "vector_operations_total"
      type: "counter"
      labels: ["operation", "status"]
      
    - name: "veritas_calculations_duration"
      type: "histogram"
      buckets: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
      
    - name: "active_connections"
      type: "gauge"
```

### Configuration Jaeger

```yaml
# monitoring/jaeger.yaml
jaeger:
  enabled: true
  endpoint: "http://jaeger:14268/api/traces"
  service_name: "aindusdb-core"
  sampling_rate: 0.1  # 10% des traces
  
  tags:
    version: "1.0.0"
    environment: "production"
    
  # Propagation
  propagation_formats:
    - "jaeger"
    - "b3"
    - "tracecontext"
```

---

## 🗄️ Configuration de la Base de Données

### Configuration PostgreSQL Avancée

```yaml
# database/postgresql.yaml
postgresql:
  # Connection Pool
  pool:
    size: 50
    max_overflow: 100
    timeout: 30
    recycle: 3600
    pre_ping: true
    
  # SSL
  ssl:
    mode: "require"
    cert_file: "/etc/ssl/certs/client.crt"
    key_file: "/etc/ssl/private/client.key"
    ca_file: "/etc/ssl/certs/ca.crt"
    
  # Réplication
  replication:
    enabled: true
    mode: "streaming"
    sync_commit: "on"
    
  # Performance
  performance:
    statement_timeout: 30000
    idle_in_transaction_session_timeout: 60000
    lock_timeout: 5000
```

### Configuration Redis Cluster

```yaml
# redis/cluster.yaml
redis_cluster:
  enabled: true
  nodes:
    - host: "redis-1"
      port: 6379
    - host: "redis-2"
      port: 6379
    - host: "redis-3"
      port: 6379
    
  # Options de connexion
  decode_responses: true
  skip_full_coverage_check: true
  max_connections_per_node: 100
  
  # HA
  sentinel:
    enabled: true
    masters:
      - name: "mymaster"
        host: "sentinel-1"
        port: 26379
```

---

## 🔧 Configuration des Services Externes

### Pinecone Configuration

```yaml
# vector_store/pinecone.yaml
pinecone:
  api_key: "${PINECONE_API_KEY}"
  environment: "${PINECONE_ENVIRONMENT}"
  
  # Index par défaut
  default_index:
    name: "aindusdb-vectors"
    dimension: 1536
    metric: "cosine"
    replicas: 2
    pod_type: "p1.x1"
    
  # Options avancées
  batch_size: 1000
  timeout: 30
  max_retries: 3
  backoff_factor: 2
```

### Configuration AWS S3

```yaml
# storage/s3.yaml
aws_s3:
  access_key_id: "${AWS_ACCESS_KEY_ID}"
  secret_access_key: "${AWS_SECRET_ACCESS_KEY}"
  region: "${AWS_REGION}"
  bucket: "${AWS_S3_BUCKET}"
  
  # Options
  encryption: "AES256"
  storage_class: "STANDARD"
  multipart_threshold: 64MB
  multipart_chunksize: 16MB
  
  # Lifecycle
  lifecycle_rules:
    - id: "delete_old_backups"
      status: "Enabled"
      expiration:
        days: 365
      filter:
        prefix: "backups/"
```

---

## 🎯 Validation de Configuration

### Script de Validation

```python
# scripts/validate_config.py
import sys
from app.core.config import settings
from app.core.yaml_config import yaml_config

class ConfigValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_all(self):
        """Valide toute la configuration"""
        self.validate_database()
        self.validate_redis()
        self.validate_security()
        self.validate_vector_store()
        self.validate_monitoring()
        
        return len(self.errors) == 0
    
    def validate_database(self):
        """Valide la configuration de la base de données"""
        if not settings.db_password:
            self.errors.append("DB_PASSWORD is required")
            
        if settings.db_pool_size < 1:
            self.errors.append("DB_POOL_SIZE must be >= 1")
            
        if settings.db_max_overflow < settings.db_pool_size:
            self.warnings.append("DB_MAX_OVERFLOW should be >= DB_POOL_SIZE")
    
    def validate_redis(self):
        """Valide la configuration Redis"""
        if settings.redis_password and len(settings.redis_password) < 8:
            self.warnings.append("Redis password should be at least 8 characters")
    
    def validate_security(self):
        """Valide la configuration de sécurité"""
        if len(settings.secret_key) < 32:
            self.errors.append("SECRET_KEY must be at least 32 characters")
            
        if settings.cors_origins == ["*"] and settings.app_env == "production":
            self.warnings.append("CORS should not allow all origins in production")
    
    def validate_vector_store(self):
        """Valide la configuration du vector store"""
        if not settings.pinecone_api_key:
            self.errors.append("PINECONE_API_KEY is required")
    
    def validate_monitoring(self):
        """Valide la configuration du monitoring"""
        if settings.prometheus_enabled and settings.prometheus_port < 1024:
            self.warnings.append("Prometheus port should be > 1024")
    
    def print_results(self):
        """Affiche les résultats de validation"""
        if self.errors:
            print("\n❌ Configuration Errors:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\n⚠️ Configuration Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ Configuration is valid!")

if __name__ == "__main__":
    validator = ConfigValidator()
    is_valid = validator.validate_all()
    validator.print_results()
    
    sys.exit(0 if is_valid else 1)
```

---

## 📝 Bonnes Pratiques

### 1. Sécurité
- Ne jamais stocker de secrets dans le code
- Utiliser des variables d'environnement pour les données sensibles
- Chiffrer les secrets au repos
- Utiliser des clés différentes pour chaque environnement

### 2. Performance
- Ajuster la taille du pool de connexions selon la charge
- Utiliser le cache Redis pour les données fréquemment accédées
- Configurer correctement le nombre de workers

### 3. Fiabilité
- Activer les health checks
- Configurer les timeouts appropriés
- Mettre en place la réplication des données

### 4. Observabilité
- Activer toutes les métriques pertinentes
- Configurer le logging structuré
- Mettre en place des alertes

---

**Document maintenu par l'équipe AindusDB Core**  
**Dernière mise à jour:** 21/01/2026
