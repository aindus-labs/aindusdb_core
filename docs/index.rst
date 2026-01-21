AindusDB Core Documentation
==============================

**Open Source Vector Database built on PostgreSQL + pgvector**

.. image:: https://img.shields.io/badge/License-MIT-green.svg
   :target: https://opensource.org/licenses/MIT
   :alt: MIT License

.. image:: https://img.shields.io/badge/python-3.11+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python 3.11+

.. image:: https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white
   :target: https://fastapi.tiangolo.com/
   :alt: FastAPI

.. image:: https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white
   :target: https://www.postgresql.org/
   :alt: PostgreSQL

Welcome to AindusDB Core
------------------------

AindusDB Core is a modern, open-source alternative to Pinecone/Qdrant/Weaviate built on PostgreSQL + pgvector. 
It provides a high-performance vector database solution with a REST API for similarity search and vector operations.

Key Features
------------

🗄️ **Optimized Vector Storage**: PostgreSQL + pgvector with HNSW indexes
🔍 **Fast Similarity Search**: Cosine, euclidean, and dot product distances  
🚀 **Modern REST API**: FastAPI with complete OpenAPI documentation
🐳 **Simple Deployment**: Production-ready Docker Compose setup
🧪 **Comprehensive Testing**: Unit, integration, and performance test suites
📊 **Built-in Monitoring**: Health checks, metrics, and observability

Quick Start
-----------

**Docker Compose (Recommended)**

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/aindus-labs/aindusdb_core.git
   cd AindusDB_Core

   # Configure environment
   cp .env.template .env

   # Start all services
   docker-compose up -d

   # Verify deployment
   curl http://localhost:8000/health

**API Access**

Once running, access the interactive documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Technical Stack
---------------

==================== =============== ======== ================================
Component            Technology      Version  Role
==================== =============== ======== ================================
**Database**         PostgreSQL      15+      Vector storage with pgvector
**Extension**        pgvector        0.5.1    Vector operations and indexing
**API Framework**    FastAPI         0.104+   Modern REST API
**Database Driver**  asyncpg         0.29+    Async PostgreSQL connection
**Validation**       Pydantic        2.5+     Data validation and serialization
**Testing**          pytest          7.4+     Comprehensive test suite
**Containerization** Docker Compose  20+      Isolated deployment
**CI/CD**            GitHub Actions  -        Continuous integration
**Documentation**    OpenAPI/Swagger -        Interactive API docs
==================== =============== ======== ================================

Architecture Overview
---------------------

AindusDB Core follows a clean, modular architecture:

.. code-block::

   AindusDB_Core/
   ├── app/                          # Main application
   │   ├── core/                     # Configuration & database
   │   ├── models/                   # Pydantic data models
   │   ├── services/                 # Business logic layer
   │   ├── routers/                  # API endpoints
   │   ├── dependencies/             # FastAPI dependency injection
   │   └── main.py                   # Application entry point
   ├── tests/                        # Test suites
   ├── docs/                         # Documentation
   └── scripts/                      # Utility scripts

API Endpoints
-------------

**Health and Monitoring**
- ``GET /`` - Welcome message and status
- ``GET /health`` - System health check
- ``GET /status`` - Detailed system status
- ``GET /metrics`` - Performance metrics

**Vector Operations**
- ``POST /vectors/test`` - Test pgvector functionality
- ``POST /vectors/`` - Create new vectors
- ``POST /vectors/search`` - Similarity search

User Guide
----------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   INSTALLATION
   CONTRIBUTING

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   
   api
   
.. toctree::
   :maxdepth: 1
   :caption: Examples and Tutorials
   
   API_EXAMPLES

Performance
-----------

AindusDB Core is optimized for production workloads:

- **Connection Pooling**: Optimized asyncpg pool (5-20 connections)
- **Vector Operations**: ~1000 insertions/sec, ~500 searches/sec
- **HNSW Indexing**: Configurable parameters for speed/accuracy tradeoffs
- **Memory Efficient**: PostgreSQL TOAST compression for large vectors

Production Deployment
---------------------

**Docker Production Setup**

.. code-block:: yaml

   version: '3.8'
   services:
     postgres:
       image: ankane/pgvector:latest
       environment:
         POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
       volumes:
         - postgres_data:/var/lib/postgresql/data
       restart: unless-stopped

     api:
       image: aindusdb/core:latest
       environment:
         DATABASE_URL: postgresql://aindusdb:${POSTGRES_PASSWORD}@postgres:5432/aindusdb_core
         API_WORKERS: 4
       ports:
         - "8000:8000"
       restart: unless-stopped

**Kubernetes Deployment**

Helm charts and Kubernetes manifests are provided in the repository for scalable deployments.

Support and Community
---------------------

- **Documentation**: Complete guides and API reference
- **GitHub Issues**: Bug reports and feature requests
- **Examples**: Multi-language client libraries and integrations
- **Performance**: Benchmarks and optimization guides

License
-------

AindusDB Core is released under the MIT License. See the `LICENSE <https://github.com/aindus-labs/aindusdb_core/blob/main/LICENSE>`_ file for details.

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
