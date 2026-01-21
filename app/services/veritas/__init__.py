"""
Services VERITAS refactorés selon principes SOLID.

Ce package décompose l'ancien VeritasService monolithique en services
spécialisés respectant le Single Responsibility Principle :

- VeritasVerifier : Vérification calculs mathématiques
- VeritasGenerator : Génération réponses VERITAS  
- VeritasProofManager : Gestion preuves et certification
- VeritasAuditor : Audit et traçabilité
- VeritasMetrics : Métriques et statistiques
- VeritasOrchestrator : Coordination services (Facade pattern)

Example:
    from app.services.veritas import VeritasOrchestrator
    
    # Service orchestrateur principal
    veritas = VeritasOrchestrator(db_manager=db)
    await veritas.start()
    
    # Utilisation normale inchangée
    response = await veritas.generate_veritas_response(query, sources)
"""

from .veritas_verifier import VeritasVerifier
from .veritas_generator import VeritasGenerator  
from .veritas_proof_manager import VeritasProofManager
from .veritas_auditor import VeritasAuditor
from .veritas_metrics import VeritasMetrics
from .veritas_orchestrator import VeritasOrchestrator

__all__ = [
    "VeritasVerifier",
    "VeritasGenerator", 
    "VeritasProofManager",
    "VeritasAuditor",
    "VeritasMetrics",
    "VeritasOrchestrator"
]
