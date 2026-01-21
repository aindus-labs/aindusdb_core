# Référence API Complète - AindusDB Core

**Version:** 1.0  
**Date:** 21/01/2026  
**Auteur:** Équipe AindusDB  
**Statut:** En rédaction  

---

## 📚 Vue d'ensemble

L'API AindusDB Core fournit des endpoints RESTful pour l'indexation vectorielle, les calculs VERITAS, et la gestion des données.

---

## 🔐 Authentification

### Bearer Token

```http
Authorization: Bearer <jwt_token>
```

### Exemple de Token

```json
{
  "sub": "user123",
  "roles": ["developer"],
  "permissions": ["read", "write"],
  "iat": 1642771200,
  "exp": 1642774800,
  "iss": "aindusdb-core-auth",
  "aud": "aindusdb-core-services"
}
```

---

## 🚀 Endpoints Principaux

### Base URL
```
https://api.aindusdb.com/v1
```

### Headers Communs
```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer <token>
X-Request-ID: <unique_id>
```

---

## 📊 Endpoints Vectoriels

### Créer un Index

```http
POST /v1/vectors/indexes
```

**Corps de la requête:**
```json
{
  "name": "documents",
  "dimension": 1536,
  "metric": "cosine",
  "metadata_config": {
    "indexed": ["category", "date"]
  }
}
```

**Réponse:**
```json
{
  "id": "idx_123456",
  "name": "documents",
  "dimension": 1536,
  "metric": "cosine",
  "status": "initializing",
  "created_at": "2024-01-21T10:00:00Z",
  "updated_at": "2024-01-21T10:00:00Z"
}
```

### Insérer des Vecteurs

```http
POST /v1/vectors/indexes/{index_id}/upsert
```

**Corps de la requête:**
```json
{
  "vectors": [
    {
      "id": "doc_001",
      "values": [0.1, 0.2, 0.3, ...],
      "metadata": {
        "title": "Document 1",
        "category": "finance",
        "date": "2024-01-20"
      }
    },
    {
      "id": "doc_002",
      "values": [0.4, 0.5, 0.6, ...],
      "metadata": {
        "title": "Document 2",
        "category": "tech",
        "date": "2024-01-21"
      }
    }
  ]
}
```

**Réponse:**
```json
{
  "upserted_count": 2,
  "failed_count": 0,
  "errors": []
}
```

### Rechercher des Vecteurs

```http
POST /v1/vectors/indexes/{index_id}/query
```

**Corps de la requête:**
```json
{
  "vector": [0.1, 0.2, 0.3, ...],
  "top_k": 10,
  "include_metadata": true,
  "include_values": false,
  "filter": {
    "category": {"$eq": "finance"},
    "date": {"$gte": "2024-01-01"}
  }
}
```

**Réponse:**
```json
{
  "matches": [
    {
      "id": "doc_001",
      "score": 0.95,
      "metadata": {
        "title": "Document 1",
        "category": "finance",
        "date": "2024-01-20"
      }
    }
  ],
  "namespace": "",
  "usage": {
    "read_units": 5
  }
}
```

### Supprimer des Vecteurs

```http
DELETE /v1/vectors/indexes/{index_id}/vectors
```

**Corps de la requête:**
```json
{
  "ids": ["doc_001", "doc_002"],
  "delete_all": false,
  "filter": {
    "category": {"$eq": "archived"}
  }
}
```

**Réponse:**
```json
{
  "deleted_count": 2
}
```

---

## 🧮 Endpoints VERITAS

### Calcul avec Preuve

```http
POST /v1/veritas/calculate
```

**Corps de la requête:**
```json
{
  "query": "sqrt(16) + 3^2",
  "variables": {
    "x": 10,
    "y": 20
  },
  "verification_level": "standard",
  "include_proof": true
}
```

**Réponse:**
```json
{
  "answer": "13.0",
  "veritas_proof": {
    "proof_id": "vp_789012",
    "computation_steps": [
      {
        "step": 1,
        "operation": "sqrt",
        "input": "16",
        "result": "4.0"
      },
      {
        "step": 2,
        "operation": "power",
        "input": "3^2",
        "result": "9.0"
      },
      {
        "step": 3,
        "operation": "addition",
        "input": "4.0 + 9.0",
        "result": "13.0"
      }
    ],
    "confidence_score": 0.9999,
    "verification_hash": "a1b2c3d4e5f6...",
    "created_at": "2024-01-21T10:05:00Z"
  },
  "execution_time_ms": 150
}
```

### Vérifier une Preuve

```http
POST /v1/veritas/verify/{proof_id}
```

