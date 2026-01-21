"""
Routeur VERITAS pour endpoints de vérification et certification des calculs.

Ce routeur expose les API du protocole VERITAS (Verifiable Execution & Reasoning 
Integrated Trust Action System) pour permettre aux clients d'obtenir des réponses 
avec preuves, traçabilité et certification mathématique.

Example:
    # Client request avec header VERITAS
    headers = {"X-Aindus-Veritas": "true"}
    response = requests.post("/api/v1/veritas/verify", 
                           headers=headers,
                           json={"query": "Calculate F=ma with m=10kg, a=9.8m/s²"})
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Request, BackgroundTasks
from typing import List, Optional, Dict, Any
import asyncio

from ..core.database import get_db_manager, DatabaseManager
from ..core.logging import get_logger
from ..services.veritas_service import veritas_service
from ..services.audit_service import audit_service
from ..middleware.auth import require_permission
from ..models.veritas import (
    VeritasReadyResponse, VeritasProof, ThoughtTrace, VerificationAudit,
    ProofType, VerificationStatus, ContentType, QualityMetadata
)
from ..models.auth import User
from pydantic import BaseModel, Field

# Configuration du routeur
router = APIRouter(
    prefix="/api/v1/veritas",
    tags=["veritas", "verification", "proofs"],
    responses={
        404: {"description": "Ressource non trouvée"},
        422: {"description": "Données invalides"},
        500: {"description": "Erreur serveur"}
    }
)

logger = get_logger("aindusdb.routers.veritas")


# ===== MODÈLES DE REQUÊTES =====

class VerificationRequest(BaseModel):
    """Requête de vérification VERITAS."""
    query: str = Field(..., min_length=10, max_length=2000, 
                      description="Question ou calcul à vérifier")
    sources: Optional[List[int]] = Field(None, 
                                       description="IDs des documents sources à utiliser")
    enable_proofs: bool = Field(True, 
                               description="Générer preuves mathématiques")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0,
                                                 description="Seuil de confiance minimum")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Calculate the force when mass is 10kg and acceleration is 9.8m/s²",
                "sources": [123, 456],
                "enable_proofs": True,
                "confidence_threshold": 0.8
            }
        }


class CalculationRequest(BaseModel):
    """Requête de calcul avec vérification."""
    formula: str = Field(..., min_length=3, max_length=200,
                        description="Formule mathématique à vérifier")
    input_data: Dict[str, Any] = Field(...,
                                      description="Données d'entrée pour le calcul")
    expected_result: Optional[Dict[str, Any]] = Field(None,
                                                    description="Résultat attendu (pour validation)")
    verification_method: str = Field("python_sandbox",
                                   regex="^(python_sandbox|basic_math|wolfram_alpha)$",
                                   description="Méthode de vérification")
    
    class Config:
        schema_extra = {
            "example": {
                "formula": "F = m * a",
                "input_data": {"mass": 10, "acceleration": 9.8},
                "expected_result": {"force": 98, "unit": "N"},
                "verification_method": "python_sandbox"
            }
        }


class ProofSearchRequest(BaseModel):
    """Requête de recherche de preuves existantes."""
    proof_type: Optional[ProofType] = Field(None, description="Type de preuve recherché")
    formula_pattern: Optional[str] = Field(None, max_length=100,
                                         description="Pattern de formule à rechercher")
    confidence_min: Optional[float] = Field(None, ge=0.0, le=1.0,
                                           description="Confiance minimum")
    limit: int = Field(10, ge=1, le=100, description="Nombre max de résultats")


# ===== ENDPOINTS PRINCIPAUX =====

@router.post("/verify", 
             response_model=None,
             summary="[DÉSACTIVÉ] Vérification complète VERITAS",
             description="[DÉSACTIVÉ POUR MAINTENANCE SÉCURITAIRE] - Service temporairement indisponible")
async def verify_with_veritas_disabled():
    """
    ⚠️ DÉSACTIVÉ POUR MAINTENANCE SÉCURITAIRE CRITIQUE ⚠️
    
    Ce service a été désactivé suite à l'identification de vulnérabilités 
    de sécurité critiques nécessitant une correction immédiate.
    
    Date de désactivation : 20/01/2026
    Raison : Vulnérabilité d'injection de code (eval())
    Statut : En cours de correction - Phase 1.1
    
    Contactez l'équipe de sécurité pour plus d'informations.
    """
    raise HTTPException(
        status_code=503,
        detail={
            "error": "SECURITY_MAINTENANCE",
            "message": "Service temporarily disabled for critical security maintenance",
            "disabled_at": "2026-01-20T18:00:00Z",
            "reason": "Critical security vulnerability identified",
            "expected_restoration": "Phase 2 completion (5-7 days)",
            "contact": "security@aindusdb.com"
        }
    )
    

@router.post("/calculations/verify",
            response_model=None,
            summary="[DÉSACTIVÉ] Vérifier un calcul mathématique",
            description="[DÉSACTIVÉ POUR MAINTENANCE SÉCURITAIRE] - Service temporairement indisponible")
async def verify_calculation_disabled():
    """
    ⚠️ DÉSACTIVÉ POUR MAINTENANCE SÉCURITAIRE CRITIQUE ⚠️
    
    Ce service a été désactivé suite à l'identification de vulnérabilités 
    de sécurité critiques nécessitant une correction immédiate.
    
    Date de désactivation : 20/01/2026
    Raison : Vulnérabilité d'injection de code (eval())
    Statut : En cours de correction - Phase 1.1
    
    Contactez l'équipe de sécurité pour plus d'informations.
    """
    raise HTTPException(
        status_code=503,
        detail={
            "error": "SECURITY_MAINTENANCE",
            "message": "Calculation verification service temporarily disabled for critical security maintenance",
            "disabled_at": "2026-01-20T18:00:00Z",
            "reason": "Critical security vulnerability identified (code injection)",
            "expected_restoration": "Phase 2 completion (5-7 days)",
            "contact": "security@aindusdb.com"
        }
    )


@router.get("/proofs",
           response_model=List[VeritasProof],
           summary="Rechercher preuves existantes",
           description="Recherche dans la base des preuves déjà générées")
async def search_proofs(
    request: ProofSearchRequest = Depends(),
    current_user: User = Depends(require_permission("veritas:read")),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    Rechercher dans la base des preuves VERITAS existantes.
    
    Permet de :
    - Réutiliser des calculs déjà vérifiés
    - Analyser l'historique des vérifications  
    - Identifier des patterns dans les preuves
    - Optimiser les performances en évitant les re-calculs
    """
    try:
        async with db_manager.get_connection() as conn:
            # Construire requête SQL dynamique
            where_conditions = []
            params = []
            param_counter = 1
            
            if request.proof_type:
                where_conditions.append(f"proof_type = ${param_counter}")
                params.append(request.proof_type.value)
                param_counter += 1
            
            if request.confidence_min:
                where_conditions.append(f"confidence_score >= ${param_counter}")
                params.append(request.confidence_min)
                param_counter += 1
            
            if request.formula_pattern:
                where_conditions.append(f"input_data::text ILIKE ${param_counter}")
                params.append(f"%{request.formula_pattern}%")
                param_counter += 1
            
            where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            query = f"""
                SELECT proof_type, input_data, computation_steps, result_value,
                       verification_status, confidence_score, verifier_system, created_at
                FROM veritas_proofs
                {where_clause}
                ORDER BY confidence_score DESC, created_at DESC
                LIMIT ${param_counter}
            """
            params.append(request.limit)
            
            rows = await conn.fetch(query, *params)
            
            # Convertir en modèles Pydantic
            proofs = []
            for row in rows:
                proof = VeritasProof(
                    proof_type=ProofType(row['proof_type']),
                    input_data=row['input_data'],
                    computation_steps=[],  # TODO: deserialiser from JSON
                    result_value=row['result_value'],
                    verification_status=VerificationStatus(row['verification_status']),
                    confidence_score=float(row['confidence_score']) if row['confidence_score'] else None,
                    verifier_system=row['verifier_system']
                )
                proofs.append(proof)
            
            logger.info(f"Found {len(proofs)} matching proofs",
                       extra={"user_id": current_user.id, "search_params": request.dict()})
            
            return proofs
            
    except Exception as e:
        logger.error(f"Error searching proofs: {e}")
        raise HTTPException(status_code=500, detail=f"Proof search failed: {str(e)}")


