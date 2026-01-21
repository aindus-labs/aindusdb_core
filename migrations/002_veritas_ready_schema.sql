-- ============================================================================
-- MIGRATION 002: VERITAS-READY SCHEMA
-- Ajout des colonnes nécessaires pour support protocole VERITAS
-- (Verifiable Execution & Reasoning Integrated Trust Action System)
-- ============================================================================

-- ============================================================================
-- 1. MISE À JOUR TABLE DOCUMENTS - Support VERITAS
-- ============================================================================

-- Ajouter colonnes pour traçabilité et certification
ALTER TABLE IF EXISTS documents 
ADD COLUMN IF NOT EXISTS content_type VARCHAR(50) DEFAULT 'markdown',
ADD COLUMN IF NOT EXISTS source_hash VARCHAR(64), 
ADD COLUMN IF NOT EXISTS quality_metadata JSONB,
ADD COLUMN IF NOT EXISTS latex_content TEXT,
ADD COLUMN IF NOT EXISTS extraction_method VARCHAR(30) DEFAULT 'standard',
ADD COLUMN IF NOT EXISTS veritas_compatible BOOLEAN DEFAULT false;

-- Commentaires sur les nouvelles colonnes
COMMENT ON COLUMN documents.content_type IS 'Type de contenu: markdown, latex, html, plain_text';
COMMENT ON COLUMN documents.source_hash IS 'Hash SHA-256 du document source pour intégrité VERITAS';
COMMENT ON COLUMN documents.quality_metadata IS 'Métadonnées qualité: scores extraction, validation, etc.';
COMMENT ON COLUMN documents.latex_content IS 'Version LaTeX du contenu pour équations et formules';
COMMENT ON COLUMN documents.extraction_method IS 'Méthode extraction: standard, latex_aware, ocr_enhanced';
COMMENT ON COLUMN documents.veritas_compatible IS 'Document compatible protocole VERITAS (traçabilité complète)';

-- Index pour performances sur nouvelles colonnes
CREATE INDEX IF NOT EXISTS idx_documents_content_type ON documents(content_type);
CREATE INDEX IF NOT EXISTS idx_documents_source_hash ON documents(source_hash);
CREATE INDEX IF NOT EXISTS idx_documents_extraction_method ON documents(extraction_method);
CREATE INDEX IF NOT EXISTS idx_documents_veritas_compatible ON documents(veritas_compatible);

-- Index GIN pour recherche dans quality_metadata
CREATE INDEX IF NOT EXISTS idx_documents_quality_gin ON documents USING GIN (quality_metadata);

-- ============================================================================
-- 2. TABLE VERITAS_PROOFS - Stockage des preuves de calculs
-- ============================================================================

CREATE TABLE IF NOT EXISTS veritas_proofs (
    id BIGSERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    proof_type VARCHAR(50) NOT NULL, -- 'calculation', 'dimensional_analysis', 'logical_reasoning'
    input_data JSONB NOT NULL,
    computation_steps JSONB NOT NULL,
    result_value JSONB NOT NULL,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'verified', 'failed', 'rejected'
    confidence_score DECIMAL(5,4), -- Score de confiance 0.0000 à 1.0000
    verifier_system VARCHAR(50), -- 'python_sandbox', 'wolfram_alpha', 'sympy', 'pint'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Contraintes de validation
    CONSTRAINT veritas_proofs_type_valid CHECK (proof_type IN ('calculation', 'dimensional_analysis', 'logical_reasoning', 'unit_conversion', 'formula_validation')),
    CONSTRAINT veritas_proofs_status_valid CHECK (verification_status IN ('pending', 'verified', 'failed', 'rejected')),
    CONSTRAINT veritas_proofs_confidence_range CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1))
);