**Réponse:**
```json
{
  "is_valid": true,
  "verification_details": {
    "mathematical_validity": true,
    "cryptographic_integrity": true,
    "verification_timestamp": "2024-01-21T10:06:00Z",
    "verifier": "veritas-engine-v2.1"
  },
  "confidence_score": 0.9999
}
```

### Historique des Calculs

```http
GET /v1/veritas/calculations
```

**Paramètres de requête:**
- `limit`: Nombre de résultats (défaut: 20, max: 100)
- `offset`: Pagination (défaut: 0)
- `start_date`: Date de début (ISO 8601)
- `end_date`: Date de fin (ISO 8601)
- `verification_level`: Filtre par niveau

**Réponse:**
```json
{
  "calculations": [
    {
      "id": "calc_001",
      "query": "sqrt(16) + 3^2",
      "answer": "13.0",
      "verification_level": "standard",
      "created_at": "2024-01-21T10:05:00Z",
      "proof_id": "vp_789012"
    }
  ],
  "total_count": 1,
  "has_more": false
}
```

---

## 📈 Endpoints de Monitoring

### Statistiques de l'Index

```http
GET /v1/vectors/indexes/{index_id}/stats
```

**Réponse:**
```json
{
  "index_id": "idx_123456",
  "vector_count": 10000,
  "dimension": 1536,
  "index_size_mb": 125.5,
  "index_fullness": 0.1,
  "total_requests": 50000,
  "last_updated": "2024-01-21T10:00:00Z"
}
```

### Métriques d'Utilisation

```http
GET /v1/usage/metrics
```

**Paramètres de requête:**
- `period`: hour/day/week/month
- `start_date`: Date de début
- `end_date`: Date de fin

**Réponse:**
```json
{
  "period": "day",
  "metrics": {
    "vector_operations": {
      "upserts": 1000,
      "queries": 5000,
      "deletes": 50
    },
    "veritas_operations": {
      "calculations": 200,
      "verifications": 180
    },
    "storage": {
      "vectors_gb": 10.5,
      "metadata_gb": 2.3,
      "proofs_gb": 0.8
    },
    "cost": {
      "compute_units": 15000,
      "storage_units": 13000,
      "estimated_cost_usd": 25.50
    }
  }
}
```

---

## 👥 Endpoints de Gestion

### Informations Utilisateur

```http
GET /v1/users/me
```

**Réponse:**
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "roles": ["developer"],
  "permissions": ["read", "write"],
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-21T09:30:00Z",
  "usage_quota": {
    "current": 15000,
    "limit": 100000,
    "reset_date": "2024-02-01"
  }
}
```

### Clés API

```http
GET /v1/users/keys
```

**Réponse:**
```json
{
  "keys": [
    {
      "id": "key_001",
      "name": "Production Key",
      "prefix": "aind_...",
      "created_at": "2024-01-01T00:00:00Z",
      "last_used": "2024-01-21T10:00:00Z",
      "expires_at": "2025-01-01T00:00:00Z",
      "permissions": ["read", "write"]
    }
  ]
}
```

### Créer une Clé API

```http
POST /v1/users/keys
```

**Corps de la requête:**
```json
{
  "name": "New Key",
  "expires_in_days": 365,
  "permissions": ["read"],
  "ip_whitelist": ["192.168.1.0/24"]
}
```

**Réponse:**
```json
{
  "id": "key_002",
  "name": "New Key",
  "key": "aind_abcdef123456...",
  "expires_at": "2025-01-21T00:00:00Z",
  "permissions": ["read"]
}
```

---

## 🚨 Gestion des Erreurs

### Format d'Erreur

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request is invalid",
    "details": {
      "field": "vector",
      "reason": "Dimension mismatch"
    },
    "request_id": "req_123456",
    "timestamp": "2024-01-21T10:00:00Z"
  }
}
```

### Codes d'Erreur

| Code | HTTP | Description |
|------|------|-------------|
| `INVALID_REQUEST` | 400 | Requête invalide |
| `UNAUTHORIZED` | 401 | Non authentifié |
| `FORBIDDEN` | 403 | Permissions insuffisantes |
| `NOT_FOUND` | 404 | Ressource non trouvée |
| `RATE_LIMITED` | 429 | Limite de débit dépassée |
| `INTERNAL_ERROR` | 500 | Erreur interne |
| `SERVICE_UNAVAILABLE` | 503 | Service indisponible |

---

## 📝 Exemples de Code

### Python

