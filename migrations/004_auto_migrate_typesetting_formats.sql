-- ============================================================================
-- MIGRATION 004: AUTO-MIGRATION TYPESETTING FORMATS
-- Migration automatique des données existantes vers architecture Typeset-Agnostic
-- Utilise les fonctions de détection automatique du format pour classifier le contenu
-- ============================================================================

-- ============================================================================
-- 1. MIGRATION BATCH DOCUMENTS EXISTANTS
-- ============================================================================

-- Fonction de migration par batch pour éviter timeout sur gros volumes
CREATE OR REPLACE FUNCTION migrate_documents_typesetting_batch(
    batch_size INT DEFAULT 1000,
    offset_start INT DEFAULT 0
)
RETURNS TABLE (
    processed_count INT,
    success_count INT,
    error_count INT,
    batch_details JSONB
) AS $$
DECLARE
    doc_record RECORD;
    processed_count INT := 0;
    success_count INT := 0; 
    error_count INT := 0;
    batch_details JSONB := '{}';
    format_stats JSONB := '{"typst": 0, "latex": 0, "asciimath": 0, "mathml": 0, "markdown_math": 0}';
BEGIN
    -- Log début migration
    RAISE NOTICE 'Starting typesetting format migration batch: size=%, offset=%', batch_size, offset_start;
    
    -- Traitement par batch des documents
    FOR doc_record IN 
        SELECT id, content, legacy_latex_content, structured_math_content, typesetting_format
        FROM documents 
        WHERE structured_math_content IS NULL OR typesetting_format = 'typst'
        ORDER BY id
        LIMIT batch_size OFFSET offset_start
    LOOP
        BEGIN
            processed_count := processed_count + 1;
            
            DECLARE 
                detected_format VARCHAR(20);
                content_to_analyze TEXT;
                calculated_complexity DECIMAL(3,2);
            BEGIN
                -- Choisir contenu à analyser (priorité: legacy_latex_content > content)
                content_to_analyze := COALESCE(doc_record.legacy_latex_content, doc_record.content, '');
                
                -- Détecter format automatiquement
                detected_format := detect_typesetting_format(content_to_analyze);
                
                -- Calculer score complexité
                calculated_complexity := calculate_math_complexity(content_to_analyze, detected_format);
                
                -- Mise à jour document
                UPDATE documents 
                SET 
                    structured_math_content = CASE 
                        WHEN doc_record.legacy_latex_content IS NOT NULL THEN doc_record.legacy_latex_content
                        ELSE content_to_analyze
                    END,
                    typesetting_format = detected_format,
                    format_version = CASE detected_format
                        WHEN 'typst' THEN '0.10.0'
                        WHEN 'latex' THEN '2e'
                        WHEN 'asciimath' THEN '2.7'
                        WHEN 'mathml' THEN '3.0'
                        WHEN 'katex' THEN '0.16.0'
                        ELSE '1.0.0'
                    END,
                    math_complexity_score = calculated_complexity,
                    updated_at = NOW()
                WHERE id = doc_record.id;
                
                -- Statistiques par format
                format_stats := jsonb_set(
                    format_stats, 
                    ARRAY[detected_format], 
                    ((format_stats->>detected_format)::INT + 1)::TEXT::JSONB
                );
                
                success_count := success_count + 1;
                
            EXCEPTION WHEN OTHERS THEN
                error_count := error_count + 1;
                RAISE WARNING 'Error migrating document ID %: %', doc_record.id, SQLERRM;
            END;
            
        END;
    END LOOP;
    
    -- Construire détails batch
    batch_details := jsonb_build_object(
        'batch_size', batch_size,
        'offset_start', offset_start,
        'format_distribution', format_stats,
        'migration_timestamp', NOW()
    );
    
    RAISE NOTICE 'Migration batch completed: processed=%, success=%, errors=%', processed_count, success_count, error_count;
    
    RETURN QUERY SELECT processed_count, success_count, error_count, batch_details;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 2. MIGRATION COMPLÈTE AVEC MONITORING
-- ============================================================================

