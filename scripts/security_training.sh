#!/bin/bash
# 🎓 security_training.sh - Programme de formation sécurité

echo "🎓 PROGRAMME DE FORMATION SÉCURITÉ"
echo "================================="
echo "AindusDB Core - Équipe de Développement"
echo ""

# Créer le répertoire de formation
TRAINING_DIR="security_training_$(date +%Y%m%d)"
mkdir -p "$TRAINING_DIR"

echo "📚 MODULES DE FORMATION"
echo "===================="

# Module 1: OWASP Top 10
echo ""
echo "1️⃣  MODULE 1: OWASP Top 10 2021"
echo "------------------------------"

cat > "$TRAINING_DIR/module1_owasp.md" << 'EOF'
# Module 1: OWASP Top 10 2021

## Objectifs
- Comprendre les 10 vulnérabilités les plus critiques
- Identifier comment elles s'appliquent à notre code
- Apprendre les stratégies de prévention

## A01: Broken Access Control
**Exemple dans notre code:**
```python
# ❌ Vulnérable
@app.get("/api/v1/users/{user_id}")
def get_user(user_id):
    return db.get_user(user_id)  # Pas de vérification!

# ✅ Sécurisé
@app.get("/api/v1/users/{user_id}")
@require_auth
def get_user(user_id, current_user):
    if current_user.id != user_id and not current_user.is_admin:
        raise Forbidden()
    return db.get_user(user_id)
```

## A02: Cryptographic Failures
**Points clés:**
- Toujours utiliser des algorithmes forts (bcrypt, AES-256)
- Ne jamais stocker de mots de passe en clair
- Utiliser TLS 1.3 en production

## A03: Injection
**Types d'injection:**
- SQL: `SELECT * FROM users WHERE id = '$user_input'`
- NoSQL: `db.users.find({$ne: null})`
- Command: `; rm -rf /`
- XSS: `<script>alert('XSS')</script>`

**Prévention:**
- Requêtes paramétrées
- Validation et sanitization
- Echappement des sorties

## A07: Identification & Authentication Failures
**Bonnes pratiques:**
- MFA obligatoire pour les comptes privilégiés
- Passwords forts (min 12 caractères)
- Sessions avec timeout
- Login lockout après tentatives

## A05: Security Misconfiguration
**Checklist:**
- [ ] Headers de sécurité configurés
- [ ] Messages d'erreur génériques
- [ ] Pas de features de debug en prod
- [ ] Permissions minimales

## Quiz
1. Quel est le risque principal de ce code ?
   ```python
   query = f"SELECT * FROM users WHERE name = '{name}'"
   ```
2. Comment prévenir une XSS ?
3. Pourquoi utiliser bcrypt pour les mots de passe ?
EOF

# Module 2: Secure Coding
echo ""
echo "2️⃣  MODULE 2: Codage Sécurisé"
echo "--------------------------"

cat > "$TRAINING_DIR/module2_secure_coding.md" << 'EOF'
# Module 2: Codage Sécurisé

## Principes Fondamentaux

### 1. Principe du Moindre Privilège
Donner uniquement les permissions nécessaires.

### 2. Défense en Profondeur
Plusieurs couches de sécurité.

### 3. Échec Sécurisé
Ne jamais révéler d'informations en cas d'erreur.

## Validation des Entrées

### Pydantic pour la validation
```python
from pydantic import BaseModel, validator

class UserInput(BaseModel):
    email: str
    age: int
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Email invalide')
        return v
    
    @validator('age')
    def validate_age(cls, v):
        if v < 0 or v > 120:
            raise ValueError('Âge invalide')
        return v
```

### Sanitization
```python
import bleach

def sanitize_html(content: str) -> str:
    allowed_tags = ['p', 'b', 'i', 'u', 'code']
    return bleach.clean(content, tags=allowed_tags)
```

## Gestion des Secrets

### Variables d'environnement
```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    
    class Config:
        env_file = ".env"
```

### Jamais hardcoder!
```python
# ❌ MAUVAIS
API_KEY = "sk-1234567890abcdef"

# ✅ BON
API_KEY = os.getenv("API_KEY")
```

## Logging Sécurisé

### Masquer les données sensibles
```python
import re

def mask_sensitive_data(log_message: str) -> str:
    patterns = [
        (r'password["\s]*[:=]["\s]*([^"\s,}]+)', 'password":"***"'),
        (r'token["\s]*[:=]["\s]*([^"\s,}]+)', 'token":"***"'),
    ]
    
    for pattern, replacement in patterns:
        log_message = re.sub(pattern, replacement, log_message)
    
    return log_message
```

## Exercices Pratiques

