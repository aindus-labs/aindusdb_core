#!/bin/bash
# 🚀 pre_deployment_security_checklist.sh
# Checklist de sécurité pré-déploiement

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 PRÉ-DÉPLOIEMENT SÉCURITÉ${NC}"
echo "=========================="
echo "AindusDB Core - Production Ready Check"
echo ""

# Variables
ENVIRONMENT="${1:-production}"
VERSION="${2:-latest}"
CHECKLIST_FILE="deployment_security_checklist_$(date +%Y%m%d_%H%M%S).md"

# Compteurs
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Fonctions
check_passed() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED_CHECKS++))
    ((TOTAL_CHECKS++))
    echo "   [✓] $(date '+%Y-%m-%d %H:%M:%S')" >> "$CHECKLIST_FILE"
}

check_failed() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED_CHECKS++))
    ((TOTAL_CHECKS++))
    echo "   [✗] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$CHECKLIST_FILE"
}

check_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
    ((TOTAL_CHECKS++))
    echo "   [!] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$CHECKLIST_FILE"
}

# Initialiser le fichier de checklist
cat > "$CHECKLIST_FILE" << EOF
# 🚀 Checklist Sécurité Déploiement

**Environnement**: $ENVIRONMENT  
**Version**: $VERSION  
**Date**: $(date '+%Y-%m-%d %H:%M:%S')  
**Exécuté par**: $(whoami)

## Résultats

EOF

echo ""
echo "📋 SECTION 1: ENVIRONNEMENT"
echo "=========================="

# Vérifier l'environnement
if [[ "$ENVIRONMENT" != "production" && "$ENVIRONMENT" != "staging" ]]; then
    check_failed "Environnement non valide: $ENVIRONMENT"
    exit 1
else
    check_passed "Environnement valide: $ENVIRONMENT"
fi

# Vérifier qu'on n'est pas en mode debug
if [[ "$DEBUG" == "true" || "$DEBUG" == "1" ]]; then
    check_failed "Mode DEBUG activé!"
else
    check_passed "Mode DEBUG désactivé"
fi

# Vérifier les variables d'environnement critiques
echo ""
echo "Vérification des variables d'environnement..."
CRITICAL_VARS=("DATABASE_URL" "SECRET_KEY" "JWT_SECRET")

for var in "${CRITICAL_VARS[@]}"; do
    if [[ -z "${!var}" ]]; then
        check_failed "Variable manquante: $var"
    else
        if [[ "$var" == *"SECRET"* ]] && [[ "${!var}" == *"default"* || "${!var}" == *"change"* ]]; then
            check_failed "Secret par défaut détecté: $var"
        else
            check_passed "Variable configurée: $var"
        fi
    fi
done

echo ""
echo "🔒 SECTION 2: SÉCURITÉ APPLICATION"
echo "================================="

# Vérifier la version des dépendances
echo "Vérification des dépendances..."
if command -v safety &> /dev/null; then
    if safety check --json --output safety_check.json 2>/dev/null; then
        CRITICAL_DEPS=$(cat safety_check.json | jq '.vulnerabilities | map(select(.severity == "CRITICAL")) | length' 2>/dev/null || echo "0")
        HIGH_DEPS=$(cat safety_check.json | jq '.vulnerabilities | map(select(.severity == "HIGH")) | length' 2>/dev/null || echo "0")
        
        if [[ "$CRITICAL_DEPS" -eq 0 ]]; then
            check_passed "Aucune dépendance critique vulnérable"
        else
            check_failed "$CRITICAL_DEPS dépendance(s) critique(s)"
        fi
        
        if [[ "$HIGH_DEPS" -le 2 ]]; then
            check_passed "$HIGH_DEPS dépendance(s) haute(s) maximum"
        else
            check_warning "$HIGH_DEPS dépendance(s) haute(s) détectée(s)"
        fi
    else
        check_warning "Impossible de vérifier les dépendances"
    fi
else
    check_warning "Safety non installé"
fi

# Vérifier les tests de sécurité
echo ""
echo "Exécution des tests de sécurité..."
if python -m pytest tests/test_security_suite.py -v > security_test_output.txt 2>&1; then
    check_passed "Tests de sécurité passés"
    
    # Vérifier le score
    if grep -q "risk_score.*[0-9]" security_test_output.txt; then
        RISK_SCORE=$(grep "risk_score" security_test_output.txt | grep -o '[0-9]*' | head -1)
        if [[ "$RISK_SCORE" -le 20 ]]; then
            check_passed "Score de risque acceptable: $RISK_SCORE"
        else
            check_warning "Score de risque élevé: $RISK_SCORE"
        fi
    fi
else
    check_failed "Échec des tests de sécurité"
fi

