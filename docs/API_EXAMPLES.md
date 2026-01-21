# 📚 Guide d'utilisation API - AindusDB Core

Ce guide présente des exemples pratiques d'utilisation de l'API AindusDB Core avec différents langages et outils.

## 🌐 Accès à la documentation interactive

Une fois AindusDB Core démarré, accédez à :
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc
- **OpenAPI JSON** : http://localhost:8000/openapi.json

---

## 🔍 Endpoints disponibles

### **Monitoring et santé**
- `GET /` - Message de bienvenue
- `GET /health` - Vérification santé complète
- `GET /status` - Statut détaillé du système
- `GET /metrics` - Métriques de performance

### **Opérations vectorielles**
- `POST /vectors/test` - Test des capacités pgvector
- `POST /vectors/` - Créer un nouveau vecteur
- `POST /vectors/search` - Recherche de similarité

---

## 🐍 Exemples Python

### **Installation des dépendances**
```bash
pip install requests httpx aiohttp
```

### **Client Python synchrone**

```python
import requests
import json
from typing import List, Optional

class AindusDBClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self) -> dict:
        """Vérifier la santé du système."""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def test_vectors(self) -> dict:
        """Tester les opérations vectorielles."""
        response = self.session.post(f"{self.base_url}/vectors/test")
        response.raise_for_status()
        return response.json()
    
    def create_vector(self, embedding: List[float], metadata: Optional[str] = None) -> dict:
        """Créer un nouveau vecteur."""
        payload = {"embedding": embedding}
        if metadata:
            payload["metadata"] = metadata
            
        response = self.session.post(
            f"{self.base_url}/vectors/",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def search_vectors(self, query_embedding: List[float], limit: int = 10) -> dict:
        """Recherche de similarité vectorielle."""
        payload = {
            "embedding": query_embedding,
            "limit": limit
        }
        response = self.session.post(
            f"{self.base_url}/vectors/search",
            json=payload
        )
        response.raise_for_status()
        return response.json()

# Utilisation
client = AindusDBClient()

# Test de santé
health = client.health_check()
print(f"Status: {health['status']}")
print(f"Database: {health['database']}")

# Test opérations vectorielles
test_result = client.test_vectors()
print(f"Test result: {test_result['status']}")

# Créer des vecteurs
vector1 = client.create_vector([0.1, 0.2, 0.3], "Document 1")
vector2 = client.create_vector([0.4, 0.5, 0.6], "Document 2")

# Recherche de similarité
results = client.search_vectors([0.15, 0.25, 0.35], limit=5)
print(f"Found {len(results['results'])} similar vectors")
```

### **Client Python asynchrone**

```python
import asyncio
import aiohttp
from typing import List, Optional

class AsyncAindusDBClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    async def health_check(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/health") as response:
                return await response.json()
    
    async def create_vector(self, embedding: List[float], metadata: Optional[str] = None) -> dict:
        payload = {"embedding": embedding}
        if metadata:
            payload["metadata"] = metadata
            
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/vectors/", json=payload) as response:
                return await response.json()
    
    async def search_vectors(self, query_embedding: List[float], limit: int = 10) -> dict:
        payload = {"embedding": query_embedding, "limit": limit}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/vectors/search", json=payload) as response:
                return await response.json()

# Utilisation asynchrone
async def main():
    client = AsyncAindusDBClient()
    
    # Opérations parallèles
    health_task = client.health_check()
    vector_task = client.create_vector([0.1, 0.2, 0.3], "Async document")
    
    health, vector = await asyncio.gather(health_task, vector_task)
    print(f"Health: {health}")
    print(f"Vector created: {vector}")

# Lancer
asyncio.run(main())
```

---

## 🌐 Exemples JavaScript/Node.js

### **Client Node.js avec axios**

