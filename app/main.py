"""
AindusDB Core API - Point d'entrée principal
Vector Database API with PostgreSQL + pgvector
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.database import db_manager
from .core.logging import setup_logging, get_logger
from .core.metrics import metrics_service
from .core.secure_logging import secure_logger, SecurityLoggingMiddleware
from .services.veritas import VeritasOrchestrator
from .routers import health_router, vectors_router
from .routers.veritas import router as veritas_router
from .routers.typst_native import router as typst_native_router
from .routers.security_monitoring import router as security_monitoring_router
from .middleware.veritas_middleware import VeritasMiddleware
from .middleware.logging_middleware import LoggingMiddleware
from .middleware.metrics_middleware import PrometheusMetricsMiddleware
from .middleware.security_validation import SecurityValidationMiddleware, SimpleRateLimitMiddleware
from .middleware.advanced_rate_limiting import AdvancedRateLimitMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application avec support VERITAS complet."""
    # Initialiser logger pour lifecycle
    logger = get_logger("aindusdb.main.lifecycle")
    
    # Startup
    logger.info("🚀 Starting AindusDB Core with VERITAS support...")
    
    # 1. Configurer logging structuré
    setup_logging()
    
    # 2. Configurer logging sécurisé
    await secure_logger.setup_file_logging()
    await secure_logger.log_security_event(
        event_type="SYSTEM_STARTUP",
        message="AindusDB Core starting up",
        level="INFO"
    )
    
    # 3. Connecter base de données
    await db_manager.connect()
    
    # 4. Démarrer service de métriques
    await metrics_service.start(port=9090)
    
    # 5. Démarrer service VERITAS refactorisé (dependency injection propre)
    veritas_service = VeritasOrchestrator(db_manager=db_manager)  # Injection propre
    await veritas_service.start()
    
    logger.info("✅ AindusDB Core started successfully")
    logger.info("🔬 VERITAS protocol enabled for industrial AI")
    logger.info("📊 Metrics available on http://localhost:9090")
    logger.info("🛡️ Security dashboard: http://localhost:8000/api/v1/security/dashboard")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AindusDB Core...")
    await secure_logger.log_security_event(
        event_type="SYSTEM_SHUTDOWN",
        message="AindusDB Core shutting down",
        level="INFO"
    )
    await veritas_service.stop()
    await db_manager.disconnect()
    await metrics_service.stop()
    logger.info("✅ AindusDB Core stopped successfully")


