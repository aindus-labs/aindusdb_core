# 📋 Changelog - AindusDB Core

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Implémentation CRUD vecteurs complet
- Support index HNSW/IVFFlat avancé
- Cache Redis pour embeddings
- Interface web d'administration
- Support multi-tenant avec RLS
- Authentification JWT
- Rate limiting et quotas

## [1.0.0] - 2026-01-15

### Added
- **Architecture modulaire** : Structure FastAPI avec séparation claire des responsabilités
  - `app/core/` : Configuration centralisée et gestion base de données
  - `app/models/` : Modèles Pydantic pour validation API
  - `app/services/` : Logique métier isolée
  - `app/routers/` : Endpoints API avec documentation OpenAPI complète
  - `app/dependencies/` : Injection de dépendances FastAPI

- **API REST complète** :
  - `GET /` : Message de bienvenue et statut
  - `GET /health` : Health check PostgreSQL + pgvector
  - `GET /status` : Informations détaillées du système
  - `GET /metrics` : Métriques de performance
  - `POST /vectors/test` : Test opérations vectorielles pgvector
  - `POST /vectors/` : Création de vecteurs (implémentation de base)
  - `POST /vectors/search` : Recherche de similarité (implémentation de base)

- **Documentation OpenAPI enrichie** :
  - Métadonnées complètes (titre, version, contact, licence)
  - Descriptions détaillées pour tous les endpoints
  - Exemples de requêtes et réponses
  - Codes d'erreur documentés
  - Tags et regroupement logique des endpoints

- **Base de données vectorielle** :
  - Support PostgreSQL 15+ avec extension pgvector 0.5.1
  - Connexions asynchrones avec asyncpg
  - Pool de connexions configuré
  - Tests opérationnels intégrés

- **Infrastructure Docker** :
  - `docker-compose.yml` pour développement
  - Images optimisées PostgreSQL + pgvector
  - Configuration environnement avec `.env`
  - Health checks et restart policies

- **Suite de tests complète** :
  - **Tests unitaires** : Modèles, services, routers (95%+ couverture)
  - **Tests d'intégration** : Base de données et API end-to-end
  - **Tests de performance** : Benchmarks insertion et recherche
  - Configuration pytest avec fixtures et helpers
  - Base de données de test isolée

- **CI/CD GitHub Actions** :
  - Pipeline automatisé pour tests
  - Support multi-plateforme (Ubuntu, Windows, macOS)
  - Tests avec plusieurs versions Python (3.11, 3.12)
  - Rapports de couverture automatiques

- **Documentation complète** :
  - **README.md** : Guide complet avec exemples et architecture
  - **docs/INSTALLATION.md** : Instructions détaillées tous environnements
  - **docs/CONTRIBUTING.md** : Guide développeur et standards
  - **docs/API_EXAMPLES.md** : Exemples pratiques multi-langages
  - Documentation interactive Swagger/ReDoc

### Technical Stack
- **Framework API** : FastAPI 0.104+ avec Uvicorn
- **Base de données** : PostgreSQL 15+ + pgvector 0.5.1
- **Driver DB** : asyncpg 0.29+ (asynchrone haute performance)
- **Validation** : Pydantic 2.5+ avec settings
- **Tests** : pytest 7.4+ avec httpx et asyncio
- **Containerisation** : Docker + Docker Compose
- **Documentation** : OpenAPI/Swagger automatique

### Performance
- **Connexions DB** : Pool asyncpg optimisé (10 connexions par défaut)
- **API** : Support multi-workers Uvicorn
- **Tests benchmark** : Insertion ~1000 vecteurs/sec, recherche ~500 req/sec
- **Monitoring** : Health checks temps réel et métriques

### Security
- **Configuration sécurisée** : Variables d'environnement pour secrets
- **Validation entrées** : Pydantic pour tous les endpoints
- **Gestion erreurs** : Pas d'exposition d'informations sensibles
- **Base de données** : Connexions authentifiées uniquement

## [0.9.0] - 2026-01-10 (Pre-release)

### Added
- Implémentation initiale FastAPI avec endpoints de base
- Connexion PostgreSQL + pgvector basique
- Tests préliminaires
- Configuration Docker initiale

### Known Issues
- Documentation API limitée
- Tests de performance manquants
- Gestion d'erreurs basique
- Configuration production non optimisée

## [0.1.0] - 2026-01-05 (Initial Development)

### Added
- Structure projet initiale
- Configuration développement
- Premières expérimentations pgvector
- Proof of concept vectoriel

---

## 🔄 Politique de versioning

