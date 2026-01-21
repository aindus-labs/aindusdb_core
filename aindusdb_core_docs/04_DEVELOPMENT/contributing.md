# 🤝 CONTRIBUTING GUIDE - AINDUSDB CORE

**Version** : 1.0.0  
**Niveau** : Guide Contributeurs  
**Date** : 21 janvier 2026  

---

## 🎯 **INTRODUCTION**

Guide complet pour contribuer au projet AindusDB Core. Nous apprécions votre intérêt à améliorer cette base de données vectorielle enterprise-grade !

### **🏆 NOS VALEURS**
- **Excellence Technique** : Code de haute qualité, testé et documenté
- **Collaboration** : Esprit d'équipe et communication ouverte
- **Innovation** : Créativité et nouvelles idées bienvenues
- **Sécurité** : Priorité absolue à chaque niveau
- **Performance** : Optimisation continue et scalabilité

---

## 🚀 **PREMIERS PAS**

### **📋 Prérequis**
```bash
# Requirements techniques
- Python 3.11+
- Docker & Docker Compose
- Git 2.30+
- PostgreSQL 14+ avec pgvector
- Redis 6+
- Node.js 18+ (pour développement frontend)

# Outils recommandés
- VS Code avec extensions Python/Docker
- Postman ou Insomnia pour tests API
- DBeaver ou pgAdmin pour base de données
```

### **🔧 Installation Environnement**
```bash
# 1. Forker le repository
git clone https://github.com/VOTRE_USERNAME/aindusdb_core.git
cd aindusdb_core

# 2. Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# 3. Installer dépendances
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Configuration environnement
cp .env.template .env
# Éditer .env avec vos configurations

# 5. Démarrer services
docker-compose up -d postgres redis

# 6. Appliquer migrations
alembic upgrade head

# 7. Lancer tests
pytest tests/
```

---

## 🏗️ **ARCHITECTURE PROJET**

### **📊 Structure Code**
```
aindusdb_core/
├── app/                    # Application principale
│   ├── core/              # Services centraux
│   │   ├── config.py      # Configuration
│   │   ├── database.py    # Gestion BDD
│   │   ├── security.py    # Sécurité
│   │   ├── cqrs/          # Pattern CQRS
│   │   └── resilience/    # Patterns résilience
│   ├── models/            # Modèles Pydantic
│   ├── services/          # Logique métier
│   ├── routers/           # API endpoints
│   ├── middleware/        # Middlewares
│   └── main.py           # Point d'entrée
├── tests/                 # Tests
├── docs/                  # Documentation
├── scripts/               # Scripts utilitaires
└── aindusdb_core_docs/   # Documentation mondiale
```

### **🔄 Patterns Implémentés**
- **CQRS** : Séparation commandes/queries
- **Event Sourcing** : Audit immuable
- **Circuit Breaker** : Résilience automatique
- **Repository** : Abstraction données
- **Dependency Injection** : Découplage maximal

---

## 🌟 **TYPES DE CONTRIBUTIONS**

### **🐛 Rapports de Bugs**
```bash
# Template rapport bug
## Description
[Bug description claire et concise]

## Étapes pour reproduire
1. Aller sur...
2. Cliquer sur...
3. Voir erreur...

## Comportement attendu
[Ce qui devrait se passer]

## Comportement actuel
[Ce qui se passe réellement]

## Environnement
- OS: [Ubuntu 22.04]
- Python: [3.11.0]
- Version: [v1.0.0]

## Logs/Erreurs
```

### **✨ Nouvelles Fonctionnalités**
```bash
# Processus nouvelle fonctionnalité
1. Issue: Créer issue avec description fonctionnalité
2. Design: Discuter architecture dans issue
3. Branche: git checkout -b feature/nouvelle-fonction
4. Développement: Implémenter avec tests
5. Documentation: Mettre à jour docs
6. Tests: pytest && bandit && safety
7. PR: Pull request avec template complété
```

### **📚 Documentation**
```bash
# Types documentation acceptés
- Code comments et docstrings
- README et guides
- Documentation API (OpenAPI)
- Tutoriels et exemples
- Architecture diagrams
- Procédures opérationnelles
```

### **🧪 Tests**
```bash
# Types de tests
- Unit tests: pytest tests/unit/
- Integration tests: pytest tests/integration/
- Performance tests: pytest tests/load/
- Security tests: pytest tests/security/
- End-to-end tests: pytest tests/e2e/
```

---

## 🛠️ **DÉVELOPPEMENT LOCAL**

### **🔧 Configuration Développement**
```python
# config/development.py
from app.core.config import Settings

class DevelopmentSettings(Settings):
    debug: bool = True
    database_url: str = "postgresql://postgres:password@localhost:5432/aindusdb_dev"
    redis_url: str = "redis://localhost:6379/0"
    
    # Logging développement
    log_level: str = "DEBUG"
    log_format: str = "detailed"
    
    # Features développement
    auto_reload: bool = True
    debug_toolbar: bool = True
    profiling: bool = True

settings = DevelopmentSettings()
```

