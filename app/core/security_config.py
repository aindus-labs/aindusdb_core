"""
🔐 Configuration Sécurité Durcie - AindusDB Core
Configuration production avec sécurité maximale

Créé : 20 janvier 2026
Objectif : Phase 2.3 - Durcir configuration sécurité
"""

import os
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

class SecuritySettings(BaseSettings):
    """Configuration de sécurité avec valeurs par défaut sécurisées."""
    
    # === Configuration CORS ===
    cors_origins: str = ""  # Vide = pas de CORS par défaut
    cors_allow_methods: str = "GET,POST,PUT,DELETE,OPTIONS"
    cors_allow_headers: str = "Authorization,Content-Type,X-Requested-With"
    cors_allow_credentials: bool = False
    cors_max_age: int = 86400  # 24h
    
    # === Configuration TLS/SSL ===
    ssl_enabled: bool = True
    ssl_cert_path: str = "/etc/ssl/certs/aindusdb.crt"
    ssl_key_path: str = "/etc/ssl/private/aindusdb.key"
    ssl_ca_path: str = "/etc/ssl/certs/ca.crt"
    tls_version: str = "TLSv1.3"
    force_https: bool = True
    
    # === Configuration Sécurité Headers ===
    security_headers_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 an
    hsts_include_subdomains: bool = True
    hsts_preload: bool = True
    content_security_policy: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    
    # === Configuration Rate Limiting ===
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10
    rate_limit_storage: str = "redis"  # redis, memory
    
    # === Configuration JWT ===
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_issuer: str = "aindusdb-core"
    jwt_audience: str = "aindusdb-users"
    
    # === Configuration Session ===
    session_timeout_minutes: int = 30
    max_concurrent_sessions: int = 3
    secure_cookies: bool = True
    cookie_samesite: str = "Strict"
    
    # === Configuration Validation ===
    max_request_size_mb: int = 10
    max_file_size_mb: int = 5
    allowed_file_types: List[str] = [
        ".txt", ".pdf", ".doc", ".docx", 
        ".png", ".jpg", ".jpeg", ".gif"
    ]
    
    # === Configuration Audit ===
    audit_enabled: bool = True
    audit_retention_days: int = 90
    audit_sensitive_operations: bool = True
    log_failed_auth: bool = True
    log_data_access: bool = True
    
    # === Configuration Monitoring ===
    security_monitoring_enabled: bool = True
    alert_on_failed_attempts: int = 5
    alert_on_suspicious_patterns: bool = True
    block_suspicious_ips: bool = True
    ip_block_duration_minutes: int = 60
    
    # === Configuration Backup ===
    backup_encryption_enabled: bool = True
    backup_retention_days: int = 30
    backup_verify_checksums: bool = True
    
    @field_validator('cors_origins')
    @classmethod
    def validate_cors_origins(cls, v):
        """Valider la configuration CORS."""
        if not v:
            return v
        
        # En production, spécifier les domaines exacts
        origins = [origin.strip() for origin in v.split(',')]
        
        for origin in origins:
            if not origin.startswith(('http://', 'https://')):
                raise ValueError(f"CORS origin must start with http:// or https://: {origin}")
            
            # Pas de wildcards en production
            if '*' in origin and os.getenv('ENVIRONMENT') == 'production':
                raise ValueError("Wildcards not allowed in production CORS origins")
        
        return ','.join(origins)
    
    @field_validator('tls_version')
    @classmethod
    def validate_tls_version(cls, v):
        """Valider la version TLS."""
        allowed_versions = ['TLSv1.2', 'TLSv1.3']
        if v not in allowed_versions:
            raise ValueError(f"TLS version must be one of: {allowed_versions}")
        return v
    
    @field_validator('content_security_policy')
    @classmethod
    def validate_csp(cls, v):
        """Valider le Content Security Policy."""
        # Pas de 'unsafe-inline' ou 'unsafe-eval' en production
        if os.getenv('ENVIRONMENT') == 'production':
            if "'unsafe-inline'" in v or "'unsafe-eval'" in v:
                raise ValueError("Unsafe directives not allowed in production CSP")
        return v
    
    @field_validator('rate_limit_storage')
    @classmethod
    def validate_rate_limit_storage(cls, v):
        """Valider le stockage du rate limiting."""
        allowed_storages = ['redis', 'memory']
        if v not in allowed_storages:
            raise ValueError(f"Rate limit storage must be one of: {allowed_storages}")
        return v
    
    @field_validator('cookie_samesite')
    @classmethod
    def validate_cookie_samesite(cls, v):
        """Valider l'attribut SameSite."""
        allowed_values = ['Strict', 'Lax', 'None']
        if v not in allowed_values:
            raise ValueError(f"cookie_samesite must be one of: {allowed_values}")
        return v
    
    @field_validator('allowed_file_types')
    @classmethod
    def validate_file_types(cls, v):
        """Valider les types de fichiers autorisés."""
        dangerous_types = [
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr',
            '.js', '.vbs', '.jar', '.app', '.deb', '.pkg',
            '.dmg', '.rpm', '.msi', '.php', '.asp', '.jsp'
        ]
        
        for file_type in dangerous_types:
            if file_type in v:
                raise ValueError(f"Dangerous file type not allowed: {file_type}")
        
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Instance globale
security_settings = SecuritySettings()

