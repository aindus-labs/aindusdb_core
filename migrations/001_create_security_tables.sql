-- Migration 001: Création des tables de sécurité pour AindusDB Core
-- Phase 6 - Sécurité Avancée : Tables utilisateurs, audit et sessions
-- 
-- Cette migration crée toute l'infrastructure base de données nécessaire
-- pour l'authentification JWT, RBAC et audit trail complet.

-- ============================================================================
-- 1. TABLE USERS - Gestion des utilisateurs avec authentification
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    permissions TEXT[] DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    
    -- Contraintes de validation
    CONSTRAINT users_username_format CHECK (username ~ '^[a-zA-Z0-9_-]+$'),
    CONSTRAINT users_role_valid CHECK (role IN ('admin', 'manager', 'user', 'readonly')),
    CONSTRAINT users_email_format CHECK (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Index pour performances sur requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login);

-- ============================================================================
-- 2. TABLE AUDIT_LOGS - Traçabilité complète des opérations
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,
    level VARCHAR(20) NOT NULL DEFAULT 'info',
    category VARCHAR(30) NOT NULL DEFAULT 'data_operation',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_id VARCHAR(50),
    endpoint VARCHAR(255),
    method VARCHAR(10),
    
    -- Contraintes de validation
    CONSTRAINT audit_logs_level_valid CHECK (level IN ('info', 'warning', 'critical', 'security')),
    CONSTRAINT audit_logs_category_valid CHECK (category IN ('authentication', 'authorization', 'data_operation', 'system_admin', 'security_event', 'api_access'))
);

-- Index pour recherches et performances audit
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_username ON audit_logs(username);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_success ON audit_logs(success);
CREATE INDEX IF NOT EXISTS idx_audit_logs_level ON audit_logs(level);
CREATE INDEX IF NOT EXISTS idx_audit_logs_category ON audit_logs(category);
CREATE INDEX IF NOT EXISTS idx_audit_logs_ip_address ON audit_logs(ip_address);

-- Index composé pour requêtes complexes fréquentes
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_timestamp ON audit_logs(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_timestamp ON audit_logs(action, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_failed_actions ON audit_logs(action, success, timestamp) WHERE success = false;

-- Index GIN pour recherche dans les détails JSON
CREATE INDEX IF NOT EXISTS idx_audit_logs_details_gin ON audit_logs USING GIN (details);

-- ============================================================================
-- 3. TABLE USER_SESSIONS - Gestion des sessions et tokens
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token_hash VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    revoked_at TIMESTAMPTZ,
    revoked_reason VARCHAR(100)
);

-- Index pour gestion des sessions
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_refresh_hash ON user_sessions(refresh_token_hash);
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active, expires_at);
CREATE INDEX IF NOT EXISTS idx_user_sessions_cleanup ON user_sessions(expires_at) WHERE is_active = false;

-- ============================================================================
-- 4. TABLE API_KEYS - Clés d'API pour accès programmatique  
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    permissions TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true,
    usage_count BIGINT DEFAULT 0,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    description TEXT
);

-- Index pour API keys
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active, expires_at);

-- ============================================================================
-- 5. TABLE RATE_LIMITS - Limitation de débit par utilisateur/IP
-- ============================================================================

CREATE TABLE IF NOT EXISTS rate_limits (
    id BIGSERIAL PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL, -- user_id, ip_address, api_key_id
    identifier_type VARCHAR(20) NOT NULL, -- 'user', 'ip', 'api_key'
    endpoint VARCHAR(255),
    requests_count INTEGER NOT NULL DEFAULT 1,
    window_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    window_duration_minutes INTEGER NOT NULL DEFAULT 60,
    limit_per_window INTEGER NOT NULL DEFAULT 1000,
    blocked_until TIMESTAMPTZ,
    
    -- Contrainte unicité par fenêtre
    UNIQUE(identifier, identifier_type, endpoint, window_start)
);

-- Index pour rate limiting efficace
CREATE INDEX IF NOT EXISTS idx_rate_limits_identifier ON rate_limits(identifier, identifier_type);
CREATE INDEX IF NOT EXISTS idx_rate_limits_window ON rate_limits(window_start, window_duration_minutes);
CREATE INDEX IF NOT EXISTS idx_rate_limits_blocked ON rate_limits(blocked_until) WHERE blocked_until IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_rate_limits_cleanup ON rate_limits(window_start) WHERE requests_count = 0;