AindusDB Core suit le [Semantic Versioning](https://semver.org/) (SemVer) :

### Format de version : `MAJOR.MINOR.PATCH`

- **MAJOR** : Changements incompatibles de l'API
- **MINOR** : Nouvelles fonctionnalités compatibles
- **PATCH** : Corrections de bugs compatibles

### Exemples de changements par type

#### MAJOR (Breaking changes)
- Modification schema API incompatible
- Suppression d'endpoints existants
- Changement format base de données
- Modification signatures fonctions publiques

#### MINOR (Features)
- Nouveaux endpoints API
- Nouvelles fonctionnalités optionnelles
- Améliorations performance non-disruptives
- Nouvelles options de configuration

#### PATCH (Bug fixes)
- Corrections de bugs
- Améliorations sécurité
- Optimisations mineures
- Mises à jour documentation

### Branches et releases

#### Branches principales
- `main` : Code stable, correspond aux releases
- `develop` : Développement actif (si workflow GitFlow utilisé)
- `feature/*` : Nouvelles fonctionnalités
- `hotfix/*` : Corrections urgentes
- `release/*` : Préparation releases

#### Processus de release

1. **Development** : Travail sur branches feature
2. **Integration** : Merge vers develop et tests
3. **Release preparation** : Branch release/vX.Y.Z
4. **Testing** : Tests complets et validation
5. **Release** : Tag et merge vers main
6. **Deployment** : Publication automatique

#### Tags Git
```bash
# Format des tags
v1.0.0      # Release stable
v1.1.0-rc1  # Release candidate
v1.1.0-beta1 # Version beta
v1.1.0-alpha1 # Version alpha
```

### Cycle de release

#### Releases majeures (tous les 6-12 mois)
- Nouvelles fonctionnalités importantes
- Changements d'architecture
- Migration guides fournis
- Support versions précédentes limité

#### Releases mineures (tous les 2-3 mois)  
- Nouvelles fonctionnalités
- Améliorations existantes
- Backwards compatible
- Documentation mise à jour

#### Releases patch (selon besoins)
- Corrections critiques
- Patches sécurité
- Déployées rapidement
- Tests automatisés obligatoires

### Support des versions

#### LTS (Long Term Support)
- Version 1.x : Support jusqu'à version 3.0
- Corrections critiques uniquement
- Pas de nouvelles fonctionnalités

#### Versions courantes
- 3 dernières versions mineures supportées
- Corrections bugs et sécurité
- Migration path documentée

#### Versions obsolètes
- Support communautaire uniquement
- Documentation archivée
- Migration recommandée

### Communication des changements

#### Breaking Changes
```markdown
## ⚠️ BREAKING CHANGES in v2.0.0

### API Endpoints
- `POST /vectors/create` → `POST /vectors/` 
- Response format changed for `/search` endpoint

### Migration Guide
1. Update endpoint URLs in client code
2. Modify response parsing for search results
3. Run migration script: `python scripts/migrate_v2.py`
```

#### Deprecation Notices
```markdown
## 🚨 DEPRECATED in v1.5.0

### Functions
- `create_vector_legacy()` → Use `create_vector()` instead
- Will be removed in v2.0.0

### Configuration
- `LEGACY_MODE` setting deprecated
- Use new configuration format in .env
```

#### Security Updates
```markdown
## 🔒 SECURITY UPDATE v1.2.1

### CVE-2026-1234
- **Severity**: Medium
- **Component**: Authentication middleware
- **Impact**: Potential token validation bypass
- **Fix**: Upgrade immediately to v1.2.1+
```

### Automated versioning

#### GitHub Actions
```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Create Release
        uses: actions/create-release@v1
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          body_path: RELEASE_NOTES.md
```

#### Version bumping
```bash
# Scripts utilitaires
scripts/bump_version.py --major    # 1.0.0 → 2.0.0
scripts/bump_version.py --minor    # 1.0.0 → 1.1.0  
scripts/bump_version.py --patch    # 1.0.0 → 1.0.1
```

---

## 📅 Roadmap

### v1.1.0 (Q2 2026)
- **CRUD vecteurs complet** : GET, PUT, DELETE endpoints
- **Pagination avancée** : Cursors et offsets
- **Filtrage métadonnées** : Requêtes SQL dynamiques
- **Authentification** : JWT tokens et permissions

### v1.2.0 (Q3 2026)
- **Index HNSW optimisé** : Configuration paramètres avancés
- **Cache Redis** : Performance insertion/recherche
- **Batch operations** : Insertion/mise à jour en lot
- **Monitoring** : Métriques Prometheus intégrées

### v2.0.0 (Q4 2026)
- **Multi-tenant RLS** : Isolation données par tenant
- **Interface web** : Dashboard administration
- **API v2** : Endpoints restructurés et optimisés
- **Support clusters** : PostgreSQL haute disponibilité

---

*Changelog AindusDB Core - Dernière mise à jour : 2026-01-15*
