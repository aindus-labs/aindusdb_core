-- ============================================================================
-- MIGRATION 003: TYPESET-AGNOSTIC EVOLUTION 
-- Évolution vers architecture multi-format : Typst, LaTeX, AsciiMath
-- Rend VERITAS indépendant du format de composition mathématique
-- ============================================================================

-- ============================================================================
-- 1. ÉVOLUTION TABLE DOCUMENTS - Architecture Typeset-Agnostic
-- ============================================================================

-- Renommer colonne existante pour compatibilité
ALTER TABLE IF EXISTS documents 
RENAME COLUMN latex_content TO legacy_latex_content;

-- Ajouter nouvelles colonnes format-agnostiques
ALTER TABLE IF EXISTS documents
ADD COLUMN IF NOT EXISTS structured_math_content TEXT,
ADD COLUMN IF NOT EXISTS typesetting_format VARCHAR(20) DEFAULT 'typst',
ADD COLUMN IF NOT EXISTS format_version VARCHAR(10) DEFAULT '0.10.0',
ADD COLUMN IF NOT EXISTS math_complexity_score DECIMAL(3,2) DEFAULT 0.0;

-- Commentaires détaillés sur nouvelles colonnes
COMMENT ON COLUMN documents.structured_math_content IS 'Contenu mathématique dans le format spécifié (Typst, LaTeX, AsciiMath, etc.)';
COMMENT ON COLUMN documents.typesetting_format IS 'Format de composition: typst, latex, asciimath, mathml, katex';
COMMENT ON COLUMN documents.format_version IS 'Version du format utilisé (ex: 0.10.0 pour Typst, 2e pour LaTeX)';
COMMENT ON COLUMN documents.math_complexity_score IS 'Score de complexité mathématique (0.0 = texte simple, 1.0 = très complexe)';

-- Contraintes de validation format
ALTER TABLE documents
ADD CONSTRAINT documents_typesetting_format_valid 
CHECK (typesetting_format IN ('typst', 'latex', 'asciimath', 'mathml', 'katex', 'markdown_math'));

ALTER TABLE documents  
ADD CONSTRAINT documents_math_complexity_range
CHECK (math_complexity_score >= 0.0 AND math_complexity_score <= 1.0);

-- Index pour recherche par format
CREATE INDEX IF NOT EXISTS idx_documents_typesetting_format ON documents(typesetting_format);
CREATE INDEX IF NOT EXISTS idx_documents_format_version ON documents(typesetting_format, format_version);
CREATE INDEX IF NOT EXISTS idx_documents_math_complexity ON documents(math_complexity_score DESC);

-- Index composé pour requêtes VERITAS sur contenu mathématique
CREATE INDEX IF NOT EXISTS idx_documents_veritas_math 
ON documents(veritas_compatible, typesetting_format, math_complexity_score) 
WHERE veritas_compatible = true AND structured_math_content IS NOT NULL;

-- ============================================================================
-- 2. TABLE FORMAT_CAPABILITIES - Métadonnées des formats supportés
-- ============================================================================

CREATE TABLE IF NOT EXISTS typesetting_formats (
    id SERIAL PRIMARY KEY,
    format_name VARCHAR(20) NOT NULL UNIQUE,
    display_name VARCHAR(50) NOT NULL,
    file_extensions TEXT[] NOT NULL,
    veritas_support_level VARCHAR(20) NOT NULL DEFAULT 'basic', -- 'native', 'full', 'basic', 'legacy'
    parsing_complexity VARCHAR(20) NOT NULL DEFAULT 'medium', -- 'low', 'medium', 'high', 'extreme'
    ai_generation_difficulty VARCHAR(20) NOT NULL DEFAULT 'medium', -- 'easy', 'medium', 'hard', 'nightmare'
    deterministic_parsing BOOLEAN NOT NULL DEFAULT false,
    real_time_compilation BOOLEAN NOT NULL DEFAULT false,
    math_notation_quality VARCHAR(20) DEFAULT 'good', -- 'excellent', 'good', 'fair', 'poor'
    ecosystem_maturity VARCHAR(20) DEFAULT 'developing', -- 'mature', 'stable', 'developing', 'experimental'
    performance_score DECIMAL(3,2) DEFAULT 0.5, -- 0.0 = très lent, 1.0 = ultra rapide
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT format_support_level_valid CHECK (veritas_support_level IN ('native', 'full', 'basic', 'legacy', 'deprecated')),
    CONSTRAINT parsing_complexity_valid CHECK (parsing_complexity IN ('low', 'medium', 'high', 'extreme')),
    CONSTRAINT generation_difficulty_valid CHECK (ai_generation_difficulty IN ('easy', 'medium', 'hard', 'nightmare')),
    CONSTRAINT performance_score_range CHECK (performance_score >= 0.0 AND performance_score <= 1.0)
);

