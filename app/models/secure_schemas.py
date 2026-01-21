"""
🛡️ Schémas de Validation Sécurisés - AindusDB Core
Validation d'entrée stricte pour prévenir les injections

Créé : 20 janvier 2026
Objectif : Phase 2.2 - Validation d'entrée stricte
"""

import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, validator, constr, Field
import logging

logger = logging.getLogger(__name__)

# Patterns de validation
SAFE_TEXT_PATTERN = r'^[a-zA-Z0-9\s\.,;:!?\'"\-\+\*\/\(\)\=\[\]\{\}_]+$'
SAFE_QUERY_PATTERN = r'^[a-zA-Z0-9\s\+\-\*\/\(\)\=\.\,\;\:\?\!\-\_\[\]\{\}]+$'
SAFE_FORMULA_PATTERN = r'^[a-zA-Z0-9\s\+\-\*\/\(\)\=\.\^]+$'
SAFE_IDENTIFIER_PATTERN = r'^[a-zA-Z][a-zA-Z0-9_]*$'
SAFE_EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}$'
SAFE_PATH_PATTERN = r'^[a-zA-Z0-9_\-/\.]+$'

# Mots dangereux à bloquer
DANGEROUS_KEYWORDS = [
    'import', 'exec', 'eval', '__', 'open', 'file', 'input', 'subprocess',
    'os', 'sys', 'globals', 'locals', 'vars', 'getattr', 'setattr',
    'delattr', 'hasattr', 'callable', 'type', 'isinstance', 'class',
    'def', 'return', 'if', 'else', 'elif', 'for', 'while', 'break',
    'continue', 'pass', 'try', 'except', 'finally', 'raise', 'assert',
    'del', 'global', 'nonlocal', 'lambda', 'yield', 'with', 'from'
]

# Patterns d'injection SQL
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
    r"(--|#|/\*|\*/|;|')",
    r"(\bOR\b.*\b1\s*=\s*1\b|\bAND\b.*\b1\s*=\s*1\b)",
    r"(\bUNION\b.*\bSELECT\b)",
    r"(\bWHERE\b.*\bOR\b)",
    r"(\bHAVING\b.*\bOR\b)",
]

# Patterns d'injection NoSQL
NOSQL_INJECTION_PATTERNS = [
    r'(\$where|\$ne|\$gt|\$lt|\$gte|\$lte|\$in|\$nin)',
    r'(\{.*\$.*\})',
    r"(javascript:|<script|</script)",
]

# Patterns XSS
XSS_PATTERNS = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'on\w+\s*=',  # onclick, onload, etc.
    r'<iframe[^>]*>',
    r'<object[^>]*>',
    r'<embed[^>]*>',
    r'<link[^>]*>',
    r'<meta[^>]*>',
]

class SecureBaseModel(BaseModel):
    """Modèle de base avec validation sécurisée."""
    
    @validator('*', pre=True)
    def validate_not_empty(cls, v):
        """Valider que les chaînes ne sont pas vides."""
        if isinstance(v, str) and not v.strip():
            raise ValueError("Field cannot be empty")
        return v
    
    @validator('*', pre=True)
    def validate_no_null_bytes(cls, v):
        """Bloquer les bytes nuls."""
        if isinstance(v, str) and '\x00' in v:
            raise ValueError("Null bytes not allowed")
        return v

class SecureText(SecureBaseModel):
    """Texte sécurisé avec validation de base."""
    text: constr(regex=SAFE_TEXT_PATTERN, min_length=1, max_length=1000)
    
    @validator('text')
    def validate_no_dangerous_keywords(cls, v):
        """Vérifier l'absence de mots-clés dangereux."""
        text_lower = v.lower()
        for keyword in DANGEROUS_KEYWORDS:
            if keyword in text_lower:
                raise ValueError(f"Dangerous keyword detected: {keyword}")
        return v

