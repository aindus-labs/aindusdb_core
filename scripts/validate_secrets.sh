#!/bin/bash
# 🔐 validate_secrets.sh - Validation des secrets de sécurité AindusDB Core
# Usage: ./validate_secrets.sh [env_file]

ENV_FILE=${1:-".env"}

echo "🔍 Validation des secrets de sécurité - AindusDB Core"
echo "Fichier analysé : $ENV_FILE"
echo "========================================"

# Vérifier que le fichier existe
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Erreur : Fichier $ENV_FILE introuvable"
    exit 1
fi

# Compteur d'erreurs
ERRORS=0

# Fonction de validation
validate_secret() {
    local secret_name=$1
    local secret_value=$2
    local min_length=$3
    local default_pattern=$4
    
    # Vérifier que ce n'est pas une valeur par défaut
    if [[ "$secret_value" =~ $default_pattern ]]; then
        echo "❌ $secret_name : Valeur par défaut détectée!"
        ((ERRORS++))
        return 1
    fi
    
    # Vérifier la longueur minimale
    if [ ${#secret_value} -lt $min_length ]; then
        echo "❌ $secret_name : Trop court (${#secret_value} < $min_length)"
        ((ERRORS++))
        return 1
    fi
    
    # Vérifier l'entropie minimale (caractères variés)
    if [[ "$secret_value" =~ ^[a-zA-Z0-9]+$ ]]; then
        echo "⚠️  $secret_name : Faible entropie (que des alphanumériques)"
        ((ERRORS++))
        return 1
    fi
    
    echo "✅ $secret_name : Valide"
    return 0
}

# Extraire et valider les secrets
echo ""
echo "🔑 Validation des secrets..."

JWT_SECRET=$(grep "^JWT_SECRET_KEY=" "$ENV_FILE" | cut -d'=' -f2)
validate_secret "JWT_SECRET_KEY" "$JWT_SECRET" 64 "your_super_secret|CHANGE_|YOUR_"

DB_PASSWORD=$(grep "^POSTGRES_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)
validate_secret "POSTGRES_PASSWORD" "$DB_PASSWORD" 24 "change_me|CHANGE_|password123"

REDIS_PASSWORD=$(grep "^REDIS_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)
if [ ! -z "$REDIS_PASSWORD" ]; then
    validate_secret "REDIS_PASSWORD" "$REDIS_PASSWORD" 16 "change_|CHANGE_"
fi

# Vérifications supplémentaires
echo ""
echo "🔍 Vérifications supplémentaires..."

# Vérifier les droits du fichier
FILE_PERMS=$(stat -c "%a" "$ENV_FILE")
if [ "$FILE_PERMS" != "600" ]; then
    echo "⚠️  Droits du fichier : $FILE_PERMS (recommandé : 600)"
    echo "   Correction : chmod 600 $ENV_FILE"
fi

# Vérifier qu'il n'y a pas de secrets hardcodés dans le code Python
echo ""
echo "🔍 Recherche de secrets hardcodés..."
if grep -r "your_super_secret\|password123\|change_me" app/ --include="*.py" >/dev/null 2>&1; then
    echo "❌ Secrets hardcodés détectés dans le code Python!"
    grep -rn "your_super_secret\|password123\|change_me" app/ --include="*.py"
    ((ERRORS++))
else
    echo "✅ Aucun secret hardcodé détecté"
fi

# Vérifier la présence de .env.secrets
if [ -f ".env.secrets" ]; then
    echo "✅ Fichier .env.secrets présent (template de production)"
else
    echo "⚠️  Fichier .env.secrets manquant"
fi

# Résumé
echo ""
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    echo "🎉 Validation réussie : Aucune erreur détectée!"
    echo "✅ Configuration sécurisée prête pour le déploiement"
    exit 0
else
    echo "❌ Validation échouée : $ERRORS erreur(s) détectée(s)"
    echo "🔧 Corrigez les problèmes avant de déployer en production"
    exit 1
fi