### **🚀 Lancer Services**
```bash
# Option 1: Docker Compose (recommandé)
docker-compose -f docker-compose.dev.yml up

# Option 2: Manuel
# Terminal 1: PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=aindusdb_dev \
  -p 5432:5432 \
  ankane/pgvector:latest

# Terminal 2: Redis
docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine

# Terminal 3: Application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 4: Frontend (si applicable)
cd frontend && npm run dev
```

### **🧪 Exécuter Tests**
```bash
# Tous les tests
pytest

# Tests avec couverture
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/unit/test_vector_service.py

# Tests avec markers
pytest -m "unit and not slow"

# Tests performance
pytest tests/load/ --benchmark-only
```

---

## 📝 **STANDARDS DE CODE**

### **🐍 Style Python**
```python
# Suivre PEP 8 et Black formatting
import asyncio
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.models.vector import VectorCreate, VectorResponse


class VectorService:
    """Service pour gestion des vecteurs.
    
    Ce service gère la création, recherche et manipulation
    de vecteurs avec validation et optimisation.
    """
    
    def __init__(self) -> None:
        self.database = DatabaseManager()
        self.cache = CacheManager()
    
    async def create_vector(
        self, 
        vector_data: VectorCreate,
        user_id: UUID
    ) -> VectorResponse:
        """Créer un nouveau vecteur.
        
        Args:
            vector_data: Données du vecteur à créer
            user_id: ID de l'utilisateur créateur
            
        Returns:
            VectorResponse: Vecteur créé
            
        Raises:
            ValidationError: Si données invalides
            DatabaseError: Si erreur base de données
        """
        try:
            # Validation
            if len(vector_data.content) > 10000:
                raise HTTPException(
                    status_code=400,
                    detail="Content too long"
                )
            
            # Génération embedding
            embedding = await self.generate_embedding(
                vector_data.content
            )
            
            # Sauvegarde
            vector = await self.database.create_vector({
                "content": vector_data.content,
                "embedding": embedding,
                "metadata": vector_data.metadata,
                "user_id": user_id
            })
            
            # Cache
            await self.cache.set(
                f"vector:{vector.id}",
                vector,
                ttl=300
            )
            
            return VectorResponse.from_orm(vector)
            
        except Exception as e:
            logger.error(f"Error creating vector: {e}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )
```

### **📝 Documentation Code**
```python
def calculate_similarity(
    vector1: List[float], 
    vector2: List[float],
    metric: str = "cosine"
) -> float:
    """Calculer similarité entre deux vecteurs.
    
    Cette fonction implémente plusieurs métriques de similarité
    pour comparer des vecteurs dans un espace multidimensionnel.
    
    Args:
        vector1: Premier vecteur
        vector2: Second vecteur  
        metric: Métrique à utiliser ("cosine", "euclidean", "dotproduct")
        
    Returns:
        Score de similarité entre 0.0 et 1.0
        
    Raises:
        ValueError: Si vecteurs de dimensions différentes
        
    Example:
        >>> v1 = [1.0, 0.0, 0.0]
        >>> v2 = [0.0, 1.0, 0.0]
        >>> similarity = calculate_similarity(v1, v2, "cosine")
        >>> print(f"Similarity: {similarity:.3f}")
        Similarity: 0.000
    """
    if len(vector1) != len(vector2):
        raise ValueError("Vectors must have same dimension")
    
    if metric == "cosine":
        return self._cosine_similarity(vector1, vector2)
    elif metric == "euclidean":
        return self._euclidean_similarity(vector1, vector2)
    elif metric == "dotproduct":
        return self._dot_product_similarity(vector1, vector2)
    else:
        raise ValueError(f"Unknown metric: {metric}")
```