### Exercice 1: Identifier la vulnérabilité
```python
def get_user_profile(user_id):
    # Trouver et corriger la vulnérabilité
    query = f"SELECT * FROM profiles WHERE user_id = {user_id}"
    return db.execute(query)
```

### Exercice 2: Sécuriser l'API
```python
@app.post("/api/upload")
def upload_file(file: UploadFile):
    # Ajouter les validations nécessaires
    with open(f"uploads/{file.filename}", "wb") as f:
        f.write(file.file.read())
    return {"status": "ok"}
```

## Solutions
Voir `exercises/solutions.md`
EOF

# Module 3: Testing de Sécurité
echo ""
echo "3️⃣  MODULE 3: Testing de Sécurité"
echo "------------------------------"

cat > "$TRAINING_DIR/module3_security_testing.md" << 'EOF'
# Module 3: Testing de Sécurité

## Types de Tests

### 1. Tests Statiques (SAST)
Analyse du code sans l'exécuter.

**Outils:**
- Bandit: Python security linter
- Safety: Vulnerability scanner
- Semgrep: Pattern matching

```bash
# Lancer les tests
bandit -r app/
safety check
semgrep --config=auto app/
```

### 2. Tests Dynamiques (DAST)
Test de l'application en cours d'exécution.

**Outils:**
- OWASP ZAP
- Burp Suite
- SQLMap

### 3. Tests de Pénétration
Simulation d'attaques réelles.

## Écrire des Tests de Sécurité

### Tests unitaires
```python
import pytest

def test_sql_injection_protection():
    malicious_input = "'; DROP TABLE users; --"
    
    with pytest.raises(ValueError):
        search_users(malicious_input)

def test_password_hashing():
    password = "MyPassword123!"
    hashed = hash_password(password)
    
    assert password not in hashed
    assert verify_password(password, hashed)
```

### Tests d'intégration
```python
async def test_authentication_flow(client):
    # Test login réussi
    response = await client.post("/auth/login", json={
        "username": "testuser",
        "password": "TestPass123!"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    
    # Test avec mauvais mot de passe
    response = await client.post("/auth/login", json={
        "username": "testuser",
        "password": "wrong"
    })
    assert response.status_code == 401
```

## Scénarios de Test

### 1. Injection SQL
- Tenter `'; DROP TABLE users; --`
- Vérifier que la requête échoue
- Confirmer que les données sont intactes

### 2. XSS
- Soumettre `<script>alert(1)</script>`
- Vérifier que le script est échappé
- Tester dans différents champs

### 3. Brute Force
- 10 tentatives de login échouées
- Vérifier le blocage (429)
- Confirmer la temporisation

### 4. Privilege Escalation
- Login utilisateur normal
- Tenter d'accéder aux endpoints admin
- Vérifier le refus (403)

## Automatisation

