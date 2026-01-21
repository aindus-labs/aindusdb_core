-- AindusDB Core - Initialisation Base de Données
-- Version: 1.0.0
-- Compatible: PostgreSQL 15+ avec pgvector

-- Activation extension pgvector
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Pour full-text search
CREATE EXTENSION IF NOT EXISTS btree_gin; -- Pour index composites

-- Création du schéma principal
CREATE SCHEMA IF NOT EXISTS aindusdb;
SET search_path TO aindusdb, public;

-- Table des tenants (multi-tenant support)
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}'::jsonb
);

-- Insertion tenant par défaut
INSERT INTO tenants (name) VALUES ('default') ON CONFLICT (name) DO NOTHING;

-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, username),
    UNIQUE(tenant_id, email)
);

-- Index pour les utilisateurs
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

-- Table des collections (regroupement logique de documents)
CREATE TABLE IF NOT EXISTS collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, name)
);

-- Index collections
CREATE INDEX idx_collections_tenant_id ON collections(tenant_id);

-- Table principale des documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    collection_id UUID REFERENCES collections(id) ON DELETE SET NULL,
    
    -- Contenu du document
    content TEXT NOT NULL,
    title VARCHAR(1000),
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Embeddings multimodaux (5 modalités)
    embedding_text vector(384),     -- Texte: 384 dimensions (E5 multilingual)
    embedding_image vector(512),    -- Image: 512 dimensions (CLIP ViT-B/32)
    embedding_audio vector(512),    -- Audio: 512 dimensions (CLAP)
    embedding_video vector(512),    -- Vidéo: 512 dimensions (CLIP frames)
    embedding_3d vector(256),       -- 3D CAO: 256 dimensions (PointNet-like)
    
    -- Métadonnées techniques
    file_path TEXT,
    file_type VARCHAR(50),
    file_size BIGINT,
    checksum VARCHAR(64),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Full-text search
    content_tsvector tsvector GENERATED ALWAYS AS (to_tsvector('french', content)) STORED
);

-- Index principaux pour documents
CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
CREATE INDEX idx_documents_collection_id ON documents(collection_id);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_documents_file_type ON documents(file_type);

-- Index HNSW pour recherche vectorielle (optimisés)
CREATE INDEX idx_documents_embedding_text ON documents 
    USING hnsw (embedding_text vector_cosine_ops) 
    WITH (m = 32, ef_construction = 128);

CREATE INDEX idx_documents_embedding_image ON documents 
    USING hnsw (embedding_image vector_cosine_ops) 
    WITH (m = 32, ef_construction = 128);

CREATE INDEX idx_documents_embedding_audio ON documents 
    USING hnsw (embedding_audio vector_cosine_ops) 
    WITH (m = 32, ef_construction = 128);

CREATE INDEX idx_documents_embedding_video ON documents 
    USING hnsw (embedding_video vector_cosine_ops) 
    WITH (m = 32, ef_construction = 128);

CREATE INDEX idx_documents_embedding_3d ON documents 
    USING hnsw (embedding_3d vector_cosine_ops) 
    WITH (m = 32, ef_construction = 128);

-- Index GIN pour métadonnées
CREATE INDEX idx_documents_metadata ON documents USING gin(metadata);

-- Index GIN pour full-text search
CREATE INDEX idx_documents_content_tsvector ON documents USING gin(content_tsvector);

-- Row Level Security pour multi-tenant
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY documents_tenant_policy ON documents 
    FOR ALL 
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE collections ENABLE ROW LEVEL SECURITY;
CREATE POLICY collections_tenant_policy ON collections 
    FOR ALL 
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_tenant_policy ON users 
    FOR ALL 
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Fonction de recherche hybride (vectorielle + BM25)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(384),
    similarity_threshold FLOAT DEFAULT 0.7,
    limit_results INT DEFAULT 10,
    bm25_weight FLOAT DEFAULT 0.3,
    vector_weight FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    doc_id UUID,
    doc_title VARCHAR(1000),
    doc_content TEXT,
    doc_metadata JSONB,
    vector_similarity FLOAT,
    bm25_score FLOAT,
    hybrid_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH vector_search AS (
        SELECT 
            id,
            title,
            content,
            metadata,
            1 - (embedding_text <=> query_embedding) AS vector_sim
        FROM documents
        WHERE embedding_text IS NOT NULL
        AND (1 - (embedding_text <=> query_embedding)) >= similarity_threshold
    ),
    bm25_search AS (
        SELECT 
            id,
            ts_rank_cd(content_tsvector, plainto_tsquery('french', query_text)) AS bm25_score
        FROM documents
        WHERE content_tsvector @@ plainto_tsquery('french', query_text)
    )
    SELECT 
        v.id,
        v.title,
        v.content,
        v.metadata,
        v.vector_sim,
        COALESCE(b.bm25_score, 0.0),
        (vector_weight * v.vector_sim + bm25_weight * COALESCE(b.bm25_score, 0.0)) AS hybrid_score
    FROM vector_search v
    LEFT JOIN bm25_search b ON v.id = b.id
    ORDER BY hybrid_score DESC
    LIMIT limit_results;
END;
$$ LANGUAGE plpgsql;

-- Fonction de mise à jour des timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers pour updated_at
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_collections_updated_at BEFORE UPDATE ON collections
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Vue pour statistiques
CREATE OR REPLACE VIEW stats_overview AS
SELECT 
    t.name AS tenant_name,
    COUNT(DISTINCT d.id) AS total_documents,
    COUNT(DISTINCT c.id) AS total_collections,
    COUNT(DISTINCT u.id) AS total_users,
    AVG(CASE WHEN d.embedding_text IS NOT NULL THEN 1 ELSE 0 END) AS text_embedding_coverage,
    AVG(CASE WHEN d.embedding_image IS NOT NULL THEN 1 ELSE 0 END) AS image_embedding_coverage,
    SUM(d.file_size) AS total_storage_bytes
FROM tenants t
LEFT JOIN documents d ON t.id = d.tenant_id
LEFT JOIN collections c ON t.id = c.tenant_id  
LEFT JOIN users u ON t.id = u.tenant_id
WHERE t.is_active = true
GROUP BY t.id, t.name;

-- Création d'un utilisateur admin par défaut (mot de passe: admin123 - À CHANGER!)
INSERT INTO users (tenant_id, username, email, password_hash, is_superuser) 
SELECT 
    t.id, 
    'admin', 
    'admin@aindusdb.local',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- admin123
    true
FROM tenants t WHERE t.name = 'default'
ON CONFLICT (tenant_id, username) DO NOTHING;

-- Collection par défaut
INSERT INTO collections (tenant_id, name, description)
SELECT 
    t.id,
    'default',
    'Collection par défaut pour documents'
FROM tenants t WHERE t.name = 'default'
ON CONFLICT (tenant_id, name) DO NOTHING;
