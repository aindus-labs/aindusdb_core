#!/bin/bash
# 🔒 validate_security_config.sh - Validation configuration sécurité
# Usage: ./validate_security_config.sh [env_file]

ENV_FILE=${1:-".env"}

echo "🔒 Validation Configuration Sécurité - AindusDB Core"
echo "Fichier analysé : $ENV_FILE"
echo "=========================================="

# Vérifier que le fichier existe
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Erreur : Fichier $ENV_FILE introuvable"
    exit 1
fi

# Charger les variables
set -a
source $ENV_FILE
set +a

# Compteur d'erreurs et avertissements
ERRORS=0
WARNINGS=0

# Fonctions de validation
validate_cors() {
    echo ""
    echo "🌐 Validation CORS..."
    
    if [ -z "$CORS_ORIGINS" ]; then
        echo "⚠️  Avertissement : CORS_ORIGINS non défini"
        ((WARNINGS++))
        return
    fi
    
    # Vérifier les wildcards en production
    if [ "$ENVIRONMENT" = "production" ]; then
        if [[ "$CORS_ORIGINS" == *"*"* ]]; then
            echo "❌ Erreur : Wildcard (*) dans CORS_ORIGINS en production"
            ((ERRORS++))
        fi
    fi
    
    # Vérifier que les origines commencent par http/https
    IFS=',' read -ra ORIGINS <<< "$CORS_ORIGINS"
    for origin in "${ORIGINS[@]}"; do
        origin=$(echo $origin | xargs)  # trim
        if [[ ! "$origin" =~ ^https?:// ]]; then
            echo "❌ Erreur : Origin '$origin' ne commence pas par http:// ou https://"
            ((ERRORS++))
        fi
    done
    
    echo "✅ CORS validé"
}

validate_ssl() {
    echo ""
    echo "🔐 Validation SSL/TLS..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        if [ "$SSL_ENABLED" != "true" ]; then
            echo "❌ Erreur : SSL doit être activé en production"
            ((ERRORS++))
        fi
        
        if [ "$FORCE_HTTPS" != "true" ]; then
            echo "❌ Erreur : FORCE_HTTPS doit être true en production"
            ((ERRORS++))
        fi
    fi
    
    # Vérifier la version TLS
    if [ "$TLS_VERSION" != "TLSv1.3" ] && [ "$TLS_VERSION" != "TLSv1.2" ]; then
        echo "❌ Erreur : Version TLS '$TLS_VERSION' non supportée"
        ((ERRORS++))
    fi
    
    echo "✅ SSL/TLS validé"
}

validate_headers() {
    echo ""
    echo "📋 Validation Headers Sécurité..."
    
    if [ "$SECURITY_HEADERS_ENABLED" != "true" ]; then
        echo "⚠️  Avertissement : Headers sécurité désactivés"
        ((WARNINGS++))
        return
    fi
    
    # Vérifier CSP en production
    if [ "$ENVIRONMENT" = "production" ]; then
        if [[ "$CONTENT_SECURITY_POLICY" == *"unsafe-inline"* ]]; then
            echo "❌ Erreur : 'unsafe-inline' dans CSP en production"
            ((ERRORS++))
        fi
        
        if [[ "$CONTENT_SECURITY_POLICY" == *"unsafe-eval"* ]]; then
            echo "❌ Erreur : 'unsafe-eval' dans CSP en production"
            ((ERRORS++))
        fi
    fi
    
    echo "✅ Headers sécurité validés"
}

validate_jwt() {
    echo ""
    echo "🎫 Validation JWT..."
    
    # Vérifier l'algorithme
    if [ "$JWT_ALGORITHM" != "HS256" ] && [ "$JWT_ALGORITHM" != "RS256" ]; then
        echo "❌ Erreur : Algorithme JWT '$JWT_ALGORITHM' non recommandé"
        ((ERRORS++))
    fi
    
    # Vérifier la durée des tokens
    if [ "$JWT_ACCESS_TOKEN_EXPIRE_MINUTES" -gt 60 ]; then
        echo "⚠️  Avertissement : Tokens d'accès de plus de 60 minutes"
        ((WARNINGS++))
    fi
    
    if [ "$JWT_REFRESH_TOKEN_EXPIRE_DAYS" -gt 30 ]; then
        echo "⚠️  Avertissement : Tokens de refresh de plus de 30 jours"
        ((WARNINGS++))
    fi
    
    echo "✅ JWT validé"
}

validate_rate_limiting() {
    echo ""
    echo "⏱️  Validation Rate Limiting..."
    
    if [ "$RATE_LIMIT_ENABLED" != "true" ]; then
        echo "❌ Erreur : Rate limiting doit être activé"
        ((ERRORS++))
        return
    fi
    
    # Vérifier le stockage
    if [ "$RATE_LIMIT_STORAGE" != "redis" ] && [ "$RATE_LIMIT_STORAGE" != "memory" ]; then
        echo "❌ Erreur : Stockage rate limiting '$RATE_LIMIT_STORAGE' invalide"
        ((ERRORS++))
    fi
    
    # Vérifier les limites
    if [ "$RATE_LIMIT_REQUESTS_PER_MINUTE" -gt 1000 ]; then
        echo "⚠️  Avertissement : Rate limit très élevé (>1000/min)"
        ((WARNINGS++))
    fi
    
    echo "✅ Rate limiting validé"
}

validate_secrets() {
    echo ""
    echo "🔑 Validation Secrets..."
    
    # Vérifier les mots de passe par défaut
    if [ "$POSTGRES_PASSWORD" = "aindusdb_secure_2026_change_me" ]; then
        echo "❌ Erreur : Mot de passe PostgreSQL par défaut"
        ((ERRORS++))
    fi
    
    if [ "$JWT_SECRET_KEY" = "your_super_secret_jwt_key_256_bits_minimum_change_in_production" ]; then
        echo "❌ Erreur : Clé JWT par défaut"
        ((ERRORS++))
    fi
    
    # Vérifier la longueur des secrets
    if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
        echo "❌ Erreur : Clé JWT trop courte (<32 caractères)"
        ((ERRORS++))
    fi
    
    echo "✅ Secrets validés"
}

validate_audit() {
    echo ""
    echo "📊 Validation Audit..."
    
    if [ "$AUDIT_ENABLED" != "true" ]; then
        echo "⚠️  Avertissement : Audit désactivé"
        ((WARNINGS++))
    fi
    
    if [ "$AUDIT_RETENTION_DAYS" -gt 365 ]; then
        echo "⚠️  Avertissement : Rétention audit > 1 an"
        ((WARNINGS++))
    fi
    
    echo "✅ Audit validé"
}

# Exécuter les validations
validate_cors
validate_ssl
validate_headers
validate_jwt
validate_rate_limiting
validate_secrets
validate_audit

# Résumé
echo ""
echo "=========================================="
echo "📊 RÉSUMÉ DE LA VALIDATION"
echo "=========================================="
echo "Erreurs : $ERRORS"
echo "Avertissements : $WARNINGS"

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "❌ VALIDATION ÉCHOUÉE - Corrigez les erreurs avant de déployer"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo ""
    echo "⚠️  VALIDATION AVEC AVERTISSEMENTS - Vérifiez les points signalés"
    exit 0
else
    echo ""
    echo "✅ VALIDATION RÉUSSIE - Configuration sécurisée!"
    echo ""
    echo "🎯 Prochaines étapes:"
    echo "1. Générer des secrets uniques si non déjà fait"
    echo "2. Configurer les certificats SSL/TLS"
    echo "3. Déployer avec un reverse proxy (nginx/apache)"
    echo "4. Activer le monitoring de sécurité"
    exit 0
fi
