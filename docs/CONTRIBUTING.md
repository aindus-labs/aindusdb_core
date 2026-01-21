# 🤝 Guide de Contribution - AindusDB Core

Merci de votre intérêt pour contribuer à AindusDB Core ! Ce guide vous aidera à comprendre l'architecture du projet et le processus de contribution.

## 🏗️ Architecture du projet

### **📁 Structure des dossiers**

```
AindusDB_Core/
├── app/                          # Application principale
│   ├── core/                     # Configuration & DB
│   │   ├── config.py            # Settings Pydantic
│   │   └── database.py          # Gestionnaire PostgreSQL
│   ├── models/                   # Modèles de données
│   │   ├── vector.py            # Modèles vectoriels
│   │   └── health.py            # Modèles santé
│   ├── services/                 # Logique métier
│   │   ├── vector_service.py    # Services vectoriels
│   │   └── health_service.py    # Services monitoring
│   ├── routers/                  # Endpoints API
│   │   ├── vectors.py           # Routes vectorielles
│   │   └── health.py            # Routes santé
│   ├── dependencies/             # DI FastAPI
│   │   └── database.py          # Provider DB
│   └── main.py                  # Point d'entrée
├── tests/                        # Tests complets
│   ├── unit/                    # Tests unitaires
│   ├── integration/             # Tests d'intégration  
│   └── load/                    # Tests performance
├── docs/                         # Documentation
│   ├── INSTALLATION.md          # Guide installation
│   ├── CONTRIBUTING.md          # Ce fichier
│   └── API_EXAMPLES.md          # Exemples API
├── scripts/                      # Utilitaires
└── .github/workflows/            # CI/CD
```

### **🔄 Flux de données**

1. **Client** → **FastAPI Router** → **Service Layer** → **Database**
2. **Dependencies** injectent connexions DB dans les endpoints
3. **Models** valident entrées/sorties avec Pydantic
4. **Services** contiennent la logique métier PostgreSQL/pgvector

### **🧩 Composants principaux**

#### **Configuration (`app/core/`)**
- `config.py` : Settings centralisés avec Pydantic
- `database.py` : Pool de connexions asyncpg

#### **Modèles (`app/models/`)**  
- Modèles Pydantic pour validation API
- Séparation vectors/health pour clarté

#### **Services (`app/services/`)**
- Logique métier isolée des routers
- Opérations SQL avec asyncpg
- Gestion erreurs et transactions

#### **Routers (`app/routers/`)**
- Endpoints FastAPI avec OpenAPI complet
- Injection dépendances pour DB
- Validation automatique Pydantic

---

## 🛠️ Environnement de développement

### **Setup initial**

```bash
# 1. Fork et clone
git clone https://github.com/YOUR_USERNAME/AindusDB_Core.git
cd AindusDB_Core

# 2. Environnement Python
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. Dépendances
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Base de données de développement
docker-compose up -d postgres
# Attendre que PostgreSQL démarre

# 5. Configuration
cp .env.template .env
export DATABASE_URL="postgresql://aindusdb:aindusdb_secure_2026_change_me@localhost:5432/aindusdb_core"

# 6. Lancer l'API
uvicorn app.main:app --reload
```

### **Outils de développement**

```bash
# Formatage code
black app/ tests/
isort app/ tests/

# Linting
flake8 app/ tests/
mypy app/

# Tests
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest --cov=app --cov-report=html

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

---

## 📝 Standards de code

### **Style Python**
- **PEP 8** respecté avec Black (ligne 88 caractères)
- **Type hints** obligatoires pour fonctions publiques
- **Docstrings** Google style pour méthodes publiques
- **Import ordering** avec isort

### **Conventions nommage**
- **Variables/fonctions** : `snake_case`
- **Classes** : `PascalCase`
- **Constants** : `UPPER_CASE`
- **Fichiers** : `snake_case.py`

### **Exemple de fonction bien documentée**

```python
async def create_vector(
    db: AsyncConnection,
    embedding: List[float],
    metadata: Optional[str] = None
) -> VectorCreateResponse:
    """Create a new vector in the database.
    
    Args:
        db: Database connection from dependency injection
        embedding: Vector embedding as list of floats
        metadata: Optional metadata string
        
    Returns:
        VectorCreateResponse with created vector ID and status
        
    Raises:
        DatabaseError: If vector creation fails
        ValidationError: If embedding format invalid
    """
    try:
        # Implementation here
        pass
    except Exception as e:
        logger.error(f"Failed to create vector: {e}")
        raise DatabaseError("Vector creation failed") from e
```

---

## 🧪 Tests et qualité

### **Types de tests**

#### **Tests unitaires (`tests/unit/`)**
- Tests isolés sans dépendances externes
- Mocking des services/DB
- Couverture >90% visée

```python
def test_vector_model_validation():
    """Test vector model validates correctly."""
    vector_data = VectorCreate(
        embedding=[0.1, 0.2, 0.3],
        metadata="test"
    )
    assert len(vector_data.embedding) == 3
    assert vector_data.metadata == "test"
