"""
Modèles VERITAS sécurisés pour AindusDB Core.

Ce module étend les modèles VERITAS avec validation de sécurité renforcée.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator, model_validator, field_validator
import re

from .secure_schemas import SecureQuery, SecureJSON

# Import des modèles de base
from .veritas import (
    VerificationRequest as BaseVerificationRequest,
    CalculationRequest as BaseCalculationRequest,
    ProofType,
    VerificationStatus,
    ConfidenceMetrics,
    VeritasProof,
    SourceMetadata,
    ThoughtTrace
)

# Requête VERITAS sécurisée
class SecureVerificationRequest(SecureQuery):
    """Requête de vérification VERITAS avec validation sécurisée."""
    enable_proofs: bool = True
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    sources: Optional[List[str]] = None
    max_sources: int = Field(10, ge=1, le=50)
    
    @field_validator('sources')
    def validate_sources(cls, v):
        """Valider les sources."""
        if v is None:
            return v
        
        if len(v) > 10:
            raise ValueError("Too many sources (max 10)")
        
        for source in v:
            if not isinstance(source, str):
                raise ValueError("Source must be string")
            if len(source) > 100:
                raise ValueError("Source name too long")
            if not re.match(r'^[a-zA-Z0-9_-]+$', source):
                raise ValueError("Invalid source format")
        
        return v

# Requête de calcul sécurisée
class SecureCalculationRequest(BaseModel):
    """Requête de calcul avec validation sécurisée."""
    input_data: Dict[str, float]
    formula: str
    expected_result: Optional[Dict[str, float]] = None
    verification_method: str = Field("mathematical", pattern="^(mathematical|numerical|symbolic)$")
    max_variables: int = Field(20, ge=1, le=100)
    
    @field_validator('input_data')
    def validate_input_data(cls, v, values):
        """Valider les données d'entrée."""
        if not v:
            raise ValueError("Input data cannot be empty")
        
        max_vars = values.get('max_variables', 20)
        if len(v) > max_vars:
            raise ValueError(f"Too many variables (max {max_vars})")
        
        for key, value in v.items():
            # Nom de variable sécurisé
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', key):
                raise ValueError(f"Invalid variable name: {key}")
            
            # Type numérique
            if not isinstance(value, (int, float)):
                raise ValueError(f"Variable {key} must be numeric")
            
            # Valeur raisonnable
            if abs(value) > 1e10:
                raise ValueError(f"Variable {key} value too large")
            
            # Pas de NaN ou Inf
            if value != value or value in (float('inf'), float('-inf')):
                raise ValueError(f"Variable {key} cannot be NaN or infinite")
        
        return v
    
    @field_validator('formula')
    def validate_formula(cls, v):
        """Valider la formule avec SafeMathEvaluator."""
        if not v or not v.strip():
            raise ValueError("Formula cannot be empty")
        
        # Longueur raisonnable
        if len(v) > 500:
            raise ValueError("Formula too long")
        
        # Validation avec SafeMathEvaluator
        try:
            from ..core.safe_math import safe_math
            validation = safe_math.validate_expression(v)
            if not validation['valid']:
                raise ValueError(f"Invalid formula: {validation['error']}")
        except Exception as e:
            raise ValueError(f"Formula validation failed: {e}")
        
        return v.strip()
    
    @field_validator('expected_result')
    def validate_expected_result(cls, v):
        """Valider le résultat attendu."""
        if v is None:
            return v
        
        for key, value in v.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Expected result {key} must be numeric")
        
        return v

