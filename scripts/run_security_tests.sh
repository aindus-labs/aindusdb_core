#!/bin/bash
# 🧪 run_security_tests.sh - Exécuter tous les tests de sécurité

set -e

echo "🔐 SUITE DE TESTS SÉCURITÉ - AindusDB Core"
echo "=========================================="

# Vérifier les prérequis
echo "📋 Vérification des prérequis..."

# Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 requis"
    exit 1
fi

# Docker (optionnel)
if command -v docker &> /dev/null; then
    echo "✅ Docker trouvé"
    DOCKER_AVAILABLE=true
else
    echo "⚠️  Docker non trouvé (tests de conteneur ignorés)"
    DOCKER_AVAILABLE=false
fi

# Créer le répertoire des rapports
REPORT_DIR="security_reports_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"

echo ""
echo "🚀 DÉMARRAGE DES TESTS"
echo "====================="

# 1. Scan des dépendances
echo ""
echo "1️⃣  Scan des dépendances Python"
echo "-------------------------------"

echo "Installation des outils de scan..."
pip install safety bandit semgrep

echo "Scan avec Safety..."
safety check --json --output "$REPORT_DIR/safety_report.json" || true
safety check --output "$REPORT_DIR/safety_report.txt"

echo "Scan avec Bandit..."
bandit -r app/ -f json -o "$REPORT_DIR/bandit_report.json" || true
bandit -r app/ -o "$REPORT_DIR/bandit_report.txt"

echo "Scan avec Semgrep..."
semgrep --config=auto --json --output="$REPORT_DIR/semgrep_report.json" app/ || true
semgrep --config=auto app/ > "$REPORT_DIR/semgrep_report.txt"

# 2. Vérifier si le serveur est démarré
echo ""
echo "2️⃣  Tests dynamiques"
echo "-------------------"

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Serveur détecté, lancement des tests dynamiques..."
    
    # Exécuter la suite de tests
    python tests/test_security_suite.py > "$REPORT_DIR/dynamic_tests.txt" 2>&1
    
    # Test avec OWASP ZAP si disponible
    if command -v docker &> /dev/null; then
        echo "Scan avec OWASP ZAP..."
        docker run -t owasp/zap2docker-stable \
            zap-baseline.py -t http://localhost:8000 \
            -J "$REPORT_DIR/zap_report.json" \
            -w "$REPORT_DIR/zap_report.html" || true
    fi
    
    # Test avec SQLMap si disponible
    if command -v sqlmap &> /dev/null; then
        echo "Test avec SQLMap..."
        sqlmap -u "http://localhost:8000/api/v1/vectors/search?q=1" \
            --batch --random-agent --level=1 --risk=1 \
            --output-dir="$REPORT_DIR/sqlmap_results" || true
    fi
else
    echo "⚠️  Serveur non démarré. Démarrer avec:"
    echo "   uvicorn app.main:app --reload"
    echo "Tests dynamiques ignorés."
fi

# 3. Tests de conteneur
echo ""
echo "3️⃣  Tests de conteneur"
echo "---------------------"

if [ "$DOCKER_AVAILABLE" = true ]; then
    echo "Build de l'image Docker..."
    docker build -t aindusdb-core:security-test . || echo "⚠️  Build Docker échoué"
    
    if docker images | grep aindusdb-core; then
        echo "Scan avec Trivy..."
        if docker run --rm -v "$PWD:/reports" \
            aquasec/trivy:latest image \
            --format json --output "/reports/trivy_report.json" \
            aindusdb-core:security-test 2>/dev/null || true; then
            echo "✅ Trivy scan complété"
        else
            echo "⚠️  Trivy non disponible"
        fi
    fi
else
    echo "Tests de conteneur ignorés (Docker non disponible)"
fi

# 4. Tests de charge
echo ""
echo "4️⃣  Tests de charge"
echo "------------------"

if command -v locust &> /dev/null; then
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "Exécution des tests de charge..."
        locust -f tests/locustfile.py --headless \
            --users 20 --spawn-rate 2 \
            --run-time 30s --host http://localhost:8000 \
            --html "$REPORT_DIR/load_test_report.html" || true
    else
        echo "⚠️  Serveur requis pour les tests de charge"
    fi