### CI/CD Pipeline
```yaml
security_tests:
  stage: test
  script:
    - bandit -r app/
    - safety check
    - pytest tests/security/
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

## Checklist de Test
- [ ] Validation des entrées
- [ ] Authentification forte
- [ ] Autorisation correcte
- [ ] Pas de data leakage
- [ ] Résistance aux attaques connues
- [ ] Logs sécurisés
- [ ] Rate limiting actif
EOF

# Module 4: Incident Response
echo ""
echo "4️⃣  MODULE 4: Gestion des Incidents"
echo "-------------------------------"

cat > "$TRAINING_DIR/module4_incident_response.md" << 'EOF'
# Module 4: Gestion des Incidents de Sécurité

## Cycle de Vie d'un Incident

### 1. Détection
- Monitoring alertes
- Rapports utilisateurs
- Scans automatiques
- Logs suspects

### 2. Analyse
- Évaluer l'impact
- Contenir l'incident
- Préserver les preuves
- Identifier la cause

### 3. Containment
- Isoler les systèmes affectés
- Bloquer les IPs malveillantes
- Révoquer les compromis
- Appliquer les patchs

### 4. Éradication
- Éliminer la menace
- Nettoyer les systèmes
- Corriger les vulnérabilités

### 5. Recovery
- Restaurer les services
- Surveiller les activités
- Valider la sécurité

### 6. Lessons Learned
- Documenter l'incident
- Mettre à jour les procédures
- Former l'équipe

## Rôles et Responsabilités

### CISO
- Coordination globale
- Communication externe
- Décisions stratégiques

### Security Lead
- Investigation technique
- Coordination équipe
- Rapport détaillé

### Développeur
- Analyse code source
- Implémentation correctifs
- Tests de validation

### DevOps
- Isolation infrastructure
- Application des patchs
- Monitoring post-incident

## Procédures Spécifiques

### Data Breach
1. **Immédiat**
   - Isoler les bases de données
   - Révoquer les accès
   - Activer le logging détaillé

2. **Investigation**
   - Identifier les données exposées
   - Analyser les logs d'accès
   - Déterminer la timeline

3. **Notification**
   - Notifier le CISO
   - Préparer communication
   - Conformité légale (GDPR)

### DDoS Attack
1. **Détection**
   - Spike de trafic anormal
   - Services ralentis
   - Alertes monitoring

2. **Mitigation**
   - Activer rate limiting
   - Bloquer IPs source
   - Utiliser CDN/Cloudflare

3. **Post-Attaque**
   - Analyser les patterns
   - Renforcer les défenses
   - Documenter l'attaque

### Compromised Account
1. **Immédiat**
   - Désactiver le compte
   - Révoquer tous les tokens
   - Notifier l'utilisateur

2. **Investigation**
   - Analyser les activités
   - Identifier l'étendue
   - Checker autres comptes

3. **Récupération**
   - Forcer le changement MFA
   - Réinitialiser les permissions
   - Surveiller le compte

## Outils de Response

### SIEM
- Centralisation des logs
- Corrélation d'événements
- Alertes automatiques

### SOAR
- Automatisation des réponses
- Playbooks prédéfinis
- Intégration outils

### Forensics
- Capture d'images
- Analyse mémoire
- Récupération données

## Exercice Pratique

### Scénario: Data Breach
```
10:23 - Alert: accès anormal à la base de données
10:25 - Vérification: requêtes suspectes depuis IP X.X.X.X
10:30 - Action: blocage IP, révocation accès
10:35 - Analyse: données utilisateurs consultées
11:00 - Identification: compte admin compromis
11:30 - Correction: reset password, activation MFA
12:00 - Validation: plus d'activités suspectes
```

**Questions:**
1. Qu'auriez-vous fait différemment?
2. Comment prévenir ce type d'incident?
3. Quels logs auraient été utiles?

## Checklist Post-Incident
- [ ] Rapport d'incident rédigé
- [ ] Causes racines identifiées
- [ ] Correctifs implémentés
- [ ] Tests de validation
- [ ] Équipe informée
- [ ] Procédures mises à jour
- [ ] Monitoring renforcé
EOF

# Créer les exercices
echo ""
echo "📝 CRÉATION DES EXERCICES"
echo "======================"

mkdir -p "$TRAINING_DIR/exercises"

# Exercice 1
cat > "$TRAINING_DIR/exercises/exercise1_vulnerability.py" << 'EOF'
# Exercice 1: Identifier et corriger les vulnérabilités
# 
# Instructions:
# 1. Identifier toutes les vulnérabilités dans ce code
# 2. Proposer des corrections
# 3. Écrire les tests de sécurité correspondants

import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key'  # À changer en production!

@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Vulnérabilité 1: SQL Injection
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    user = cursor.fetchone()
    
    if user:
        # Vulnérabilité 2: Information Disclosure
        return jsonify({
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'password_hash': user[3],  # Ne jamais exposer!
            'ssn': user[4]  # Donnée sensible!
        })
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/api/search')
def search():
    # Vulnérabilité 3: XSS
    query = request.args.get('q', '')
    return f"<h1>Résultats pour: {query}</h1>"

@app.route('/api/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    
    # Vulnérabilité 4: Path Traversal
    filename = file.filename
    file.save(f'/var/www/uploads/{filename}')
    
    return jsonify({'status': 'uploaded'})

@app.route('/api/admin/users')
def admin_users():
    # Vulnérabilité 5: Broken Access Control
    # Pas de vérification d'autorisation!
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    
    return jsonify(users)

if __name__ == '__main__':
    app.run(debug=True)  # Vulnérabilité 6: Debug en production!
EOF

# Solutions
cat > "$TRAINING_DIR/exercises/solutions.md" << 'EOF'
# Solutions des Exercices

## Exercice 1: Corrections

### 1. SQL Injection
```python
# ❌ Vulnérable
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ Sécurisé
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```

### 2. Information Disclosure
```python
# ❌ Trop d'informations
return jsonify({
    'id': user[0],
    'username': user[1],
    'email': user[2],
    'password_hash': user[3],
    'ssn': user[4]
})

# ✅ Minimum nécessaire
return jsonify({
    'id': user[0],
    'username': user[1]
})
```

### 3. XSS
```python
# ❌ Vulnérable
return f"<h1>Résultats pour: {query}</h1>"

# ✅ Échappé
from markupsafe import escape
return f"<h1>Résultats pour: {escape(query)}</h1>"
```

### 4. Path Traversal
```python
# ❌ Vulnérable
filename = file.filename
file.save(f'/var/www/uploads/{filename}')

# ✅ Sécurisé
import os
from werkzeug.utils import secure_filename

