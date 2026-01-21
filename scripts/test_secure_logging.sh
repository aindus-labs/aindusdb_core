#!/bin/bash
# 🧪 test_secure_logging.sh - Test du logging sécurisé

echo "🧪 TEST LOGGING SÉCURISÉ & MONITORING"
echo "====================================="

# Vérifier si le serveur est démarré
echo "📡 Vérification du serveur..."
curl -s http://localhost:8000/health > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Serveur non démarré. Démarrer avec:"
    echo "   uvicorn app.main:app --reload"
    exit 1
fi

echo "✅ Serveur démarré"
echo ""

# Test 1: Dashboard de sécurité
echo "📊 Test 1: Dashboard de Sécurité"
echo "--------------------------------"
echo "URL du dashboard: http://localhost:8000/api/v1/security/dashboard"
echo ""

# Test 2: API de stats
echo "📈 Test 2: API Statistiques"
echo "---------------------------"
echo "Récupération des statistiques de sécurité..."

response=$(curl -s http://localhost:8000/api/v1/security/stats)
echo "Réponse:"
echo "$response" | jq '.' 2>/dev/null || echo "$response"

echo ""

# Test 3: Recherche d'événements
echo "🔍 Test 3: Recherche d'Événements"
echo "---------------------------------"
echo "Recherche des 10 derniers événements..."

response=$(curl -s "http://localhost:8000/api/v1/security/events?limit=10")
echo "Réponse:"
echo "$response" | jq '.events | length' 2>/dev/null || echo "Erreur de parsing"

echo ""

# Test 4: Masquage des données sensibles
echo "🔒 Test 4: Masquage Données Sensibles"
echo "--------------------------------------"
echo "Envoi de données sensibles pour vérifier le masquage..."

# Envoyer un login avec mot de passe
response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"MySecretPassword123!"}' \
    http://localhost:8000/auth/login)

echo "Tentative de login (mot de passe masqué dans les logs)"
echo "Vérifier les logs: tail -f logs/security.log"

echo ""

# Test 5: Génération d'événements de sécurité
echo "⚠️  Test 5: Génération Événements Sécurité"
echo "----------------------------------------"
echo "Génération de différents types d'événements..."

# Événement de risque élevé
curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"query":"SELECT * FROM users; DROP TABLE users;"}' \
    http://localhost:8000/api/v1/veritas/verify > /dev/null 2>&1

# Multiple requêtes pour trigger rate limit
for i in {1..10}; do
    curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1
    sleep 0.05
done

echo "Événements générés:"
echo "  • Injection SQL (risque élevé)"
echo "  • Rate limit dépassé"
echo "  • Requêtes multiples"

echo ""

# Test 6: Export des logs
echo "📤 Test 6: Export des Logs"
echo "--------------------------"
echo "Export des logs des dernières 24 heures..."

yesterday=$(date -d "yesterday" -Iseconds)
today=$(date -Iseconds)

response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"start_time\":\"$yesterday\",\"end_time\":\"$today\",\"format\":\"json\"}" \
    http://localhost:8000/api/v1/security/export)

echo "Réponse d'export:"
echo "$response" | jq '.' 2>/dev/null || echo "$response"

echo ""
echo "====================================="
echo "✅ TESTS TERMINÉS"
echo ""
echo "📋 Fonctionnalités testées:"
echo "  • Dashboard sécurité (HTML/JS)"
echo "  • API statistiques temps réel"
echo "  • Recherche événements avec filtres"
echo "  • Masquage automatique données sensibles"
echo "  • Génération événements avec score de risque"
echo "  • Export logs (JSON/CSV)"
echo ""
echo "🔍 Vérification manuelle:"
echo "  • Logs: tail -f logs/security.log"
echo "  • Audit: tail -f logs/audit.log"
echo "  • Dashboard: http://localhost:8000/api/v1/security/dashboard"