```javascript
const axios = require('axios');

class AindusDBClient {
    constructor(baseURL = 'http://localhost:8000') {
        this.client = axios.create({
            baseURL,
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }
    
    async healthCheck() {
        const response = await this.client.get('/health');
        return response.data;
    }
    
    async testVectors() {
        const response = await this.client.post('/vectors/test');
        return response.data;
    }
    
    async createVector(embedding, metadata = null) {
        const payload = { embedding };
        if (metadata) payload.metadata = metadata;
        
        const response = await this.client.post('/vectors/', payload);
        return response.data;
    }
    
    async searchVectors(queryEmbedding, limit = 10) {
        const payload = {
            embedding: queryEmbedding,
            limit
        };
        const response = await this.client.post('/vectors/search', payload);
        return response.data;
    }
}

// Utilisation
(async () => {
    const client = new AindusDBClient();
    
    try {
        // Test de santé
        const health = await client.healthCheck();
        console.log(`Status: ${health.status}`);
        
        // Créer vecteurs
        const vector1 = await client.createVector([0.1, 0.2, 0.3], "JS Document 1");
        const vector2 = await client.createVector([0.4, 0.5, 0.6], "JS Document 2");
        
        // Recherche
        const results = await client.searchVectors([0.15, 0.25, 0.35]);
        console.log(`Found ${results.results.length} similar vectors`);
        
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
})();
```

### **Client Frontend JavaScript**

```html
<!DOCTYPE html>
<html>
<head>
    <title>AindusDB Client</title>
</head>
<body>
    <div id="app">
        <button onclick="testConnection()">Test Connection</button>
        <button onclick="createSampleVector()">Create Sample Vector</button>
        <div id="results"></div>
    </div>

    <script>
        class AindusDBWebClient {
            constructor(baseURL = 'http://localhost:8000') {
                this.baseURL = baseURL;
            }
            
            async request(endpoint, options = {}) {
                const url = `${this.baseURL}${endpoint}`;
                const response = await fetch(url, {
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    ...options
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                return response.json();
            }
            
            async healthCheck() {
                return this.request('/health');
            }
            
            async createVector(embedding, metadata = null) {
                const payload = { embedding };
                if (metadata) payload.metadata = metadata;
                
                return this.request('/vectors/', {
                    method: 'POST',
                    body: JSON.stringify(payload)
                });
            }
            
            async searchVectors(queryEmbedding, limit = 10) {
                return this.request('/vectors/search', {
                    method: 'POST',
                    body: JSON.stringify({
                        embedding: queryEmbedding,
                        limit
                    })
                });
            }
        }
        
        const client = new AindusDBWebClient();
        const resultsDiv = document.getElementById('results');
        
        async function testConnection() {
            try {
                const health = await client.healthCheck();
                resultsDiv.innerHTML = `<p>✅ Connection OK: ${health.status}</p>`;
            } catch (error) {
                resultsDiv.innerHTML = `<p>❌ Error: ${error.message}</p>`;
            }
        }
        
        async function createSampleVector() {
            try {
                const vector = await client.createVector(
                    [Math.random(), Math.random(), Math.random()],
                    "Sample web vector"
                );
                resultsDiv.innerHTML += `<p>✅ Vector created: ${JSON.stringify(vector)}</p>`;
            } catch (error) {
                resultsDiv.innerHTML += `<p>❌ Error: ${error.message}</p>`;
            }
        }
    </script>
</body>
</html>
```

---

## 🔧 Exemples cURL

### **Tests de base**

```bash
# Test de connexion
curl -X GET http://localhost:8000/ \
  -H "Content-Type: application/json"

# Vérification santé
curl -X GET http://localhost:8000/health \
  -H "Content-Type: application/json"

# Test opérations vectorielles
curl -X POST http://localhost:8000/vectors/test \
  -H "Content-Type: application/json"
```

### **Opérations vectorielles**

```bash
# Créer un vecteur
curl -X POST http://localhost:8000/vectors/ \
  -H "Content-Type: application/json" \
  -d '{
    "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
    "metadata": "Document exemple cURL"
  }'

# Recherche de similarité
curl -X POST http://localhost:8000/vectors/search \
  -H "Content-Type: application/json" \
  -d '{
    "embedding": [0.15, 0.25, 0.35, 0.45, 0.55],
    "limit": 10
  }'
```

### **Scripts de test automatisés**

