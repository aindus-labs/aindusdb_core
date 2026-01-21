#!/bin/bash
# 🔍 sonar_audit.sh - Audit de code statique avec SonarQube

set -e

echo "🔍 SONARQUBE STATIC CODE ANALYSIS"
echo "==============================="

# Configuration
PROJECT_KEY="aindusdb-core"
PROJECT_NAME="AindusDB Core"
SONAR_HOST_URL="http://localhost:9000"
SONAR_TOKEN="${SONAR_TOKEN:-}"

# Vérifier les prérequis
echo "📋 Vérification des prérequis..."

# Java
if ! command -v java &> /dev/null; then
    echo "❌ Java 11+ requis pour SonarQube Scanner"
    exit 1
fi

# Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 requis"
    exit 1
fi

# Vérifier si SonarQube est en cours d'exécution
if curl -s "$SONAR_HOST_URL/api/system/status" | grep -q "UP"; then
    echo "✅ SonarQube détecté à $SONAR_HOST_URL"
else
    echo "⚠️  SonarQube non détecté. Démarrage avec Docker..."
    if command -v docker &> /dev/null; then
        docker run -d --name sonarqube \
            -p 9000:9000 \
            -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true \
            sonarqube:community
        
        echo "⏳ Attente du démarrage de SonarQube..."
        for i in {1..30}; do
            if curl -s "$SONAR_HOST_URL/api/system/status" | grep -q "UP"; then
                echo "✅ SonarQube démarré"
                break
            fi
            echo -n "."
            sleep 5
        done
    else
        echo "❌ Docker requis pour démarrer SonarQube"
        echo "Ou démarrez SonarQube manuellement avant d'exécuter ce script"
        exit 1
    fi
fi

# Télécharger SonarScanner
echo ""
echo "📦 Téléchargement de SonarScanner..."
SCANNER_VERSION="4.8.0.2856"
SCANNER_FILE="sonar-scanner-cli-$SCANNER_VERSION.zip"

if [ ! -f "$SCANNER_FILE" ]; then
    wget -O "$SCANNER_FILE" \
        "https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-$SCANNER_VERSION.zip"
fi

# Extraire le scanner
if [ ! -d "sonar-scanner-$SCANNER_VERSION" ]; then
    unzip -q "$SCANNER_FILE"
fi

export SONAR_SCANNER_HOME="$PWD/sonar-scanner-$SCANNER_VERSION"
export PATH="$SONAR_SCANNER_HOME/bin:$PATH"

echo "✅ SonarScanner prêt"

# Installer les plugins Python pour SonarQube
echo ""
echo "🐍 Installation des plugins Python..."
pip install sonar-python==3.3.0.883

# Créer la configuration SonarQube
echo ""
echo "⚙️  Configuration de l'analyse..."

cat > sonar-project.properties << EOF
# SonarQube Project Configuration
sonar.projectKey=$PROJECT_KEY
sonar.projectName=$PROJECT_NAME
sonar.projectVersion=1.0.0

