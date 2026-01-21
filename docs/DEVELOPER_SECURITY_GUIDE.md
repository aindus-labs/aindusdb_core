# 📚 Guide Sécurité Développeur

**Version**: 1.0  
**Date**: 20 janvier 2026  
**Audience**: Équipe de développement AindusDB Core

---

## 📋 Table des Matières

1. [Introduction](#introduction)
2. [Principes de Sécurité](#principes-de-sécurité)
3. [Bonnes Pratiques de Codage](#bonnes-pratiques-de-codage)
4. [Gestion des Secrets](#gestion-des-secrets)
5. [Validation des Entrées](#validation-des-entrées)
6. [Authentification & Autorisation](#authentification--autorisation)
7. [Logging & Monitoring](#logging--monitoring)
8. [Tests de Sécurité](#tests-de-sécurité)
9. [Outils et Ressources](#outils-et-ressources)
10. [Checklist de Review](#checklist-de-review)

---

## 🎯 Introduction

Ce guide définit les standards de sécurité à suivre lors du développement d'AindusDB Core. L'objectif est de garantir que chaque nouvelle fonctionnalité soit sécurisée par défaut.

### Pourquoi c'est important ?
- **Protection des données** : Sécuriser les informations sensibles
- **Confiance client** : Maintenir la confiance des utilisateurs
- **Conformité** : Respecter les standards (OWASP, GDPR)
- **Réduction des risques** : Prévenir les vulnérabilités

---

## 🔐 Principes de Sécurité

### 1. Principe du Moindre Privilège
```python
# ❌ MAUVAIS : Admin par défaut
def get_user_data(user_id):
    return db.execute("SELECT * FROM users")  # Toutes les données!

# ✅ BON : Uniquement les données autorisées
def get_user_data(user_id, current_user):
    if current_user.id != user_id and not current_user.is_admin:
        raise PermissionError("Accès non autorisé")
    return db.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

### 2. Défense en Profondeur
```python
# ✅ BON : Plusieurs couches de validation
@router.post("/api/v1/data")
async def create_data(request: DataRequest, user: User = Depends(get_current_user)):
    # 1. Validation Pydantic
    if not request.is_valid():
        raise HTTPException(400, "Données invalides")
    
    # 2. Vérification autorisation
    if not user.can_create_data():
        raise HTTPException(403, "Non autorisé")
    
    # 3. Sanitization
    sanitized_data = sanitize_input(request.data)
    
    # 4. Requête paramétrée
    result = await db.execute(
        "INSERT INTO data (content, user_id) VALUES (%s, %s)",
        (sanitized_data, user.id)
    )
    
    return result
```

### 3. Échec Sécurisé
```python
# ❌ MAUVAIS : Révélation d'informations
try:
    user = authenticate(credentials)
except Exception as e:
    return {"error": f"Erreur: {str(e)}"}  # Révèle l'erreur!

# ✅ BON : Message générique
try:
    user = authenticate(credentials)
except Exception:
    logger.error(f"Auth failed for {credentials.username}")
    return {"error": "Identifiants invalides"}  # Générique
```

---

## 💻 Bonnes Pratiques de Codage

### Utiliser les Types Sécurisés
```python
from pydantic import BaseModel, validator
import re

class SecureUserInput(BaseModel):
    email: str
    username: str
    content: str
    
    @validator('email')
    def validate_email(cls, v):
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Email invalide')
        return v.lower()
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Username entre 3 et 50 caractères')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username alphanumérique uniquement')
        return v
    
    @validator('content')
    def validate_content(cls, v):
        # Bloquer les patterns dangereux
        dangerous_patterns = ['<script', 'javascript:', 'data:']
        for pattern in dangerous_patterns:
            if pattern.lower() in v.lower():
                raise ValueError('Contenu non autorisé')
        return v
```

### Éviter eval() et exec()
```python
# ❌ DANGEREUX : Ne jamais utiliser eval()
def calculate(expression: str):
    return eval(expression)  # Injection possible!

# ✅ SÉCURISÉ : Parser et valider
from app.core.safe_math import SafeMathEvaluator

def calculate(expression: str):
    evaluator = SafeMathEvaluator()
    return evaluator.evaluate(expression)  # Sûr et contrôlé
```

### Gestion des Fichiers Sécurisée
```python
import os
from pathlib import Path

def save_upload(file: UploadFile, user_id: str):
    # Valider le type de fichier
    allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
    if file.content_type not in allowed_types:
        raise ValueError("Type de fichier non autorisé")
    
    # Générer un nom de fichier sécurisé
    file_ext = Path(file.filename).suffix
    safe_filename = f"{user_id}_{int(time.time())}{file_ext}"
    
    # Construire le chemin de manière sécurisée
    upload_dir = Path("uploads") / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / safe_filename
    
    # Limiter la taille
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    content = file.file.read(MAX_SIZE + 1)
    if len(content) > MAX_SIZE:
        raise ValueError("Fichier trop volumineux")
    
    # Sauvegarder
    with open(file_path, "wb") as f:
        f.write(content)
    
    return file_path
```

---

## 🔑 Gestion des Secrets

### Variables d'Environnement
```python
# .env.template (jamais commit avec les vraies valeurs)
DATABASE_URL=postgresql://user:password@localhost:5432/db
SECRET_KEY=votre-secret-key-ici
JWT_SECRET=jwt-secret-key
REDIS_URL=redis://localhost:6379

# app/core/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    jwt_secret: str
    
    class Config:
        env_file = ".env"
```

### Secrets avec Vault (Production)
```python
import hvac

class VaultManager:
    def __init__(self, vault_url: str, token: str):
        self.client = hvac.Client(url=vault_url, token=token)
    
    def get_secret(self, path: str) -> dict:
        secret = self.client.secrets.kv.v2_read_secret_version(path=path)
        return secret['data']['data']
    
    def get_database_credentials(self) -> dict:
        return self.get_secret('database/creds')
```

### Rotation des Secrets
```python
from datetime import datetime, timedelta

class SecretRotation:
    def __init__(self):
        self.last_rotation = {}
        self.rotation_interval = timedelta(days=90)
    
    def should_rotate(self, secret_name: str) -> bool:
        last = self.last_rotation.get(secret_name)
        if not last:
            return True
        return datetime.now() - last > self.rotation_interval
    
    def rotate_jwt_secret(self):
        if self.should_rotate('jwt_secret'):
            new_secret = generate_secure_secret()
            # Mettre à jour dans la base
            # Notifier les services
            self.last_rotation['jwt_secret'] = datetime.now()
```

---

## ✅ Validation des Entrées

### Validation Pydantic
```python
from pydantic import BaseModel, validator
from typing import Optional
import bleach

class SecurePostRequest(BaseModel):
    title: str
    content: str
    tags: Optional[list[str]] = None
    
    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Titre requis')
        if len(v) > 200:
            raise ValueError('Titre trop long')
        # Nettoyer le HTML
        return bleach.clean(v.strip())
    
    @validator('content')
    def validate_content(cls, v):
        if len(v) > 10000:
            raise ValueError('Contenu trop long')
        # Autoriser certains tags HTML
        allowed_tags = ['p', 'b', 'i', 'u', 'code', 'pre']
        return bleach.clean(v, tags=allowed_tags)
    
    @validator('tags')
    def validate_tags(cls, v):
        if v and len(v) > 10:
            raise ValueError('Trop de tags')
        if v:
            # Filtrer les tags vides
            return [tag.strip() for tag in v if tag.strip()]
        return []
```

### Validation SQL
```python
# ❌ VULNÉRABLE : Concaténation SQL
def get_user(username: str):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return db.execute(query)  # SQL Injection!

# ✅ SÉCURISÉ : Requêtes paramétrées
def get_user(username: str):
    query = "SELECT * FROM users WHERE username = %s"
    return db.execute(query, (username,))  # Sûr!
```

### Validation NoSQL
```python
# ❌ VULNÉRABLE : Injection NoSQL
def find_users(query: dict):
    return db.users.find(query)  # Peut injecter $gt, $ne, etc.

# ✅ SÉCURISÉ : Validation des opérateurs
def find_users(query: dict):
    allowed_operators = ['$eq', '$in', '$regex']
    
    def validate_query(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.startswith('$') and key not in allowed_operators:
                    raise ValueError(f"Opérateur non autorisé: {key}")
                validate_query(value)
    
    validate_query(query)
    return db.users.find(query)
```

---

## 🔐 Authentification & Autorisation

### MFA Implementation
```python
import pyotp
import qrcode
from typing import Optional

class MFAService:
    def __init__(self):
        self.issuer = "AindusDB Core"
    
    def generate_secret(self, user_email: str) -> str:
        """Générer un secret TOTP pour l'utilisateur."""
        return pyotp.random_base32()
    
    def generate_qr_code(self, user_email: str, secret: str) -> bytes:
        """Générer le QR code pour la configuration TOTP."""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=self.issuer
        )
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def verify_token(self, secret: str, token: str) -> bool:
        """Vérifier le token TOTP."""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # Fenêtre de 30s
```

### RBAC (Role-Based Access Control)
```python
from enum import Enum
from functools import wraps

class Role(Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class Permission(Enum):
    READ_OWN = "read_own"
    READ_ALL = "read_all"
    WRITE_OWN = "write_own"
    WRITE_ALL = "write_all"
    DELETE_OWN = "delete_own"
    DELETE_ALL = "delete_all"
    MANAGE_USERS = "manage_users"
    VIEW_LOGS = "view_logs"

ROLE_PERMISSIONS = {
    Role.USER: [Permission.READ_OWN, Permission.WRITE_OWN, Permission.DELETE_OWN],
    Role.MODERATOR: [
        Permission.READ_OWN, Permission.READ_ALL,
        Permission.WRITE_OWN, Permission.DELETE_OWN
    ],
    Role.ADMIN: [
        Permission.READ_OWN, Permission.READ_ALL,
        Permission.WRITE_OWN, Permission.WRITE_ALL,
        Permission.DELETE_OWN, Permission.DELETE_ALL,
        Permission.VIEW_LOGS
    ],
    Role.SUPER_ADMIN: list(Permission)
}

def require_permission(permission: Permission):
    """Décorateur pour vérifier les permissions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Récupérer l'utilisateur depuis le contexte
            current_user = get_current_user()
            
            if not current_user.has_permission(permission):
                raise HTTPException(403, "Permission insuffisante")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Utilisation
@router.get("/api/v1/users/{user_id}")
@require_permission(Permission.READ_ALL)
async def get_user(user_id: str):
    # Seuls les admins peuvent voir tous les utilisateurs
    pass
```

---

## 📊 Logging & Monitoring

### Logging Sécurisé
```python
import logging
from app.core.secure_logging import secure_logger

class UserController:
    async def login(self, credentials: LoginRequest):
        # Logger la tentative
        await secure_logger.log_security_event(
            event_type="AUTH_ATTEMPT",
            message=f"Tentative de connexion pour {credentials.username}",
            ip_address=get_client_ip(),
            user_id=credentials.username
        )
        
        try:
            user = await authenticate(credentials)
            await secure_logger.log_security_event(
                event_type="AUTH_SUCCESS",
                message="Connexion réussie",
                user_id=user.id
            )
            return user
        except AuthError:
            await secure_logger.log_security_event(
                event_type="AUTH_FAILED",
                message="Échec de connexion",
                user_id=credentials.username,
                risk_score=3
            )
            raise
```

### Monitoring des Métriques
```python
from prometheus_client import Counter, Histogram, Gauge

# Métriques de sécurité
AUTH_ATTEMPTS = Counter('auth_attempts_total', 'Total auth attempts', ['status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'Request duration')
ACTIVE_USERS = Gauge('active_users_total', 'Number of active users')

class SecurityMetrics:
    @staticmethod
    def record_auth_attempt(success: bool):
        AUTH_ATTEMPTS.labels(status='success' if success else 'failed').inc()
    
    @staticmethod
    def record_request_duration(duration: float):
        REQUEST_DURATION.observe(duration)
    
    @staticmethod
    def update_active_users(count: int):
        ACTIVE_USERS.set(count)
```

---

## 🧪 Tests de Sécurité

### Tests Unitaires
```python
import pytest
from app.core.security import hash_password, verify_password

class TestSecurity:
    def test_password_hashing(self):
        """Tester le hachage des mots de passe."""
        password = "MySecurePassword123!"
        hashed = hash_password(password)
        
        # Le hash ne doit pas contenir le mot de passe
        assert password not in hashed
        
        # La vérification doit fonctionner
        assert verify_password(password, hashed)
        
        # Mauvais mot de passe doit échouer
        assert not verify_password("WrongPassword", hashed)
    
    def test_sql_injection_protection(self):
        """Tester la protection contre l'injection SQL."""
        malicious_input = "'; DROP TABLE users; --"
        
        # La requête doit échouer proprement
        with pytest.raises(ValueError):
            search_users(malicious_input)
```

### Tests d'Intégration
```python
import pytest
from httpx import AsyncClient

class TestAuthSecurity:
    async def test_brute_force_protection(self, client: AsyncClient):
        """Tester la protection contre le brute force."""
        # 10 tentatives de login échouées
        for i in range(10):
            response = await client.post("/auth/login", json={
                "username": "admin",
                "password": f"wrong{i}"
            })
            assert response.status_code in [401, 429]
        
        # La 11ème doit être bloquée
        response = await client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 429  # Too Many Requests
```

---

## 🛠️ Outils et Ressources

### Outils de Sécurité
```bash
# Analyse statique
pip install bandit safety semgrep

# Tests de dépendances
safety check
bandit -r app/

# Scan de vulnérabilités
pip install pip-audit
pip-audit

# Analyse de complexité
pip install radon
radon cc app/ -j
```

### VS Code Extensions recommandées
- Python
- SonarLint
- GitLens
- Docker
- Thunder Client (pour les tests API)

### Ressources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)
- [Python Security Best Practices](https://docs.python.org/3/library/security.html)

---

## ✅ Checklist de Review Code

### Avant de merger une PR :
- [ ] **Validation des entrées** : Toutes les entrées sont validées
- [ ] **Requêtes paramétrées** : Pas de concaténation SQL
- [ ] **Gestion des erreurs** : Pas de fuite d'information
- [ ] **Logging sécurisé** : Pas de données sensibles dans les logs
- [ ] **Authentification** : Vérifiée si nécessaire
- [ ] **Autorisation** : RBAC correctement implémenté
- [ ] **Tests** : Tests de sécurité inclus
- [ ] **Documentation** : Code commenté si complexe

### Questions à se poser :
1. Cette fonctionnalité introduit-elle une nouvelle surface d'attaque ?
2. Les données utilisateur sont-elles protégées ?
3. Que se passe-t-il en cas d'échec ?
4. Les logs sont-ils utiles pour le debug mais sécurisés ?
5. Les tests couvrent-ils les scénarios de sécurité ?

---

## 🚨 En Cas de Découverte de Vulnérabilité

1. **Ne pas commiter** le code vulnérable
2. **Créer une issue** security privée
3. **Notifier** immédiatement le CISO
4. **Préparer** un correctif
5. **Tester** le correctif
6. **Déployer** en urgence si critique

---

**Ce guide est un document vivant. Merci de contribuer à son amélioration !**

Pour toute question ou suggestion : security@aindusdb.com