```bash
#!/bin/bash
# test_api.sh - Script de test complet

API_URL="http://localhost:8000"

echo "🔍 Test de l'API AindusDB Core..."

# Test 1: Connexion de base
echo "Test 1: Connexion de base"
curl -s -f "${API_URL}/" > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ API accessible"
else
    echo "❌ API non accessible"
    exit 1
fi

# Test 2: Santé du système
echo "Test 2: Santé du système"
HEALTH=$(curl -s "${API_URL}/health")
STATUS=$(echo $HEALTH | jq -r '.status')
if [ "$STATUS" == "healthy" ]; then
    echo "✅ Système en bonne santé"
else
    echo "❌ Problème de santé: $HEALTH"
    exit 1
fi

# Test 3: Opérations vectorielles
echo "Test 3: Opérations vectorielles"
TEST_RESULT=$(curl -s -X POST "${API_URL}/vectors/test")
TEST_STATUS=$(echo $TEST_RESULT | jq -r '.status')
if [ "$TEST_STATUS" == "success" ]; then
    echo "✅ Opérations vectorielles fonctionnelles"
else
    echo "❌ Problème vectoriel: $TEST_RESULT"
    exit 1
fi

# Test 4: Création de vecteur
echo "Test 4: Création de vecteur"
CREATE_RESULT=$(curl -s -X POST "${API_URL}/vectors/" \
  -H "Content-Type: application/json" \
  -d '{"embedding": [0.1, 0.2, 0.3], "metadata": "Test script"}')

echo $CREATE_RESULT | jq '.'

echo "🎉 Tous les tests sont passés!"
```

---

## 🔗 Intégrations spécialisées

### **Avec Sentence Transformers**

```python
from sentence_transformers import SentenceTransformer
import requests

# Charger le modèle d'embedding
model = SentenceTransformer('all-MiniLM-L6-v2')
client_url = "http://localhost:8000"

def store_text_document(text: str, metadata: str = None):
    """Stocker un document texte avec embedding automatique."""
    # Générer embedding
    embedding = model.encode(text).tolist()
    
    # Stocker dans AindusDB
    response = requests.post(
        f"{client_url}/vectors/",
        json={
            "embedding": embedding,
            "metadata": metadata or text[:100]
        }
    )
    return response.json()

def search_similar_documents(query: str, limit: int = 10):
    """Rechercher des documents similaires à une requête."""
    # Générer embedding de la requête
    query_embedding = model.encode(query).tolist()
    
    # Rechercher dans AindusDB
    response = requests.post(
        f"{client_url}/vectors/search",
        json={
            "embedding": query_embedding,
            "limit": limit
        }
    )
    return response.json()

# Utilisation
documents = [
    "Intelligence artificielle et machine learning",
    "Base de données vectorielles pour la recherche",
    "PostgreSQL et extensions pgvector",
    "FastAPI pour développement d'APIs modernes"
]

# Stocker tous les documents
for doc in documents:
    result = store_text_document(doc)
    print(f"Stored: {result}")

# Rechercher
results = search_similar_documents("IA et apprentissage automatique")
print(f"Similar documents: {results}")
```

### **Avec OpenAI embeddings**

```python
import openai
import requests
from typing import List

# Configuration OpenAI
openai.api_key = "your-api-key-here"

class OpenAIAindusDBClient:
    def __init__(self, aindus_url: str = "http://localhost:8000"):
        self.aindus_url = aindus_url
    
    def get_embedding(self, text: str, model: str = "text-embedding-ada-002") -> List[float]:
        """Générer embedding avec OpenAI."""
        response = openai.Embedding.create(
            input=[text],
            model=model
        )
        return response['data'][0]['embedding']
    
    def store_text(self, text: str, metadata: str = None) -> dict:
        """Stocker texte avec embedding OpenAI."""
        embedding = self.get_embedding(text)
        
        response = requests.post(
            f"{self.aindus_url}/vectors/",
            json={
                "embedding": embedding,
                "metadata": metadata or text[:100]
            }
        )
        return response.json()
    
    def semantic_search(self, query: str, limit: int = 10) -> dict:
        """Recherche sémantique avec OpenAI + AindusDB."""
        query_embedding = self.get_embedding(query)
        
        response = requests.post(
            f"{self.aindus_url}/vectors/search",
            json={
                "embedding": query_embedding,
                "limit": limit
            }
        )
        return response.json()

# Utilisation
client = OpenAIAindusDBClient()

# Stocker des documents
texts = [
    "Les modèles de langage transforment l'IA moderne",
    "PostgreSQL est une base de données relationnelle robuste",
    "FastAPI simplifie le développement d'APIs Python"
]

for text in texts:
    result = client.store_text(text)
    print(f"Stored: {result}")

# Recherche sémantique
results = client.semantic_search("développement d'applications IA")
print(f"Search results: {results}")
```

---

## 📊 Monitoring et métriques

### **Dashboard simple avec Python**

