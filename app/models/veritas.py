"""
Modèles Pydantic pour le protocole VERITAS (Verifiable Execution & Reasoning Integrated Trust Action System).

Ces modèles définissent les structures de données nécessaires pour supporter
l'IA industrielle avec preuves, traçabilité et certification des calculs.

Example:
    from app.models.veritas import VeritasReadyResponse, ThoughtTrace
    
    # Réponse avec trace de raisonnement
    response = VeritasReadyResponse(
        answer="La force résultante est 100 N",
        thought_trace="<thought>Appliquons F=ma avec m=10kg et a=10m/s²</thought>",
        confidence_metrics={"calculation": 0.98, "units": 0.95},
        sources=[source1, source2]
    )
"""

from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, confloat, conint, model_validator, field_validator
from pydantic.types import conint, confloat


class ContentType(str, Enum):
    """Types de contenu supportés par VERITAS."""
    MARKDOWN = "markdown"
    LATEX = "latex"
    TYPST = "typst" 
    HTML = "html"
    PLAIN_TEXT = "plain_text"
    MIXED = "mixed"


class TypesettingFormat(str, Enum):
    """Formats de composition mathématique supportés par VERITAS."""
    TYPST = "typst"          # Format natif VERITAS - parsing déterministe
    LATEX = "latex"          # Legacy académique - macros complexes  
    ASCIIMATH = "asciimath"  # Simplicité pour IA
    MATHML = "mathml"        # Standard W3C
    KATEX = "katex"          # Web moderne
    MARKDOWN_MATH = "markdown_math"  # Simplicité maximale


class VeritasSupportLevel(str, Enum):
    """Niveaux de support VERITAS par format."""
    NATIVE = "native"        # Support natif optimal (Typst)
    FULL = "full"           # Support complet avec adaptations
    BASIC = "basic"         # Support basique fonctionnel
    LEGACY = "legacy"       # Support héritage, migration recommandée
    DEPRECATED = "deprecated" # Plus supporté


class ExtractionMethod(str, Enum):
    """Méthodes d'extraction de contenu."""
    STANDARD = "standard"
    LATEX_AWARE = "latex_aware"
    TYPST_AWARE = "typst_aware"      # Nouvelle méthode pour Typst natif
    OCR_ENHANCED = "ocr_enhanced"
    FORMULA_SPECIALIZED = "formula_specialized"
    MULTI_FORMAT = "multi_format"    # Support multi-format intelligent


class ProofType(str, Enum):
    """Types de preuves supportés."""
    CALCULATION = "calculation"
    DIMENSIONAL_ANALYSIS = "dimensional_analysis"
    LOGICAL_REASONING = "logical_reasoning"
    UNIT_CONVERSION = "unit_conversion"
    FORMULA_VALIDATION = "formula_validation"


class VerificationStatus(str, Enum):
    """Statuts de vérification."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    REJECTED = "rejected"


class ConfidenceLevel(str, Enum):
    """Niveaux de confiance."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CERTAIN = "certain"


class ThoughtType(str, Enum):
    """Types de pensée dans les traces."""
    REASONING = "reasoning"
    CALCULATION = "calculation"
    VERIFICATION = "verification"
    CONCLUSION = "conclusion"
    ASSUMPTION = "assumption"
    CONTRADICTION = "contradiction"


class TypesettingMetadata(BaseModel):
    """Métadonnées spécifiques au format de composition mathématique."""
    format_type: TypesettingFormat = Field(..., description="Format de composition")
    format_version: Optional[str] = Field(None, description="Version du format (ex: 0.10.0 pour Typst)")
    veritas_support_level: VeritasSupportLevel = Field(..., description="Niveau support VERITAS")
    parsing_deterministic: bool = Field(..., description="Parsing déterministe")
    ai_generation_friendly: bool = Field(..., description="Format IA-friendly")
    real_time_compilation: bool = Field(default=False, description="Compilation temps réel")
    complexity_score: confloat(ge=0.0, le=1.0) = Field(..., description="Score complexité format")
    migration_path_available: Optional[str] = Field(None, description="Chemin migration disponible")
    
    class Config:
        schema_extra = {
            "example": {
                "format_type": "typst",
                "format_version": "0.10.0",
                "veritas_support_level": "native", 
                "parsing_deterministic": True,
                "ai_generation_friendly": True,
                "real_time_compilation": True,
                "complexity_score": 0.1,
                "migration_path_available": "latex_to_typst"
            }
        }


