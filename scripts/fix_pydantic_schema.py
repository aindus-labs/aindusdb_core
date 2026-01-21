#!/usr/bin/env python3
"""
Script pour corriger les erreurs Pydantic v2 (schema_extra -> json_schema_extra).
"""

import os
import re
from pathlib import Path

def fix_schema_in_file(file_path):
    """Corrige schema_extra= en json_schema_extra= dans un fichier."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remplacer schema_extra= par json_schema_extra=
        modified_content = re.sub(r'schema_extra=', 'json_schema_extra=', content)
        
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
    print("Fixing Pydantic v2 schema_extra -> json_schema_extra issues...")
    
    # Trouver tous les fichiers Python avec schema_extra
    app_dir = Path("app")
    files_to_fix = []
    
    for file_path in app_dir.rglob("*.py"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if 'schema_extra=' in f.read():
                    files_to_fix.append(str(file_path))
        except:
            pass
    
    fixed_count = 0
    for file_path in files_to_fix:
        if fix_schema_in_file(file_path):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files.")

if __name__ == "__main__":
    main()