# Création de l'application FastAPI avec documentation enrichie
app = FastAPI(
    title=settings.api_title,
    description="""
    # 🔬 AindusDB Core API - VERITAS Industrial AI Ready
    
    Base de données vectorielle **industrielle** avec protocole **VERITAS** pour IA prouvable.
    
    ## 🚀 Fonctionnalités principales
    
    ### Base vectorielle enterprise
    * 🗄️ **Stockage vectoriel** : Vecteurs haute dimension avec métadonnées enrichies  
    * 🔍 **Recherche sémantique** : Similarité cosinus optimisée avec pgvector
    * 🐘 **PostgreSQL robuste** : Backend enterprise avec haute disponibilité
    * 📊 **Monitoring production** : Métriques Prometheus + dashboards Grafana
    
    ### 🔬 VERITAS Protocol (Innovation mondiale)
    * 🧮 **Calculs vérifiés** : Preuves mathématiques étape par étape
    * 📜 **Traçabilité complète** : Hash SHA-256 des sources, audit trail
    * 🧠 **Traces de raisonnement** : Capture `<thought>` et `<action>` tags
    * 🎯 **Métriques de confiance** : Scoring granulaire de fiabilité  
    * 📐 **Support LaTeX natif** : Équations et formules avec validation
    
    ## 💼 Cas d'usage industriels
    
    ### IA Probabiliste → IA Prouvable
    * **Ingénierie** : Calculs certifiés F=ma, contraintes matériaux  
    * **Finance** : Modèles risque avec preuves mathématiques
    * **Recherche** : Publications avec sources traçables
    * **Juridique** : Analyses documentaires auditables
    * **Santé** : Diagnostics avec niveau de confiance
    
    ## 🛠️ Utilisation VERITAS
    
    ```bash
    # Requête standard
    curl -X POST /api/v1/vectors/search
    
    # Requête avec vérification VERITAS  
    curl -X POST /api/v1/veritas/verify \
         -H "X-Aindus-Veritas: true" \
         -d '{"query": "Calculate F=ma with m=10kg, a=9.8m/s²"}'
    ```
    
    ## 📈 Architecture production
    
    * **API** : FastAPI async avec middleware spécialisés
    * **DB** : PostgreSQL + pgvector + tables VERITAS  
    * **Monitoring** : Prometheus (port 9090) + logging structuré
    * **Sécurité** : JWT + RBAC + audit trail complet
    * **Déploiement** : Docker + Kubernetes ready
    
    ---
    
    **🎯 AindusDB Core : Le seul moteur vectoriel VERITAS-Ready au monde**
    """,
    version=settings.api_version,
    contact={
        "name": "AindusDB Team",
        "url": "https://github.com/aindus-labs/aindusdb_core",
        "email": "contact@aindusdb.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Environnement de développement"
        },
        {
            "url": "https://api.aindusdb.com",
            "description": "Environnement de production"
        }
    ],
    tags_metadata=[
        {
            "name": "health",
            "description": "Endpoints de santé et monitoring du système"
        },
        {
            "name": "vectors",
            "description": "Opérations sur les vecteurs et recherche de similarité"
        },
        {
            "name": "veritas",
            "description": "🔬 Protocole VERITAS - Vérification et certification des calculs"
        },
        {
            "name": "verification",
            "description": "🔍 Endpoints de vérification mathématique et traçabilité"
        },
        {
            "name": "proofs",
            "description": "📜 Gestion des preuves et certifications VERITAS"
        }
    ],
    openapi_tags=[
        {
            "name": "health",
            "description": "Health checks et status système"
        },
        {
            "name": "vectors", 
            "description": "CRUD et recherche vectorielle"
        },
        {
            "name": "veritas",
            "description": "🔬 VERITAS - IA Industrielle avec Preuves"
        }
    ],
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ===== MIDDLEWARES VERITAS =====
# Ordre important : les middlewares sont exécutés dans l'ordre inverse d'ajout

# 1. Middleware Security Headers (en premier pour sécurité maximale)
app.add_middleware(
    SecurityHeadersMiddleware,
    environment="production",  # Changez en "development" pour dev
    enable_csp=True,
    enable_hsts=True,
    csp_report_uri="/api/v1/security/csp-report"
)

# 2. Middleware de métriques (après sécurité)
app.add_middleware(
    PrometheusMetricsMiddleware,
    exclude_paths=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
)

# 3. Middleware de logging (après métriques)
app.add_middleware(
    LoggingMiddleware,
    log_requests=True,
    log_responses=True,
    include_request_body=False,  # Sécurité en production
    include_headers=True,
    exclude_paths=["/health", "/metrics", "/docs"]
)

# 4. Middleware VERITAS (après logging)
app.add_middleware(
    VeritasMiddleware,
    enable_proofs=True,
    audit_all_requests=False
)

# 5. Middleware de Rate Limiting Avancé (sécurité)
app.add_middleware(
    AdvancedRateLimitMiddleware,
    redis_url=settings.redis_url if hasattr(settings, 'redis_url') else None,
    default_limits="100/minute,1000/hour",
    protected_paths={
        "/auth/login": "5/minute,20/hour",
        "/auth/register": "3/minute,10/hour", 
        "/auth/forgot-password": "3/hour",
        "/api/v1/veritas/verify": "10/minute,100/hour",
        "/api/v1/veritas/calculate": "20/minute,200/hour",
        "/api/v1/admin": "50/minute,500/hour"
    },
    enable_brute_force=True,
    enable_ddos_protection=True
)

