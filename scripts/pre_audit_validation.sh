#!/bin/bash
# ✅ pre_audit_validation.sh - Validation finale avant audit externe

set -e

echo "✅ PRÉ-AUDIT VALIDATION - AindusDB Core"
echo "====================================="

# Couleurs pour le output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Compteurs
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Fonctions utilitaires
check_passed() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED_CHECKS++))
    ((TOTAL_CHECKS++))
}

check_failed() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED_CHECKS++))
    ((TOTAL_CHECKS++))
}

check_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
    ((TOTAL_CHECKS++))
}

# Créer le répertoire de rapport
REPORT_DIR="pre_audit_report_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"

echo ""
echo "🔍 VALIDATION DE LA SÉCURITÉ"
echo "=========================="

# 1. Vérifier l'environnement
echo ""
echo "1️⃣  Environnement de Test"
echo "-----------------------"

# Vérifier si on est en environnement de test
if [[ "$ENVIRONMENT" == "production" ]]; then
    check_failed "Exécution en environnement de production!"
    echo "   Arrêt immédiat pour sécurité"
    exit 1
else
    check_passed "Environnement non-production"
fi

# Vérifier les variables d'environnement
if [[ -f ".env" ]]; then
    if grep -q "admin123" .env; then
        check_failed "Mot de passe par défaut détecté!"
    else
        check_passed "Pas de mots de passe par défaut"
    fi
else
    check_warning "Fichier .env non trouvé"
fi

# 2. Configuration Sécurité
echo ""
echo "2️⃣  Configuration Sécurité"
echo "-------------------------"

# Vérifier les headers de sécurité
echo "Vérification des headers de sécurité..."
HEADERS=$(curl -s -I http://localhost:8000/ 2>/dev/null || echo "")

if echo "$HEADERS" | grep -q "X-Content-Type-Options"; then
    check_passed "X-Content-Type-Options présent"
else
    check_failed "X-Content-Type-Options manquant"
fi

if echo "$HEADERS" | grep -q "X-Frame-Options"; then
    check_passed "X-Frame-Options présent"
else
    check_failed "X-Frame-Options manquant"
fi

if echo "$HEADERS" | grep -q "Strict-Transport-Security"; then
    check_passed "HSTS présent"
else
    check_warning "HSTS manquant (OK en HTTP)"
fi

# 3. Authentification
echo ""
echo "3️⃣  Authentification"
echo "-------------------"

# Vérifier que l'authentification est requise
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"wrong","password":"wrong"}' 2>/dev/null || echo "")

if echo "$AUTH_RESPONSE" | grep -q "401\|403\|422"; then
    check_passed "Authentification fonctionnelle"
else
    check_failed "Authentification défaillante"
fi

# Vérifier MFA
if curl -s http://localhost:8000/auth/mfa/setup 2>/dev/null | grep -q "qr_code\|totp"; then
    check_passed "MFA configuré"
else
    check_warning "MFA non détecté"
fi

# 4. Base de Données
echo ""
echo "4️⃣  Base de Données"
echo "------------------"

# Vérifier la connexion à la base
if python -c "
import asyncio
import sys
sys.path.append('.')
from app.core.database import db_manager

async def test():
    try:
        await db_manager.connect()
        result = await db_manager.fetch_one('SELECT 1 as test')
        await db_manager.disconnect()
        print('OK')
    except Exception as e:
        print(f'ERROR: {e}')

asyncio.run(test())
" 2>/dev/null | grep -q "OK"; then
    check_passed "Connexion base de données OK"
else
    check_failed "Connexion base de données échouée"
fi

# Vérifier les migrations
if python -c "
import asyncio
import sys
sys.path.append('.')
from app.core.database import db_manager

async def test():
    try:
        await db_manager.connect()
        result = await db_manager.fetch_one('SELECT COUNT(*) FROM alembic_version')
        await db_manager.disconnect()
        print('OK')
    except Exception as e:
        print(f'ERROR: {e}')

asyncio.run(test())
" 2>/dev/null | grep -q "OK"; then
    check_passed "Migrations base de données appliquées"
else
    check_warning "Migrations potentiellement manquantes"
