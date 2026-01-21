# FAQ et Dépannage - AindusDB Core

**Version:** 1.0  
**Date:** 21/01/2026  
**Auteur:** Équipe AindusDB  
**Statut:** En rédaction  

---

## ❓ Questions Fréquentes

### Installation et Configuration

**Q: Comment installer AindusDB Core ?**

R: Suivez ces étapes :
```bash
# Cloner le repository
git clone https://github.com/aindus-labs/aindusdb-core.git
cd aindusdb-core

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos configurations

# Exécuter les migrations
alembic upgrade head

# Démarrer l'application
python -m app.main
```

**Q: Quelles sont les dépendances système requises ?**

R: AindusDB Core nécessite :
- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- 4GB RAM minimum
- 50GB espace disque

**Q: Comment configurer la base de données PostgreSQL ?**

R: Créez une base de données et un utilisateur :
```sql
CREATE DATABASE aindusdb;
CREATE USER aindusdb_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE aindusdb TO aindusdb_user;
ALTER USER aindusdb_user CREATEDB;
```

---

### Utilisation de l'API

**Q: Comment générer un token JWT ?**

R: Utilisez l'endpoint d'authentification :
```bash
curl -X POST https://api.aindusdb.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your_password"
  }'
```

**Q: Quelle est la taille maximale d'un batch de vecteurs ?**

R: La taille maximale par défaut est de 1000 vecteurs par batch. Vous pouvez l'augmenter jusqu'à 10000 en modifiant la configuration :
```yaml
vector_store:
  max_batch_size: 10000
```

**Q: Comment effectuer une recherche avec filtres ?**

R: Utilisez le paramètre `filter` dans votre requête :
```json
{
  "vector": [0.1, 0.2, 0.3, ...],
  "top_k": 10,
  "filter": {
    "category": {"$eq": "finance"},
    "date": {"$gte": "2024-01-01"}
  }
}
```

---

### VERITAS Calculations

**Q: Quelles fonctions mathématiques sont supportées ?**

R: Les fonctions supportées incluent :
- Arithmétique : `+`, `-`, `*`, `/`, `%`, `^`
- Trigonométrie : `sin`, `cos`, `tan`, `asin`, `acos`, `atan`
- Logarithmes : `log`, `log10`, `exp`
- Racines : `sqrt`, `cbrt`
- Autres : `abs`, `ceil`, `floor`, `round`

**Q: Comment vérifier une preuve VERITAS ?**

R: Utilisez l'endpoint de vérification :
```bash
curl -X POST https://api.aindusdb.com/v1/veritas/verify/vp_123456 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Q: Quelle est la complexité maximale d'une expression ?**

R: Par défaut, la complexité maximale est de 1000 opérations. Vous pouvez l'ajuster :
```yaml
veritas:
  max_complexity: 2000
```

---

## 🐛 Problèmes Courants

### Erreurs de Connexion

**Problème : "Connection to database failed"**

Solutions possibles :
1. Vérifiez que PostgreSQL est en cours d'exécution :
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. Vérifiez les identifiants dans `.env` :
   ```bash
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=aindusdb
   DB_USER=aindusdb_user
   DB_PASSWORD=votre_mot_de_passe
   ```

3. Vérifiez que l'utilisateur a les droits nécessaires :
   ```sql
   \l  # Lister les bases de données
   \du  # Lister les utilisateurs
   ```

4. Vérifiez les règles de pare-feu :
   ```bash
   sudo ufw status
   sudo ufw allow 5432
   ```

**Problème : "Redis connection refused"**

Solutions :
1. Démarrez Redis :
   ```bash
   sudo systemctl start redis
   ```

2. Vérifiez la configuration Redis :
   ```bash
   redis-cli ping
   ```

3. Vérifiez le port Redis dans `.env` :
   ```bash
   REDIS_HOST=localhost
   REDIS_PORT=6379
   ```

### Erreurs d'Authentification

**Problème : "Invalid JWT token"**

Solutions :
1. Vérifiez que le token n'a pas expiré :
   ```python
   import jwt
   decoded = jwt.decode(token, options={"verify_signature": False})
   print(decoded['exp'])
   ```

2. Vérifiez la clé secrète JWT :
   ```bash
   JWT_SECRET_KEY=votre_clé_secrète
   ```

3. Régénérez un token :
   ```bash
   curl -X POST https://api.aindusdb.com/v1/auth/refresh \
     -H "Authorization: Bearer YOUR_REFRESH_TOKEN"
   ```

**Problème : "Insufficient permissions"**

Solutions :
1. Vérifiez les permissions de l'utilisateur :
   ```bash
   curl -X GET https://api.aindusdb.com/v1/users/me \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

2. Contactez votre administrateur pour obtenir les permissions nécessaires

### Erreurs de Performance

**Problème : "Request timeout"**

Solutions :
1. Augmentez le timeout dans la configuration :
   ```yaml
   app:
     request_timeout_seconds: 60
   ```

2. Vérifiez l'utilisation des ressources :
   ```bash
   top
   htop
   ```

3. Optimisez vos requêtes vectorielles :
   - Utilisez des filtres pour réduire l'espace de recherche
   - Limitez `top_k` à une valeur raisonnable
   - Utilisez le batch processing pour de multiples insertions

**Problème : "High memory usage"**