-- ============================================================================
-- 3. DONNÉES INITIALES - Formats supportés avec métadonnées VERITAS
-- ============================================================================

INSERT INTO typesetting_formats (
    format_name, display_name, file_extensions, 
    veritas_support_level, parsing_complexity, ai_generation_difficulty,
    deterministic_parsing, real_time_compilation, math_notation_quality,
    ecosystem_maturity, performance_score
) VALUES 
-- Typst - Le champion VERITAS
('typst', 'Typst', ARRAY['.typ'], 
 'native', 'low', 'easy', 
 true, true, 'excellent', 
 'developing', 0.95),

-- LaTeX - L'héritage académique 
('latex', 'LaTeX', ARRAY['.tex', '.latex'], 
 'legacy', 'extreme', 'nightmare',
 false, false, 'excellent',
 'mature', 0.2),

-- AsciiMath - Simplicité
('asciimath', 'AsciiMath', ARRAY['.am'], 
 'basic', 'low', 'easy',
 true, true, 'good',
 'stable', 0.8),

-- MathML - Standard W3C
('mathml', 'MathML', ARRAY['.mml', '.mathml'], 
 'full', 'medium', 'hard',
 true, false, 'excellent',
 'mature', 0.3),

-- KaTeX - Web moderne  
('katex', 'KaTeX', ARRAY['.katex'], 
 'full', 'medium', 'medium',
 true, true, 'good',
 'stable', 0.85),

-- Markdown Math - Simplicité
('markdown_math', 'Markdown Math', ARRAY['.md'], 
 'basic', 'low', 'easy',
 true, true, 'fair',
 'stable', 0.9)
ON CONFLICT (format_name) DO NOTHING;

-- ============================================================================
-- 4. VUES ANALYTIQUES - Support multi-format VERITAS
-- ============================================================================

-- Vue des documents par format avec statistiques VERITAS
CREATE OR REPLACE VIEW documents_by_format_stats AS
SELECT 
    d.typesetting_format,
    tf.display_name,
    tf.veritas_support_level,
    COUNT(*) as document_count,
    COUNT(*) FILTER (WHERE d.veritas_compatible = true) as veritas_documents,
    AVG(d.math_complexity_score) as avg_complexity,
    COUNT(*) FILTER (WHERE d.structured_math_content IS NOT NULL) as with_math_content,
    tf.performance_score,
    tf.deterministic_parsing
FROM documents d
LEFT JOIN typesetting_formats tf ON d.typesetting_format = tf.format_name
GROUP BY d.typesetting_format, tf.display_name, tf.veritas_support_level, tf.performance_score, tf.deterministic_parsing
ORDER BY veritas_documents DESC, tf.performance_score DESC;

-- Vue recommandations de format pour VERITAS
CREATE OR REPLACE VIEW format_veritas_recommendations AS
SELECT 
    format_name,
    display_name,
    veritas_support_level,
    CASE 
        WHEN veritas_support_level = 'native' AND deterministic_parsing = true THEN 'EXCELLENT'
        WHEN veritas_support_level = 'full' AND performance_score > 0.7 THEN 'GOOD'  
        WHEN veritas_support_level = 'basic' THEN 'ACCEPTABLE'
        WHEN veritas_support_level = 'legacy' THEN 'MIGRATION_NEEDED'
        ELSE 'NOT_RECOMMENDED'
    END as veritas_recommendation,
    performance_score,
    deterministic_parsing,
    real_time_compilation,
    ai_generation_difficulty,
    CONCAT(
        'Performance: ', performance_score, '/1.0, ',
        'Parsing: ', CASE WHEN deterministic_parsing THEN 'Deterministic' ELSE 'Heuristic' END, ', ',
        'AI-Gen: ', ai_generation_difficulty
    ) as recommendation_details
FROM typesetting_formats
ORDER BY 
    CASE veritas_support_level 
        WHEN 'native' THEN 1 
        WHEN 'full' THEN 2 
        WHEN 'basic' THEN 3 
        WHEN 'legacy' THEN 4 
        ELSE 5 
    END,
    performance_score DESC;

-- ============================================================================
-- 5. FONCTIONS UTILITAIRES - Multi-format
-- ============================================================================