```

#### **Tests d'intégration (`tests/integration/`)**
- Tests avec vraie base PostgreSQL
- Vérification bout-en-bout
- Base de test isolée

```python
async def test_create_vector_integration(test_db):
    """Test vector creation with real database."""
    service = VectorService()
    response = await service.create_vector(
        test_db, [0.1, 0.2, 0.3], "integration_test"
    )
    assert response.status == "success"
```

#### **Tests de performance (`tests/load/`)**
- Benchmarks insertion/recherche
- Tests charge avec pytest-benchmark
- Métriques latence/throughput

### **Couverture de code**
- **Minimum** : 80% couverture globale
- **Objectif** : 90% pour nouveaux modules
- **Exclusions** : Fichiers config, migrations

```bash
# Rapport couverture
pytest --cov=app --cov-report=html
# Ouvrir htmlcov/index.html
```

---

## 🚀 Processus de contribution

### **1. Préparation**
```bash
# Créer branch feature
git checkout -b feature/nom-fonctionnalite
git checkout -b fix/nom-bug
git checkout -b docs/amelioration-doc
```

### **2. Développement**
1. **Code** : Implémenter avec tests
2. **Tests** : Écrire tests unitaires/intégration
3. **Documentation** : Mettre à jour docs si nécessaire
4. **Qualité** : Linter + formater le code

```bash
# Validation avant commit
black app/ tests/
isort app/ tests/
flake8 app/ tests/
mypy app/
pytest tests/unit/ -v
```

### **3. Commit et Push**
```bash
# Commits atomiques avec messages clairs
git add .
git commit -m "feat: add vector similarity search endpoint

- Add /vectors/search POST endpoint
- Implement cosine similarity with pgvector
- Add pagination and filtering
- Include comprehensive tests and docs"

git push origin feature/nom-fonctionnalite
```

### **4. Pull Request**
- **Titre clair** décrivant le changement
- **Description** avec contexte et tests effectués
- **Checklist** complétée
- **Screenshots** si UI impactée

#### **Template PR**
```markdown
## Description
Brief description of changes

## Type of change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)  
- [ ] Breaking change (fix/feature causing existing functionality to change)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] Tests added/updated
```

### **5. Review process**
1. **Automated checks** : CI/CD doit passer
2. **Code review** : Au moins 1 approbation
3. **Manual testing** : Si applicable
4. **Merge** : Squash commits préféré

---

## 🏷️ Conventions Git

### **Types de commits**
- `feat:` Nouvelle fonctionnalité
- `fix:` Correction de bug
- `docs:` Documentation uniquement
- `style:` Formatage, pas de changement logique
- `refactor:` Refactoring sans nouvelle fonctionnalité
- `test:` Ajout/modification tests
- `chore:` Maintenance (dépendances, config)

### **Branches**
- `main` : Version stable production
- `develop` : Développement principal (si utilisé)
- `feature/*` : Nouvelles fonctionnalités
- `fix/*` : Corrections de bugs
- `docs/*` : Améliorations documentation

---

## 📊 Monitoring et debugging

### **Logs application**
```python
import logging

logger = logging.getLogger(__name__)

# Dans les services
logger.info(f"Creating vector with {len(embedding)} dimensions")
logger.error(f"Database error: {e}", exc_info=True)
```

### **Métriques performance**
- Temps réponse endpoints
- Utilisation mémoire
- Connexions DB actives
- Erreurs par endpoint

### **Debugging local**
```bash
# Logs application
docker-compose logs -f api

# Logs PostgreSQL
docker-compose logs -f postgres

# Connexion directe DB
docker exec -it aindusdb_postgres_1 psql -U aindusdb -d aindusdb_core
```

---

## 🎯 Domaines de contribution

### **🔧 Core Features**
- Implémentation CRUD vecteurs complet
- Optimisation requêtes pgvector
- Support index HNSW/IVFFlat
- Pagination et filtrage avancé

### **🚀 Performance**
- Cache Redis pour embeddings
- Connection pooling optimisé  
- Compression vecteurs
- Benchmarks et profiling

### **📖 Documentation**
- Guides d'usage avancés
- Tutoriels intégration
- Exemples concrets
- Documentation API complète

### **🧪 Tests**
- Tests end-to-end
- Tests de charge
- Tests multi-plateforme
- Coverage amélioration

### **🛠️ DevOps**
- Optimisation Docker
- Déploiement Kubernetes
- Monitoring Prometheus
- CI/CD améliorations

---

## 🙋‍♂️ Support et questions

- **GitHub Issues** : Bugs et demandes de fonctionnalités
- **GitHub Discussions** : Questions générales et aide
- **Code Review** : Commentaires sur PR pour apprentissage
- **Documentation** : README et docs/ pour référence

### **Bonnes pratiques issues**
- **Template** utilisé pour structure
- **Labels** appropriés (bug, enhancement, documentation)
- **Contexte complet** avec étapes reproduction
- **Environnement** spécifié (OS, versions)

---

**Merci de contribuer à AindusDB Core ! 🚀**

*Guide de contribution - Version 1.0.0*