# Sources
sonar.sources=app,tests
sonar.tests=tests
sonar.inclusions=**/*.py
sonar.exclusions=**/migrations/**,**/__pycache__/**,**/venv/**,**/.venv/**

# Python
sonar.python.coverage.reportPaths=coverage.xml
sonar.python.xunit.reportPath=xunit-test-results.xml

# Encoding
sonar.sourceEncoding=UTF-8

# Quality Profiles
sonar.qualityprofile.wait=true

# Additional parameters
sonar.python.bandit.reportPaths=bandit-report.json
sonar.python.pylint.reportPaths=pylint-report.txt
sonar.python.flake8.reportPaths=flake8-report.txt
EOF

# Exécuter les outils d'analyse Python
echo ""
echo "🔬 Exécution des analyses Python..."

# Bandit (sécurité)
echo "  • Bandit (sécurité)..."
bandit -r app/ -f json -o bandit-report.json || true

# Pylint (qualité)
echo "  • Pylint (qualité)..."
pylint app/ --output-format=json > pylint-report.json || true
pylint app/ > pylint-report.txt || true

# Flake8 (style)
echo "  • Flake8 (style)..."
flake8 app/ > flake8-report.txt || true

# Tests de couverture avec coverage
echo "  • Coverage (couverture de tests)..."
pip install coverage pytest pytest-asyncio
coverage run -m pytest tests/ -v
coverage xml
coverage html

# Tests unitaires avec pytest (format xUnit)
echo "  • Pytest (tests unitaires)..."
pytest tests/ --junitxml=xunit-test-results.xml || true

# Complexité avec radon
echo "  • Radon (complexité)..."
pip install radon
radon cc app/ --json > radon-complexity.json || true
radon mi app/ --json > radon-maintainability.json || true

# Lancer l'analyse SonarQube
echo ""
echo "🚀 Lancement de l'analyse SonarQube..."
echo "Cela peut prendre plusieurs minutes..."

sonar-scanner \
    -Dsonar.projectKey=$PROJECT_KEY \
    -Dsonar.sources=app \
    -Dsonar.tests=tests \
    -Dsonar.host.url=$SONAR_HOST_URL \
    -Dsonar.login=$SONAR_TOKEN \
    -Dsonar.python.bandit.reportPaths=bandit-report.json \
    -Dsonar.python.pylint.reportPaths=pylint-report.txt \
    -Dsonar.python.flake8.reportPaths=flake8-report.txt \
    -Dsonar.python.coverage.reportPaths=coverage.xml \
    -Dsonar.python.xunit.reportPath=xunit-test-results.xml

# Vérifier les résultats
echo ""
echo "📊 RÉSULTATS DE L'ANALYSE"
echo "========================"

# Obtenir le task ID
TASK_ID=$(curl -s -u "$SONAR_TOKEN:" \
    "$SONAR_HOST_URL/api/ce/activity?component=$PROJECT_KEY&type=REPORT" \
    | jq -r '.tasks[0].id')

# Attendre la fin de l'analyse
echo "⏳ Attente des résultats..."
for i in {1..60}; do
    STATUS=$(curl -s -u "$SONAR_TOKEN:" \
        "$SONAR_HOST_URL/api/ce/task?id=$TASK_ID" \
        | jq -r '.task.status')
    
    if [ "$STATUS" = "SUCCESS" ]; then
        echo "✅ Analyse terminée"
        break
    elif [ "$STATUS" = "FAILED" ]; then
        echo "❌ Échec de l'analyse"
        exit 1
    fi
    
    echo -n "."
    sleep 2
done

# Obtenir l'ID de l'analyse
ANALYSIS_ID=$(curl -s -u "$SONAR_TOKEN:" \
    "$SONAR_HOST_URL/api/ce/task?id=$TASK_ID" \
    | jq -r '.task.analysisId')

# Obtenir les métriques principales
echo ""
echo "📈 Métriques principales:"
METRICS=$(curl -s -u "$SONAR_TOKEN:" \
    "$SONAR_HOST_URL/api/measures/component?component=$PROJECT_KEY&metricKeys=bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density,sqale_rating,reliability_rating,security_rating")

echo "$METRICS" | jq -r '
    .component.measures[] |
    "\(.metric): \(.value)"
'

# Calculer le score de qualité
BUGS=$(echo "$METRICS" | jq -r '.component.measures[] | select(.metric=="bugs") | ..value')
VULNS=$(echo "$METRICS" | jq -r '.component.measures[] | select(.metric=="vulnerabilities") | .value')
CODE_SMELLS=$(echo "$METRICS" | jq -r '.component.measures[] | select(.metric=="code_smells") | .value')
COVERAGE=$(echo "$METRICS" | jq -r '.component.measures[] | select(.metric=="coverage") | .value')

echo ""
echo "🎯 Score de Qualité:"
TOTAL_ISSUES=$((BUGS + VULNS + CODE_SMELLS))

if [ "$TOTAL_ISSUES" -eq 0 ]; then
    echo "  ✅ QUALITÉ EXCELLENTE (Aucun problème)"
elif [ "$TOTAL_ISSUES" -le 10 ]; then
    echo "  ✅ BONNE QUALITÉ (Moins de 10 problèmes)"
elif [ "$TOTAL_ISSUES" -le 50 ]; then
    echo "  ⚠️  QUALITÉ MOYENNE ($TOTAL_ISSUES problèmes)"
else
    echo "  ❌ QUALITÉ À AMÉLIORER ($TOTAL_ISSUES problèmes)"
fi

echo ""
echo "📄 Rapport détaillé disponible:"
echo "  • SonarQube Dashboard: $SONAR_HOST_URL/dashboard?id=$PROJECT_KEY"
echo "  • Coverage Report: htmlcov/index.html"
echo "  • Bandit Report: bandit-report.json"
echo "  • Pylint Report: pylint-report.txt"

# Générer un rapport résumé
cat > sonar-audit-summary.md << EOF
# 🔍 SonarQube Audit Report

**Date**: $(date)
**Projet**: $PROJECT_NAME
**Version**: 1.0.0

## 📊 Résumé des Métriques

| Métrique | Valeur | Status |
|----------|--------|--------|
| Bugs | $BUGS | $([ $BUGS -eq 0 ] && echo "✅" || echo "⚠️") |
| Vulnérabilités | $VULNS | $([ $VULNS -eq 0 ] && echo "✅" || echo "⚠️") |
| Code Smells | $CODE_SMELLS | $([ $CODE_SMELLS -le 10 ] && echo "✅" || echo "⚠️") |
| Couverture | $COVERAGE% | $([ ${COVERAGE%.*} -ge 80 ] && echo "✅" || echo "⚠️") |

## 🎯 Actions Recommandées

EOF

if [ "$BUGS" -gt 0 ]; then
    echo "- Corriger les $BUGS bugs identifiés" >> sonar-audit-summary.md
fi

if [ "$VULNS" -gt 0 ]; then
    echo "- Traiter les $VULNS vulnérabilités de sécurité" >> sonar-audit-summary.md
fi

if [ "$CODE_SMELLS" -gt 10 ]; then
    echo "- Refactoriser le code pour réduire les code smells" >> sonar-audit-summary.md
fi

if [ "${COVERAGE%.*}" -lt 80 ]; then
    echo "- Améliorer la couverture de tests (actuellement $COVERAGE%)" >> sonar-audit-summary.md
fi

echo ""
echo "✅ Audit SonarQube terminé"
echo "📄 Rapport sauvegardé: sonar-audit-summary.md"