# Configuration recommandée par environnement
def get_security_config(env: str = "development") -> dict:
    """Obtenir la configuration de sécurité recommandée."""
    
    configs = {
        "development": {
            "cors_origins": "http://localhost:3000,http://localhost:8080",
            "cors_allow_credentials": True,
            "ssl_enabled": False,
            "force_https": False,
            "security_headers_enabled": True,
            "rate_limit_requests_per_minute": 1000,
            "audit_enabled": True,
            "debug_mode": True
        },
        "staging": {
            "cors_origins": "https://staging.aindusdb.com",
            "cors_allow_credentials": True,
            "ssl_enabled": True,
            "force_https": True,
            "security_headers_enabled": True,
            "rate_limit_requests_per_minute": 100,
            "audit_enabled": True,
            "debug_mode": False
        },
        "production": {
            "cors_origins": "https://app.aindusdb.com,https://admin.aindusdb.com",
            "cors_allow_credentials": False,
            "ssl_enabled": True,
            "force_https": True,
            "security_headers_enabled": True,
            "rate_limit_requests_per_minute": 60,
            "audit_enabled": True,
            "debug_mode": False,
            "content_security_policy": (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        }
    }
    
    return configs.get(env, configs["development"])

# Validation de la configuration actuelle
def validate_security_config() -> List[str]:
    """Valider la configuration et retourner les avertissements."""
    warnings = []
    
    # Vérifier CORS
    if not security_settings.cors_origins and os.getenv('ENVIRONMENT') != 'development':
        warnings.append("CORS not configured - API may be inaccessible")
    
    # Vérifier SSL
    if not security_settings.ssl_enabled and os.getenv('ENVIRONMENT') == 'production':
        warnings.append("SSL disabled in production - traffic will be unencrypted")
    
    # Vérifier rate limiting
    if not security_settings.rate_limit_enabled:
        warnings.append("Rate limiting disabled - API may be vulnerable to DoS")
    
    # Vérifier audit
    if not security_settings.audit_enabled:
        warnings.append("Audit disabled - security events will not be logged")
    
    # Vérifier JWT
    if security_settings.jwt_access_token_expire_minutes > 60:
        warnings.append("Long-lived access tokens - consider shorter expiration")
    
    # Vérifier CSP
    if "'unsafe-inline'" in security_settings.content_security_policy:
        warnings.append("Unsafe inline in CSP - XSS vulnerability")
    
    return warnings

# Génération de configuration nginx
def generate_nginx_config() -> str:
    """Générer la configuration nginx sécurisée."""
    return f"""
# Configuration nginx sécurisée pour AindusDB Core
server {{
    listen 443 ssl http2;
    server_name api.aindusdb.com;
    
    # Configuration SSL/TLS
    ssl_certificate {security_settings.ssl_cert_path};
    ssl_certificate_key {security_settings.ssl_key_path};
    ssl_protocols {security_settings.tls_version};
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    
    # Headers de sécurité
    add_header Strict-Transport-Security "max-age={security_settings.hsts_max_age}; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "{security_settings.content_security_policy}" always;
    
    # Configuration proxy
    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Taille max des requêtes
        client_max_body_size {security_settings.max_request_size_mb}M;
        
        # Timeout
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}
    
    # Redirection HTTP vers HTTPS
    server {{
        listen 80;
        server_name api.aindusdb.com;
        return 301 https://$server_name$request_uri;
    }}
}}
"""
