# @echo off
REM 🧪 test_rate_limiting.bat - Script de test du rate limiting Windows

echo.
echo 🧪 TEST RATE LIMITING ^& PROTECTION DDoS
echo ======================================

REM Vérifier si curl est disponible
curl --version >nul 2>&1
if errorlevel 1 (
    echo ❌ curl requis pour exécuter ce test
    pause
    exit /b 1
)

REM Vérifier si le serveur est démarré
echo 📡 Vérification du serveur...
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo ❌ Serveur non démarré. Démarrer avec:
    echo    uvicorn app.main:app --reload
    pause
    exit /b 1
)

echo ✅ Serveur démarré
echo.

REM Test 1: Rate limiting basique
echo 🔍 Test 1: Rate Limiting Basique
echo --------------------------------
echo Envoi de 10 requêtes rapides...

for /l %%i in (1,1,10) do (
    curl -s -w "%%{http_code}" http://localhost:8000/api/v1/health > temp_response.txt
    set /p http_code=<temp_response.txt
    
    set "status="
    if "!http_code!"=="429" set "status=⏱️  Rate limité"
    if "!http_code!"=="200" set "status=✅ Succès"
    if "!status!"=="" set "status=❌ Erreur (!http_code!)"
    
    echo   Requête %%i: !status!
    
    timeout /t 1 >nul
)

del temp_response.txt
echo.

REM Test 2: Brute force sur login
echo 🛡️  Test 2: Protection Brute Force
echo ------------------------------------
echo Simulation de 10 tentatives de login échouées...

for /l %%i in (1,1,10) do (
    curl -s -w "%%{http_code}" -X POST ^
        -H "Content-Type: application/json" ^
        -d "{\"username\":\"admin\",\"password\":\"wrong%%i\"}" ^
        http://localhost:8000/auth/login > temp_response.txt
    
    set /p http_code=<temp_response.txt
    
    set "status="
    if "!http_code!"=="429" (
        set "status=🚫 Brute force bloqué"
        echo   Tentative %%i: !status!
        goto :end_brute_force
    )
    if "!http_code!"=="401" set "status=❌ Échec authentification"
    if "!status!"=="" set "status=? (!http_code!)"
    
    echo   Tentative %%i: !status!
    
    timeout /t 2 >nul
)

:end_brute_force
del temp_response.txt
echo.

REM Test 3: Vérification des headers
echo 📋 Test 3: Headers Rate Limit
echo -------------------------------
echo Vérification des headers de rate limit...

curl -s -I http://localhost:8000/api/v1/health > headers.txt

echo Headers reçus:
findstr /i "x-ratelimit" headers.txt || echo   ❌ Headers rate limit non trouvés

del headers.txt
echo.

echo ======================================
echo ✅ TESTS TERMINÉS
echo.
echo 📊 Résultats attendus:
echo   • Rate limiting: Après ~6 requêtes
echo   • Brute force: Après 10 tentatives
echo   • DDoS: Limitation automatique
echo   • Headers: X-RateLimit-* présents

pause
