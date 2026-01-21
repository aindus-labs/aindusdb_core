#!/bin/bash
# 🧪 test_rate_limiting.sh - Script de test du rate limiting

echo "🧪 TEST RATE LIMITING & PROTECTION DDoS"
echo "======================================"

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

# Test 1: Rate limiting basique
echo "🔍 Test 1: Rate Limiting Basique"
echo "-------------------------------"
echo "Envoi de 10 requêtes rapides..."

for i in {1..10}; do
    response=$(curl -s -w "%{http_code}" http://localhost:8000/api/v1/health)
    http_code="${response: -3}"
    
    if [ "$http_code" = "429" ]; then
        echo "  Requête $i: ⏱️  Rate limité"
    elif [ "$http_code" = "200" ]; then
        echo "  Requête $i: ✅ Succès"
    else
        echo "  Requête $i: ❌ Erreur ($http_code)"
    fi
    
    sleep 0.1
done

echo ""

# Test 2: Brute force sur login
echo "🛡️  Test 2: Protection Brute Force"
echo "----------------------------------"
echo "Simulation de 10 tentatives de login échouées..."

for i in {1..10}; do
    response=$(curl -s -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"wrong'$i'"}' \
        http://localhost:8000/auth/login)
    
    http_code="${response: -3}"
    
    if [ "$http_code" = "429" ]; then
        echo "  Tentative $i: 🚫 Brute force bloqué"
        break
    elif [ "$http_code" = "401" ]; then
        echo "  Tentative $i: ❌ Échec authentification"
    else
        echo "  Tentative $i: ? ($http_code)"
    fi
    
    sleep 0.2
done

echo ""

# Test 3: DDoS protection
echo "🌊 Test 3: Protection DDoS"
echo "--------------------------"
echo "Envoi de 50 requêtes concurrentes..."

# Créer un script temporaire pour les requêtes concurrentes
cat > /tmp/ddos_test.sh << 'EOF'
#!/bin/bash
for i in {1..50}; do
    curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1 &
done
wait
EOF

chmod +x /tmp/ddos_test.sh
start_time=$(date +%s.%N)
/tmp/ddos_test.sh
end_time=$(date +%s.%N)

duration=$(echo "$end_time - $start_time" | bc)
echo "⏱️  Durée: ${duration}s"

rm /tmp/ddos_test.sh

echo ""

# Test 4: Vérification des headers
echo "📋 Test 4: Headers Rate Limit"
echo "-----------------------------"
echo "Vérification des headers de rate limit..."

response=$(curl -s -I http://localhost:8000/api/v1/health)

echo "Headers reçus:"
echo "$response" | grep -i "x-ratelimit" || echo "  ❌ Headers rate limit non trouvés"

echo ""
echo "======================================"
echo "✅ TESTS TERMINÉS"
echo ""
echo "📊 Résultats attendus:"
echo "  • Rate limiting: Après ~6 requêtes"
echo "  • Brute force: Après 10 tentatives"
echo "  • DDoS: Limitation automatique"
echo "  • Headers: X-RateLimit-* présents"