```python
import requests
import json

class AindusDBClient:
    def __init__(self, api_key, base_url="https://api.aindusdb.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def create_index(self, name, dimension, metric="cosine"):
        """Crée un nouvel index vectoriel"""
        url = f"{self.base_url}/vectors/indexes"
        data = {
            "name": name,
            "dimension": dimension,
            "metric": metric
        }
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()
    
    def upsert_vectors(self, index_id, vectors):
        """Insère des vecteurs dans un index"""
        url = f"{self.base_url}/vectors/indexes/{index_id}/upsert"
        data = {"vectors": vectors}
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()
    
    def query_vectors(self, index_id, query_vector, top_k=10):
        """Recherche des vecteurs similaires"""
        url = f"{self.base_url}/vectors/indexes/{index_id}/query"
        data = {
            "vector": query_vector,
            "top_k": top_k,
            "include_metadata": True
        }
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()
    
    def calculate_veritas(self, query, variables=None, level="standard"):
        """Effectue un calcul avec preuve VERITAS"""
        url = f"{self.base_url}/veritas/calculate"
        data = {
            "query": query,
            "variables": variables or {},
            "verification_level": level,
            "include_proof": True
        }
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()

# Exemple d'utilisation
client = AindusDBClient(api_key="your_api_key")

# Créer un index
index = client.create_index("documents", 1536)
index_id = index["id"]

# Insérer des vecteurs
vectors = [
    {
        "id": "doc1",
        "values": [0.1] * 1536,
        "metadata": {"title": "Doc 1"}
    }
]
result = client.upsert_vectors(index_id, vectors)

# Rechercher
results = client.query_vectors(index_id, [0.1] * 1536)

# Calcul VERITAS
calc_result = client.calculate_veritas("sqrt(16) + 3^2")
print(calc_result["answer"])  # 13.0
```

### JavaScript

```javascript
class AindusDBClient {
    constructor(apiKey, baseUrl = 'https://api.aindusdb.com/v1') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }

    async createIndex(name, dimension, metric = 'cosine') {
        const response = await fetch(`${this.baseUrl}/vectors/indexes`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({ name, dimension, metric })
        });
        return response.json();
    }

    async upsertVectors(indexId, vectors) {
        const response = await fetch(`${this.baseUrl}/vectors/indexes/${indexId}/upsert`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({ vectors })
        });
        return response.json();
    }

    async queryVectors(indexId, queryVector, topK = 10) {
        const response = await fetch(`${this.baseUrl}/vectors/indexes/${indexId}/query`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                vector: queryVector,
                top_k: topK,
                include_metadata: true
            })
        });
        return response.json();
    }

    async calculateVeritas(query, variables = {}, level = 'standard') {
        const response = await fetch(`${this.baseUrl}/veritas/calculate`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                query,
                variables,
                verification_level: level,
                include_proof: true
            })
        });
        return response.json();
    }
}

// Exemple d'utilisation
const client = new AindusDBClient('your_api_key');

// Créer un index
const index = await client.createIndex('documents', 1536);

// Rechercher des vecteurs
const results = await client.queryVectors(index.id, Array(1536).fill(0.1));
console.log(results.matches);
```

### cURL

```bash
# Créer un index
curl -X POST https://api.aindusdb.com/v1/vectors/indexes \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "documents",
    "dimension": 1536,
    "metric": "cosine"
  }'

# Insérer des vecteurs
curl -X POST https://api.aindusdb.com/v1/vectors/indexes/idx_123456/upsert \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [
      {
        "id": "doc1",
        "values": [0.1, 0.2, 0.3],
        "metadata": {"title": "Document 1"}
      }
    ]
  }'

# Calcul VERITAS
curl -X POST https://api.aindusdb.com/v1/veritas/calculate \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "sqrt(16) + 3^2",
    "verification_level": "standard",
    "include_proof": true
  }'
```

---

## 🔄 Limites et Quotas

### Limites par Défaut

| Ressource | Limite |
|-----------|--------|
| Dimension maximale | 20000 |
| Taille de batch | 1000 vecteurs |
| Requêtes/minute | 1000 |
| Stockage | 100 GB |
| Calculs VERITAS/jour | 10000 |

### Headers de Limitation

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642774800
```

---

## 📚 SDKs Officiels

- Python: `pip install aindusdb`
- JavaScript: `npm install aindusdb`
- Go: `go get github.com/aindusdb/go-client`
- Java: Maven/Gradle disponible
- Ruby: `gem install aindusdb`

---

## 🔄 Changelog API

### v1.0 (2024-01-21)
- Version initiale de l'API
- Support des vecteurs et VERITAS
- Authentification JWT

### v1.1 (Prévu)
- Support du streaming
- Filtres avancés
- Métriques étendues

---

**Document maintenu par l'équipe AindusDB Core**  
**Dernière mise à jour:** 21/01/2026
