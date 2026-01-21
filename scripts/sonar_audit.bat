# @echo off
REM 🔍 sonar_audit.bat - Audit de code statique avec SonarQube (Windows)

echo.
echo 🔍 SONARQUBE STATIC CODE ANALYSIS
echo ===============================

REM Configuration
set PROJECT_KEY=aindusdb-core
set PROJECT_NAME=AindusDB Core
set SONAR_HOST_URL=http://localhost:9000
if "%SONAR_TOKEN%"=="" set SONAR_TOKEN=

REM Vérifier Java
java -version >nul 2>&1
if errorlevel 1 (
    echo ❌ Java 11+ requis pour SonarQube Scanner
    pause
    exit /b 1
)

REM Vérifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 3 requis
    pause
    exit /b 1
)

REM Vérifier SonarQube
curl -s "%SONAR_HOST_URL%/api/system/status" | findstr "UP" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  SonarQube non détecté. Démarrage avec Docker...
    docker --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Docker requis pour démarrer SonarQube
        pause
        exit /b 1
    )
    
    echo Démarrage de SonarQube...
    docker run -d --name sonarqube ^
        -p 9000:9000 ^
        -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true ^
        sonarqube:community
    
    echo ⏳ Attente du démarrage...
    :wait_loop
    timeout /t 5 >nul
    curl -s "%SONAR_HOST_URL%/api/system/status" | findstr "UP" >nul 2>&1
    if errorlevel 1 (
        echo.
        goto wait_loop
    )
    echo ✅ SonarQube démarré
) else (
    echo ✅ SonarQube détecté à %SONAR_HOST_URL%
)

REM Télécharger SonarScanner
echo.
echo 📦 Téléchargement de SonarScanner...
set SCANNER_VERSION=4.8.0.2856
set SCANNER_FILE=sonar-scanner-cli-%SCANNER_VERSION%.zip

if not exist "%SCANNER_FILE%" (
    powershell -Command "Invoke-WebRequest -Uri 'https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-%SCANNER_VERSION%.zip' -OutFile '%SCANNER_FILE%'"
)

REM Extraire le scanner
if not exist "sonar-scanner-%SCANNER_VERSION%" (
    powershell -Command "Expand-Archive -Path '%SCANNER_FILE%' -DestinationPath ."
)

set SONAR_SCANNER_HOME=%CD%\sonar-scanner-%SCANNER_VERSION%
set PATH=%SONAR_SCANNER_HOME%\bin;%PATH%

echo ✅ SonarScanner prêt

REM Installer les plugins Python
echo.
echo 🐍 Installation des plugins Python...
pip install sonar-python==3.3.0.883

REM Créer la configuration
echo.
echo ⚙️  Configuration de l'analyse...
(
echo # SonarQube Project Configuration
echo sonar.projectKey=%PROJECT_KEY%
echo sonar.projectName=%PROJECT_NAME%
echo sonar.projectVersion=1.0.0
echo.
echo # Sources
echo sonar.sources=app,tests
echo sonar.tests=tests
echo sonar.inclusions=**/*.py
echo sonar.exclusions=**/migrations/**,**/__pycache__/**,**/venv/**,**/.venv/**
echo.
echo # Python
echo sonar.python.coverage.reportPaths=coverage.xml
echo sonar.python.xunit.reportPath=xunit-test-results.xml
echo.
echo # Encoding
echo sonar.sourceEncoding=UTF-8
echo.
echo # Quality Profiles
echo sonar.qualityprofile.wait=true
) > sonar-project.properties

REM Exécuter les analyses Python
echo.
echo 🔬 Exécution des analyses Python...

echo   • Bandit ^(sécurité^)...
python -m bandit -r app/ -f json -o bandit-report.json

echo   • Pylint ^(qualité^)...
python -m pylint app/ --output-format=json > pylint-report.json
python -m pylint app/ > pylint-report.txt

echo   • Flake8 ^(style^)...
python -m flake8 app/ > flake8-report.txt

echo   • Coverage ^(couverture de tests^)...
pip install coverage pytest pytest-asyncio
python -m coverage run -m pytest tests/ -v
python -m coverage xml
python -m coverage html

echo   • Pytest ^(tests unitaires^)...
python -m pytest tests/ --junitxml=xunit-test-results.xml

echo   • Radon ^(complexité^)...
pip install radon
python -m radon cc app/ --json > radon-complexity.json
python -m radon mi app/ --json > radon-maintainability.json

REM Lancer l'analyse SonarQube
echo.
echo 🚀 Lancement de l'analyse SonarQube...
echo Cela peut prendre plusieurs minutes...

sonar-scanner ^
    -Dsonar.projectKey=%PROJECT_KEY% ^
    -Dsonar.sources=app ^
    -Dsonar.tests=tests ^
    -Dsonar.host.url=%SONAR_HOST_URL% ^
    -Dsonar.login=%SONAR_TOKEN% ^
    -Dsonar.python.bandit.reportPaths=bandit-report.json ^
    -Dsonar.python.pylint.reportPaths=pylint-report.txt ^
    -Dsonar.python.flake8.reportPaths=flake8-report.txt ^
    -Dsonar.python.coverage.reportPaths=coverage.xml ^
    -Dsonar.python.xunit.reportPath=xunit-test-results.xml

REM Afficher les résultats
echo.
echo 📊 RÉSULTATS DE L'ANALYSE
echo ========================

echo.
echo 📄 Rapport détaillé disponible:
echo   • SonarQube Dashboard: %SONAR_HOST_URL%/dashboard?id=%PROJECT_KEY%
echo   • Coverage Report: htmlcov\index.html
echo   • Bandit Report: bandit-report.json
echo   • Pylint Report: pylint-report.txt

echo.
echo ✅ Audit SonarQube terminé
pause