# Réponse VERITAS sécurisée
class SecureVeritasResponse(BaseModel):
    """Réponse VERITAS avec validation sécurisée."""
    query_id: str
    query: str
    answer: str
    sources: List[SourceMetadata]
    proofs: List[VeritasProof]
    traces: List[ThoughtTrace]
    confidence_metrics: ConfidenceMetrics
    processing_time_ms: int = Field(..., ge=0)
    timestamp: datetime
    
    @field_validator('query_id')
    def validate_query_id(cls, v):
        """Valider l'ID de requête."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Query ID must be alphanumeric")
        return v
    
    @field_validator('answer')
    def validate_answer(cls, v):
        """Valider la réponse."""
        if not v or not v.strip():
            raise ValueError("Answer cannot be empty")
        
        v = v.strip()
        
        # Longueur max
        if len(v) > 10000:
            raise ValueError("Answer too long")
        
        # Pas de code injecté
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'__import__',
            r'exec\s*\(',
            r'eval\s*\(',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Answer contains potentially dangerous content")
        
        return v
    
    @field_validator('sources')
    def validate_sources(cls, v):
        """Valider les sources."""
        if not v:
            raise ValueError("At least one source required")
        
        if len(v) > 50:
            raise ValueError("Too many sources")
        
        return v
    
    @field_validator('proofs')
    def validate_proofs(cls, v):
        """Valider les preuves."""
        if len(v) > 100:
            raise ValueError("Too many proofs")
        
        # Valider chaque preuve
        for proof in v:
            if proof.confidence_score and (proof.confidence_score < 0 or proof.confidence_score > 1):
                raise ValueError("Proof confidence score must be between 0 and 1")
        
        return v
    
    @field_validator('traces')
    def validate_traces(cls, v):
        """Valider les traces."""
        if len(v) > 1000:
            raise ValueError("Too many thought traces")
        
        return v

# Requête de recherche sécurisée
class SecureProofSearchRequest(BaseModel):
    """Requête de recherche de preuves sécurisée."""
    proof_type: Optional[str] = None
    confidence_min: Optional[float] = Field(None, ge=0.0, le=1.0)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    formula_pattern: Optional[str] = None
    limit: int = Field(10, ge=1, le=100)
    
    @field_validator('proof_type')
    def validate_proof_type(cls, v):
        """Valider le type de preuve."""
        if v is None:
            return v
        
        allowed_types = [pt.value for pt in ProofType]
        if v not in allowed_types:
            raise ValueError(f"Invalid proof type. Must be one of: {allowed_types}")
        return v
    
    @field_validator('formula_pattern')
    def validate_formula_pattern(cls, v):
        """Valider le pattern de formule."""
        if v is None:
            return v
        
        # Pas de patterns dangereux
        dangerous = ['import', 'exec', 'eval', '__', 'subprocess', 'os', 'sys']
        pattern_lower = v.lower()
        for word in dangerous:
            if word in pattern_lower:
                raise ValueError(f"Dangerous pattern detected: {word}")
        
        # Longueur raisonnable
        if len(v) > 200:
            raise ValueError("Pattern too long")
        
        return v
    
    @field_validator('date_from', 'date_to')
    def validate_date_range(cls, v, values):
        """Valider la plage de dates."""
        if v is None:
            return v
        
        # Pas dans le futur
        if v > datetime.now():
            raise ValueError("Date cannot be in the future")
        
        # Pas trop ancien
        min_date = datetime(2020, 1, 1)
        if v < min_date:
            raise ValueError("Date too old")
        
        return v

# Métadonnées de sécurité
class SecurityMetadata(BaseModel):
    """Métadonnées de sécurité pour les réponses."""
    validation_passed: bool = True
    threats_blocked: List[str] = []
    security_score: float = Field(..., ge=0.0, le=1.0)
    scan_timestamp: datetime
    scanner_version: str = "1.0.0"
    
    @field_validator('threats_blocked')
    def validate_threats(cls, v):
        """Valider la liste des menaces."""
        allowed_threats = [
            'sql_injection', 'xss', 'code_injection', 'path_traversal',
            'command_injection', 'ldap_injection', 'xpath_injection'
        ]
        
        for threat in v:
            if threat not in allowed_threats:
                raise ValueError(f"Unknown threat type: {threat}")
        
        return v

# Réponse enrichie avec métadonnées de sécurité
class SecureVeritasReadyResponse(SecureVeritasResponse):
    """Réponse VERITAS avec métadonnées de sécurité."""
    security_metadata: SecurityMetadata
    
    @field_validator('security_metadata')
    def validate_security_metadata(cls, v):
        """Valider les métadonnées de sécurité."""
        if not v.validation_passed:
            raise ValueError("Security validation failed")
        
        return v