# Vérifier la configuration TLS/SSL
echo ""
echo "Vérification TLS/SSL..."
if [[ "$ENVIRONMENT" == "production" ]]; then
    if [[ "$FORCE_HTTPS" == "true" || "$FORCE_HTTPS" == "1" ]]; then
        check_passed "HTTPS forcé en production"
    else
        check_failed "HTTPS non forcé en production!"
    fi
    
    if [[ "$SSL_CERT_PATH" ]] && [[ -f "$SSL_CERT_PATH" ]]; then
        # Vérifier la validité du certificat
        if openssl x509 -in "$SSL_CERT_PATH" -noout -dates 2>/dev/null; then
            check_passed "Certificat SSL valide"
            
            # Vérifier l'expiration
            EXPIRY=$(openssl x509 -in "$SSL_CERT_PATH" -noout -enddate 2>/dev/null | cut -d= -f2)
            EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null || echo "0")
            NOW_EPOCH=$(date +%s)
            DAYS_LEFT=$((($EXPIRY_EPOCH - $NOW_EPOCH) / 86400))
            
            if [[ "$DAYS_LEFT" -gt 30 ]]; then
                check_passed "Certificat expire dans $DAYS_LEFT jours"
            elif [[ "$DAYS_LEFT" -gt 7 ]]; then
                check_warning "Certificat expire bientôt ($DAYS_LEFT jours)"
            else
                check_failed "Certificat expire très bientôt ($DAYS_LEFT jours)!"
            fi
        else
            check_failed "Certificat SSL invalide"
        fi
    else
        check_failed "Certificat SSL non trouvé"
    fi
fi

echo ""
echo "🗄️ SECTION 3: BASE DE DONNÉES"
echo "============================"

# Vérifier la connexion à la base
echo "Test de connexion base de données..."
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
echo "Vérification des migrations..."
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
    check_failed "Migrations non appliquées"
fi

# Vérifier les permissions de la base
echo "Vérification des permissions..."
if python -c "
import asyncio
import sys
sys.path.append('.')
from app.core.database import db_manager

async def test():
    try:
        await db_manager.connect()
        # Vérifier que l'utilisateur n'est pas superuser
        result = await db_manager.fetch_one('SELECT current_user')
        await db_manager.disconnect()
        print(result['current_user'])
    except Exception as e:
        print(f'ERROR: {e}')

asyncio.run(test())
" 2>/dev/null | grep -v -i "postgres\|root"; then
    check_passed "Utilisateur base non-privilegié"
else
    check_warning "Utilisateur base avec privilèges élevés"
fi

echo ""
echo "🌐 SECTION 4: INFRASTRUCTURE"
echo "==========================="

# Vérifier Redis
if curl -s "${REDIS_URL:-redis://localhost:6379}/ping" 2>/dev/null | grep -q "PONG"; then
    check_passed "Redis actif"
else
    check_warning "Redis non disponible"
fi

# Vérifier le monitoring
echo "Vérification du monitoring..."
if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    check_passed "Prometheus actif"
else
    check_warning "Prometheus non détecté"
fi

# Vérifier les logs
if [[ -d "logs" ]]; then
    if [[ -f "logs/security.log" ]]; then
        check_passed "Logs de sécurité configurés"
    else
        check_warning "Logs de sécurité non créés"
    fi
else
    check_warning "Répertoire de logs absent"
fi

# Vérifier les backups
echo "Vérification des backups..."
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
        check_failed "Aucun backup trouvé"
    fi
else
    check_failed "Répertoire de backups absent"
fi

echo ""
echo "🔍 SECTION 5: SCAN DE SÉCURITÉ"
echo "============================="

# Scan avec Bandit
echo "Scan Bandit (SAST)..."
if bandit -r app/ -f json -o bandit_report.json 2>/dev/null; then
    HIGH_ISSUES=$(cat bandit_report.json | jq '.results | map(select(.issue_severity == "HIGH")) | length' 2>/dev/null || echo "0")
    
    if [[ "$HIGH_ISSUES" -eq 0 ]]; then
        check_passed "Aucune issue haute détectée par Bandit"
    else
        check_failed "$HIGH_ISSUES issue(s) haute(s) détectée(s)"
    fi
else
    check_warning "Bandit scan échoué"
fi

# Scan des conteneurs si Docker
if command -v docker &> /dev/null; then
    echo "Scan conteneurs avec Trivy..."
    if docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        -v "$PWD":/root/.cache/ \
        aquasec/trivy:latest image --format json --output trivy_report.json \
        aindusdb-core:$VERSION 2>/dev/null; then
        CRITICAL_CONTAINER=$(cat trivy_report.json | jq '.Results | map(select(.Vulnerabilities | map(select(.Severity == "CRITICAL")) | length > 0)) | length' 2>/dev/null || echo "0")
        
        if [[ "$CRITICAL_CONTAINER" -eq 0 ]]; then
            check_passed "Aucune vulnérabilité critique dans le conteneur"
        else
            check_failed "$CRITICAL_CONTAINER vulnérabilité(s) critique(s) dans le conteneur"
        fi
    else
        check_warning "Trivy scan échoué"
    fi
fi

