#!/usr/bin/env python3
"""
Script pour corriger les validateurs Pydantic v2.
"""

import os
import re
from pathlib import Path

def fix_validators_in_file(file_path):
    """Corrige les validateurs Pydantic v2 dans un fichier."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Corrections à faire
        modified_content = content
        
        # 1. Remplacer @root_validator par @model_validator(mode='before')
        modified_content = re.sub(
            r'@root_validator',
            '@model_validator(mode=\'before\')',
            modified_content
        )
        
        # 2. Remplacer @validator par @field_validator
        modified_content = re.sub(
            r'@validator\(',
            '@field_validator(',
            modified_content
        )
        
        # 3. Corriger les imports
        modified_content = re.sub(
            r'from pydantic import (.*)',
            r'from pydantic import \1, model_validator, field_validator',
            modified_content
        )
        
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
    print("Fixing Pydantic v2 validators...")
    
    # Trouver tous les fichiers Python avec des validateurs
    app_dir = Path("app")
    files_to_fix = []
    
    for file_path in app_dir.rglob("*.py"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '@root_validator' in content or '@validator(' in content:
                    files_to_fix.append(str(file_path))
        except:
            pass
    
    fixed_count = 0
    for file_path in files_to_fix:
        if fix_validators_in_file(file_path):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files.")

if __name__ == "__main__":
    main()