# 6. Middleware de Validation Sécurisée (sécurité)
app.add_middleware(
    SecurityValidationMiddleware,
    max_request_size=10 * 1024 * 1024,  # 10MB
    max_header_size=8192,  # 8KB
    blocked_user_agents=[
        'sqlmap', 'nikto', 'nmap', 'masscan', 'zap', 'burp',
        'scanner', 'crawler', 'bot', 'spider'
    ]
)

# ===== INCLUSION DES ROUTERS =====

# Routers de base
app.include_router(health_router)
app.include_router(vectors_router)

# 🔬 Router VERITAS pour IA industrielle
app.include_router(veritas_router)

# 🎯 Router Typst Native pour génération IA optimisée
app.include_router(typst_native_router)

# 🛡️ Router Security Monitoring
app.include_router(security_monitoring_router)

# ===== ENDPOINTS RACINE =====

@app.get("/", 
         summary="Page d'accueil AindusDB Core",
         description="Point d'entrée principal avec informations VERITAS")
async def root():
    """Page d'accueil avec statut VERITAS."""
    return {
        "message": "🚀 AindusDB Core - Industrial Vector Database",
        "version": settings.api_version,
        "features": [
            "🗄️ Vector Storage with pgvector", 
            "🔍 Semantic Search",
            "🔬 VERITAS Protocol (Industrial AI)",
            "📊 Production Monitoring",
            "🔐 Enterprise Security"
        ],
        "veritas": {
            "enabled": True,
            "description": "Verifiable Execution & Reasoning Integrated Trust Action System",
            "capabilities": [
                "Mathematical proof generation",
                "Calculation verification", 
                "Source traceability",
                "Reasoning trace capture",
                "Confidence scoring"
            ]
        },
        "endpoints": {
            "health": "/health",
            "vectors": "/api/v1/vectors",
            "veritas": "/api/v1/veritas",
            "metrics": "http://localhost:9090",
            "docs": "/docs"
        }
    }

@app.get("/veritas/info",
         summary="Informations protocole VERITAS", 
         description="Détails sur les capacités VERITAS disponibles")
async def veritas_info():
    """Informations détaillées sur le protocole VERITAS."""
    return {
        "protocol": "VERITAS v1.0",
        "full_name": "Verifiable Execution & Reasoning Integrated Trust Action System",
        "description": "Transform probabilistic AI into provable industrial AI",
        "core_features": {
            "mathematical_proofs": "Generate step-by-step verified calculations",
            "source_traceability": "SHA-256 hash verification of document sources", 
            "reasoning_traces": "Capture and index <thought> and <action> tags",
            "confidence_metrics": "Granular confidence scoring for all operations",
            "latex_support": "Native LaTeX equation processing and validation"
        },
        "usage": {
            "header": "Add 'X-Aindus-Veritas: true' to any request",
            "endpoints": {
                "verify": "/api/v1/veritas/verify",
                "calculate": "/api/v1/veritas/calculations/verify", 
                "proofs": "/api/v1/veritas/proofs",
                "stats": "/api/v1/veritas/stats"
            }
        },
        "quality_standards": {
            "source_hash_required": True,
            "latex_equations_supported": True,
            "calculation_sandbox": "Secure Python execution environment",
            "audit_trail": "Complete operation logging and traceability"
        },
        "service_status": {
            "veritas_service": "active" if veritas_service.started else "inactive",
            "metrics_export": "http://localhost:9090",
            "database_ready": True  # TODO: check real DB status
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🔬 Starting AindusDB Core with VERITAS Protocol")
    print("📊 Metrics will be available on http://localhost:9090")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔬 VERITAS Info: http://localhost:8000/veritas/info")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_config=None,  # Use our custom logging setup
        access_log=False  # Disable default access log (we have our own)
    )