class SourceMetadata(BaseModel):
    """
    Métadonnées d'une source de donnée avec traçabilité VERITAS.
    
    Attributes:
        document_id: ID du document source
        title: Titre du document
        content_type: Type de contenu
        source_hash: Hash SHA-256 pour intégrité
        quality_score: Score qualité 0.0-1.0
        extraction_confidence: Confiance extraction 0.0-1.0
        page_number: Numéro de page (si applicable)
        section: Section du document
        relevance_score: Score de pertinence pour la requête
        
    Example:
        source = SourceMetadata(
            document_id=123,
            title="Handbook of Physics",
            content_type=ContentType.LATEX,
            source_hash="abc123...",
            quality_score=0.95,
            extraction_confidence=0.87
        )
    """
    document_id: int = Field(..., description="ID unique du document source")
    title: str = Field(..., min_length=1, max_length=500, description="Titre du document")
    content_type: ContentType = Field(default=ContentType.MARKDOWN, description="Type de contenu")
    source_hash: Optional[str] = Field(None, pattern=r"^[a-f0-9]{64}$", description="Hash SHA-256 du contenu source")
    quality_score: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Score qualité du document")
    extraction_confidence: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Confiance de l'extraction")
    page_number: Optional[conint(ge=1)] = Field(None, description="Numéro de page source")
    section: Optional[str] = Field(None, max_length=200, description="Section du document")
    relevance_score: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Pertinence pour la requête")
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class QualityMetadata(BaseModel):
    """
    Métadonnées de qualité pour un document VERITAS.
    
    Attributes:
        extraction_quality: Qualité de l'extraction (0.0-1.0)
        latex_equations_count: Nombre d'équations LaTeX détectées
        validation_score: Score de validation du contenu
        source_reliability: Fiabilité de la source
        ocr_confidence: Confiance OCR si applicable
        formula_completeness: Complétude des formules mathématiques
        
    Example:
        quality = QualityMetadata(
            extraction_quality=0.95,
            latex_equations_count=12,
            validation_score=0.88,
            source_reliability="high"
        )
    """
    extraction_quality: confloat(ge=0.0, le=1.0) = Field(..., description="Qualité extraction 0.0-1.0")
    math_equations_count: conint(ge=0) = Field(default=0, description="Nombre équations mathématiques")
    typesetting_format: Optional[TypesettingFormat] = Field(None, description="Format de composition utilisé")
    format_parsing_success: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Succès parsing format")
    validation_score: confloat(ge=0.0, le=1.0) = Field(..., description="Score validation contenu")
    source_reliability: str = Field(..., pattern="^(low|medium|high|verified)$", description="Fiabilité source")
    ocr_confidence: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Confiance OCR")
    formula_completeness: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Complétude formules")
    structural_integrity: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Intégrité structure")
    semantic_coherence: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Cohérence sémantique")
    ai_generation_difficulty: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Difficulté génération IA (0=facile, 1=difficile)")


class ComputationStep(BaseModel):
    """
    Étape de calcul dans une preuve VERITAS.
    
    Attributes:
        step: Numéro d'étape
        description: Description de l'étape
        formula: Formule utilisée
        calculation: Calcul effectué
        result: Résultat de l'étape
        units: Unités du résultat
        verification: Vérification de l'étape
        
    Example:
        step = ComputationStep(
            step=1,
            description="Apply Newton's second law",
            formula="F = m * a",
            calculation="10 * 9.8 = 98",
            result="98",
            units="N"
        )
    """
    step: conint(ge=1) = Field(..., description="Numéro d'étape")
    description: str = Field(..., min_length=5, max_length=500, description="Description de l'étape")
    formula: Optional[str] = Field(None, max_length=200, description="Formule utilisée")
    calculation: Optional[str] = Field(None, max_length=1000, description="Calcul détaillé")
    result: Optional[str] = Field(None, max_length=200, description="Résultat de l'étape")
    units: Optional[str] = Field(None, max_length=50, description="Unités du résultat")
    verification: Optional[bool] = Field(None, description="Étape vérifiée")
    confidence: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Confiance dans l'étape")


class VeritasProof(BaseModel):
    """
    Preuve complète d'un calcul VERITAS.
    
    Attributes:
        proof_type: Type de preuve
        input_data: Données d'entrée
        computation_steps: Étapes de calcul
        result_value: Valeur résultat
        verification_status: Statut de vérification
        confidence_score: Score de confiance global
        verifier_system: Système de vérification utilisé
        
    Example:
        proof = VeritasProof(
            proof_type=ProofType.CALCULATION,
            input_data={"mass": 10, "acceleration": 9.8},
            computation_steps=[step1, step2],
            result_value={"force": 98, "unit": "N"},
            verification_status=VerificationStatus.VERIFIED,
            confidence_score=0.95
        )
    """
    proof_type: ProofType = Field(..., description="Type de preuve")
    input_data: Dict[str, Any] = Field(..., description="Données d'entrée du calcul")
    computation_steps: List[ComputationStep] = Field(..., min_items=1, description="Étapes de calcul")
    result_value: Dict[str, Any] = Field(..., description="Résultat final")
    verification_status: VerificationStatus = Field(default=VerificationStatus.PENDING, description="Statut vérification")
    confidence_score: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Score confiance global")
    verifier_system: Optional[str] = Field(None, max_length=50, description="Système de vérification")
    error_details: Optional[str] = Field(None, max_length=1000, description="Détails erreurs si échec")
    
    @field_validator('computation_steps')
    def validate_steps_order(cls, v):
        """Valider que les étapes sont dans l'ordre."""
        if len(v) > 1:
            steps_numbers = [step.step for step in v]
            if steps_numbers != sorted(steps_numbers):
                raise ValueError("Computation steps must be in sequential order")
        return v


