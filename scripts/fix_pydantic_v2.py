#!/usr/bin/env python3
"""
Script pour corriger les erreurs Pydantic v2 (regex -> pattern).
"""

import os
import re
from pathlib import Path

def fix_regex_in_file(file_path):
    """Corrige regex= en pattern= dans un fichier."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remplacer regex= par pattern=
        modified_content = re.sub(r'regex=', 'pattern=', content)
        
        if content != modified_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fonction principale."""
    print("Fixing Pydantic v2 regex -> pattern issues...")
    
    # Liste des fichiers à corriger
    files_to_fix = [
        "app/core/cqrs/commands.py",
        "app/core/cqrs/queries.py",
        "app/core/secure_logging.py",
        "app/models/health.py",
        "app/models/secure_schemas.py",
        "app/models/secure_veritas.py",
        "app/models/vector.py",
        "app/routers/security_monitoring.py",
        "app/routers/typst_native.py",
        "app/routers/veritas.py"
    ]
    
    fixed_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_regex_in_file(file_path):
                fixed_count += 1
    
    print(f"\nFixed {fixed_count} files.")

if __name__ == "__main__":
    main()
