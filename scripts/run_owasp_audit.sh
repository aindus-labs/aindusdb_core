#!/bin/bash
# 🔍 run_owasp_audit.sh - Exécution audit OWASP complet
# Usage: ./run_owasp_audit.sh

echo "🔍 AUDIT DE CONFORMITÉ OWASP - AindusDB Core"
echo "=========================================="

# Vérifier Python
if ! command -v python &> /dev/null; then
    echo "❌ Python non trouvé"
    exit 1
fi

# Vérifier l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "⚠️  Environnement virtuel non trouvé"
    echo "Création de l'environnement..."
    python -m venv venv
fi

# Activer l'environnement
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# Installer les dépendances si nécessaire
if ! pip list | grep -q pydantic; then
    echo "📦 Installation des dépendances..."
    pip install -r requirements.txt
fi

# Exécuter l'audit
echo ""
echo "🚀 Exécution de l'audit OWASP..."
echo ""

if python scripts/owasp_audit.py; then
    echo ""
    echo "✅ Audit terminé avec succès!"
    
    # Afficher le résumé si le rapport existe
    if [ -f "owasp_audit_report.json" ]; then
        echo ""
        echo "📊 RÉSUMÉ DE L'AUDIT :"
        echo "====================="
        
        # Extraire le score avec python
        SCORE=$(python -c "import json; print(json.load(open('owasp_audit_report.json'))['score']['global'])")
        LEVEL=$(python -c "import json; print(json.load(open('owasp_audit_report.json'))['score']['level'])")
        
        echo f"Score OWASP : {SCORE}/10 ({LEVEL})"
        
        # Afficher les recommandations
        echo ""
        echo "🎯 RECOMMANDATIONS PRIORITAIRES :"
        python -c "
import json
report = json.load(open('owasp_audit_report.json'))
for rec in report['recommendations'][:3]:
    print(f'  • {rec}')
"
    fi
else
    echo ""
    echo "❌ Échec de l'audit"
    exit 1
fi

echo ""
echo "=========================================="
echo "📄 Rapport détaillé : owasp_audit_report.json"
echo ""
echo "🔍 Prochaines étapes recommandées :"
echo "1. Analyser le rapport détaillé"
echo "2. Implémenter les recommandations prioritaires"
echo "3. Planifier un audit de sécurité externe"
echo "4. Préparer la documentation de conformité"