-- Table de suivi migration
CREATE TABLE IF NOT EXISTS migration_tracking (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(100) NOT NULL,
    phase VARCHAR(50) NOT NULL,
    batch_number INT NOT NULL,
    processed_count INT DEFAULT 0,
    success_count INT DEFAULT 0,
    error_count INT DEFAULT 0,
    batch_details JSONB DEFAULT '{}',
    execution_time_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(migration_name, batch_number)
);

-- Fonction migration complète avec suivi
CREATE OR REPLACE FUNCTION migrate_all_documents_typesetting()
RETURNS TABLE (
    total_processed INT,
    total_success INT, 
    total_errors INT,
    execution_summary JSONB
) AS $$
DECLARE
    batch_size INT := 1000;
    current_offset INT := 0;
    batch_number INT := 1;
    batch_result RECORD;
    total_docs INT;
    migration_start TIMESTAMPTZ;
    migration_end TIMESTAMPTZ;
    total_processed INT := 0;
    total_success INT := 0;
    total_errors INT := 0;
BEGIN
    migration_start := NOW();
    
    -- Compter total documents à migrer
    SELECT COUNT(*) INTO total_docs 
    FROM documents 
    WHERE structured_math_content IS NULL OR typesetting_format = 'typst';
    
    RAISE NOTICE 'Starting full typesetting migration: % documents to process', total_docs;
    
    -- Migration par batch
    WHILE current_offset < total_docs LOOP
        -- Exécuter batch migration
        SELECT * INTO batch_result 
        FROM migrate_documents_typesetting_batch(batch_size, current_offset);
        
        -- Enregistrer suivi
        INSERT INTO migration_tracking (
            migration_name, phase, batch_number,
            processed_count, success_count, error_count, 
            batch_details, execution_time_ms
        ) VALUES (
            'typeset_agnostic_migration', 'data_migration', batch_number,
            batch_result.processed_count, batch_result.success_count, batch_result.error_count,
            batch_result.batch_details, 
            EXTRACT(MILLISECONDS FROM (NOW() - migration_start))::INT
        );
        
        -- Cumuler totaux
        total_processed := total_processed + batch_result.processed_count;
        total_success := total_success + batch_result.success_count;
        total_errors := total_errors + batch_result.error_count;
        
        -- Préparer batch suivant
        current_offset := current_offset + batch_size;
        batch_number := batch_number + 1;
        
        -- Break si pas de documents traités
        EXIT WHEN batch_result.processed_count = 0;
        
        -- Pause entre batches pour ne pas surcharger
        PERFORM pg_sleep(0.1);
    END LOOP;
    
    migration_end := NOW();
    
    -- Résumé final
    DECLARE
        execution_summary JSONB;
        format_distribution JSONB;
    BEGIN
        -- Statistiques formats après migration
        SELECT jsonb_object_agg(typesetting_format, doc_count) INTO format_distribution
        FROM (
            SELECT typesetting_format, COUNT(*) as doc_count 
            FROM documents 
            WHERE structured_math_content IS NOT NULL
            GROUP BY typesetting_format
        ) stats;
        
        execution_summary := jsonb_build_object(
            'migration_name', 'typeset_agnostic_migration',
            'total_documents', total_docs,
            'execution_time_seconds', EXTRACT(EPOCH FROM (migration_end - migration_start)),
            'batches_processed', batch_number - 1,
            'format_distribution', format_distribution,
            'success_rate', ROUND((total_success::DECIMAL / NULLIF(total_processed, 0)) * 100, 2),
            'completed_at', migration_end
        );
        
        RAISE NOTICE 'Migration completed successfully: %', execution_summary;
        
        RETURN QUERY SELECT total_processed, total_success, total_errors, execution_summary;
    END;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 3. VUES DE MONITORING POST-MIGRATION  
-- ============================================================================

