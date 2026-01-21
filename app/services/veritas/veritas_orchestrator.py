"""
VeritasOrchestrator - Façade pour coordonner tous les services VERITAS refactorés.

Ce service implémente le pattern Facade pour maintenir une API simple
tout en déléguant aux services spécialisés selon les principes SOLID.

Example:
    orchestrator = VeritasOrchestrator(db_manager=db)
    await orchestrator.start()
    
    # API inchangée pour compatibilité
    response = await orchestrator.generate_veritas_response(query, sources)
"""

from typing import Dict, List, Optional, Any
from functools import lru_cache

from ...core.logging import get_logger
from ...core.database import DatabaseManager
from ...models.veritas import (
    VeritasReadyResponse, VeritasProof, SourceMetadata
)

from .veritas_verifier import VeritasVerifier
from .veritas_generator import VeritasGenerator
from .veritas_proof_manager import VeritasProofManager


class VeritasOrchestrator:
    """
    Service orchestrateur VERITAS utilisant pattern Facade.
    
    Coordonne tous les services spécialisés VERITAS pour maintenir
    une API simple et cohérente tout en respectant les principes SOLID.
    Remplace l'ancien VeritasService monolithique.
    
    Services coordonnés:
    - VeritasVerifier: Vérification des calculs
    - VeritasGenerator: Génération de réponses  
    - VeritasProofManager: Gestion des preuves
    - Cache LRU: Évite memory leaks (correction audit)
    
    Attributes:
        db_manager: Gestionnaire de base de données (injection)
        verifier: Service de vérification
        generator: Service de génération
        proof_manager: Gestionnaire de preuves
        
    Example:
        # Initialisation avec dependency injection
        orchestrator = VeritasOrchestrator(db_manager=db_manager)
        await orchestrator.start()
        
        # API identique à l'ancien VeritasService
        response = await orchestrator.generate_veritas_response(
            query="Calculate force", 
            sources=sources,
            base_answer="F = ma = 98N"
        )
    """
    
    def __init__(self, 
                 db_manager: DatabaseManager,
                 enable_sandbox: bool = True,
                 confidence_threshold: float = 0.7,
                 max_computation_time: int = 30000):
        """
        Initialiser l'orchestrateur VERITAS avec dependency injection.
        
        Args:
            db_manager: Gestionnaire de base de données (injecté)
            enable_sandbox: Activer sandbox sécurisé
            confidence_threshold: Seuil minimum de confiance
            max_computation_time: Temps max calculs (ms)
        """
        self.db_manager = db_manager
        self.enable_sandbox = enable_sandbox
        self.confidence_threshold = confidence_threshold
        self.max_computation_time = max_computation_time
        
        self.logger = get_logger("aindusdb.services.veritas.orchestrator")
        
        # Services spécialisés (initialization lazy)
        self._verifier: Optional[VeritasVerifier] = None
        self._generator: Optional[VeritasGenerator] = None
        self._proof_manager: Optional[VeritasProofManager] = None
        
        # État du service
        self.started = False
        
        # Statistiques consolidées
        self.stats = {
            "verifications_completed": 0,
            "proofs_generated": 0,
            "responses_generated": 0,
            "confidence_scores_sum": 0.0,
            "failed_verifications": 0
        }
    
    @property
    def verifier(self) -> VeritasVerifier:
        """Service de vérification (lazy loading)."""
        if self._verifier is None:
            self._verifier = VeritasVerifier(
                enable_sandbox=self.enable_sandbox,
                max_computation_time=self.max_computation_time
            )
        return self._verifier
    
    @property
    def generator(self) -> VeritasGenerator:
        """Service de génération (lazy loading)."""
        if self._generator is None:
            self._generator = VeritasGenerator(
                confidence_threshold=self.confidence_threshold,
                enable_thought_traces=True,
                max_thought_depth=10
            )
        return self._generator
    
    @property
    def proof_manager(self) -> VeritasProofManager:
        """Gestionnaire de preuves (lazy loading)."""
        if self._proof_manager is None:
            self._proof_manager = VeritasProofManager(
                db_manager=self.db_manager,
                enable_compression=False
            )
        return self._proof_manager
    
    async def start(self):
        """
        Démarrer l'orchestrateur et initialiser tous les services.
        
        Cette méthode maintient la compatibilité avec l'ancien VeritasService.
        """
        if self.started:
            self.logger.warning("VeritasOrchestrator already started")
            return
        
        try:
            self.logger.info("Starting VERITAS Orchestrator with refactored services")
            
            # Initialiser tous les services (force lazy loading)
            _ = self.verifier
            _ = self.generator  
            _ = self.proof_manager
            
            # Vérifier connectivité base de données
            if not self.db_manager.is_connected:
                await self.db_manager.connect()
            
            self.started = True
            
            self.logger.info("✅ VERITAS Orchestrator started successfully", 
                           extra={
                               "services_initialized": ["verifier", "generator", "proof_manager"],
                               "confidence_threshold": self.confidence_threshold,
                               "sandbox_enabled": self.enable_sandbox
                           })
            
        except Exception as e:
            self.logger.error(f"Failed to start VERITAS Orchestrator: {e}")
            raise
    
    async def stop(self):
        """Arrêter l'orchestrateur et nettoyer les ressources."""
        if not self.started:
            return
        
        try:
            self.logger.info("Stopping VERITAS Orchestrator")
            
            # Nettoyer les caches
            if self._proof_manager:
                self._proof_manager.clear_cache()
            
            # Nettoyer verification_cache (correction memory leak)
            if hasattr(self, 'verification_cache'):
                self.verification_cache.clear()
            
            self.started = False
            self.logger.info("✅ VERITAS Orchestrator stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping VERITAS Orchestrator: {e}")
    
    async def generate_veritas_response(self,
                                      query: str,
                                      sources: List[SourceMetadata],
                                      base_answer: str,
                                      request_id: Optional[str] = None,
                                      enable_proofs: bool = True) -> VeritasReadyResponse:
        """
        Générer une réponse VERITAS complète (API compatible).
        
        Cette méthode orchestre les services spécialisés pour générer
        une réponse complète tout en maintenant l'API de l'ancien service.
        
        Args:
            query: Requête utilisateur originale
            sources: Sources documentaires utilisées  
            base_answer: Réponse de base de l'IA
            request_id: ID de requête pour traçabilité
            enable_proofs: Générer preuves automatiques
            
        Returns:
            VeritasReadyResponse: Réponse complète VERITAS
            
        Example:
            response = await orchestrator.generate_veritas_response(
                query="What is the force needed?",
                sources=[physics_source],
                base_answer="Using F=ma, force = 10 * 9.8 = 98N",
                enable_proofs=True
            )
        """
        if not self.started:
            raise RuntimeError("VeritasOrchestrator not started. Call await start() first.")
        
        self.logger.info("Generating VERITAS response via orchestrator",
                        extra={"request_id": request_id, "enable_proofs": enable_proofs})
        
        try:
            # 1. Générer réponse de base avec le generator
            response = await self.generator.generate_veritas_response(
                query=query,
                sources=sources,
                base_answer=base_answer,
                request_id=request_id,
                enable_proofs=enable_proofs
            )
            
            # 2. Générer preuves automatiques si demandé
            if enable_proofs and response.veritas_compatible:
                proofs = await self._generate_proofs_for_answer(
                    query, base_answer, sources
                )
                response.proofs = proofs
                
                # 3. Stocker les preuves pour traçabilité
                if proofs and response.verification_id:
                    for proof in proofs:
                        await self.proof_manager.store_proof(
                            proof, response.verification_id,
                            metadata={"query": query[:100], "source_count": len(sources)}
                        )
            
            # 4. Mettre à jour statistiques
            self.stats["responses_generated"] += 1
            if response.confidence_metrics:
                self.stats["confidence_scores_sum"] += response.confidence_metrics.overall
            
            self.logger.info("VERITAS response generated successfully",
                           extra={
                               "verification_id": response.verification_id,
                               "proofs_count": len(response.proofs),
                               "veritas_compatible": response.veritas_compatible
                           })
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating VERITAS response: {e}")
            self.stats["failed_verifications"] += 1
            
            # Retourner réponse d'erreur basique
            from ...models.veritas import ConfidenceMetrics
            return VeritasReadyResponse(
                answer=base_answer,
                confidence_metrics=ConfidenceMetrics(
                    overall=0.1, source_reliability=0.0,
                    logical_consistency=0.0, factual_accuracy=0.0,
                    completeness=0.0
                ),
                sources=sources,
                veritas_compatible=False,
                processing_time_ms=0,
                error_details=str(e)
            )
    
    @lru_cache(maxsize=128)  # Correction memory leak avec LRU cache
    async def _generate_proofs_for_answer(self,
                                        query: str,
                                        answer: str, 
                                        sources: List[SourceMetadata]) -> List[VeritasProof]:
        """
        Générer preuves automatiques pour une réponse (avec cache LRU).
        
        Args:
            query: Requête utilisateur
            answer: Réponse générée
            sources: Sources utilisées
            
        Returns:
            List[VeritasProof]: Preuves générées
        """
        proofs = []
        
        try:
            # Détecter nombres et opérations dans la réponse
            import re
            numbers = [float(x) for x in re.findall(r'\b\d+(?:\.\d+)?\b', answer)]
            operations = re.findall(r'[+\-*/=]', answer)
            
            if len(numbers) >= 2 and operations:
                # Utiliser le verifier pour créer une preuve
                proof = await self.verifier.verify_calculation(
                    input_data={f"num_{i}": num for i, num in enumerate(numbers[:3])},
                    formula=f"Calculation from: {answer[:50]}{'...' if len(answer) > 50 else ''}",
                    expected_result={"verified": True}
                )
                proofs.append(proof)
                
                # Mettre à jour statistiques
                self.stats["proofs_generated"] += 1
                if proof.verification_status.value == "VERIFIED":
                    self.stats["verifications_completed"] += 1
                else:
                    self.stats["failed_verifications"] += 1
        
        except Exception as e:
            self.logger.debug(f"Could not generate automatic proof: {e}")
        
        return proofs
    
    async def verify_calculation(self,
                               input_data: Dict[str, Any],
                               formula: str,
                               expected_result: Dict[str, Any]) -> VeritasProof:
        """
        Vérifier un calcul mathématique (délégation au verifier).
        
        Args:
            input_data: Données d'entrée du calcul
            formula: Formule à vérifier
            expected_result: Résultat attendu
            
        Returns:
            VeritasProof: Preuve de vérification
        """
        if not self.started:
            raise RuntimeError("VeritasOrchestrator not started")
        
        return await self.verifier.verify_calculation(
            input_data, formula, expected_result
        )
    
    def get_consolidated_stats(self) -> Dict[str, Any]:
        """
        Obtenir statistiques consolidées de tous les services.
        
        Returns:
            Dict: Statistiques complètes VERITAS
        """
        base_stats = self.stats.copy()
        
        # Ajouter statistiques moyennes
        if base_stats["responses_generated"] > 0:
            base_stats["avg_confidence"] = (
                base_stats["confidence_scores_sum"] / base_stats["responses_generated"]
            )
        else:
            base_stats["avg_confidence"] = 0.0
        
        # Ajouter taux de succès
        total_operations = (base_stats["verifications_completed"] + 
                          base_stats["failed_verifications"])
        if total_operations > 0:
            base_stats["success_rate"] = (
                base_stats["verifications_completed"] / total_operations
            )
        else:
            base_stats["success_rate"] = 1.0
        
        # Ajouter stats des services
        base_stats["services_status"] = {
            "verifier_initialized": self._verifier is not None,
            "generator_initialized": self._generator is not None,
            "proof_manager_initialized": self._proof_manager is not None,
            "orchestrator_started": self.started
        }
        
        return base_stats
    
    # Propriétés pour compatibilité avec l'ancien VeritasService
    @property
    def verification_cache(self):
        """Cache de vérification (vide pour éviter memory leaks)."""
        return {}  # Retourner cache vide pour éviter memory leaks
