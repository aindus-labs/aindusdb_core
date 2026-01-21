# @echo off
REM 🔍 AUDIT DE CONFORMITÉ OWASP - AindusDB Core (Windows)
echo.
echo 🔍 AUDIT DE CONFORMITÉ OWASP - AindusDB Core
echo ==========================================

REM Vérifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python non trouvé
    pause
    exit /b 1
)

REM Vérifier l'environnement virtuel
if not exist "venv" (
    echo ⚠️  Environnement virtuel non trouvé
    echo Création de l'environnement...
    python -m venv venv
)

REM Activer l'environnement
call venv\Scripts\activate.bat

REM Installer les dépendances si nécessaire
pip show pydantic >nul 2>&1
if errorlevel 1 (
    echo 📦 Installation des dépendances...
    pip install -r requirements.txt
)

REM Exécuter l'audit
echo.
echo 🚀 Exécution de l'audit OWASP...
echo.

python scripts/owasp_audit.py
if errorlevel 1 (
    echo.
    echo ❌ Échec de l'audit
    pause
    exit /b 1
)

echo.
echo ✅ Audit terminé avec succès!

REM Afficher le résumé si le rapport existe
if exist "owasp_audit_report.json" (
    echo.
    echo 📊 RÉSUMÉ DE L'AUDIT :
    echo =====================
    
    REM Extraire le score avec python
    for /f "delims=" %%i in ('python -c "import json; print(json.load(open('owasp_audit_report.json'))['score']['global'])"') do set SCORE=%%i
    for /f "delims=" %%i in ('python -c "import json; print(json.load(open('owasp_audit_report.json'))['score']['level'])"') do set LEVEL=%%i
    
    echo Score OWASP : %SCORE%/10 (%LEVEL%)
    
    REM Afficher les recommandations
    echo.
    echo 🎯 RECOMMANDATIONS PRIORITAIRES :
    python -c "import json; [print(f'  • {rec}') for rec in json.load(open('owasp_audit_report.json'))['recommendations'][:3]]"
)

echo.
echo ==========================================
echo 📄 Rapport détaillé : owasp_audit_report.json
echo.
echo 🔍 Prochaines étapes recommandées :
echo 1. Analyser le rapport détaillé
echo 2. Implémenter les recommandations prioritaires
echo 3. Planifier un audit de sécurité externe
echo 4. Préparer la documentation de conformité

pause