class ThoughtTrace(BaseModel):
    """
    Trace de raisonnement pour traçabilité VERITAS.
    
    Attributes:
        reasoning_step: Numéro d'étape du raisonnement
        thought_content: Contenu de la pensée
        thought_type: Type de pensée
        confidence_level: Niveau de confiance
        source_documents: Documents sources référencés
        veritas_tags: Tags pour catégorisation
        
    Example:
        trace = ThoughtTrace(
            reasoning_step=1,
            thought_content="Je dois calculer la force en utilisant F=ma",
            thought_type=ThoughtType.REASONING,
            confidence_level=ConfidenceLevel.HIGH,
            source_documents=[123, 456],
            veritas_tags=["physics", "mechanics"]
        )
    """
    reasoning_step: conint(ge=1) = Field(..., description="Numéro d'étape du raisonnement")
    thought_content: str = Field(..., min_length=10, max_length=2000, description="Contenu de la pensée")
    thought_type: ThoughtType = Field(default=ThoughtType.REASONING, description="Type de pensée")
    confidence_level: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM, description="Niveau confiance")
    source_documents: List[int] = Field(default_factory=list, description="IDs documents sources")
    veritas_tags: List[str] = Field(default_factory=list, max_items=10, description="Tags catégorisation")
    
    @field_validator('veritas_tags')
    def validate_tags(cls, v):
        """Valider les tags."""
        return [tag.lower().strip() for tag in v if tag.strip()]


class ConfidenceMetrics(BaseModel):
    """
    Métriques de confiance détaillées pour VERITAS.
    
    Attributes:
        overall: Confiance globale
        calculation: Confiance des calculs
        sources: Confiance des sources
        reasoning: Confiance du raisonnement
        units: Confiance des unités
        logical_consistency: Cohérence logique
        dimensional_analysis: Analyse dimensionnelle
        
    Example:
        metrics = ConfidenceMetrics(
            overall=0.89,
            calculation=0.95,
            sources=0.87,
            reasoning=0.92,
            units=0.98
        )
    """
    overall: confloat(ge=0.0, le=1.0) = Field(..., description="Confiance globale")
    calculation: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Confiance calculs")
    sources: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Confiance sources")
    reasoning: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Confiance raisonnement")
    units: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Confiance unités")
    logical_consistency: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Cohérence logique")
    dimensional_analysis: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Analyse dimensionnelle")
    
    @model_validator(mode='before')
    @classmethod
    def validate_consistency(cls, values):
        """Valider cohérence des métriques."""
        overall = values.get('overall')
        individual_metrics = [
            values.get('calculation'),
            values.get('sources'), 
            values.get('reasoning'),
            values.get('units')
        ]
        
        # Filtrer les valeurs None
        valid_metrics = [m for m in individual_metrics if m is not None]
        
        if valid_metrics and overall:
            avg_individual = sum(valid_metrics) / len(valid_metrics)
            # Overall ne devrait pas être beaucoup plus élevé que la moyenne
            if overall > avg_individual + 0.2:
                raise ValueError("Overall confidence cannot be much higher than individual metrics")
        
        return values