-- Index pour recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_veritas_proofs_document_id ON veritas_proofs(document_id);
CREATE INDEX IF NOT EXISTS idx_veritas_proofs_type ON veritas_proofs(proof_type);
CREATE INDEX IF NOT EXISTS idx_veritas_proofs_status ON veritas_proofs(verification_status);
CREATE INDEX IF NOT EXISTS idx_veritas_proofs_confidence ON veritas_proofs(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_veritas_proofs_created ON veritas_proofs(created_at DESC);

-- Index composé pour requêtes complexes
CREATE INDEX IF NOT EXISTS idx_veritas_proofs_doc_status ON veritas_proofs(document_id, verification_status);

-- Index GIN pour recherche dans les données
CREATE INDEX IF NOT EXISTS idx_veritas_proofs_input_gin ON veritas_proofs USING GIN (input_data);
CREATE INDEX IF NOT EXISTS idx_veritas_proofs_steps_gin ON veritas_proofs USING GIN (computation_steps);
CREATE INDEX IF NOT EXISTS idx_veritas_proofs_result_gin ON veritas_proofs USING GIN (result_value);

-- ============================================================================
-- 3. TABLE THOUGHT_TRACES - Stockage des traces de raisonnement
-- ============================================================================

CREATE TABLE IF NOT EXISTS thought_traces (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(50),
    request_id VARCHAR(50),
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reasoning_step INTEGER NOT NULL DEFAULT 1,
    thought_content TEXT NOT NULL,
    thought_type VARCHAR(30) NOT NULL DEFAULT 'reasoning', -- 'reasoning', 'calculation', 'verification', 'conclusion'
    confidence_level VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high', 'certain'
    source_documents INTEGER[], -- Array d'IDs de documents sources
    veritas_tags TEXT[], -- Tags pour indexation: ['physics', 'mathematics', 'engineering']
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Contraintes de validation
    CONSTRAINT thought_traces_type_valid CHECK (thought_type IN ('reasoning', 'calculation', 'verification', 'conclusion', 'assumption', 'contradiction')),
    CONSTRAINT thought_traces_confidence_valid CHECK (confidence_level IN ('low', 'medium', 'high', 'certain'))
);

-- Index pour recherches et performance
CREATE INDEX IF NOT EXISTS idx_thought_traces_session_id ON thought_traces(session_id);
CREATE INDEX IF NOT EXISTS idx_thought_traces_request_id ON thought_traces(request_id);
CREATE INDEX IF NOT EXISTS idx_thought_traces_user_id ON thought_traces(user_id);
CREATE INDEX IF NOT EXISTS idx_thought_traces_type ON thought_traces(thought_type);
CREATE INDEX IF NOT EXISTS idx_thought_traces_confidence ON thought_traces(confidence_level);
CREATE INDEX IF NOT EXISTS idx_thought_traces_timestamp ON thought_traces(timestamp DESC);

-- Index pour recherche full-text dans le contenu
CREATE INDEX IF NOT EXISTS idx_thought_traces_content_fts ON thought_traces USING GIN (to_tsvector('english', thought_content));

-- Index GIN pour arrays
CREATE INDEX IF NOT EXISTS idx_thought_traces_source_docs ON thought_traces USING GIN (source_documents);
CREATE INDEX IF NOT EXISTS idx_thought_traces_tags ON thought_traces USING GIN (veritas_tags);

-- Index composé pour requêtes par session et étape
CREATE INDEX IF NOT EXISTS idx_thought_traces_session_step ON thought_traces(session_id, reasoning_step);

-- ============================================================================
-- 4. TABLE VERIFICATION_AUDIT - Audit des vérifications VERITAS
-- ============================================================================

CREATE TABLE IF NOT EXISTS verification_audit (
    id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(50) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    verification_type VARCHAR(50) NOT NULL, -- 'full_veritas', 'partial_check', 'confidence_only'
    input_query TEXT NOT NULL,
    documents_used INTEGER[] NOT NULL,
    proofs_generated INTEGER[] DEFAULT '{}',
    thought_traces_ids INTEGER[] DEFAULT '{}',
    final_confidence DECIMAL(5,4),
    verification_time_ms INTEGER,
    success BOOLEAN NOT NULL DEFAULT true,
    error_details JSONB,
    veritas_version VARCHAR(20),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Contraintes de validation
    CONSTRAINT verification_audit_type_valid CHECK (verification_type IN ('full_veritas', 'partial_check', 'confidence_only', 'fact_verification')),
    CONSTRAINT verification_audit_confidence_range CHECK (final_confidence IS NULL OR (final_confidence >= 0 AND final_confidence <= 1))
);

-- Index pour audit et monitoring
CREATE INDEX IF NOT EXISTS idx_verification_audit_request_id ON verification_audit(request_id);
CREATE INDEX IF NOT EXISTS idx_verification_audit_user_id ON verification_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_verification_audit_type ON verification_audit(verification_type);
CREATE INDEX IF NOT EXISTS idx_verification_audit_timestamp ON verification_audit(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_verification_audit_confidence ON verification_audit(final_confidence DESC);
CREATE INDEX IF NOT EXISTS idx_verification_audit_success ON verification_audit(success);

-- Index pour arrays
CREATE INDEX IF NOT EXISTS idx_verification_audit_docs ON verification_audit USING GIN (documents_used);
CREATE INDEX IF NOT EXISTS idx_verification_audit_proofs ON verification_audit USING GIN (proofs_generated);

-- ============================================================================
-- 5. VUES POUR ANALYTICS VERITAS
-- ============================================================================

-- Vue des documents prêts VERITAS
CREATE OR REPLACE VIEW veritas_ready_documents AS
SELECT 
    d.id,
    d.title,
    d.content_type,
    d.source_hash,
    d.quality_metadata,
    d.veritas_compatible,
    d.extraction_method,
    COUNT(vp.id) as proofs_count,
    AVG(vp.confidence_score) as avg_confidence,
    d.created_at
FROM documents d
LEFT JOIN veritas_proofs vp ON d.id = vp.document_id
WHERE d.veritas_compatible = true
GROUP BY d.id, d.title, d.content_type, d.source_hash, d.quality_metadata, 
         d.veritas_compatible, d.extraction_method, d.created_at;

-- Vue des statistiques de vérification
CREATE OR REPLACE VIEW verification_stats AS
SELECT 
    DATE_TRUNC('day', timestamp) as verification_date,
    verification_type,
    COUNT(*) as total_verifications,
    COUNT(*) FILTER (WHERE success = true) as successful_verifications,
    COUNT(*) FILTER (WHERE success = false) as failed_verifications,
    AVG(final_confidence) as avg_confidence,
    AVG(verification_time_ms) as avg_time_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY verification_time_ms) as p95_time_ms
FROM verification_audit
GROUP BY DATE_TRUNC('day', timestamp), verification_type
ORDER BY verification_date DESC, verification_type;

-- ============================================================================
-- 6. TRIGGERS POUR MAINTENANCE AUTOMATIQUE
-- ============================================================================

-- Fonction pour mise à jour automatique des timestamps
CREATE OR REPLACE FUNCTION update_veritas_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger sur veritas_proofs
CREATE TRIGGER tr_veritas_proofs_updated_at
    BEFORE UPDATE ON veritas_proofs
    FOR EACH ROW
    EXECUTE FUNCTION update_veritas_timestamp();

-- Fonction pour audit automatique des documents VERITAS
CREATE OR REPLACE FUNCTION audit_veritas_document_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Enregistrer changement si document devient VERITAS-compatible
    IF NEW.veritas_compatible = true AND (OLD.veritas_compatible IS NULL OR OLD.veritas_compatible = false) THEN
        INSERT INTO audit_logs (
            action, 
            resource, 
            details, 
            level, 
            category,
            timestamp
        ) VALUES (
            'document_veritas_enabled',
            'documents',
            jsonb_build_object(
                'document_id', NEW.id,
                'title', NEW.title,
                'content_type', NEW.content_type,
                'source_hash', NEW.source_hash
            ),
            'info',
            'system_admin',
            NOW()
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger sur documents pour audit VERITAS
CREATE TRIGGER tr_audit_veritas_document
    AFTER UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION audit_veritas_document_change();

-- ============================================================================
-- 7. FONCTIONS UTILITAIRES VERITAS
-- ============================================================================

-- Fonction pour calculer hash de contenu
CREATE OR REPLACE FUNCTION calculate_content_hash(content TEXT)
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN encode(digest(content, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Fonction pour valider format LaTeX
CREATE OR REPLACE FUNCTION is_valid_latex(latex_content TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- Vérification basique de balises LaTeX
    RETURN latex_content ~ '\$.*\$|\\\w+\{.*\}|\\\w+\[.*\]';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Fonction pour extraire métriques qualité d'un document
CREATE OR REPLACE FUNCTION get_document_quality_score(doc_id INTEGER)
RETURNS DECIMAL(3,2) AS $$
DECLARE
    quality_score DECIMAL(3,2) := 0.0;
    doc_record RECORD;
BEGIN
    SELECT * FROM documents WHERE id = doc_id INTO doc_record;
    
    IF NOT FOUND THEN
        RETURN 0.0;
    END IF;
    
    -- Score basé sur présence de hash source
    IF doc_record.source_hash IS NOT NULL THEN
        quality_score := quality_score + 0.3;
    END IF;
    
    -- Score basé sur type de contenu
    IF doc_record.content_type IN ('markdown', 'latex') THEN
        quality_score := quality_score + 0.3;
    END IF;
    
    -- Score basé sur compatibilité VERITAS
    IF doc_record.veritas_compatible = true THEN
        quality_score := quality_score + 0.4;
    END IF;
    
    RETURN quality_score;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. INSERTION DE DONNÉES DE TEST (Développement uniquement)
-- ============================================================================

-- Insertion d'exemples de documents VERITAS-ready (pour tests)
INSERT INTO documents (title, content, content_type, source_hash, latex_content, extraction_method, veritas_compatible, quality_metadata)
SELECT 
    'Test Document - Physics Formulas',
    'This document contains Newton''s second law: F = ma',
    'markdown',
    calculate_content_hash('This document contains Newton''s second law: F = ma'),
    'This document contains Newton''s second law: $F = ma$',
    'latex_aware',
    true,
    jsonb_build_object(
        'extraction_quality', 0.95,
        'latex_equations_count', 1,
        'validation_score', 0.87,
        'source_reliability', 'high'
    )
WHERE NOT EXISTS (SELECT 1 FROM documents WHERE title = 'Test Document - Physics Formulas');

-- Ajout d'une preuve de test
INSERT INTO veritas_proofs (document_id, proof_type, input_data, computation_steps, result_value, verification_status, confidence_score, verifier_system)
SELECT 
    d.id,
    'calculation',
    jsonb_build_object('force', 100, 'mass', 10, 'operation', 'calculate_acceleration'),
    jsonb_build_array(
        jsonb_build_object('step', 1, 'description', 'Apply F = ma', 'formula', 'a = F / m'),
        jsonb_build_object('step', 2, 'description', 'Substitute values', 'calculation', '100 / 10 = 10'),
        jsonb_build_object('step', 3, 'description', 'Result with units', 'result', '10 m/s²')
    ),
    jsonb_build_object('acceleration', 10, 'unit', 'm/s²', 'verified', true),
    'verified',
    0.9850,
    'python_sandbox'
FROM documents d 
WHERE d.title = 'Test Document - Physics Formulas'
AND NOT EXISTS (SELECT 1 FROM veritas_proofs WHERE document_id = d.id);

-- ============================================================================
-- MIGRATION TERMINÉE - VERITAS-READY
-- ============================================================================

-- Message de confirmation
DO $$
BEGIN
    RAISE NOTICE 'Migration 002 VERITAS-Ready terminée avec succès';
    RAISE NOTICE 'Tables créées: veritas_proofs, thought_traces, verification_audit';
    RAISE NOTICE 'Vues créées: veritas_ready_documents, verification_stats';
    RAISE NOTICE 'Fonctions utilitaires: calculate_content_hash, is_valid_latex, get_document_quality_score';
END $$;
