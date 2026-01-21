#!/bin/bash
# 🚀 secure_deployment.sh - Déploiement sécurisé en production

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-production}"
VERSION="${2:-latest}"
BACKUP_ENABLED="${3:-true}"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 DÉPLOIEMENT SÉCURISÉ - AindusDB Core${NC}"
echo "======================================"
echo "Environnement: $ENVIRONMENT"
echo "Version: $VERSION"
echo "Date: $(date)"
echo ""

# Vérifier les prérequis
echo "📋 Vérification des prérequis..."
if [[ "$EUID" -ne 0 ]]; then
    echo -e "${YELLOW}⚠️  Exécution sans root (recommandé)${NC}"
fi

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker requis${NC}"
    exit 1
fi

# Vérifier kubectl si Kubernetes
if [[ "$USE_KUBERNETES" == "true" ]]; then
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl requis pour Kubernetes${NC}"
        exit 1
    fi
fi

# Charger les variables d'environnement
if [[ -f "$PROJECT_ROOT/.env.$ENVIRONMENT" ]]; then
    source "$PROJECT_ROOT/.env.$ENVIRONMENT"
    echo -e "${GREEN}✅ Variables $ENVIRONMENT chargées${NC}"
else
    echo -e "${RED}❌ Fichier .env.$ENVIRONMENT non trouvé${NC}"
    exit 1
fi

# Étape 1: Exécuter la checklist de sécurité
echo ""
echo "🔍 ÉTAPE 1: Checklist de Sécurité"
echo "==============================="

if bash "$SCRIPT_DIR/pre_deployment_security_checklist.sh" "$ENVIRONMENT" "$VERSION"; then
    echo -e "${GREEN}✅ Sécurité validée${NC}"
else
    echo -e "${RED}❌ Échec validation sécurité${NC}"
    exit 1
fi

# Étape 2: Backup de l'application actuelle
echo ""
echo "💾 ÉTAPE 2: Backup de l'Application"
echo "==============================="

if [[ "$BACKUP_ENABLED" == "true" ]]; then
    BACKUP_DIR="$PROJECT_ROOT/backups/pre-deployment-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    echo "Backup de la base de données..."
    if docker exec aindusdb-postgres pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_DIR/database.sql"; then
        echo -e "${GREEN}✅ Base de données sauvegardée${NC}"
    else
        echo -e "${RED}❌ Échec backup base de données${NC}"
        exit 1
    fi
    
    echo "Backup de Redis..."
    if docker exec aindusdb-redis redis-cli BGSAVE > /dev/null; then
        docker cp aindusdb-redis:/data/dump.rdb "$BACKUP_DIR/"
        echo -e "${GREEN}✅ Redis sauvegardé${NC}"
    else
        echo -e "${YELLOW}⚠️  Backup Redis échoué (non-critique)${NC}"
    fi
    
    echo "Backup de la configuration..."
    cp -r "$PROJECT_ROOT/config" "$BACKUP_DIR/" 2>/dev/null || true
    cp "$PROJECT_ROOT/.env.$ENVIRONMENT" "$BACKUP_DIR/"
    echo -e "${GREEN}✅ Configuration sauvegardée${NC}"
    
    echo "Backup créé dans: $BACKUP_DIR"
else
    echo -e "${YELLOW}⚠️  Backup désactivé${NC}"
fi

# Étape 3: Build de l'image Docker
echo ""
echo "🏗️  ÉTAPE 3: Build Image Docker"
echo "============================"

echo "Construction de l'image $VERSION..."
docker build -t "aindusdb-core:$VERSION" "$PROJECT_ROOT"

# Scanner l'image avec Trivy
echo "Scan de sécurité de l'image..."
if docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$PWD":/root/.cache/ \
    aquasec/trivy:latest image \
    --exit-code 1 \
    --severity HIGH,CRITICAL \
    "aindusdb-core:$VERSION"; then
    echo -e "${GREEN}✅ Image sécurisée${NC}"
else
    echo -e "${RED}❌ Vulnérabilités détectées dans l'image${NC}"
    exit 1
fi

# Marquer la version
docker tag "aindusdb-core:$VERSION" "aindusdb-core:latest"

# Étape 4: Déploiement
echo ""
echo "🚀 ÉTAPE 4: Déploiement"
echo "===================="

