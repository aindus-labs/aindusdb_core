-- Migration MFA - Multi-Factor Authentication
-- Ajout des tables pour TOTP et codes de secours

-- Créer la table pour les configurations MFA
CREATE TABLE IF NOT EXISTS user_mfa (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mfa_type VARCHAR(50) NOT NULL, -- 'totp', 'webauthn', 'sms'
    secret TEXT NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    activated_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(user_id, mfa_type),
    CONSTRAINT valid_mfa_type CHECK (mfa_type IN ('totp', 'webauthn', 'sms'))
);

-- Créer la table pour les codes de secours
CREATE TABLE IF NOT EXISTS user_backup_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash VARCHAR(255) NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    used_at TIMESTAMP WITH TIME ZONE
);

-- Créer la table pour les tentatives MFA
CREATE TABLE IF NOT EXISTS mfa_attempts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mfa_type VARCHAR(50) NOT NULL,
    success BOOLEAN NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_attempt_mfa_type CHECK (mfa_type IN ('totp', 'webauthn', 'sms', 'backup_code'))
);

-- Ajouter la colonne mfa_enabled à la table users
ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN DEFAULT FALSE;

-- Index pour optimiser les performances
CREATE INDEX IF NOT EXISTS idx_user_mfa_user_id ON user_mfa(user_id);
CREATE INDEX IF NOT EXISTS idx_user_mfa_enabled ON user_mfa(enabled);
CREATE INDEX IF NOT EXISTS idx_backup_codes_user_id ON user_backup_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_backup_codes_used ON user_backup_codes(used);
CREATE INDEX IF NOT EXISTS idx_mfa_attempts_user_id ON mfa_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_mfa_attempts_created_at ON mfa_attempts(created_at);

-- Trigger pour mettre à jour updated_at
CREATE OR REPLACE FUNCTION update_mfa_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_mfa_updated_at
    BEFORE UPDATE ON user_mfa
    FOR EACH ROW
    EXECUTE FUNCTION update_mfa_updated_at();

-- Politique RLS (Row Level Security)
ALTER TABLE user_mfa ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_backup_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE mfa_attempts ENABLE ROW LEVEL SECURITY;

-- Politiques pour user_mfa
CREATE POLICY user_mfa_policy ON user_mfa
    FOR ALL
    TO authenticated_user
    USING (user_id = current_user_id());

-- Politiques pour user_backup_codes
CREATE POLICY user_backup_codes_policy ON user_backup_codes
    FOR ALL
    TO authenticated_user
    USING (user_id = current_user_id());

-- Politiques pour mfa_attempts (lecture seule pour l'utilisateur)
CREATE POLICY mfa_attempts_read_policy ON mfa_attempts
    FOR SELECT
    TO authenticated_user
    USING (user_id = current_user_id());

-- Vue pour le statut MFA
CREATE OR REPLACE VIEW user_mfa_status AS
SELECT 
    u.id as user_id,
    u.email,
    u.is_admin,
    u.mfa_enabled,
    CASE 
        WHEN um.enabled THEN 'totp'
        ELSE NULL
    END as active_mfa_method,
    um.activated_at as mfa_activated_at,
    COALESCE(backup_codes.count, 0) as backup_codes_remaining,
    CASE 
        WHEN u.mfa_enabled THEN true
        ELSE false
    END as fully_configured
FROM users u
LEFT JOIN user_mfa um ON u.id = um.user_id AND um.enabled = true
LEFT JOIN (
    SELECT user_id, COUNT(*) as count
    FROM user_backup_codes
    WHERE used = false
    GROUP BY user_id
) backup_codes ON u.id = backup_codes.user_id;

-- Commentaires
COMMENT ON TABLE user_mfa IS 'Configuration MFA par utilisateur';
COMMENT ON TABLE user_backup_codes IS 'Codes de secours MFA';
COMMENT ON TABLE mfa_attempts IS 'Journal des tentatives MFA';
COMMENT ON VIEW user_mfa_status IS 'Vue du statut MFA des utilisateurs';