class VeritasReadyResponse(BaseModel):
    """
    Réponse complète compatible avec le protocole VERITAS.
    
    Cette classe définit le format standard de réponse pour toutes les API
    AindusDB Core supportant la vérification et la traçabilité VERITAS.
    
    Attributes:
        answer: Réponse textuelle principale
        thought_trace: Trace complète du raisonnement
        confidence_metrics: Métriques de confiance détaillées
        sources: Liste des sources utilisées
        proofs: Preuves de calculs si applicables
        veritas_compatible: Réponse compatible protocole VERITAS
        verification_id: ID de session de vérification
        processing_time_ms: Temps de traitement
        
    Example:
        response = VeritasReadyResponse(
            answer="La force résultante est 98 N",
            thought_trace="<thought>J'applique F=ma avec m=10kg, a=9.8m/s²</thought>",
            confidence_metrics=ConfidenceMetrics(overall=0.95, calculation=0.98),
            sources=[source1, source2],
            proofs=[proof1],
            veritas_compatible=True
        )
    """
    answer: str = Field(..., min_length=1, max_length=10000, description="Réponse textuelle principale")
    thought_trace: Optional[str] = Field(None, max_length=5000, description="Trace raisonnement Système 2")
    confidence_metrics: ConfidenceMetrics = Field(..., description="Métriques confiance détaillées")
    sources: List[SourceMetadata] = Field(..., min_items=0, description="Sources utilisées")
    proofs: List[VeritasProof] = Field(default_factory=list, description="Preuves calculs")
    veritas_compatible: bool = Field(default=True, description="Compatible protocole VERITAS")
    verification_id: Optional[str] = Field(None, max_length=50, description="ID session vérification")
    processing_time_ms: Optional[conint(ge=0)] = Field(None, description="Temps traitement en ms")
    
    # Métadonnées additionnelles
    model_used: Optional[str] = Field(None, max_length=100, description="Modèle IA utilisé")
    veritas_version: Optional[str] = Field(None, max_length=20, description="Version protocole VERITAS")
    thought_traces: List[ThoughtTrace] = Field(default_factory=list, description="Traces détaillées")
    
    class Config:
        schema_extra = {
            "example": {
                "answer": "La force gravitationnelle exercée est de 98 N vers le bas.",
                "thought_trace": "<thought>Pour calculer la force, j'utilise la loi de Newton F=ma. Avec m=10kg et a=9.8m/s² (gravité terrestre), F=10×9.8=98 N.</thought>",
                "confidence_metrics": {
                    "overall": 0.95,
                    "calculation": 0.98,
                    "sources": 0.92,
                    "units": 0.99,
                    "reasoning": 0.94
                },
                "sources": [
                    {
                        "document_id": 123,
                        "title": "Fundamentals of Physics - Mechanics",
                        "content_type": "latex",
                        "source_hash": "a1b2c3d4e5f6...",
                        "quality_score": 0.95,
                        "relevance_score": 0.89
                    }
                ],
                "proofs": [
                    {
                        "proof_type": "calculation",
                        "input_data": {"mass": 10, "acceleration": 9.8},
                        "computation_steps": [
                            {
                                "step": 1,
                                "description": "Apply Newton's second law",
                                "formula": "F = m × a",
                                "calculation": "F = 10 × 9.8 = 98",
                                "result": "98",
                                "units": "N"
                            }
                        ],
                        "result_value": {"force": 98, "unit": "N", "direction": "downward"},
                        "verification_status": "verified",
                        "confidence_score": 0.98
                    }
                ],
                "veritas_compatible": True,
                "processing_time_ms": 245,
                "model_used": "gpt-4-veritas"
            }
        }
    
    @field_validator('thought_trace')
    def validate_thought_trace(cls, v):
        """Valider format des traces de pensée."""
        if v and not ('<thought>' in v and '</thought>' in v):
            raise ValueError("Thought trace must contain <thought></thought> tags")
        return v
    
    @model_validator(mode='before')
    @classmethod
    def validate_veritas_requirements(cls, values):
        """Valider exigences VERITAS."""
        veritas_compatible = values.get('veritas_compatible', False)
        sources = values.get('sources', [])
        confidence_metrics = values.get('confidence_metrics')
        
        if veritas_compatible:
            # Exiger au moins une source pour compatibilité VERITAS
            if not sources:
                raise ValueError("VERITAS compatible responses must have at least one source")
            
            # Exiger métriques de confiance
            if not confidence_metrics or confidence_metrics.overall < 0.1:
                raise ValueError("VERITAS compatible responses must have meaningful confidence metrics")
        
        return values


class VerificationAudit(BaseModel):
    """
    Audit d'une session de vérification VERITAS.
    
    Attributes:
        request_id: ID de la requête
        verification_type: Type de vérification effectuée
        input_query: Requête d'entrée
        documents_used: Documents utilisés
        final_confidence: Confiance finale
        success: Succès de la vérification
        verification_time_ms: Temps de vérification
        
    Example:
        audit = VerificationAudit(
            request_id="req_abc123",
            verification_type="full_veritas",
            input_query="Calculate gravitational force",
            documents_used=[123, 456],
            final_confidence=0.95,
            success=True,
            verification_time_ms=1200
        )
    """
    request_id: str = Field(..., max_length=50, description="ID requête unique")
    verification_type: str = Field(..., description="Type vérification")
    input_query: str = Field(..., min_length=1, max_length=2000, description="Requête originale")
    documents_used: List[int] = Field(..., description="IDs documents utilisés")
    final_confidence: Optional[confloat(ge=0.0, le=1.0)] = Field(None, description="Confiance finale")
    success: bool = Field(default=True, description="Vérification réussie")
    verification_time_ms: Optional[conint(ge=0)] = Field(None, description="Temps vérification")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Détails erreurs")
    veritas_version: Optional[str] = Field(None, max_length=20, description="Version VERITAS")
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
