#!/bin/bash
# 🗄️ setup_auth_db.sh - Script de configuration base de données auth
# Usage: ./setup_auth_db.sh [db_url]

DB_URL=${1:-"postgresql://aindusdb:CHANGE_STRONG_PASSWORD@localhost:5432/aindusdb_core"}

echo "🔧 Configuration Authentification DB - AindusDB Core"
echo "Database URL: $DB_URL"
echo "=========================================="

# Vérifier psql
if ! command -v psql &> /dev/null; then
    echo "❌ psql non trouvé. Installez PostgreSQL client."
    exit 1
fi

# Exécuter la migration
echo ""
echo "📋 Exécution migration 001_create_users_table.sql..."
if psql "$DB_URL" -f migrations/001_create_users_table.sql; then
    echo "✅ Migration exécutée avec succès"
else
    echo "❌ Erreur lors de la migration"
    exit 1
fi

# Vérifier création admin
echo ""
echo "🔍 Vérification utilisateur admin..."
ADMIN_PASSWORD=$(psql "$DB_URL" -t -c "SELECT 'TempAdmin2026!' WHERE EXISTS (SELECT 1 FROM users WHERE username = 'admin');" | tr -d ' ')

if [ "$ADMIN_PASSWORD" = "TempAdmin2026!" ]; then
    echo "✅ Utilisateur admin créé"
    echo "⚠️  MOT DE PASSE ADMIN: TempAdmin2026!"
    echo "🚨 CHANGEZ CE MOT DE PASSE IMMÉDIATEMENT! 🚨"
else
    echo "❌ Utilisateur admin non trouvé"
    exit 1
fi

# Test connexion
echo ""
echo "🧪 Test connexion authentification..."
cat > test_auth.py << 'EOF'
import asyncio
import sys
sys.path.append('.')

async def test_auth():
    from app.services.auth_service import get_auth_service
    
    auth_svc = await get_auth_service()
    
    # Test login admin
    user = await auth_svc.authenticate_user("admin", "TempAdmin2026!")
    
    if user:
        print("✅ Authentification admin réussie")
        print(f"   User ID: {user.id}")
        print(f"   Username: {user.username}")
        print(f"   Role: {user.role}")
        print(f"   Permissions: {user.permissions}")
        return True
    else:
        print("❌ Authentification admin échouée")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_auth())
    sys.exit(0 if success else 1)
EOF

if python test_auth.py; then
    echo "✅ Test authentification réussi"
else
    echo "❌ Test authentification échoué"
    exit 1
fi

# Nettoyer
rm test_auth.py

echo ""
echo "=========================================="
echo "🎉 Configuration authentification terminée!"
echo ""
echo "📝 Prochaines étapes:"
echo "1. Changez le mot de passe admin immédiatement"
echo "2. Créez vos utilisateurs avec le endpoint /auth/register"
echo "3. Configurez les permissions selon vos besoins"
echo ""
echo "🔐 Credentials admin (temporaire):"
echo "   Username: admin"
echo "   Password: TempAdmin2026!"
echo ""
echo "⚠️  NE UTILISEZ PAS CES CREDENTIALS EN PRODUCTION!"
