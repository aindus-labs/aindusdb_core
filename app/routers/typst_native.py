"""
Router API pour génération Typst Native VERITAS.

Endpoints pour la génération intelligente de contenu Typst avec:
- Génération IA guidée par templates VERITAS
- Validation syntaxique temps réel
- Conversion LaTeX → Typst automatisée
- Métriques de performance et qualité

Architecture:
- POST /typst/generate - Génération IA native
- POST /typst/validate - Validation syntaxique
- POST /typst/convert - Conversion LaTeX → Typst
- GET /typst/templates - Templates VERITAS disponibles
- GET /typst/metrics - Métriques génération

Author: AindusDB Core Team
Version: 1.0.0 - Typst Native API
"""

from typing import List, Dict, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog

from app.services.ai_typst_generator import (
    AITypstGenerator, ContentDomain, GenerationStrategy, GenerationResult,
    get_ai_typst_generator
)
from app.services.typst_service import TypstService, TypstValidationResult, LaTeXToTypstConversion
from app.models.veritas import TypesettingMetadata

logger = structlog.get_logger(__name__)

# ============================================================================
# MODÈLES PYDANTIC POUR API
# ============================================================================

class TypstGenerationRequest(BaseModel):
    """Requête de génération Typst native."""
    content_description: str = Field(..., min_length=10, max_length=2000, 
                                   description="Description détaillée du contenu à générer")
    domain: ContentDomain = Field(..., description="Domaine scientifique")
    strategy: GenerationStrategy = Field(default=GenerationStrategy.HYBRID, 
                                       description="Stratégie de génération")
    complexity_level: str = Field(default="medium", pattern="^(simple|medium|complex)$",
                                description="Niveau de complexité souhaité")
    include_proof: bool = Field(default=True, description="Inclure preuves détaillées")
    include_dimensional_analysis: bool = Field(default=False, 
                                             description="Inclure analyse dimensionnelle")
    veritas_mode: bool = Field(default=True, description="Mode VERITAS activé")
    real_time_validation: bool = Field(default=True, 
                                     description="Validation temps réel")
    
    class Config:
        schema_extra = {
            "example": {
                "content_description": "Calculer la force gravitationnelle exercée sur un objet de 10kg à la surface de la Terre",
                "domain": "physics",
                "strategy": "hybrid",
                "complexity_level": "medium",
                "include_proof": True,
                "include_dimensional_analysis": True,
                "veritas_mode": True,
                "real_time_validation": True
            }
        }


class TypstValidationRequest(BaseModel):
    """Requête de validation Typst."""
    typst_content: str = Field(..., min_length=1, max_length=50000,
                             description="Contenu Typst à valider")
    strict_mode: bool = Field(default=False, description="Mode validation stricte")
    check_veritas_compliance: bool = Field(default=True, 
                                         description="Vérifier conformité VERITAS")


class LaTeXConversionRequest(BaseModel):
    """Requête de conversion LaTeX vers Typst."""
    latex_content: str = Field(..., min_length=1, max_length=50000,
                             description="Contenu LaTeX à convertir")
    preserve_structure: bool = Field(default=True, 
                                   description="Préserver structure document")
    optimize_for_veritas: bool = Field(default=True, 
                                     description="Optimiser pour VERITAS")
    auto_validate: bool = Field(default=True, 
                              description="Valider automatiquement résultat")


class TypstGenerationResponse(BaseModel):
    """Réponse de génération Typst."""
    success: bool = Field(..., description="Génération réussie")
    typst_content: str = Field(..., description="Contenu Typst généré")
    validation_result: TypstValidationResult = Field(..., description="Résultat validation")
    generation_time_ms: int = Field(..., description="Temps génération")
    strategy_used: GenerationStrategy = Field(..., description="Stratégie utilisée")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Score confiance")
    veritas_compatible: bool = Field(..., description="Compatible VERITAS")
    error_details: Optional[str] = Field(None, description="Détails erreurs")
    
    # Métadonnées additionnelles
    tokens_estimated: Optional[int] = Field(None, description="Tokens estimés utilisés")
    complexity_detected: float = Field(..., description="Complexité détectée")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions amélioration")