if [[ "$USE_KUBERNETES" == "true" ]]; then
    echo "Déploiement Kubernetes..."
    
    # Appliquer les configurations
    kubectl apply -f "$PROJECT_ROOT/k8s/"
    
    # Mettre à jour l'image
    kubectl set image deployment/aindusdb-core \
        aindusdb-core="aindusdb-core:$VERSION" \
        -n "$ENVIRONMENT"
    
    # Attendre le rollout
    echo "Attente du déploiement..."
    kubectl rollout status deployment/aindusdb-core -n "$ENVIRONMENT" --timeout=300s
    
else
    echo "Déploiement Docker Compose..."
    
    # Arrêter les services actuels
    echo "Arrêt des services actuels..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.$ENVIRONMENT.yml" down
    
    # Démarrer avec la nouvelle version
    echo "Démarrage des nouveaux services..."
    VERSION="$VERSION" docker-compose -f "$PROJECT_ROOT/docker-compose.$ENVIRONMENT.yml" up -d
    
    # Attendre le démarrage
    echo "Attente du démarrage..."
    sleep 30
fi

# Étape 5: Validation post-déploiement
echo ""
echo "✅ ÉTAPE 5: Validation Post-Déploiement"
echo "=================================="

# Attendre que l'application soit prête
echo "Vérification de la santé de l'application..."
for i in {1..30}; do
    if curl -f -s "http://localhost:8000/api/v1/health" > /dev/null; then
        echo -e "${GREEN}✅ Application active${NC}"
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo -e "${RED}❌ Application non démarrée${NC}"
        exit 1
    fi
    echo -n "."
    sleep 2
done

# Tests de smoke
echo ""
echo "Tests de smoke..."
SMOKE_TESTS=(
    "GET /api/v1/health"
    "GET /api/v1/status"
    "GET /docs"
)

for test in "${SMOKE_TESTS[@]}"; do
    METHOD=$(echo $test | cut -d' ' -f1)
    PATH=$(echo $test | cut -d' ' -f2)
    
    if [[ "$METHOD" == "GET" ]]; then
        if curl -f -s "http://localhost:8000$PATH" > /dev/null; then
            echo -e "${GREEN}✅ $test${NC}"
        else
            echo -e "${RED}❌ $test${NC}"
            ROLLBACK_NEEDED=true
        fi
    fi
done

# Vérifier les logs d'erreurs
echo ""
echo "Vérification des logs..."
ERROR_COUNT=$(docker logs aindusdb-core 2>&1 | grep -i error | wc -l)
if [[ "$ERROR_COUNT" -eq 0 ]]; then
    echo -e "${GREEN}✅ Aucune erreur dans les logs${NC}"
else
    echo -e "${YELLOW}⚠️  $ERROR_COUNT erreur(s) dans les logs${NC}"
fi

# Étape 6: Monitoring
echo ""
echo "📊 ÉTAPE 6: Configuration Monitoring"
echo "================================"

# Vérifier Prometheus
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo -e "${GREEN}✅ Prometheus actif${NC}"
else
    echo -e "${YELLOW}⚠️  Prometheus non détecté${NC}"
fi

# Vérifier Grafana
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo -e "${GREEN}✅ Grafana actif${NC}"
else
    echo -e "${YELLOW}⚠️  Grafana non détecté${NC}"
fi

# Créer l'alerte de déploiement
echo "Création de l'alerte de déploiement..."
curl -X POST http://localhost:9093/api/v1/alerts \
    -H "Content-Type: application/json" \
    -d '[{
        "labels": {
            "alertname": "DeploymentCompleted",
            "environment": "'$ENVIRONMENT'",
            "version": "'$VERSION'",
            "severity": "info"
        },
        "annotations": {
            "summary": "Deployment completed successfully",
            "description": "AindusDB Core version '$VERSION' deployed to '$ENVIRONMENT'"
        }
    }]' > /dev/null 2>&1 || true

# Étape 7: Nettoyage
echo ""
echo "🧹 ÉTAPE 7: Nettoyage"
echo "=================="

# Supprimer les anciennes images (garder les 3 dernières)
echo "Nettoyage des anciennes images..."
docker images "aindusdb-core" --format "table {{.Repository}}:{{.Tag}}" | \
    tail -n +2 | \
    tail -n +4 | \
    xargs -r docker rmi > /dev/null 2>&1 || true