-- Fonction pour détecter format à partir du contenu
CREATE OR REPLACE FUNCTION detect_typesetting_format(content TEXT)
RETURNS VARCHAR(20) AS $$
BEGIN
    -- Détection Typst (priorité haute)
    IF content ~ '#set |#show |#let |#import |\$.*?\$|```' THEN
        RETURN 'typst';
    -- Détection LaTeX
    ELSIF content ~ '\\begin\{|\\end\{|\\documentclass|\\usepackage|\\\w+\{' THEN
        RETURN 'latex';
    -- Détection AsciiMath  
    ELSIF content ~ '`.*?`|sum_|int_|lim_|sqrt\(' THEN
        RETURN 'asciimath';
    -- Détection MathML
    ELSIF content ~ '<math|<mrow|<mi>|<mn>' THEN
        RETURN 'mathml';
    -- Par défaut Typst (format natif VERITAS)
    ELSE
        RETURN 'typst';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Fonction pour calculer score de complexité mathématique
CREATE OR REPLACE FUNCTION calculate_math_complexity(content TEXT, format_type VARCHAR(20))
RETURNS DECIMAL(3,2) AS $$
DECLARE
    complexity_score DECIMAL(3,2) := 0.0;
    equation_count INTEGER := 0;
    symbol_count INTEGER := 0;
BEGIN
    IF content IS NULL OR length(content) = 0 THEN
        RETURN 0.0;
    END IF;
    
    -- Compter équations selon le format
    CASE format_type
        WHEN 'typst' THEN
            equation_count := (length(content) - length(replace(content, '$', ''))) / 2;
            symbol_count := length(content) - length(regexp_replace(content, '[∫∑∏√∆∇]', '', 'g'));
        WHEN 'latex' THEN  
            equation_count := (SELECT count(*) FROM regexp_split_to_table(content, '\\begin\{equation\}|\\begin\{align\}|\$\$|\$'));
            symbol_count := length(content) - length(regexp_replace(content, '\\[a-zA-Z]+', '', 'g'));
        ELSE
            equation_count := (length(content) - length(replace(content, '`', ''))) / 2;
    END CASE;
    
    -- Calculer score basé sur densité mathématique
    complexity_score := LEAST(1.0, 
        (equation_count * 0.1) + 
        (symbol_count * 0.05) + 
        (length(content) * 0.0001)
    );
    
    RETURN complexity_score;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- 6. MIGRATION DES DONNÉES EXISTANTES
-- ============================================================================

-- Migrer contenu LaTeX existant vers nouveau schéma
UPDATE documents 
SET 
    structured_math_content = legacy_latex_content,
    typesetting_format = 'latex',
    format_version = '2e',
    math_complexity_score = calculate_math_complexity(legacy_latex_content, 'latex')
WHERE legacy_latex_content IS NOT NULL 
  AND structured_math_content IS NULL;

-- Détecter et définir format pour documents sans structured_math_content
UPDATE documents 
SET 
    typesetting_format = detect_typesetting_format(content),
    math_complexity_score = calculate_math_complexity(content, detect_typesetting_format(content))
WHERE structured_math_content IS NULL 
  AND typesetting_format = 'typst';  -- Seulement les documents par défaut

-- ============================================================================
-- 7. TRIGGERS POUR MAINTENANCE AUTOMATIQUE
-- ============================================================================

-- Fonction trigger pour détection automatique format
CREATE OR REPLACE FUNCTION auto_detect_format_and_complexity()
RETURNS TRIGGER AS $$
BEGIN
    -- Si pas de format spécifié, détection automatique
    IF NEW.structured_math_content IS NOT NULL AND NEW.typesetting_format IS NULL THEN
        NEW.typesetting_format := detect_typesetting_format(NEW.structured_math_content);
    END IF;
    
    -- Calcul automatique complexité si contenu mathématique présent
    IF NEW.structured_math_content IS NOT NULL THEN
        NEW.math_complexity_score := calculate_math_complexity(
            NEW.structured_math_content, 
            NEW.typesetting_format
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger sur insertion/update documents
CREATE TRIGGER tr_auto_detect_format_complexity
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION auto_detect_format_and_complexity();

-- ============================================================================
-- MIGRATION TERMINÉE - TYPESET-AGNOSTIC VERITAS
-- ============================================================================

-- Message de confirmation
DO $$
BEGIN
    RAISE NOTICE 'Migration 003 Typeset-Agnostic terminée avec succès';
    RAISE NOTICE 'Architecture multi-format : Typst (natif), LaTeX (legacy), AsciiMath, MathML, KaTeX';
    RAISE NOTICE 'Nouvelles colonnes : structured_math_content, typesetting_format, format_version, math_complexity_score';
    RAISE NOTICE 'Fonctions : detect_typesetting_format(), calculate_math_complexity()';
    RAISE NOTICE 'VERITAS désormais format-agnostique avec priorité Typst';
END $$;