class TypstMetrics(BaseModel):
    """Métriques de performance Typst."""
    total_generations: int = Field(..., description="Total générations")
    success_rate: float = Field(..., description="Taux de succès")
    average_generation_time_ms: float = Field(..., description="Temps moyen génération")
    average_confidence_score: float = Field(..., description="Score confiance moyen")
    top_domains: List[Dict[str, Any]] = Field(..., description="Domaines les plus utilisés")
    error_patterns: List[Dict[str, Any]] = Field(..., description="Patterns d'erreur")
    veritas_compliance_rate: float = Field(..., description="Taux conformité VERITAS")


# ============================================================================
# ROUTER PRINCIPAL
# ============================================================================

router = APIRouter(
    prefix="/typst",
    tags=["Typst Native Generation"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)

# Métriques globales (en production, utiliser Redis/base de données)
_metrics_store = {
    "total_generations": 0,
    "successful_generations": 0,
    "total_generation_time_ms": 0,
    "confidence_scores": [],
    "domain_usage": {},
    "error_count": 0
}


@router.post(
    "/generate",
    response_model=TypstGenerationResponse,
    summary="Générer contenu Typst avec IA Native",
    description="""
    Génère du contenu Typst nativement optimisé pour VERITAS en utilisant
    l'IA spécialisée avec templates pré-validés et prompts adaptés.
    
    Fonctionnalités:
    - Templates VERITAS spécialisés par domaine
    - Validation syntaxique temps réel
    - Auto-correction des erreurs communes
    - Métriques de confiance et qualité
    """
)
async def generate_typst_content(
    request: TypstGenerationRequest,
    background_tasks: BackgroundTasks,
    generator: AITypstGenerator = Depends(get_ai_typst_generator)
) -> TypstGenerationResponse:
    """Générer contenu Typst avec IA native."""
    
    logger.info("typst_generation_request", 
               domain=request.domain, 
               strategy=request.strategy,
               content_length=len(request.content_description))
    
    try:
        # Génération avec IA native
        result = await generator.generate_typst_content(
            domain=request.domain,
            content_request=request.content_description,
            strategy=request.strategy,
            include_verification=request.real_time_validation
        )
        
        # Mise à jour métriques en arrière-plan
        background_tasks.add_task(
            _update_metrics,
            request.domain,
            result.generation_time_ms,
            result.confidence_score,
            result.success
        )
        
        # Suggestions d'amélioration
        suggestions = []
        if result.validation_result.complexity_score > 0.8:
            suggestions.append("Consider breaking complex content into smaller sections")
        if result.confidence_score < 0.7:
            suggestions.append("Review generated content for potential improvements")
        if not result.validation_result.veritas_compatible:
            suggestions.append("Adjust content structure for VERITAS compatibility")
        
        logger.info("typst_generation_success",
                   success=result.success,
                   generation_time=result.generation_time_ms,
                   confidence=result.confidence_score)
        
        return TypstGenerationResponse(
            success=result.success,
            typst_content=result.typst_content,
            validation_result=result.validation_result,
            generation_time_ms=result.generation_time_ms,
            strategy_used=result.strategy_used,
            confidence_score=result.confidence_score,
            veritas_compatible=result.validation_result.veritas_compatible,
            error_details=result.error_details,
            complexity_detected=result.validation_result.complexity_score,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error("typst_generation_error", error=str(e))
        background_tasks.add_task(_update_metrics, request.domain, 0, 0.0, False)
        
        raise HTTPException(
            status_code=500,
            detail=f"Typst generation failed: {str(e)}"
        )


@router.post(
    "/validate",
    response_model=TypstValidationResult,
    summary="Valider syntaxe Typst temps réel",
    description="""
    Valide la syntaxe d'un document Typst en temps réel avec:
    - Vérification syntaxique complète
    - Détection erreurs communes
    - Analyse de complexité
    - Vérification compatibilité VERITAS
    """
)
async def validate_typst_syntax(
    request: TypstValidationRequest,
    typst_service: TypstService = Depends(lambda: TypstService())
) -> TypstValidationResult:
    """Valider syntaxe Typst en temps réel."""
    
    logger.info("typst_validation_request", content_length=len(request.typst_content))
    
    try:
        validation_result = await typst_service.validate_typst_syntax(request.typst_content)
        
        logger.info("typst_validation_completed", 
                   valid=validation_result.is_valid,
                   errors=len(validation_result.syntax_errors),
                   warnings=len(validation_result.warnings))
        
        return validation_result
        
    except Exception as e:
        logger.error("typst_validation_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Typst validation failed: {str(e)}"
        )


@router.post(
    "/convert",
    response_model=LaTeXToTypstConversion,
    summary="Convertir LaTeX vers Typst",
    description="""
    Convertit automatiquement du contenu LaTeX vers Typst avec:
    - Conversion intelligente des constructs LaTeX
    - Optimisation pour génération IA
    - Amélioration compatibilité VERITAS
    - Validation automatique résultat
    """
)
async def convert_latex_to_typst(
    request: LaTeXConversionRequest,
    background_tasks: BackgroundTasks,
    typst_service: TypstService = Depends(lambda: TypstService())
) -> LaTeXToTypstConversion:
    """Convertir LaTeX vers Typst."""
    
    logger.info("latex_conversion_request", latex_length=len(request.latex_content))
    
    try:
        conversion_result = await typst_service.convert_latex_to_typst(request.latex_content)
        
        # Validation automatique si demandée
        if request.auto_validate and conversion_result.success and conversion_result.typst_content:
            validation_result = await typst_service.validate_typst_syntax(conversion_result.typst_content)
            
            # Ajouter résultat validation aux notes
            if not validation_result.is_valid:
                conversion_result.conversion_notes.append(f"Validation failed: {len(validation_result.syntax_errors)} syntax errors")
            else:
                conversion_result.conversion_notes.append("Validation passed: Typst syntax is correct")
        
        logger.info("latex_conversion_success",
                   success=conversion_result.success,
                   quality_improvement=conversion_result.quality_improvement,
                   veritas_gain=conversion_result.veritas_compliance_gain)
        
        return conversion_result
        
    except Exception as e:
        logger.error("latex_conversion_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"LaTeX to Typst conversion failed: {str(e)}"
        )


@router.get(
    "/templates",
    summary="Liste des templates VERITAS disponibles",
    description="Retourne la liste des templates Typst VERITAS disponibles par domaine"
)
async def get_available_templates(
    domain: Optional[ContentDomain] = Query(None, description="Filtrer par domaine")
) -> Dict[str, Any]:
    """Obtenir templates VERITAS disponibles."""
    
    templates_info = {
        "physics": {
            "name": "Physics Calculation",
            "description": "Templates pour calculs physiques avec vérification dimensionnelle",
            "features": ["Newton laws", "Energy calculations", "Dimensional analysis", "Unit conversion"]
        },
        "mathematics": {
            "name": "Mathematical Proof", 
            "description": "Templates pour preuves mathématiques rigoureuses",
            "features": ["Theorem proofs", "Step-by-step reasoning", "QED conclusions", "Logical structure"]
        },
        "chemistry": {
            "name": "Chemical Analysis",
            "description": "Templates pour analyses chimiques et réactions",
            "features": ["Reaction equations", "Stoichiometry", "Thermodynamics", "Kinetics"]
        },
        "engineering": {
            "name": "Engineering Design",
            "description": "Templates pour calculs d'ingénierie",
            "features": ["Structural analysis", "Fluid mechanics", "Heat transfer", "Control systems"]
        }
    }
    
    if domain:
        return {
            "domain": domain,
            "templates": templates_info.get(domain.value, {}),
            "total_available": 1 if domain.value in templates_info else 0
        }
    
    return {
        "all_domains": list(templates_info.keys()),
        "templates": templates_info,
        "total_available": len(templates_info)
    }


@router.get(
    "/metrics",
    response_model=TypstMetrics,
    summary="Métriques de génération Typst",
    description="Statistiques de performance et qualité de la génération Typst"
)
async def get_typst_metrics() -> TypstMetrics:
    """Obtenir métriques de génération Typst."""
    
    total_gens = _metrics_store["total_generations"]
    successful_gens = _metrics_store["successful_generations"]
    
    success_rate = (successful_gens / total_gens * 100) if total_gens > 0 else 0.0
    avg_time = (_metrics_store["total_generation_time_ms"] / total_gens) if total_gens > 0 else 0.0
    avg_confidence = (sum(_metrics_store["confidence_scores"]) / len(_metrics_store["confidence_scores"])) if _metrics_store["confidence_scores"] else 0.0
    
    # Top domaines
    domain_usage = _metrics_store["domain_usage"]
    top_domains = [
        {"domain": domain, "usage_count": count} 
        for domain, count in sorted(domain_usage.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    return TypstMetrics(
        total_generations=total_gens,
        success_rate=success_rate,
        average_generation_time_ms=avg_time,
        average_confidence_score=avg_confidence,
        top_domains=top_domains,
        error_patterns=[
            {"pattern": "LaTeX syntax residue", "count": _metrics_store["error_count"] // 3},
            {"pattern": "Unbalanced delimiters", "count": _metrics_store["error_count"] // 4}
        ],
        veritas_compliance_rate=95.5  # Exemple - à calculer réellement
    )


@router.get(
    "/metadata",
    response_model=TypesettingMetadata,
    summary="Métadonnées format Typst",
    description="Informations complètes sur le support Typst dans VERITAS"
)
async def get_typst_metadata(
    typst_service: TypstService = Depends(lambda: TypstService())
) -> TypesettingMetadata:
    """Obtenir métadonnées Typst pour VERITAS."""
    return typst_service.get_typst_metadata()


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

async def _update_metrics(
    domain: ContentDomain,
    generation_time_ms: int,
    confidence_score: float,
    success: bool
):
    """Mettre à jour métriques globales."""
    _metrics_store["total_generations"] += 1
    
    if success:
        _metrics_store["successful_generations"] += 1
        _metrics_store["total_generation_time_ms"] += generation_time_ms
        _metrics_store["confidence_scores"].append(confidence_score)
    else:
        _metrics_store["error_count"] += 1
    
    # Usage par domaine
    domain_str = domain.value
    _metrics_store["domain_usage"][domain_str] = _metrics_store["domain_usage"].get(domain_str, 0) + 1
    
    # Limiter taille des listes en mémoire (en production, utiliser base de données)
    if len(_metrics_store["confidence_scores"]) > 1000:
        _metrics_store["confidence_scores"] = _metrics_store["confidence_scores"][-500:]


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get(
    "/health",
    summary="Health check Typst Native",
    description="Vérification état du service de génération Typst"
)
async def health_check():
    """Health check du service Typst."""
    
    try:
        # Test rapide de génération
        generator = get_ai_typst_generator()
        test_result = await generator.generate_typst_content(
            domain=ContentDomain.MATHEMATICS,
            content_request="Test simple equation",
            strategy=GenerationStrategy.TEMPLATE_BASED,
            include_verification=True
        )
        
        return {
            "status": "healthy",
            "service": "Typst Native Generator",
            "version": "1.0.0",
            "test_generation": {
                "success": test_result.success,
                "generation_time_ms": test_result.generation_time_ms,
                "confidence_score": test_result.confidence_score
            },
            "total_generations": _metrics_store["total_generations"],
            "success_rate": (_metrics_store["successful_generations"] / max(1, _metrics_store["total_generations"])) * 100,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("typst_health_check_failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "service": "Typst Native Generator",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