### **🧪 Tests Standards**
```python
# tests/unit/test_vector_service.py
import pytest
from unittest.mock import AsyncMock, patch

from app.services.vector_service import VectorService
from app.models.vector import VectorCreate
from app.core.exceptions import ValidationError


class TestVectorService:
    """Tests pour VectorService."""
    
    @pytest.fixture
    def vector_service(self):
        """Fixture pour VectorService."""
        return VectorService()
    
    @pytest.fixture
    def sample_vector(self):
        """Fixture pour vecteur exemple."""
        return VectorCreate(
            content="Test content",
            metadata={"category": "test"},
            content_type="text"
        )
    
    @pytest.mark.asyncio
    async def test_create_vector_success(
        self, 
        vector_service, 
        sample_vector
    ):
        """Test création vecteur réussie."""
        # Arrange
        user_id = "test-user-id"
        
        # Act
        result = await vector_service.create_vector(
            sample_vector, 
            user_id
        )
        
        # Assert
        assert result.content == sample_vector.content
        assert result.metadata == sample_vector.metadata
        assert result.id is not None
        assert result.created_at is not None
    
    @pytest.mark.asyncio
    async def test_create_vector_content_too_long(
        self, 
        vector_service
    ):
        """Test erreur contenu trop long."""
        # Arrange
        long_content = "x" * 10001
        vector_data = VectorCreate(content=long_content)
        user_id = "test-user-id"
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc:
            await vector_service.create_vector(vector_data, user_id)
        
        assert exc.value.status_code == 400
        assert "too long" in str(exc.value.detail)
    
    @pytest.mark.asyncio
    @patch("app.services.vector_service.VectorService.generate_embedding")
    async def test_create_vector_embedding_error(
        self,
        mock_generate_embedding,
        vector_service,
        sample_vector
    ):
        """Test erreur génération embedding."""
        # Arrange
        mock_generate_embedding.side_effect = Exception("Embedding failed")
        user_id = "test-user-id"
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc:
            await vector_service.create_vector(sample_vector, user_id)
        
        assert exc.value.status_code == 500
```

---

## 🔒 **SÉCURITÉ**

### **🛡️ Guidelines Sécurité**
```python
# Toujours valider les entrées
def validate_user_input(user_input: str) -> str:
    """Valider et nettoyer entrée utilisateur."""
    if not user_input or len(user_input) > 1000:
        raise ValueError("Invalid input")
    
    # Nettoyer entrée
    cleaned = bleach.clean(user_input)
    
    # Vérifier patterns dangereux
    dangerous_patterns = [
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"eval\(",
        r"exec\("
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, cleaned, re.IGNORECASE):
            raise ValueError("Dangerous content detected")
    
    return cleaned

# Toujours utiliser paramètres SQL
async def get_user_vectors(user_id: str, limit: int = 10):
    """Récupérer vecteurs utilisateur."""
    query = """
        SELECT id, content, metadata, created_at
        FROM vectors 
        WHERE user_id = $1 
        ORDER BY created_at DESC 
        LIMIT $2
    """
    return await database.fetch_all(query, user_id, limit)

# Toujours chiffrer données sensibles
def encrypt_sensitive_data(data: str) -> str:
    """Chiffrer données sensibles."""
    key = settings.encryption_key
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()
```

### **🔍 Security Review Checklist**
```bash
# Avant chaque PR
□ Validation entrées utilisateur
□ Paramètres SQL (pas de concaténation)
□ Chiffrement données sensibles
□ Permissions appropriées
□ Pas de secrets dans code
□ Rate limiting implémenté
□ Headers sécurité configurés
□ Logs sans données sensibles
□ Dependencies à jour
□ Tests sécurité passent
```

---

## 📊 **PERFORMANCE**

### **⚡ Guidelines Performance**
```python
# Utiliser async/await pour I/O
async def process_vectors_batch(vectors: List[VectorCreate]):
    """Traiter batch de vecteurs en parallèle."""
    tasks = [
        process_single_vector(vector) 
        for vector in vectors
    ]
    return await asyncio.gather(*tasks)

# Utiliser cache intelligemment
@lru_cache(maxsize=1000)
def expensive_calculation(param: str) -> float:
    """Calcul coûteux avec cache."""
    return complex_math_operation(param)

# Optimiser requêtes SQL
async def get_vectors_with_metadata(
    limit: int = 10,
    offset: int = 0
):
    """Requête optimisée avec pagination."""
    query = """
        SELECT v.id, v.content, v.metadata
        FROM vectors v
        WHERE v.created_at > NOW() - INTERVAL '30 days'
        ORDER BY v.created_at DESC
        LIMIT $1 OFFSET $2
    """
    return await database.fetch_all(query, limit, offset)

# Profiler code identifié
@cprofile
def slow_function():
    """Fonction lente à optimiser."""
    pass
```

### **📈 Monitoring Performance**
```python
# Métriques personnalisées
from prometheus_client import Counter, Histogram, Gauge

# Compteurs métier
vector_operations = Counter(
    'vector_operations_total',
    'Total vector operations',
    ['operation_type', 'status']
)

# Histogrammes performance
search_duration = Histogram(
    'vector_search_duration_seconds',
    'Vector search duration',
    ['search_type']
)

# Gauges état système
active_connections = Gauge(
    'database_connections_active',
    'Active database connections'
)

# Utilisation dans code
async def search_vectors(query: str):
    start_time = time.time()
    
    try:
        results = await database.search(query)
        vector_operations.labels(
            operation_type='search',
            status='success'
        ).inc()
        return results
    except Exception as e:
        vector_operations.labels(
            operation_type='search',
            status='error'
        ).inc()
        raise
    finally:
        search_duration.labels(
            search_type='semantic'
        ).observe(time.time() - start_time)
```