-- Vue état migration par format
CREATE OR REPLACE VIEW migration_format_status AS
SELECT 
    d.typesetting_format,
    tf.display_name,
    tf.veritas_support_level,
    COUNT(*) as document_count,
    COUNT(*) FILTER (WHERE d.structured_math_content IS NOT NULL) as migrated_count,
    COUNT(*) FILTER (WHERE d.veritas_compatible = true) as veritas_ready_count,
    ROUND(AVG(d.math_complexity_score), 3) as avg_complexity,
    COUNT(*) FILTER (WHERE d.math_complexity_score > 0.7) as high_complexity_count,
    tf.parsing_deterministic,
    tf.ai_generation_difficulty
FROM documents d
LEFT JOIN typesetting_formats tf ON d.typesetting_format = tf.format_name
GROUP BY d.typesetting_format, tf.display_name, tf.veritas_support_level, tf.parsing_deterministic, tf.ai_generation_difficulty
ORDER BY 
    CASE tf.veritas_support_level 
        WHEN 'native' THEN 1 
        WHEN 'full' THEN 2 
        WHEN 'basic' THEN 3 
        WHEN 'legacy' THEN 4 
        ELSE 5 
    END;

-- Vue recommandations migration
CREATE OR REPLACE VIEW migration_recommendations AS
SELECT 
    d.typesetting_format as current_format,
    COUNT(*) as document_count,
    tf.veritas_support_level as current_support,
    CASE 
        WHEN tf.veritas_support_level = 'legacy' THEN 'typst'
        WHEN tf.veritas_support_level = 'basic' AND tf.ai_generation_difficulty = 'hard' THEN 'typst'
        WHEN AVG(d.math_complexity_score) > 0.8 THEN 'typst'
        ELSE 'keep_current'
    END as recommended_format,
    CASE 
        WHEN tf.veritas_support_level = 'legacy' THEN 'HIGH - Legacy format needs migration'
        WHEN tf.veritas_support_level = 'basic' AND tf.ai_generation_difficulty = 'hard' THEN 'MEDIUM - Improve AI generation'
        WHEN AVG(d.math_complexity_score) > 0.8 THEN 'MEDIUM - High complexity benefits from Typst'
        ELSE 'LOW - Current format adequate'
    END as migration_priority,
    CONCAT(
        'Docs: ', COUNT(*), 
        ', Avg Complexity: ', ROUND(AVG(d.math_complexity_score), 2),
        ', Support: ', tf.veritas_support_level,
        ', AI Difficulty: ', tf.ai_generation_difficulty
    ) as recommendation_details
FROM documents d
LEFT JOIN typesetting_formats tf ON d.typesetting_format = tf.format_name
WHERE d.structured_math_content IS NOT NULL
GROUP BY d.typesetting_format, tf.veritas_support_level, tf.ai_generation_difficulty
ORDER BY 
    CASE 
        WHEN tf.veritas_support_level = 'legacy' THEN 1
        WHEN tf.veritas_support_level = 'basic' AND tf.ai_generation_difficulty = 'hard' THEN 2
        ELSE 3
    END;

-- ============================================================================
-- 4. EXÉCUTION MIGRATION (COMMENTÉE - À DÉCOMMENTER POUR LANCER)
-- ============================================================================

/*
-- ATTENTION: Décommenter pour lancer la migration réelle
-- Tester d'abord sur un petit échantillon

-- Test sur 10 documents
-- SELECT * FROM migrate_documents_typesetting_batch(10, 0);

-- Migration complète (À UTILISER AVEC PRÉCAUTION)
-- SELECT * FROM migrate_all_documents_typesetting();

-- Vérification post-migration
-- SELECT * FROM migration_format_status;
-- SELECT * FROM migration_recommendations;
*/

-- ============================================================================
-- MIGRATION 004 TERMINÉE - DONNÉES TYPESET-AGNOSTIC
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 004 ready: Auto-migration typesetting formats';
    RAISE NOTICE 'Functions available: migrate_documents_typesetting_batch(), migrate_all_documents_typesetting()';  
    RAISE NOTICE 'Views available: migration_format_status, migration_recommendations';
    RAISE NOTICE 'Execute SELECT * FROM migrate_all_documents_typesetting(); to start full migration';
    RAISE NOTICE 'Phase 2 infrastructure complete - ready for Phase 3 AI Native Typst';
END $$;
