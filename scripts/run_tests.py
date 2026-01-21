#!/usr/bin/env python3
"""
Script pour exécuter les tests AindusDB Core
"""
import subprocess
import sys
import argparse
import os
from pathlib import Path


def run_command(cmd, description=""):
    """Exécuter une commande et gérer les erreurs"""
    print(f"\n🔄 {description}")
    print(f"📝 Commande: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {description} - Succès")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"❌ {description} - Échec")
        if result.stderr:
            print("Erreur:", result.stderr)
        if result.stdout:
            print("Sortie:", result.stdout)
        return False
    
    return True


def check_requirements():
    """Vérifier les dépendances requises"""
    try:
        import pytest
        import coverage
        print("✅ Dépendances pytest et coverage trouvées")
        return True
    except ImportError as e:
        print(f"❌ Dépendance manquante: {e}")
        print("💡 Installez avec: pip install pytest pytest-cov pytest-asyncio")
        return False


def main():
    parser = argparse.ArgumentParser(description="Exécuter les tests AindusDB Core")
    parser.add_argument("--unit", action="store_true", help="Exécuter seulement les tests unitaires")
    parser.add_argument("--integration", action="store_true", help="Exécuter seulement les tests d'intégration")
    parser.add_argument("--load", action="store_true", help="Exécuter seulement les tests de charge")
    parser.add_argument("--fast", action="store_true", help="Exécuter les tests rapides seulement (exclure --slow)")
    parser.add_argument("--coverage", action="store_true", help="Générer le rapport de couverture")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")
    parser.add_argument("--parallel", "-n", type=int, help="Nombre de processus parallèles")
    
    args = parser.parse_args()
    
    # Vérifier les dépendances
    if not check_requirements():
        return 1
    
    # Définir le répertoire de base
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("🚀 Lancement des tests AindusDB Core")
    print(f"📂 Répertoire: {project_root}")
    
    # Construction de la commande pytest
    cmd = ["python", "-m", "pytest"]
    
    # Choix du type de tests
    if args.unit:
        cmd.append("tests/unit/")
    elif args.integration:
        cmd.append("tests/integration/")
    elif args.load:
        cmd.append("tests/load/")
    else:
        cmd.append("tests/")
    
    # Options communes
    if args.verbose:
        cmd.append("-v")
    
    if args.fast:
        cmd.extend(["-m", "not slow"])
    
    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])
    
    # Configuration couverture
    if args.coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=80"
        ])
    
    # Options additionnelles
    cmd.extend([
        "--tb=short",
        "--strict-markers",
        "--color=yes"
    ])
    
    # Exécuter les tests
    success = run_command(cmd, "Exécution des tests")
    
    if success and args.coverage:
        print("\n📊 Rapport de couverture généré dans htmlcov/index.html")
        
        # Ouvrir le rapport si possible
        try:
            import webbrowser
            coverage_file = project_root / "htmlcov" / "index.html"
            if coverage_file.exists():
                webbrowser.open(f"file://{coverage_file}")
                print("🌐 Rapport ouvert dans le navigateur")
        except:
            pass
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
