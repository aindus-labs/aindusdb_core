# @echo off
REM 🗄️ execute_mfa_migration.bat - Exécuter la migration MFA
echo.
echo 🗄️ EXÉCUTION DE LA MIGRATION MFA
echo ================================

REM Vérifier PostgreSQL
psql --version >nul 2>&1
if errorlevel 1 (
    echo ❌ PostgreSQL (psql) non trouvé dans PATH
    echo.
    echo Installation requise :
    echo 1. Télécharger PostgreSQL : https://www.postgresql.org/download/windows/
    echo 2. Ajouter psql.exe au PATH
    echo 3. Relancer ce script
    pause
    exit /b 1
)

REM Vérifier le fichier de migration
if not exist "migrations\002_add_mfa_tables.sql" (
    echo ❌ Fichier de migration non trouvé : migrations\002_add_mfa_tables.sql
    pause
    exit /b 1
)

echo.
echo ⚙️  Configuration requise :
echo - Base de données PostgreSQL démarrée
echo - Connexion avec droits administrateur
echo - Nom de la base : aindusdb_core
echo.

REM Demander les informations de connexion
set /p DB_HOST="Hôte de la base (localhost) : " || set DB_HOST=localhost
set /p DB_PORT="Port (5432) : " || set DB_PORT=5432
set /p DB_USER="Utilisateur : " || set DB_USER=postgres
set /p DB_NAME="Nom de la base (aindusdb_core) : " || set DB_NAME=aindusdb_core

echo.
echo 📋 Informations de connexion :
echo   Hôte : %DB_HOST%
echo   Port : %DB_PORT%
echo   Utilisateur : %DB_USER%
echo   Base : %DB_NAME%
echo.

REM Test de connexion
echo Test de connexion à la base de données...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "SELECT version();" >nul 2>&1
if errorlevel 1 (
    echo ❌ Connexion échouée
    echo Vérifiez les informations et que PostgreSQL est démarré
    pause
    exit /b 1
)

echo ✅ Connexion réussie
echo.

REM Exécuter la migration
echo 🔧 Exécution de la migration MFA...
echo.

REM Créer un backup avant migration
echo 📦 Création du backup de pré-migration...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "\copy (SELECT * FROM users) TO 'users_backup.csv' WITH CSV HEADER" 2>nul
echo ✅ Backup créé : users_backup.csv
echo.

REM Exécuter le script SQL
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f migrations\002_add_mfa_tables.sql

if errorlevel 1 (
    echo ❌ Erreur lors de la migration
    pause
    exit /b 1
)

echo.
echo ✅ Migration MFA exécutée avec succès !
echo.

REM Vérifier les tables créées
echo 📊 Vérification des tables créées :
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "\dt user_mfa*"
echo.
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "\dt user_backup_codes"
echo.
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "\dt mfa_attempts"
echo.

REM Vérifier la colonne ajoutée
echo 📋 Vérification de la colonne mfa_enabled :
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "\d users" | findstr mfa_enabled

echo.
echo ========================================
echo 🎯 MIGRATION TERMINÉE AVEC SUCCÈS
echo ========================================
echo.
echo Les tables MFA sont prêtes :
echo • user_mfa - Configuration MFA par utilisateur
echo • user_backup_codes - Codes de secours
echo • mfa_attempts - Journal des tentatives
echo • Colonne mfa_enabled ajoutée à users
echo.
echo 🔍 Prochaines étapes :
echo 1. Redémarrer l'application
echo 2. Activer MFA pour les comptes admin
echo 3. Tester avec Google Authenticator
echo.

pause