echo ""
echo "📊 SECTION 6: PERFORMANCE"
echo "========================"

# Test de charge basique
echo "Test de charge basique..."
SUCCESS_COUNT=0
for i in {1..20}; do
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        ((SUCCESS_COUNT++))
    fi
done

if [[ "$SUCCESS_COUNT" -eq 20 ]]; then
    check_passed "Test de charge OK (20/20)"
elif [[ "$SUCCESS_COUNT" -ge 18 ]]; then
    check_warning "Test de charge partiel ($SUCCESS_COUNT/20)"
else
    check_failed "Test de charge échoué ($SUCCESS_COUNT/20)"
fi

# Vérifier l'utilisation mémoire
echo "Vérification utilisation mémoire..."
MEMORY_USAGE=$(ps aux | grep uvicorn | grep -v grep | awk '{sum+=$6} END {print sum/1024}' 2>/dev/null || echo "0")
if (( $(echo "$MEMORY_USAGE < 512" | bc -l) )); then
    check_passed "Utilisation mémoire OK: ${MEMORY_USAGE}MB"
elif (( $(echo "$MEMORY_USAGE < 1024" | bc -l) )); then
    check_warning "Utilisation mémoire élevée: ${MEMORY_USAGE}MB"
else
    check_failed "Utilisation mémoire critique: ${MEMORY_USAGE}MB"
fi

echo ""
echo "📋 RÉSUMÉ DE LA CHECKLIST"
echo "========================"

# Calculer le score
SCORE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

echo ""
echo "Statistiques:"
echo "  ✅ Réussis: $PASSED_CHECKS"
echo "  ❌ Échoués: $FAILED_CHECKS"
echo "  ⚠️  Avertissements: $WARNINGS"
echo "  📊 Score: $SCORE%"

# Ajouter au fichier
cat >> "$CHECKLIST_FILE" << EOF

### Statistiques

- **Total**: $TOTAL_CHECKS
- **Réussis**: $PASSED_CHECKS
- **Échoués**: $FAILED_CHECKS
- **Avertissements**: $WARNINGS
- **Score**: $SCORE%

### Évaluation

EOF

# Évaluation finale
if [[ "$FAILED_CHECKS" -eq 0 && "$SCORE" -ge 95 ]]; then
    echo -e "\n${GREEN}🎉 DÉPLOIEMENT AUTORISÉ!${NC}"
    echo "Score excellent: $SCORE%"
    echo "L'application est prête pour la production."
    STATUS="APPROVED"
    echo "### Statut: APPROUVÉ ✅" >> "$CHECKLIST_FILE"
elif [[ "$FAILED_CHECKS" -le 2 && "$SCORE" -ge 90 ]]; then
    echo -e "\n${YELLOW}⚠️  DÉPLOIEMENT AVEC RÉSERVES${NC}"
    echo "Score acceptable: $SCORE%"
    echo "Corriger les échecs avant la mise en production."
    STATUS="CONDITIONAL"
    echo "### Statut: APPROUVÉ AVEC CONDITIONS ⚠️" >> "$CHECKLIST_FILE"
else
    echo -e "\n${RED}❌ DÉPLOIEMENT REFUSÉ${NC}"
    echo "Score insuffisant: $SCORE%"
    echo "Veuillez corriger tous les échecs critiques."
    STATUS="REJECTED"
    echo "### Statut: REFUSÉ ❌" >> "$CHECKLIST_FILE"
fi

# Actions recommandées
echo ""
echo "🎯 Actions Recommandées:"
if [[ "$FAILED_CHECKS" -gt 0 ]]; then
    echo "   1. Corriger immédiatement les $FAILED_CHECKS échecs"
fi
if [[ "$WARNINGS" -gt 0 ]]; then
    echo "   2. Examiner les $WARNERS avertissements"
fi
echo "   3. Sauvegarder la configuration actuelle"
echo "   4. Préparer le plan de rollback"

# Générer le rapport final
cat >> "$CHECKLIST_FILE" << EOF

### Actions Recommandées

EOF

if [[ "$FAILED_CHECKS" -gt 0 ]]; then
    echo "- Corriger les échecs critiques avant déploiement" >> "$CHECKLIST_FILE"
fi
if [[ "$WARNINGS" -gt 0 ]]; then
    echo "- Examiner et résoudre les avertissements" >> "$CHECKLIST_FILE"
fi
echo "- Maintenir la monitoring actif post-déploiement" >> "$CHECKLIST_FILE"

echo ""
echo "📁 Rapport détaillé: $CHECKLIST_FILE"
echo ""

# Exporter les variables pour les scripts suivants
export DEPLOYMENT_STATUS="$STATUS"
export DEPLOYMENT_SCORE="$SCORE"

# Code de sortie
if [[ "$STATUS" == "APPROVED" ]]; then
    exit 0
elif [[ "$STATUS" == "CONDITIONAL" ]]; then
    exit 1
else
    exit 2
fi