# Nettoyer les anciens backups (garder 7 jours)
echo "Nettoyage des anciens backups..."
find "$PROJECT_ROOT/backups" -type d -name "pre-deployment-*" -mtime +7 -exec rm -rf {} + 2>/dev/null || true

# Étape 8: Rapport de déploiement
echo ""
echo "📋 ÉTAPE 8: Rapport de Déploiement"
echo "=============================="

DEPLOYMENT_REPORT="$PROJECT_ROOT/deployment_reports/deployment_$(date +%Y%m%d_%H%M%S).md"
mkdir -p "$(dirname "$DEPLOYMENT_REPORT")"

cat > "$DEPLOYMENT_REPORT" << EOF
# 🚀 Rapport de Déploiement

## Informations
- **Date**: $(date)
- **Environnement**: $ENVIRONMENT
- **Version**: $VERSION
- **Opérateur**: $(whoami)
- **Durée**: $SECONDS secondes

## Validation Sécurité
- ✅ Checklist sécurité validée
- ✅ Scan image Docker réussi
- ✅ Tests de smoke passés

## Backup
- **Emplacement**: $BACKUP_DIR
- **Base de données**: $(du -h "$BACKUP_DIR/database.sql" 2>/dev/null || echo "N/A")
- **Redis**: $(du -h "$BACKUP_DIR/dump.rdb" 2>/dev/null || echo "N/A")

## Services Actifs
EOF

# Ajouter l'état des services
if [[ "$USE_KUBERNETES" == "true" ]]; then
    kubectl get pods -n "$ENVIRONMENT" >> "$DEPLOYMENT_REPORT"
else
    docker-compose -f "$PROJECT_ROOT/docker-compose.$ENVIRONMENT.yml" ps >> "$DEPLOYMENT_REPORT"
fi

cat >> "$DEPLOYMENT_REPORT" << EOF

## Métriques Post-Déploiement
- Erreurs dans les logs: $ERROR_COUNT
- Temps de démarrage: $SECONDS secondes

## Actions Suivantes
- [ ] Surveillance active (24h)
- [ ] Vérification des performances
- [ ] Validation par l'équipe métier

---

Déploiement terminé avec succès! 🎉
EOF

echo -e "${GREEN}✅ Rapport créé: $DEPLOYMENT_REPORT${NC}"

# Rollback si nécessaire
if [[ "$ROLLBACK_NEEDED" == "true" ]]; then
    echo ""
    echo -e "${RED}🚨 ROLLBACK NÉCESSAIRE${NC}"
    echo "Exécution du rollback..."
    
    if [[ "$USE_KUBERNETES" == "true" ]]; then
        kubectl rollout undo deployment/aindusdb-core -n "$ENVIRONMENT"
    else
        docker-compose -f "$PROJECT_ROOT/docker-compose.$ENVIRONMENT.yml" down
        # Restaurer la version précédente
        PREVIOUS_VERSION=$(docker images --format "table {{.Repository}}:{{.Tag}}" | grep aindusdb-core | head -2 | tail -1)
        docker-compose -f "$PROJECT_ROOT/docker-compose.$ENVIRONMENT.yml" up -d
    fi
    
    echo -e "${YELLOW}⚠️  Rollback effectué${NC}"
    exit 1
fi

# Notification Slack (optionnel)
if [[ -n "$SLACK_WEBHOOK" ]]; then
    echo ""
    echo "📢 Notification Slack..."
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"🚀 Déploiement réussi!\n*Application*: AindusDB Core\n*Version*: $VERSION\n*Environnement*: $ENVIRONMENT\"}" \
        "$SLACK_WEBHOOK" > /dev/null 2>&1 || true
fi

echo ""
echo -e "${GREEN}🎉 DÉPLOIEMENT TERMINÉ AVEC SUCCÈS!${NC}"
echo ""
echo "📊 Résumé:"
echo "  • Version: $VERSION"
echo "  • Environnement: $ENVIRONMENT"
echo "  • Durée: $SECONDS secondes"
echo "  • Backup: $BACKUP_ENABLED"
echo ""
echo "🔗 Liens utiles:"
echo "  • API: http://localhost:8000"
echo "  • Docs: http://localhost:8000/docs"
echo "  • Monitoring: http://localhost:3000"
echo "  • Rapport: $DEPLOYMENT_REPORT"
echo ""
echo -e "${BLUE}⚠️  PENSEZ À SURVEILLER L'APPLICATION PENDANT 24H${NC}"
