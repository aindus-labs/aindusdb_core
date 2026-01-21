# @echo off
REM 🧪 run_security_tests.bat - Exécuter tous les tests de sécurité (Windows)

echo.
echo 🔐 SUITE DE TESTS SÉCURITÉ - AindusDB Core
echo ==========================================

REM Vérifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python requis
    pause
    exit /b 1
)

REM Créer le répertoire des rapports
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "REPORT_DIR=security_reports_%dt:~0,8%_%dt:~8,6%"
mkdir "%REPORT_DIR%"

echo.
echo 🚀 DÉMARRAGE DES TESTS
echo ====================

REM 1. Scan des dépendances
echo.
echo 1️⃣  Scan des dépendances Python
echo --------------------------------

echo Installation des outils de scan...
python -m pip install safety bandit semgrep

echo Scan avec Safety...
python -m safety check --json --output "%REPORT_DIR%\safety_report.json"
python -m safety check --output "%REPORT_DIR%\safety_report.txt"

echo Scan avec Bandit...
python -m bandit -r app/ -f json -o "%REPORT_DIR%\bandit_report.json"
python -m bandit -r app/ -o "%REPORT_DIR%\bandit_report.txt"

echo Scan avec Semgrep...
python -m semgrep --config=auto --json --output="%REPORT_DIR%\semgrep_report.json" app/
python -m semgrep --config=auto app/ > "%REPORT_DIR%\semgrep_report.txt"

REM 2. Tests dynamiques
echo.
echo 2️⃣  Tests dynamiques
echo ------------------

curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Serveur non démarré. Démarrer avec:
    echo    uvicorn app.main:app --reload
    echo Tests dynamiques ignorés.
) else (
    echo ✅ Serveur détecté, lancement des tests dynamiques...
    
    REM Exécuter la suite de tests
    python tests/test_security_suite.py > "%REPORT_DIR%\dynamic_tests.txt" 2>&1
    
    REM Test avec OWASP ZAP si Docker disponible
    docker --version >nul 2>&1
    if not errorlevel 1 (
        echo Scan avec OWASP ZAP...
        docker run -t owasp/zap2docker-stable ^
            zap-baseline.py -t http://localhost:8000 ^
            -J "%REPORT_DIR%\zap_report.json" ^
            -w "%REPORT_DIR%\zap_report.html"
    )
)

REM 3. Tests de conteneur
echo.
echo 3️⃣  Tests de conteneur
echo -------------------

docker --version >nul 2>&1
if errorlevel 1 (
    echo Tests de conteneur ignorés (Docker non disponible)
) else (
    echo Build de l'image Docker...
    docker build -t aindusdb-core:security-test .
    
    if not errorlevel 1 (
        echo Scan avec Trivy...
        docker run --rm -v "%CD%:/reports" ^
            aquasec/trivy:latest image ^
            --format json --output "/reports/trivy_report.json" ^
            aindusdb-core:security-test
    )
)

REM 4. Tests de charge
echo.
echo 4️⃣  Tests de charge
echo ------------------

python -c "import locust" >nul 2>&1
if errorlevel 1 (
    echo Installation de Locust...
    python -m pip install locust
    echo ⚠️  Relancer le script après installation pour les tests de charge
) else (
    curl -s http://localhost:8000/health >nul 2>&1
    if not errorlevel 1 (
        echo Exécution des tests de charge...
        python -m locust -f tests/locustfile.py --headless ^
            --users 20 --spawn-rate 2 ^
            --run-time 30s --host http://localhost:8000 ^
            --html "%REPORT_DIR%\load_test_report.html"
    ) else (
        echo ⚠️  Serveur requis pour les tests de charge
    )
)

REM 5. Génération du rapport
echo.
echo 5️⃣  Génération du rapport
echo -----------------------

(
echo # 🔐 Security Test Report - AindusDB Core
echo.
echo **Date**: %date%
echo **Environnement**: Local
echo.
echo ## 📊 Résultats des Tests
echo.
echo ### 1. Scan des Dépendances
echo - **Safety**: Voir safety_report.txt
echo - **Bandit**: Voir bandit_report.txt
echo - **Semgrep**: Voir semgrep_report.txt
echo.
echo ### 2. Tests Dynamiques
if exist "%REPORT_DIR%\dynamic_tests.txt" (
    echo - Tests dynamiques: Voir rapport détaillé
) else (
    echo - Non exécutés ^(serveur non démarré^)
)
echo.
echo ### 3. Sécurité des Conteneurs
if exist "%REPORT_DIR%\trivy_report.json" (
    echo - Trivy: Scan complété
) else (
    echo - Non exécuté ^(Docker/Trivy non disponible^)
)
echo.
echo ### 4. Tests de Charge
if exist "%REPORT_DIR%\load_test_report.html" (
    echo - Locust: Rapport HTML généré
) else (
    echo - Non exécutés
)
echo.
echo ## 🎯 Actions Recommandées
echo.
echo 1. **Revoir les vulnérabilités HIGH/CRITICAL** dans Safety
echo 2. **Corriger les problèmes Bandit** de haute sévérité
echo 3. **Analyser les résultats ZAP** pour les alertes
echo 4. **Mettre à jour les dépendances** avec vulnérabilités connues
echo.
echo ## 📁 Fichiers Générés
echo.
) > "%REPORT_DIR%\security_summary.md"

dir "%REPORT_DIR%" /b >> "%REPORT_DIR%\security_summary.md"

REM 6. Afficher le résumé
echo.
echo 📋 RÉSUMÉ DES TESTS
echo ==================

echo 📊 Rapport généré dans: %REPORT_DIR%
echo.
echo 📄 Rapport complet: %REPORT_DIR%\security_summary.md
echo.
echo Pour consulter les rapports:
echo   type %REPORT_DIR%\security_summary.md
echo   # Ouvrir les rapports HTML dans le navigateur
echo   start %REPORT_DIR%\*.html

echo.
echo 🎉 TESTS TERMINÉS
pause