filename = secure_filename(file.filename)
safe_path = os.path.join('/var/www/uploads', filename)
if not safe_path.startswith('/var/www/uploads/'):
    raise ValueError("Path traversal detected!")
file.save(safe_path)
```

### 5. Access Control
```python
# ❌ Pas de vérification
@app.route('/api/admin/users')
def admin_users():
    # Code...

# ✅ Avec vérification
from functools import wraps

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/admin/users')
@require_admin
def admin_users():
    # Code...
```

### 6. Configuration
```python
# ❌ Debug en production
app.run(debug=True)

# ✅ Configuration par environnement
app.run(debug=os.getenv('DEBUG', 'False') == 'True')
```

## Tests de Sécurité

```python
import pytest

def test_sql_injection(client):
    """Test la protection contre l'injection SQL."""
    malicious_id = "1; DROP TABLE users; --"
    response = client.get(f'/api/users/{malicious_id}')
    # Doit échouer proprement
    assert response.status_code == 404

def test_xss_protection(client):
    """Test la protection XSS."""
    xss_payload = "<script>alert('XSS')</script>"
    response = client.get(f'/api/search?q={xss_payload}')
    assert '<script>' not in response.get_data(as_text=True)

def test_path_traversal(client):
    """Test la protection path traversal."""
    malicious_filename = "../../../etc/passwd"
    # Doit lever une erreur
    with pytest.raises(ValueError):
        upload_file(malicious_filename)
```
EOF

# Créer le quiz final
cat > "$TRAINING_DIR/quiz.md" << 'EOF'
# Quiz de Sécurité

## Question 1
Quelle est la vulnérabilité principale dans ce code ?
```python
def login(username, password):
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    return db.execute(query)
```

a) Hardcoded password  
b) SQL Injection  
c) XSS  
d) CSRF

## Question 2
Comment prévenir efficacement une attaque XSS ?
a) Utiliser des mots de passe forts
b) Échapper les sorties HTML
c) Activer HTTPS
d) Utiliser des tokens CSRF

## Question 3
Quel est le principe du moindre privilège ?
a) Donner tous les droits aux admins
b) Donner uniquement les permissions nécessaires
c) Utiliser des mots de passe complexes
d) Chiffrer toutes les données

## Question 4
Que signifie OWASP ?
a) Open Web Application Security Project
b) Online Web Application Security Protocol
c) Open Web Application Software Project
d) Online Web Application Security Project

## Question 5
Quel est le risque de stocker des mots de passe en clair ?
a) Performance réduite
b) Risque de vol en cas de fuite
c) Complexité accrue
d) Aucun risque si HTTPS

## Réponses
1. b) SQL Injection
2. b) Échapper les sorties HTML
3. b) Donner uniquement les permissions nécessaires
4. a) Open Web Application Security Project
5. b) Risque de vol en cas de fuite

## Score
- 5/5: Expert en sécurité! 🏆
- 4/5: Très bon niveau ✅
- 3/5: Bon niveau, à revoir certains points ⚠️
- <3/5: Formation complémentaire recommandée 📚
EOF

# Créer un README pour la formation
cat > "$TRAINING_DIR/README.md" << 'EOF'
# Programme de Formation Sécurité

## Objectifs
- Former l'équipe aux bonnes pratiques de sécurité
- Prévenir les vulnérabilités courantes
- Promouvoir une culture sécurité

## Programme
1. **Module 1**: OWASP Top 10 (2h)
2. **Module 2**: Codage Sécurisé (3h)
3. **Module 3**: Testing de Sécurité (2h)
4. **Module 4**: Gestion des Incidents (1h)

## Format
- Présentations théoriques
- Exercices pratiques
- Quiz final
- Certification interne

## Prérequis
- Connaissance de Python
- Notions de base en développement web

## Validation
- Participation à tous les modules
- Réalisation des exercices
- Quiz final avec score ≥ 80%

## Ressources
- Guides de référence
- Checklists
- Outils et liens utiles

## Support
- security@aindusdb.com
- Canal Slack #security-training
EOF

echo ""
echo "✅ MATÉRIEL DE FORMATION CRÉÉ"
echo "=========================="
echo "📁 Répertoire: $TRAINING_DIR"
echo ""
echo "Contenu:"
echo "  📚 Module 1: OWASP Top 10"
echo "  💻 Module 2: Codage Sécurisé"
echo "  🧪 Module 3: Testing Sécurité"
echo "  🚨 Module 4: Gestion Incidents"
echo "  📝 Exercices pratiques"
echo "  📋 Quiz final"
echo ""
echo "Pour commencer la formation:"
echo "  cd $TRAINING_DIR"
echo "  cat README.md"
