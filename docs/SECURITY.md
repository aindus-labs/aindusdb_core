# 🔐 SÉCURITÉ - AINDUSDB CORE

## 🚨 **GESTION DES SECRETS ET CRÉDENTIALS**

### **Règles d'Or**
1. **JAMAIS** de secrets en clair dans le code
2. **JAMAIS** de valeurs par défaut en production
3. **TOUJOURS** générer des secrets uniques par déploiement
4. **TOUJOURS** utiliser des variables d'environnement

### **Procédure de Génération des Secrets**

#### **JWT Secret Key (256 bits minimum)**
```bash
# Générer une clé JWT sécurisée
openssl rand -hex 32

# Exemple de sortie : a8f5b2c9e1d4a7b6c3e8f2a9d5b8c1e4f7a9b2c5d8e1f4a7b9c2e5f8a1b4c7d9
```

#### **PostgreSQL Password (32+ caractères)**
```bash
# Générer un mot de passe DB fort
openssl rand -base64 32

# Exemple : Kx9@mP7$nQ2#rL5&wT8!zV3*bN6^sF1
```

#### **Redis Password**
```bash
# Générer un mot de passe Redis
openssl rand -base64 24

# Exemple : R3d1s_S3cur3_K3y_2026_A1ndusDB
```

### **Configuration Production Recommandée**

#### **1. Variables d'Environment**
```bash
# .env.production
JWT_SECRET_KEY=<generated_256_bits_key>
POSTGRES_PASSWORD=<generated_strong_password>
REDIS_PASSWORD=<generated_redis_password>
SESSION_ENCRYPTION_KEY=<generated_session_key>
```

#### **2. Docker Secrets (recommandé)**
```yaml
# docker-compose.prod.yml
services:
  api:
    environment:
      - JWT_SECRET_KEY_FILE=/run/secrets/jwt_secret
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - jwt_secret
      - db_password

secrets:
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  db_password:
    file: ./secrets/db_password.txt
```

#### **3. Kubernetes Secrets**
```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: aindusdb-secrets
type: Opaque
data:
  jwt-secret: <base64-encoded-secret>
  db-password: <base64-encoded-password>
```

### **Rotation des Secrets**

#### **Fréquence Recommandée**
- **JWT Keys** : Tous les 90 jours
- **DB Passwords** : Tous les 180 jours
- **API Keys** : Tous les 30 jours
- **Certificates** : Tous les 90 jours

#### **Procédure de Rotation**
1. Générer nouveaux secrets
2. Mettre à jour configuration
3. Redémarrer services progressivement
4. Invalider anciens tokens/jeton
5. Supprimer anciens secrets

### **Validation de Sécurité**

#### **Checklist Déploiement**
- [ ] Aucun secret par défaut utilisé
- [ ] Tous les secrets générés aléatoirement
- [ ] Variables d'environnement protégées
- [ ] Droits fichiers restrictifs (600)
- [ ] Logs ne contiennent pas de secrets
- [ ] Backup chiffrés

#### **Scripts de Validation**
```bash
#!/bin/bash
# validate_secrets.sh

# Vérifier qu'aucun secret par défaut n'est utilisé
if grep -q "your_super_secret_jwt_key" .env; then
    echo "❌ JWT secret par défaut détecté!"
    exit 1
fi

if grep -q "CHANGE_STRONG_DB_PASSWORD" .env; then
    echo "❌ Mot de passe DB par défaut détecté!"
    exit 1
fi

# Vérifier longueur minimale des secrets
JWT_KEY=$(grep JWT_SECRET_KEY .env | cut -d'=' -f2)
if [ ${#JWT_KEY} -lt 64 ]; then
    echo "❌ JWT secret trop court (< 256 bits)"
    exit 1
fi

echo "✅ Validation secrets réussie"
```

### **Monitoring et Alertes**

#### **Métriques de Sécurité**
- Tentatives d'accès avec anciens secrets
- Changements de configuration non autorisés
- Exposition de secrets dans les logs
- Accès anormaux aux endpoints sensibles

#### **Alertes Critiques**
```yaml
# Exemple configuration Prometheus
- alert: DefaultSecretInUse
  expr: aindusdb_default_secret_detected == 1
  for: 0m
  labels:
    severity: critical
  annotations:
    summary: "Secret par défaut détecté en production"
```

### **Références et Bonnes Pratiques**

- [OWASP Secret Management](https://owasp.org/www-project-cheat-sheets/cheatsheets/Secret_Management_Cheat_Sheet.html)
- [NIST SP 800-57](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)
- [12-Factor App - Config](https://12factor.net/config)

---

**Dernière mise à jour** : 20 janvier 2026  
**Version** : 1.0.0  
**Contact** : security@aindusdb.com