@router.get("/proofs/{proof_id}",
           response_model=VeritasProof,
           summary="Récupérer preuve par ID",
           description="Récupère une preuve spécifique par son identifiant")
async def get_proof_by_id(
    proof_id: int,
    current_user: User = Depends(require_permission("veritas:read")),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Récupérer une preuve VERITAS spécifique par son ID."""
    try:
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow("""
                SELECT proof_type, input_data, computation_steps, result_value,
                       verification_status, confidence_score, verifier_system, created_at
                FROM veritas_proofs 
                WHERE id = $1
            """, proof_id)
            
            if not row:
                raise HTTPException(status_code=404, detail=f"Proof {proof_id} not found")
            
            proof = VeritasProof(
                proof_type=ProofType(row['proof_type']),
                input_data=row['input_data'],
                computation_steps=[],  # TODO: deserialiser computation steps
                result_value=row['result_value'],
                verification_status=VerificationStatus(row['verification_status']),
                confidence_score=float(row['confidence_score']) if row['confidence_score'] else None,
                verifier_system=row['verifier_system']
            )
            
            return proof
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving proof {proof_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve proof: {str(e)}")


@router.get("/stats",
           summary="Statistiques VERITAS",
           description="Statistiques d'utilisation et performance du système VERITAS")
async def get_veritas_stats(
    current_user: User = Depends(require_permission("veritas:admin")),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    Obtenir statistiques complètes du système VERITAS.
    
    Inclut :
    - Nombre de vérifications effectuées
    - Distribution des types de preuves
    - Métriques de confiance moyennes  
    - Performance des différents vérificateurs
    - Statistiques temporelles
    """
    try:
        async with db_manager.get_connection() as conn:
            # Statistiques globales
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_proofs,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(*) FILTER (WHERE verification_status = 'verified') as verified_proofs,
                    COUNT(*) FILTER (WHERE verification_status = 'failed') as failed_proofs
                FROM veritas_proofs
            """)
            
            # Distribution par type de preuve
            proof_types = await conn.fetch("""
                SELECT proof_type, COUNT(*) as count
                FROM veritas_proofs
                GROUP BY proof_type
                ORDER BY count DESC
            """)
            
            # Performance par vérificateur
            verifiers = await conn.fetch("""
                SELECT verifier_system, 
                       COUNT(*) as count,
                       AVG(confidence_score) as avg_confidence
                FROM veritas_proofs
                WHERE verifier_system IS NOT NULL
                GROUP BY verifier_system
                ORDER BY count DESC
            """)
            
            # Statistiques du service
            service_stats = veritas_service.get_stats()
            
            return {
                "database_stats": {
                    "total_proofs": stats['total_proofs'],
                    "average_confidence": float(stats['avg_confidence']) if stats['avg_confidence'] else 0.0,
                    "verified_proofs": stats['verified_proofs'],
                    "failed_proofs": stats['failed_proofs'],
                    "success_rate": float(stats['verified_proofs']) / max(stats['total_proofs'], 1)
                },
                "proof_type_distribution": [
                    {"type": row['proof_type'], "count": row['count']} 
                    for row in proof_types
                ],
                "verifier_performance": [
                    {
                        "verifier": row['verifier_system'],
                        "count": row['count'],
                        "avg_confidence": float(row['avg_confidence']) if row['avg_confidence'] else 0.0
                    }
                    for row in verifiers
                ],
                "service_stats": service_stats
            }
            
    except Exception as e:
        logger.error(f"Error getting VERITAS stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ===== FONCTIONS UTILITAIRES =====

async def _get_sources_metadata(source_ids: List[int], db_manager: DatabaseManager) -> List:
    """Récupérer métadonnées des sources depuis la DB."""
    # TODO: Implémenter récupération réelle des sources
    # Pour l'instant, retourner sources mock
    from ..models.veritas import SourceMetadata
    
    sources = []
    for doc_id in source_ids[:5]:  # Limiter à 5 sources max
        sources.append(SourceMetadata(
            document_id=doc_id,
            title=f"Document {doc_id}",
            content_type=ContentType.MARKDOWN,
            quality_score=0.85,
            relevance_score=0.78
        ))
    
    return sources


async def _generate_base_answer(query: str) -> str:
    """Générer réponse de base (simulation - à remplacer par vraie IA)."""
    # Simulation d'une réponse d'IA pour démonstration
    if "force" in query.lower() and "mass" in query.lower():
        return "Using Newton's second law F=ma, with mass=10kg and acceleration=9.8m/s², the force is 98 N."
    elif "calculate" in query.lower():
        return "I'll perform the calculation step by step with verification."
    else:
        return f"Based on your query about '{query[:50]}...', here is the analysis with VERITAS verification."


async def _audit_verification_request(
    user_id: int,
    verification_id: str,
    request: VerificationRequest,
    response: VeritasReadyResponse
):
    """Auditer une requête de vérification en arrière-plan."""
    try:
        await audit_service.log_data_operation(
            user_id=user_id,
            action="veritas_verification_completed",
            resource="veritas_service",
            details={
                "verification_id": verification_id,
                "query_length": len(request.query),
                "proofs_generated": len(response.proofs),
                "overall_confidence": float(response.confidence_metrics.overall),
                "processing_time_ms": response.processing_time_ms,
                "veritas_compatible": response.veritas_compatible
            }
        )
    except Exception as e:
        logger.error(f"Error auditing verification request: {e}")


# ===== ENDPOINTS DE SANTÉ =====

@router.get("/health",
           summary="Santé du système VERITAS", 
           description="Vérifier le statut et la disponibilité des composants VERITAS")
async def veritas_health():
    """Endpoint de santé pour monitoring VERITAS."""
    try:
        # Vérifier service VERITAS
        service_started = veritas_service.started
        
        # TODO: Vérifier sandbox, DB, etc.
        
        return {
            "status": "healthy" if service_started else "degraded",
            "service_started": service_started,
            "components": {
                "veritas_service": "up" if service_started else "down",
                "database": "up",  # TODO: vérifier vraie DB
                "sandbox": "up"    # TODO: vérifier sandbox
            },
            "timestamp": "2024-01-20T15:10:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error in VERITAS health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-01-20T15:10:00Z"
        }