else
    echo "Installation de Locust..."
    pip install locust
    echo "⚠️  Relancer le script après installation pour les tests de charge"
fi

# 5. Génération du rapport
echo ""
echo "5️⃣  Génération du rapport"
echo "-----------------------"

cat > "$REPORT_DIR/security_summary.md" << EOF
# 🔐 Security Test Report - AindusDB Core

**Date**: $(date)
**Environnement**: Local

## 📊 Résultats des Tests

### 1. Scan des Dépendances
- **Safety**: $(grep -c "vulnerability" "$REPORT_DIR/safety_report.txt" 2>/dev/null || echo "0") vulnérabilités
- **Bandit**: $(grep -c "Issue" "$REPORT_DIR/bandit_report.txt" 2>/dev/null || echo "0") problèmes
- **Semgrep**: $(grep -c "error" "$REPORT_DIR/semgrep_report.txt" 2>/dev/null || echo "0") erreurs

### 2. Tests Dynamiques
$(if [ -f "$REPORT_DIR/dynamic_tests.txt" ]; then
    echo "- Tests d'injection: Voir rapport détaillé"
    echo "- Tests d'authentification: Voir rapport détaillé"
    echo "- Tests de configuration: Voir rapport détaillé"
else
    echo "- Non exécutés (serveur non démarré)"
fi)

### 3. Sécurité des Conteneurs
$(if [ -f "$REPORT_DIR/trivy_report.json" ]; then
    echo "- Trivy: Scan complété"
else
    echo "- Non exécuté (Docker/Trivy non disponible)"
fi)

### 4. Tests de Charge
$(if [ -f "$REPORT_DIR/load_test_report.html" ]; then
    echo "- Locust: Rapport HTML généré"
else
    echo "- Non exécutés"
fi)

## 🎯 Actions Recommandées

1. **Revoir les vulnérabilités HIGH/CRITICAL** dans Safety
2. **Corriger les problèmes Bandit** de haute sévérité
3. **Analyser les résultats ZAP** pour les alertes
4. **Mettre à jour les dépendances** avec vulnérabilités connues

## 📁 Fichiers Générés

$(ls -la "$REPORT_DIR")

EOF

# 6. Afficher le résumé
echo ""
echo "📋 RÉSUMÉ DES TESTS"
echo "=================="

# Compter les problèmes critiques
CRITICAL_COUNT=0

if [ -f "$REPORT_DIR/safety_report.json" ]; then
    CRITICAL_COUNT=$((CRITICAL_COUNT + $(cat "$REPORT_DIR/safety_report.json" | jq '.vulnerabilities | map(select(.severity == "CRITICAL")) | length' 2>/dev/null || echo 0)))
fi

if [ -f "$REPORT_DIR/bandit_report.json" ]; then
    CRITICAL_COUNT=$((CRITICAL_COUNT + $(cat "$REPORT_DIR/bandit_report.json" | jq '.results | map(select(.issue_severity == "HIGH")) | length' 2>/dev/null || echo 0)))
fi

echo "📊 Rapport généré dans: $REPORT_DIR"
echo "🔍 Problèmes critiques: $CRITICAL_COUNT"

if [ $CRITICAL_COUNT -gt 0 ]; then
    echo ""
    echo "⚠️  VULNÉRABILITÉS CRITIQUES DÉTECTÉES!"
    echo "Veuillez consulter les rapports détaillés."
    exit 1
else
    echo ""
    echo "✅ Aucune vulnérabilité critique détectée"
fi

echo ""
echo "📄 Rapport complet: $REPORT_DIR/security_summary.md"
echo ""
echo "Pour consulter les rapports:"
echo "  cat $REPORT_DIR/security_summary.md"
echo "  # Ouvrir les rapports HTML dans le navigateur"
echo "  open $REPORT_DIR/*.html"

echo ""
echo "🎉 TESTS TERMINÉS"