---

## 🔄 **PROCESSUS PULL REQUEST**

### **📋 Template PR**
```markdown
## Description
[Brief description des changements]

## Type de changement
- [ ] Bug fix
- [ ] Nouvelle fonctionnalité
- [ ] Breaking change
- [ ] Documentation
- [ ] Performance
- [ ] Sécurité

## Tests
- [ ] Unit tests passent
- [ ] Integration tests passent
- [ ] Manual tests effectués
- [ ] Performance tests OK

## Checklist
- [ ] Code suit les standards du projet
- [ ] Self-review du code complété
- [ ] Documentation mise à jour
- [ ] Messages commits clairs
- [ ] Pas de merge conflicts
- [ ] Tests ajoutés si nécessaire

## Issues closes
Closes #123
```

### **🔍 Review Process**
```bash
# 1. Auto-checks (GitHub Actions)
- Tests passent
- Sécurité OK
- Coverage > 80%
- Linting OK

# 2. Review technique
- Architecture appropriée
- Performance OK
- Sécurité validée
- Tests complets

# 3. Review fonctionnel
- Spécifications respectées
- UX cohérente
- Documentation claire
- Examples fonctionnels

# 4. Approbation
- Au moins 2 reviews
- Maintainer approval
- CI/CD vert
- Ready to merge
```

---

## 📚 **DOCUMENTATION**

### **📝 Types Documentation**
```markdown
# 1. Code Documentation
- Docstrings complètes
- Comments complexes
- Type hints partout

# 2. API Documentation
- OpenAPI specification
- Examples pour chaque endpoint
- Error documentation

# 3. Architecture Documentation
- Diagrams (Mermaid)
- Design decisions
- Trade-offs expliqués

# 4. User Documentation
- Getting started guide
- Tutorials
- FAQ
```

### **🔧 Documentation Tools**
```bash
# Génération documentation
mkdocs build

# Vérification liens
markdown-link-check docs/

# Spell check
cspell docs/**/*.md

# Formatage
markdownlint docs/**/*.md
```

---

## 🌟 **COMMUNAUTÉ**

### **💬 Communication**
```bash
# Canaux communication
- GitHub Issues: Bugs et fonctionnalités
- GitHub Discussions: Questions générales
- Slack: #aindusdb-contributors
- Email: contributors@aindusdb.io

# Guidelines communication
- Respect et professionnalisme
- Langage: Anglais (préféré) ou Français
- Response time: 48h maximum
- Constructive feedback
```

### **🏆 Reconnaissance**
```bash
# Types contributions reconnues
- Code contributions
- Documentation
- Bug reports
- Feature suggestions
- Community support
- Security research

# Reconnaissance
- Contributors README
- Release notes
- Blog posts
- Conference talks
- Swag stickers!
```

---

## 🚀 **DEVENIR MAINTAINER**

### **📋 Critères Maintainer**
```bash
# Requirements
- 10+ contributions mergées
- Participation active 6+ mois
- Connaissance architecture
- Reviews qualité
- Leadership technique
- Esprit collaboratif

# Processus
1. Nomination par maintainer existant
2. Review par équipe
3. Vote communauté
4. Onboarding officiel
5. Accès droits étendus
```

---

## 🎯 **RESSOURCES**

### **📚 Documentation Utile**
- [Python Style Guide](https://pep8.org/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/)
- [PostgreSQL Performance](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/cluster-administration/)

### **🛠️ Outils Recommandés**
- **IDE**: VS Code + Python extension
- **Testing**: pytest + coverage
- **Linting**: black + isort + flake8
- **Security**: bandit + safety
- **Documentation**: mkdocs + mkdocstrings
- **CI/CD**: GitHub Actions

### **📖 Apprentissage**
- [Python Async/Await](https://docs.python.org/3/library/asyncio.html)
- [Kubernetes Basics](https://kubernetes.io/docs/tutorials/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [API Design](https://restfulapi.net/)

---

## 🤝 **MERCI !**

Merci de votre intérêt à contribuer à AindusDB Core ! Votre participation est essentielle pour faire de ce projet un succès.

### **📞 Contact**
- **Questions**: GitHub Discussions
- **Urgences**: security@aindusdb.io
- **Partenariats**: partnerships@aindusdb.io

### **🌟 Prochaines Étapes**
1. Forker le repository
2. Configurer environnement local
3. Choisir une issue à travailler
4. Créer une branche
5. Développer et tester
6. Soumettre une PR

**Nous avons hâte de voir vos contributions !** 🚀

---

*Contributing Guide - 21 janvier 2026*  
*Community-Driven Development*