```python
import time
import requests
from datetime import datetime

def monitor_aindusdb(url: str = "http://localhost:8000", interval: int = 30):
    """Monitoring simple d'AindusDB Core."""
    while True:
        try:
            # Test de santé
            start_time = time.time()
            health = requests.get(f"{url}/health", timeout=5)
            response_time = time.time() - start_time
            
            # Test opérationnel
            test_result = requests.post(f"{url}/vectors/test", timeout=10)
            
            # Affichage
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] "
                  f"Health: {health.json()['status']} "
                  f"Response: {response_time:.3f}s "
                  f"Vector Test: {test_result.json()['status']}")
                  
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {e}")
        
        time.sleep(interval)

# Lancer monitoring
monitor_aindusdb()
```

### **Métriques avec Prometheus (optionnel)**

```python
from prometheus_client import Counter, Histogram, start_http_server
import requests
import time

# Métriques Prometheus
REQUEST_COUNT = Counter('aindusdb_requests_total', 'Total requests', ['endpoint'])
REQUEST_DURATION = Histogram('aindusdb_request_duration_seconds', 'Request duration')

class PrometheusAindusDBClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def _request_with_metrics(self, endpoint: str, method: str = "GET", **kwargs):
        """Requête avec collecte de métriques."""
        REQUEST_COUNT.labels(endpoint=endpoint).inc()
        
        with REQUEST_DURATION.time():
            if method == "GET":
                response = requests.get(f"{self.base_url}{endpoint}", **kwargs)
            elif method == "POST":
                response = requests.post(f"{self.base_url}{endpoint}", **kwargs)
            
        return response.json()
    
    def health_check(self):
        return self._request_with_metrics("/health")
    
    def create_vector(self, embedding, metadata=None):
        payload = {"embedding": embedding}
        if metadata:
            payload["metadata"] = metadata
        return self._request_with_metrics("/vectors/", "POST", json=payload)

# Démarrer serveur métriques
start_http_server(8001)  # Métriques sur port 8001

# Utiliser le client
client = PrometheusAindusDBClient()
health = client.health_check()
```

---

## 🔧 Utilitaires et helpers

### **Validation des embeddings**

```python
import numpy as np
from typing import List

def validate_embedding(embedding: List[float]) -> bool:
    """Valider qu'un embedding est correct."""
    if not isinstance(embedding, list):
        return False
    
    if len(embedding) == 0:
        return False
    
    if not all(isinstance(x, (int, float)) for x in embedding):
        return False
    
    # Vérifier valeurs finies
    if not np.isfinite(embedding).all():
        return False
    
    return True

def normalize_embedding(embedding: List[float]) -> List[float]:
    """Normaliser un embedding (L2 norm)."""
    embedding = np.array(embedding)
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding.tolist()
    return (embedding / norm).tolist()

# Utilisation
embedding = [0.1, 0.2, 0.3, 0.4]
if validate_embedding(embedding):
    normalized = normalize_embedding(embedding)
    print(f"Normalized: {normalized}")
```

### **Batch operations**

```python
import asyncio
import aiohttp
from typing import List, Dict

async def batch_create_vectors(
    embeddings: List[List[float]], 
    metadatas: List[str] = None,
    base_url: str = "http://localhost:8000",
    batch_size: int = 10
) -> List[Dict]:
    """Créer des vecteurs par lots de façon asynchrone."""
    
    if metadatas is None:
        metadatas = [f"Vector {i}" for i in range(len(embeddings))]
    
    async def create_single_vector(session, embedding, metadata):
        payload = {"embedding": embedding, "metadata": metadata}
        async with session.post(f"{base_url}/vectors/", json=payload) as response:
            return await response.json()
    
    results = []
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(embeddings), batch_size):
            batch_embeddings = embeddings[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            
            # Traitement du batch en parallèle
            tasks = [
                create_single_vector(session, emb, meta)
                for emb, meta in zip(batch_embeddings, batch_metadatas)
            ]
            
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            print(f"Processed batch {i//batch_size + 1}/{(len(embeddings)-1)//batch_size + 1}")
    
    return results

# Utilisation
embeddings = [[0.1, 0.2, 0.3] for _ in range(100)]
results = asyncio.run(batch_create_vectors(embeddings))
print(f"Created {len(results)} vectors")
```

---

*Guide d'utilisation API AindusDB Core - Version 1.0.0*
