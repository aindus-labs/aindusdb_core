#!/bin/bash
# 🧪 test_safe_math_security.sh - Test de sécurité du SafeMathEvaluator
# Usage: ./test_safe_math_security.sh

echo "🔒 Test de Sécurité - SafeMathEvaluator"
echo "=========================================="

# Vérifier Python
if ! command -v python &> /dev/null; then
    echo "❌ Python non trouvé"
    exit 1
fi

# Créer script de test Python
cat > test_injection.py << 'EOF'
#!/usr/bin/env python3
"""
Test d'injection de code pour SafeMathEvaluator
"""

import sys
sys.path.append('.')

from app.core.safe_math import SafeMathEvaluator

# Liste des attaques par injection
injection_attempts = [
    # Code injection
    "__import__('os').system('echo PWNED')",
    "eval('__import__(\"os\").system(\"whoami\")')",
    "exec('print(\"PWNED\")')",
    
    # Accès système
    "open('/etc/passwd', 'r')",
    "file('/etc/passwd')",
    "input('Enter password: ')",
    
    # Réflexion et introspection
    "globals()",
    "locals()",
    "vars()",
    "dir()",
    "getattr(__import__('os'), 'system')",
    "setattr(__builtins__, '__import__', lambda x: __import__('os'))",
    
    # Création d'objets
    "type('Hack', (), {'__module__': '__main__'})",
    "isinstance(1, object)",
    "issubclass(int, object)",
    "callable(print)",
    
    # Compilation et exécution
    "compile('print(1)', '<string>', 'exec')",
    "__code__(0, 0, 0, 0, b'', (), (), (), '', '', 1, b'')",
    
    # Fonctions dangereuses
    "help('modules')",
    "reload(os)",
    
    # Attaques par format string
    "'{0.__class__}'.format(object())",
    "'{__import__}'.format()",
    
    # Attaques par décorateur
    "@property\ndef x(): pass",
    
    # Attaques par compréhension
    "[__import__('os') for _ in range(1)]",
    "{x: __import__('os') for x in range(1)}",
    
    # Attaques par générateur
    "(x for x in [__import__('os')])",
    
    # Attaques par lambda
    "lambda: __import__('os').system('echo PWNED')",
    
    # Attaques par opérateur bit
    "(__import__('os').system('echo PWNED')) & 0",
    
    # Attaques par exception
    "raise Exception(__import__('os').system('echo PWNED'))",
]

def test_security():
    """Tester les attaques par injection."""
    evaluator = SafeMathEvaluator()
    blocked = 0
    total = len(injection_attempts)
    
    print(f"🧪 Test de {total} tentatives d'injection...")
    print()
    
    for i, attack in enumerate(injection_attempts, 1):
        try:
            result = evaluator.evaluate(attack)
            print(f"❌ ATTAQUE RÉUSSIE #{i}: {attack[:50]}...")
            print(f"   Résultat: {result}")
            return False
        except (ValueError, SyntaxError, Exception) as e:
            print(f"✅ Attaque bloquée #{i}: {attack[:50]}...")
            blocked += 1
    
    print()
    print(f"📊 Résultat: {blocked}/{total} attaques bloquées")
    
    if blocked == total:
        print("🎉 Toutes les attaques ont été bloquées!")
        return True
    else:
        print("⚠️  Certaines attaques n'ont pas été bloquées!")
        return False

def test_legitimate_math():
    """Tester que les maths légitimes fonctionnent."""
    evaluator = SafeMathEvaluator()
    
    legitimate_tests = [
        ("2 + 3", 5.0),
        ("sin(0)", 0.0),
        ("sqrt(16)", 4.0),
        ("pi", 3.141592653589793),
        ("2 ** 8", 256.0),
        ("(1 + 2) * 3", 9.0),
    ]
    
    print("\n🧮 Test des calculs légitimes...")
    
    for expr, expected in legitimate_tests:
        try:
            result = evaluator.evaluate(expr)
            if abs(result - expected) < 1e-10:
                print(f"✅ {expr} = {result}")
            else:
                print(f"❌ {expr} = {result} (attendu: {expected})")
                return False
        except Exception as e:
            print(f"❌ Erreur avec {expr}: {e}")
            return False
    
    print("✅ Tous les calculs légitimes fonctionnent!")
    return True

if __name__ == "__main__":
    print("🔐 Test de sécurité SafeMathEvaluator")
    print("=====================================")
    
    security_ok = test_security()
    math_ok = test_legitimate_math()
    
    if security_ok and math_ok:
        print("\n🎉 TOUS LES TESTS RÉUSSIS!")
        print("✅ SafeMathEvaluator est sécurisé et fonctionnel")
        sys.exit(0)
    else:
        print("\n❌ CERTAINS TESTS ONT ÉCHOUÉ!")
        print("⚠️  SafeMathEvaluator nécessite des corrections")
        sys.exit(1)
EOF

echo ""
echo "🚀 Exécution des tests de sécurité..."
echo ""

if python test_injection.py; then
    echo ""
    echo "✅ Tests de sécurité validés avec succès!"
else
    echo ""
    echo "❌ Tests de sécurité échoués!"
    exit 1
fi

# Nettoyer
rm test_injection.py

echo ""
echo "=========================================="
echo "🎯 Prochaines étapes:"
echo "1. Exécuter les tests unitaires complets: pytest tests/test_safe_math.py"
echo "2. Intégrer SafeMathEvaluator dans tous les endpoints"
echo "3. Supprimer tous les appels à eval() restants"
echo ""
echo "📊 Score sécurité attendu: 8/10 (vs 3.5/10 initial)"