Solutions :
1. Augmentez la mémoire allouée :
   ```yaml
   app:
     memory_limit: "8Gi"
   ```

2. Optimisez la taille du batch :
   ```yaml
   vector_store:
     batch_size: 500  # Réduire si nécessaire
   ```

3. Activez le garbage collection :
   ```python
   import gc
   gc.collect()
   ```

### Erreurs Vector Store

**Problème : "Index not found"**

Solutions :
1. Vérifiez que l'index existe :
   ```bash
   curl -X GET https://api.aindusdb.com/v1/vectors/indexes \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

2. Créez l'index s'il n'existe pas :
   ```bash
   curl -X POST https://api.aindusdb.com/v1/vectors/indexes \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "mon_index",
       "dimension": 1536
     }'
   ```

**Problème : "Dimension mismatch"**

Solutions :
1. Vérifiez la dimension de l'index :
   ```bash
   curl -X GET https://api.aindusdb.com/v1/vectors/indexes/idx_123 \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

2. Assurez-vous que tous les vecteurs ont la même dimension

---

## 🔧 Outils de Dépannage

### Logs et Monitoring

**Voir les logs de l'application :**
```bash
# Logs en temps réel
tail -f /var/log/aindusdb/app.log

# Logs avec filtre
grep "ERROR" /var/log/aindusdb/app.log

# Logs des dernières 24h
journalctl -u aindusdb --since "24 hours ago"
```

**Monitoring avec Prometheus :**
```bash
# Accéder à Prometheus
http://localhost:9090

# Requêtes utiles
rate(http_requests_total[5m])
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Diagnostic de Base de Données

**Vérifier les connexions PostgreSQL :**
```bash
# Nombre de connexions actives
SELECT count(*) FROM pg_stat_activity;

# Requêtes lentes
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

# Taille de la base de données
SELECT pg_size_pretty(pg_database_size('aindusdb'));
```

**Diagnostic Redis :**
```bash
# Info Redis
redis-cli info

# Mémoire utilisée
redis-cli info memory

# Clés par pattern
redis-cli --scan --pattern "aindusdb:*"
```

### Tests de Connectivité

**Tester l'API :**
```bash
# Health check
curl https://api.aindusdb.com/v1/health

# Test avec authentification
curl -X GET https://api.aindusdb.com/v1/users/me \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test de recherche vectorielle
curl -X POST https://api.aindusdb.com/v1/vectors/indexes/test/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, 0.3],
    "top_k": 5
  }'
```

---

## 📊 Codes d'Erreur

| Code | Description | Solution |
|------|-------------|----------|
| `E001` | Database connection failed | Vérifiez la configuration DB |
| `E002` | Invalid authentication token | Régénérez le token |
| `E003` | Rate limit exceeded | Attendez avant de réessayer |
| `E004` | Vector dimension mismatch | Vérifiez la dimension de l'index |
| `E005` | Index not found | Créez l'index ou vérifiez l'ID |
| `E006` | Invalid VERITAS expression | Corrigez la syntaxe mathématique |
| `E007` | Storage quota exceeded | Supprimez des données ou upgradez |
| `E008` | Permission denied | Vérifiez les permissions utilisateur |
| `E009` | Service temporarily unavailable | Réessayez plus tard |
| `E010` | Configuration error | Validez la configuration |

---

## 🆘 Obtenir de l'Aide

### Ressources Disponibles

1. **Documentation** : https://docs.aindusdb.com
2. **GitHub Issues** : https://github.com/aindusdb/aindusdb-core/issues
3. **Community Slack** : https://aindusdb.slack.com
4. **Support Email** : support@aindusdb.com
5. **Status Page** : https://status.aindusdb.com

### Signaler un Bug

Quand vous signalez un bug, incluez :
- Version d'AindusDB Core
- Environnement (OS, Python version)
- Logs d'erreur complets
- Steps to reproduce
- Résultat attendu vs résultat obtenu

### Demander une Fonctionnalité

Pour demander une nouvelle fonctionnalité :
1. Vérifiez qu'elle n'existe pas déjà
2. Cherchez des demandes similaires
3. Créez une issue avec le tag `feature-request`
4. Décrivez le cas d'usage
5. Expliquez pourquoi c'est important

---

## 🎯 Conseils de Dépannage

### Avant de demander de l'aide :

1. **Vérifiez les logs** : Les messages d'erreur contiennent souvent des indices précieux
2. **Testez en isolation** : Essayez de reproduire le problème avec un cas simple
3. **Consultez la documentation** : La réponse s'y trouve souvent
4. **Cherchez dans les issues** : Quelqu'un a peut-être déjà eu le même problème
5. **Mettez à jour** : Assurez-vous d'utiliser la dernière version

### Informations à collecter :

```bash
# Version
python --version
pip show aindusdb-core

# Configuration
printenv | grep AINDB

# Logs récents
tail -100 /var/log/aindusdb/app.log

# Statistiques système
df -h
free -h
```

---

## 📚 Références Supplémentaires

- [Guide de Configuration](./configuration.md)
- [Référence API](./api_reference.md)
- [Architecture Système](../01_ARCHITECTURE/system_design.md)
- [Guide de Déploiement](../03_DEPLOYMENT/cloud_native.md)

---

**Document maintenu par l'équipe AindusDB Core**  
**Dernière mise à jour:** 21/01/2026