fi

# 5. Tests de Sécurité
echo ""
echo "5️⃣  Tests de Sécurité"
echo "-------------------"

# Exécuter les tests de sécurité automatisés
echo "Exécution de la suite de tests..."
if python tests/test_security_suite.py > "$REPORT_DIR/security_tests.txt" 2>&1; then
    check_passed "Tests de sécurité passés"
    
    # Compter les vulnérabilités
    CRITICAL=$(grep -c '"severity": "CRITICAL"' "$REPORT_DIR/security_tests.txt" 2>/dev/null || echo "0")
    HIGH=$(grep -c '"severity": "HIGH"' "$REPORT_DIR/security_tests.txt" 2>/dev/null || echo "0")
    
    if [[ "$CRITICAL" -eq 0 ]]; then
        check_passed "Aucune vulnérabilité critique"
    else
        check_failed "$CRITICAL vulnérabilité(s) critique(s)"
    fi
    
    if [[ "$HIGH" -le 5 ]]; then
        check_passed "$HIGH vulnérabilité(s) haute(s) maximum"
    else
        check_failed "$HIGH vulnérabilité(s) haute(s) détectée(s)"
    fi
else
    check_failed "Échec des tests de sécurité"
fi

# 6. Scan de Dépendances
echo ""
echo "6️⃣  Scan de Dépendances"
echo "----------------------"

if command -v safety &> /dev/null; then
    if safety check --json --output "$REPORT_DIR/safety.json" 2>/dev/null; then
        CRITICAL_DEPS=$(cat "$REPORT_DIR/safety.json" | jq '.vulnerabilities | map(select(.severity == "CRITICAL")) | length' 2>/dev/null || echo "0")
        
        if [[ "$CRITICAL_DEPS" -eq 0 ]]; then
            check_passed "Aucune dépendance critique vulnérable"
        else
            check_failed "$CRITICAL_DEPS dépendance(s) critique(s)"
        fi
    else
        check_warning "Scan Safety échoué"
    fi
else
    check_warning "Safety non installé"
fi

# 7. Monitoring et Logs
echo ""
echo "7️⃣  Monitoring et Logs"
echo "---------------------"

# Vérifier que les logs sont configurés
if [[ -d "logs" ]]; then
    if [[ -f "logs/security.log" ]]; then
        check_passed "Logs de sécurité configurés"
    else
        check_warning "Logs de sécurité non créés"
    fi
else
    check_warning "Répertoire de logs absent"
fi

# Vérifier Prometheus
if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    check_passed "Prometheus actif"
else
    check_warning "Prometheus non détecté"
fi

# 8. Performance et Charge
echo ""
echo "8️⃣  Performance"
echo "---------------"

# Test de charge basique
echo "Test de charge basique..."
SUCCESS_COUNT=0
for i in {1..10}; do
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        ((SUCCESS_COUNT++))
    fi
done

if [[ "$SUCCESS_COUNT" -eq 10 ]]; then
    check_passed "Test de charge basique OK (10/10)"
elif [[ "$SUCCESS_COUNT" -ge 8 ]]; then
    check_warning "Test de charge partiel ($SUCCESS_COUNT/10)"
else
    check_failed "Test de charge échoué ($SUCCESS_COUNT/10)"
fi

# 9. Documentation
echo ""
echo "9️⃣  Documentation"
echo "-----------------"

# Vérifier les documents critiques
DOCS=(
    "SECURITY_RESPONSE_PLAN.md"
    "docs/EXTERNAL_SECURITY_AUDIT_PREPARATION.md"
    "owasp_audit_report.json"
)

for doc in "${DOCS[@]}"; do
    if [[ -f "$doc" ]]; then
        check_passed "Document trouvé: $doc"
    else
        check_failed "Document manquant: $doc"
    fi
done

# 10. Backup et Recovery
echo ""
echo "🔟 Backup et Recovery"
echo "-------------------"

# Vérifier le script de backup
if [[ -f "scripts/backup.sh" ]] || [[ -f "scripts/backup_database.sh" ]]; then
    check_passed "Script de backup disponible"
else
    check_warning "Script de backup non trouvé"
fi