-- ============================================================================
-- 6. TABLE USER_STATS - Statistiques d'utilisation par utilisateur
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_stats (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    total_vectors_created BIGINT DEFAULT 0,
    total_searches_performed BIGINT DEFAULT 0,
    total_api_calls BIGINT DEFAULT 0,
    last_activity TIMESTAMPTZ,
    api_calls_today INTEGER DEFAULT 0,
    api_calls_this_month INTEGER DEFAULT 0,
    quota_limit INTEGER, -- NULL = unlimited
    quota_used_this_month INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour statistiques
CREATE INDEX IF NOT EXISTS idx_user_stats_last_activity ON user_stats(last_activity);
CREATE INDEX IF NOT EXISTS idx_user_stats_quota ON user_stats(quota_limit, quota_used_this_month);

-- ============================================================================
-- 7. TRIGGERS POUR AUDIT AUTOMATIQUE
-- ============================================================================

-- Fonction trigger pour audit automatique des modifications utilisateurs
CREATE OR REPLACE FUNCTION audit_user_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_logs (action, resource, details, level, category)
        VALUES ('user_created', 'user:' || NEW.id, 
                jsonb_build_object('username', NEW.username, 'role', NEW.role),
                'info', 'system_admin');
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Enregistrer les changements significatifs
        IF OLD.role != NEW.role OR OLD.is_active != NEW.is_active THEN
            INSERT INTO audit_logs (user_id, username, action, resource, details, level, category)
            VALUES (NEW.id, NEW.username, 'user_modified', 'user:' || NEW.id,
                    jsonb_build_object(
                        'old_role', OLD.role, 'new_role', NEW.role,
                        'old_active', OLD.is_active, 'new_active', NEW.is_active
                    ),
                    'warning', 'system_admin');
        END IF;
        NEW.updated_at = NOW();
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_logs (action, resource, details, level, category)
        VALUES ('user_deleted', 'user:' || OLD.id,
                jsonb_build_object('username', OLD.username, 'role', OLD.role),
                'critical', 'system_admin');
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Appliquer le trigger sur la table users
DROP TRIGGER IF EXISTS trigger_audit_user_changes ON users;
CREATE TRIGGER trigger_audit_user_changes
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_user_changes();

-- ============================================================================
-- 8. FONCTIONS UTILITAIRES POUR NETTOYAGE AUTOMATIQUE
-- ============================================================================

-- Fonction pour nettoyer les logs d'audit anciens
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(retention_days INTEGER DEFAULT 365)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_logs 
    WHERE timestamp < NOW() - INTERVAL '1 day' * retention_days;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Logger l'opération de nettoyage
    INSERT INTO audit_logs (action, details, level, category)
    VALUES ('audit_cleanup', 
            jsonb_build_object('deleted_records', deleted_count, 'retention_days', retention_days),
            'info', 'system_admin');
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour nettoyer les sessions expirées
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    UPDATE user_sessions 
    SET is_active = false, revoked_at = NOW(), revoked_reason = 'expired'
    WHERE expires_at < NOW() AND is_active = true;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Supprimer définitivement les sessions expirées depuis plus de 30 jours
    DELETE FROM user_sessions 
    WHERE is_active = false AND revoked_at < NOW() - INTERVAL '30 days';
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour réinitialiser les compteurs quotidiens/mensuels
CREATE OR REPLACE FUNCTION reset_usage_counters()
RETURNS VOID AS $$
BEGIN
    -- Réinitialiser compteurs quotidiens (à exécuter chaque jour à minuit)
    IF EXTRACT(hour FROM NOW()) = 0 AND EXTRACT(minute FROM NOW()) < 5 THEN
        UPDATE user_stats SET api_calls_today = 0;
        DELETE FROM rate_limits WHERE window_start < NOW() - INTERVAL '24 hours';
    END IF;
    
    -- Réinitialiser compteurs mensuels (premier jour du mois)
    IF EXTRACT(day FROM NOW()) = 1 AND EXTRACT(hour FROM NOW()) = 0 THEN
        UPDATE user_stats SET api_calls_this_month = 0, quota_used_this_month = 0;
    END IF;
    
    INSERT INTO audit_logs (action, level, category)
    VALUES ('usage_counters_reset', 'info', 'system_admin');
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 9. DONNÉES INITIALES - UTILISATEUR ADMIN PAR DÉFAUT
-- ============================================================================

-- Créer utilisateur admin par défaut (mot de passe: admin123!)
-- IMPORTANT: Changer ce mot de passe en production !
INSERT INTO users (username, email, full_name, password_hash, role, permissions, is_active)
VALUES (
    'admin',
    'admin@aindusdb.local',
    'System Administrator', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/1RGg/yd5zYvZpJ6Uu', -- admin123!
    'admin',
    ARRAY[
        'vectors:read', 'vectors:create', 'vectors:update', 'vectors:delete', 'vectors:search',
        'users:read', 'users:create', 'users:update', 'users:delete',
        'system:health', 'system:metrics', 'system:config', 'system:admin',
        'audit:read', 'audit:export'
    ],
    true
)
ON CONFLICT (username) DO NOTHING;

-- Créer entrée de statistiques pour l'admin
INSERT INTO user_stats (user_id, total_vectors_created, total_searches_performed)
SELECT id, 0, 0 FROM users WHERE username = 'admin'
ON CONFLICT (user_id) DO NOTHING;

-- ============================================================================
-- 10. VUES UTILITAIRES POUR MONITORING
-- ============================================================================

-- Vue des sessions actives avec détails utilisateur
CREATE OR REPLACE VIEW active_user_sessions AS
SELECT 
    s.id as session_id,
    u.id as user_id,
    u.username,
    u.role,
    s.ip_address,
    s.created_at as session_start,
    s.last_activity,
    s.expires_at,
    EXTRACT(EPOCH FROM (s.expires_at - NOW()))/60 as minutes_until_expiry
FROM user_sessions s
JOIN users u ON s.user_id = u.id
WHERE s.is_active = true AND s.expires_at > NOW()
ORDER BY s.last_activity DESC;

-- Vue des statistiques d'audit par utilisateur (derniers 30 jours)
CREATE OR REPLACE VIEW audit_summary_30d AS
SELECT 
    u.username,
    u.role,
    COUNT(*) as total_actions,
    COUNT(*) FILTER (WHERE a.success = true) as successful_actions,
    COUNT(*) FILTER (WHERE a.success = false) as failed_actions,
    COUNT(DISTINCT DATE(a.timestamp)) as active_days,
    MAX(a.timestamp) as last_activity
FROM users u
LEFT JOIN audit_logs a ON u.id = a.user_id 
WHERE a.timestamp >= NOW() - INTERVAL '30 days' OR a.timestamp IS NULL
GROUP BY u.id, u.username, u.role
ORDER BY total_actions DESC NULLS LAST;

-- Vue des tentatives de connexion suspectes
CREATE OR REPLACE VIEW suspicious_login_attempts AS
SELECT 
    ip_address,
    COUNT(*) as failed_attempts,
    COUNT(DISTINCT username) as different_usernames_tried,
    MIN(timestamp) as first_attempt,
    MAX(timestamp) as last_attempt,
    ARRAY_AGG(DISTINCT username ORDER BY username) as usernames_attempted
FROM audit_logs
WHERE action = 'login_failed' 
    AND timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY ip_address
HAVING COUNT(*) >= 5
ORDER BY failed_attempts DESC;

-- Commenter le succès de la migration
INSERT INTO audit_logs (action, details, level, category)
VALUES ('security_migration_001', 
        jsonb_build_object('tables_created', ARRAY['users', 'audit_logs', 'user_sessions', 'api_keys', 'rate_limits', 'user_stats']),
        'info', 'system_admin');

-- ============================================================================
-- NOTES POUR L'ADMINISTRATEUR
-- ============================================================================

/*
IMPORTANT - SÉCURITÉ POST-INSTALLATION :

1. CHANGER LE MOT DE PASSE ADMIN :
   UPDATE users SET password_hash = '$2b$12$NEW_HASH' WHERE username = 'admin';

2. CONFIGURER LES TÂCHES CRON POUR NETTOYAGE :
   -- Chaque jour à 2h du matin : SELECT cleanup_expired_sessions();
   -- Chaque dimanche : SELECT cleanup_old_audit_logs(365);  
   -- Chaque jour à minuit : SELECT reset_usage_counters();

3. MONITORING RECOMMANDÉ :
   -- Surveiller la vue suspicious_login_attempts
   -- Alertes sur audit_logs.level = 'critical' ou 'security'
   -- Monitoring de la croissance de audit_logs (archivage)

4. PERFORMANCE :
   -- Les index sont optimisés pour les requêtes fréquentes
   -- Partitioning recommandé pour audit_logs si > 10M enregistrements
   -- Considérer pg_stat_statements pour optimisation requêtes

5. SAUVEGARDE :
   -- audit_logs contient des données critiques pour conformité
   -- Sauvegardes chiffrées recommandées
   -- Réplication pour haute disponibilité

Utilisateur par défaut créé :
- Username: admin  
- Password: admin123! (À CHANGER IMMÉDIATEMENT)
- Email: admin@aindusdb.local
- Rôle: admin (toutes permissions)
*/