class SecureQuery(SecureBaseModel):
    """Requête sécurisée pour VERITAS."""
    query: constr(regex=SAFE_QUERY_PATTERN, min_length=1, max_length=500)
    formula: Optional[constr(regex=SAFE_FORMULA_PATTERN, max_length=200)] = None
    variables: Optional[Dict[str, float]] = None
    
    @validator('query')
    def validate_query_content(cls, v):
        """Validation avancée du contenu de la requête."""
        # Vérifier les injections
        text_lower = v.lower()
        for keyword in DANGEROUS_KEYWORDS:
            if keyword in text_lower:
                raise ValueError(f"Dangerous keyword in query: {keyword}")
        
        # Vérifier les patterns d'injection
        for pattern in SQL_INJECTION_PATTERNS + NOSQL_INJECTION_PATTERNS:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Potential injection detected")
        
        return v
    
    @validator('formula', pre=True)
    def validate_formula(cls, v):
        """Validation spécifique pour les formules mathématiques."""
        if v is None:
            return v
        
        # Vérifier que c'est une formule mathématique valide
        try:
            from ..core.safe_math import safe_math
            safe_math.validate_expression(v)
        except Exception as e:
            raise ValueError(f"Invalid mathematical formula: {e}")
        
        return v
    
    @validator('variables')
    def validate_variables(cls, v):
        """Valider les variables mathématiques."""
        if v is None:
            return v
        
        for key, value in v.items():
            if not re.match(SAFE_IDENTIFIER_PATTERN, key):
                raise ValueError(f"Invalid variable name: {key}")
            if not isinstance(value, (int, float)):
                raise ValueError(f"Variable {key} must be numeric")
            if abs(value) > 1e10:  # Limite raisonnable
                raise ValueError(f"Variable {key} value too large")
        
        return v

class SecureIdentifier(SecureBaseModel):
    """Identifiant sécurisé (usernames, IDs, etc.)."""
    identifier: constr(regex=SAFE_IDENTIFIER_PATTERN, min_length=3, max_length=50)
    
    @validator('identifier')
    def validate_identifier(cls, v):
        """Validation additionnelle pour les identifiants."""
        # Pas de mots réservés
        reserved = ['admin', 'root', 'system', 'api', 'www', 'mail', 'ftp']
        if v.lower() in reserved:
            raise ValueError(f"Identifier '{v}' is reserved")
        return v

class SecureEmail(SecureBaseModel):
    """Email sécurisé."""
    email: constr(regex=SAFE_EMAIL_PATTERN, max_length=255)
    
    @validator('email')
    def validate_email(cls, v):
        """Validation email avancée."""
        # Pas de domaines suspects
        suspicious_domains = ['tempmail.com', '10minutemail.com', 'guerrillamail.com']
        domain = v.split('@')[-1].lower()
        if domain in suspicious_domains:
            raise ValueError("Temporary email domains not allowed")
        return v