# Vérifier la dernière sauvegarde
if [[ -d "backups" ]]; then
    LATEST_BACKUP=$(ls -t backups/ 2>/dev/null | head -1)
    if [[ -n "$LATEST_BACKUP" ]]; then
        BACKUP_AGE=$(find "backups/$LATEST_BACKUP" -mtime -1 -print 2>/dev/null)
        if [[ -n "$BACKUP_AGE" ]]; then
            check_passed "Backup récent disponible"
        else
            check_warning "Backup datant de plus de 24h"
        fi
    else
        check_warning "Aucun backup trouvé"
    fi
else
    check_warning "Répertoire de backups absent"
fi

# Générer le rapport final
echo ""
echo "📊 RAPPORT DE VALIDATION"
echo "======================"

# Calculer le score
SCORE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

echo ""
echo "Résumé:"
echo "  ✅ Checks passés: $PASSED_CHECKS"
echo "  ❌ Checks échoués: $FAILED_CHECKS"
echo "  ⚠️  Avertissements: $WARNINGS"
echo "  📊 Score: $SCORE%"

# Évaluation
if [[ "$FAILED_CHECKS" -eq 0 && "$SCORE" -ge 95 ]]; then
    echo -e "\n${GREEN}🎉 PRÊT POUR L'AUDIT!${NC}"
    echo "   Score excellent: $SCORE%"
    STATUS="READY"
elif [[ "$FAILED_CHECKS" -le 2 && "$SCORE" -ge 90 ]]; then
    echo -e "\n${YELLOW}⚠️  PRÊT AVEC RÉSERVES${NC}"
    echo "   Score bon: $SCORE% (quelques ajustements mineurs)"
    STATUS="READY_WITH_RESERVES"
else
    echo -e "\n${RED}❌ NON PRÊT POUR L'AUDIT${NC}"
    echo "   Score insuffisant: $SCORE%"
    echo "   Veuillez corriger les échecs avant l'audit"
    STATUS="NOT_READY"
fi

# Générer le rapport JSON
cat > "$REPORT_DIR/validation_report.json" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "status": "$STATUS",
  "score": $SCORE,
  "summary": {
    "total_checks": $TOTAL_CHECKS,
    "passed": $PASSED_CHECKS,
    "failed": $FAILED_CHECKS,
    "warnings": $WARNINGS
  },
  "recommendations": [
EOF

# Ajouter les recommandations
if [[ "$FAILED_CHECKS" -gt 0 ]]; then
    echo "    \"Corriger les $FAILED_CHECKS échecs critiques avant l'audit\"," >> "$REPORT_DIR/validation_report.json"
fi

if [[ "$WARNINGS" -gt 0 ]]; then
    echo "    \"Revoir les $WARNERS avertissements pour améliorer le score\"," >> "$REPORT_DIR/validation_report.json"
fi

echo "    \"Continuer la surveillance jusqu'à l'audit\"" >> "$REPORT_DIR/validation_report.json"
echo "  ]" >> "$REPORT_DIR/validation_report.json"
echo "}" >> "$REPORT_DIR/validation_report.json"

# Afficher les actions recommandées
echo ""
echo "🎯 Actions Recommandées:"
if [[ "$FAILED_CHECKS" -gt 0 ]]; then
    echo "   1. Corriger immédiatement les échecs critiques"
fi
if [[ "$WARNINGS" -gt 0 ]]; then
    echo "   2. Examiner et résoudre les avertissements"
fi
echo "   3. Maintenir la surveillance active"
echo "   4. Préparer la documentation pour l'auditeur"

echo ""
echo "📁 Rapport détaillé: $REPORT_DIR/"
echo "   • validation_report.json"
echo "   • security_tests.txt"
echo "   • safety.json"

echo ""
if [[ "$STATUS" == "READY" ]]; then
    echo -e "${GREEN}✅ L'application est PRÊTE pour l'audit de sécurité externe!${NC}"
else
    echo -e "${RED}❌ L'application n'est PAS PRÊTE. Veuillez corriger les problèmes identifiés.${NC}"
fi

exit $([[ "$STATUS" == "READY" ]] && echo 0 || echo 1)
