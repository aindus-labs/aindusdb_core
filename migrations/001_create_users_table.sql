-- 🗄️ TABLE UTILISATEURS SÉCURISÉE - AINDUSDB CORE
-- Création : 20 janvier 2026
-- Objectif : Remplacer authentification hardcodée par DB sécurisée

-- Extension UUID si non présente
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table des utilisateurs avec sécurité renforcée
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Champs de sécurité
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    is_admin BOOLEAN DEFAULT false,
    
    -- Permissions et rôles
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('admin', 'moderator', 'user', 'readonly')),
    permissions TEXT[] DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    
    -- Sécurité supplémentaire
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    password_changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Contraintes
    CONSTRAINT users_username_length CHECK (LENGTH(username) >= 3),
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Index pour performances
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Table des sessions (pour gestion tokens)
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    refresh_token_jti VARCHAR(255) UNIQUE,
    
    -- Validité
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_used TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Métadonnées
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT true,
    
    -- Index
    CONSTRAINT sessions_expiry_check CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token_jti ON user_sessions(token_jti);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(is_active);

-- Table d'audit des authentifications
CREATE TABLE IF NOT EXISTS auth_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50),
    
    -- Événement
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('login_success', 'login_failed', 'logout', 'password_change', 'account_locked', 'account_unlocked')),
    
    -- Contexte
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Détails
    details JSONB DEFAULT '{}',
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_auth_audit_user_id ON auth_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_timestamp ON auth_audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_auth_audit_event_type ON auth_audit_log(event_type);

-- Trigger pour mettre à jour updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Fonction pour créer utilisateur admin par défaut
CREATE OR REPLACE FUNCTION create_admin_user()
RETURNS VOID AS $$
DECLARE
    admin_user_id UUID;
    admin_password_hash VARCHAR(255);
BEGIN
    -- Vérifier si admin existe déjà
    IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin') THEN
        -- Générer hash pour mot de passe admin temporaire
        -- NOTE: À changer immédiatement après premier login!
        admin_password_hash := '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6hsxq9w5GS'; -- 'TempAdmin2026!'
        
        INSERT INTO users (
            username,
            email,
            password_hash,
            is_active,
            is_verified,
            is_admin,
            role,
            permissions
        ) VALUES (
            'admin',
            'admin@aindusdb.local',
            admin_password_hash,
            true,
            true,
            true,
            'admin',
            ARRAY['admin', 'veritas:verify', 'veritas:calculate', 'system:read', 'system:write']
        );
        
        RAISE NOTICE 'Utilisateur admin créé avec mot de passe: TempAdmin2026!';
        RAISE NOTICE '⚠️  CHANGER CE MOT DE PASSE IMMÉDIATEMENT ⚠️';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Créer l'utilisateur admin
SELECT create_admin_user();

-- View pour utilisateurs actifs avec permissions
CREATE OR REPLACE VIEW active_users_with_permissions AS
SELECT 
    u.id,
    u.username,
    u.email,
    u.role,
    u.permissions,
    u.is_active,
    u.last_login,
    u.created_at
FROM users u
WHERE u.is_active = true;

COMMENT ON TABLE users IS 'Table des utilisateurs avec sécurité renforcée';
COMMENT ON TABLE user_sessions IS 'Sessions utilisateur pour gestion tokens JWT';
COMMENT ON TABLE auth_audit_log IS 'Audit des événements d authentification';