class SecurePassword(SecureBaseModel):
    """Mot de passe sécurisé."""
    password: constr(min_length=8, max_length=128)
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Valider la force du mot de passe."""
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain special character")
        return v

class SecurePath(SecureBaseModel):
    """Chemin de fichier sécurisé."""
    path: constr(regex=SAFE_PATH_PATTERN, min_length=1, max_length=255)
    
    @validator('path')
    def validate_path(cls, v):
        """Valider que le chemin est sécurisé."""
        # Pas de directory traversal
        if '../' in v or '..\\' in v:
            raise ValueError("Directory traversal not allowed")
        
        # Pas de chemins absolus (sauf si autorisé)
        if v.startswith('/') or (len(v) > 1 and v[1] == ':'):
            raise ValueError("Absolute paths not allowed")
        
        return v

class SecureJSON(SecureBaseModel):
    """JSON sécurisé."""
    data: Dict[str, Any]
    
    @validator('data')
    def validate_json_content(cls, v):
        """Valider le contenu JSON."""
        # Vérifier la taille
        import json
        if len(json.dumps(v)) > 10000:  # 10KB max
            raise ValueError("JSON data too large")
        
        # Vérifier récursivement les valeurs
        def validate_recursive(obj, depth=0):
            if depth > 10:  # Profondeur max
                raise ValueError("JSON structure too deep")
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if not isinstance(key, str):
                        raise ValueError("JSON keys must be strings")
                    validate_recursive(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    validate_recursive(item, depth + 1)
            elif isinstance(obj, str):
                # Vérifier les chaînes
                if '\x00' in obj:
                    raise ValueError("Null bytes not allowed in JSON")
                for keyword in DANGEROUS_KEYWORDS:
                    if keyword in obj.lower():
                        raise ValueError(f"Dangerous keyword in JSON: {keyword}")
        
        validate_recursive(v)
        return v

# Schémas spécifiques aux endpoints
class VeritasQueryRequest(SecureQuery):
    """Requête VERITAS sécurisée."""
    enable_proofs: bool = True
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    sources: Optional[List[str]] = None
    
    @validator('sources')
    def validate_sources(cls, v):
        """Valider les sources."""
        if v is None:
            return v
        
        if len(v) > 10:  # Max 10 sources
            raise ValueError("Too many sources")
        
        for source in v:
            if not isinstance(source, str):
                raise ValueError("Source must be string")
            if len(source) > 100:
                raise ValueError("Source name too long")
        
        return v

class CalculationRequest(SecureBaseModel):
    """Requête de calcul sécurisée."""
    input_data: Dict[str, float]
    formula: constr(regex=SAFE_FORMULA_PATTERN, min_length=1, max_length=200)
    expected_result: Optional[float] = None
    verification_method: str = Field("mathematical", regex="^(mathematical|numerical|symbolic)$")
    
    @validator('input_data')
    def validate_input_data(cls, v):
        """Valider les données d'entrée."""
        if not v:
            raise ValueError("Input data cannot be empty")
        
        if len(v) > 20:  # Max 20 variables
            raise ValueError("Too many input variables")
        
        for key, value in v.items():
            if not re.match(SAFE_IDENTIFIER_PATTERN, key):
                raise ValueError(f"Invalid variable name: {key}")
            if not isinstance(value, (int, float)):
                raise ValueError(f"Variable {key} must be numeric")
            if abs(value) > 1e10:
                raise ValueError(f"Variable {key} value too large")
        
        return v
    
    @validator('formula')
    def validate_formula(cls, v):
        """Valider la formule."""
        try:
            from ..core.safe_math import safe_math
            safe_math.validate_expression(v)
        except Exception as e:
            raise ValueError(f"Invalid formula: {e}")
        return v

class UserRegistrationRequest(SecureBaseModel):
    """Requête d'inscription sécurisée."""
    username: constr(regex=SAFE_IDENTIFIER_PATTERN, min_length=3, max_length=30)
    email: constr(regex=SAFE_EMAIL_PATTERN, max_length=255)
    password: constr(min_length=8, max_length=128)
    full_name: Optional[constr(max_length=100)] = None
    
    @validator('username')
    def validate_username(cls, v):
        """Validation spécifique du username."""
        reserved = ['admin', 'root', 'system', 'api', 'www', 'mail', 'ftp']
        if v.lower() in reserved:
            raise ValueError(f"Username '{v}' is reserved")
        return v
    
    @validator('password')
    def validate_password(cls, v):
        """Valider la force du mot de passe."""
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain special character")
        return v

# Middleware de validation global
class SecurityValidator:
    """Validateur de sécurité pour les entrées."""
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Nettoyer une entrée texte."""
        if not text:
            return text
        
        # Supprimer les caractères de contrôle
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # Normaliser les espaces
        text = ' '.join(text.split())
        
        return text
    
    @staticmethod
    def detect_injection(text: str) -> bool:
        """Détecter si un texte contient des tentatives d'injection."""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Vérifier les mots-clés dangereux
        for keyword in DANGEROUS_KEYWORDS:
            if keyword in text_lower:
                return True
        
        # Vérifier les patterns d'injection
        all_patterns = SQL_INJECTION_PATTERNS + NOSQL_INJECTION_PATTERNS + XSS_PATTERNS
        for pattern in all_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def validate_file_path(path: str, allowed_extensions: List[str] = None) -> bool:
        """Valider un chemin de fichier."""
        if not path:
            return False
        
        # Directory traversal
        if '../' in path or '..\\' in path:
            return False
        
        # Extension
        if allowed_extensions:
            ext = path.split('.')[-1].lower()
            if ext not in allowed_extensions:
                return False
        
        return True

# Instance globale
security_validator = SecurityValidator()
