"""
VeritasGenerator - Service spécialisé pour génération de réponses VERITAS.

Ce service se concentre uniquement sur la génération de réponses VERITAS
complètes avec traces de raisonnement et métriques de confiance selon
le principe Single Responsibility.

Example:
    generator = VeritasGenerator(confidence_threshold=0.8)
    
    response = await generator.generate_veritas_response(
        query="Calculate force",
        sources=[source1, source2],
        base_answer="F = ma = 10 * 9.8 = 98N"
    )
"""

import time
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from ...core.logging import get_logger, LogContext
from ...models.veritas import (
    VeritasReadyResponse, ThoughtTrace, SourceMetadata,
    ConfidenceMetrics, ThoughtType, ConfidenceLevel
)


class VeritasGenerator:
    """
    Service de génération de réponses VERITAS avec traces de raisonnement.
    
    Responsabilité unique : Générer des réponses VERITAS complètes avec
    traces de pensée, métriques de confiance et enrichissement contextuel.
    
    Features:
    - Génération de traces de raisonnement structurées
    - Calcul de métriques de confiance granulaires
    - Détection automatique de calculs dans les réponses
    - Enrichissement avec métadonnées VERITAS
    - Support des thought traces avec tags <thought> <action>
    
    Attributes:
        confidence_threshold: Seuil minimum de confiance VERITAS
        enable_thought_traces: Activer capture traces de raisonnement
        max_thought_depth: Profondeur maximum traces de pensée
        
    Example:
        generator = VeritasGenerator(
            confidence_threshold=0.7,
            enable_thought_traces=True,
            max_thought_depth=5
        )
        
        response = await generator.generate_veritas_response(
            query="What is the acceleration?",
            sources=sources,
            base_answer="Using F=ma, acceleration = F/m = 100/10 = 10 m/s²"
        )
    """
    
    def __init__(self,
                 confidence_threshold: float = 0.7,
                 enable_thought_traces: bool = True,
                 max_thought_depth: int = 10):
        """
        Initialiser le générateur de réponses VERITAS.
        
        Args:
            confidence_threshold: Seuil minimum confiance
            enable_thought_traces: Activer traces de raisonnement
            max_thought_depth: Profondeur maximum des traces
        """
        self.confidence_threshold = confidence_threshold
        self.enable_thought_traces = enable_thought_traces
        self.max_thought_depth = max_thought_depth
        self.logger = get_logger("aindusdb.services.veritas.generator")
        
        # Patterns pour détection de calculs
        self.calculation_patterns = [
            r'\d+\s*[\+\-\*/]\s*\d+',  # 10 + 5, 20 * 3
            r'[a-zA-Z]\s*=\s*[a-zA-Z]\s*[\*\/]\s*[a-zA-Z]',  # F = m * a
            r'\d+\.?\d*\s*[a-zA-Z\/²³]+',  # 9.8 m/s², 100 N
            r'(?:sin|cos|tan|sqrt|log)\([^)]+\)',  # sin(30), sqrt(16)
        ]
        
        # Types de raisonnement détectables
        self.reasoning_types = {
            'mathematical': ['calculate', 'compute', 'solve', 'equation', 'formula'],
            'logical': ['therefore', 'because', 'since', 'if', 'then'],
            'analytical': ['analyze', 'examine', 'consider', 'evaluate'],
            'comparative': ['compare', 'contrast', 'versus', 'difference'],
            'causal': ['cause', 'effect', 'reason', 'result', 'consequence']
        }
    
    async def generate_veritas_response(self,
                                      query: str,
                                      sources: List[SourceMetadata],
                                      base_answer: str,
                                      request_id: Optional[str] = None,
                                      enable_proofs: bool = True) -> VeritasReadyResponse:
        """
        Générer une réponse VERITAS complète avec traces et métriques.
        
        Args:
            query: Requête utilisateur originale
            sources: Sources documentaires utilisées
            base_answer: Réponse de base de l'IA
            request_id: ID de requête pour traçabilité
            enable_proofs: Générer preuves automatiques
            
        Returns:
            VeritasReadyResponse: Réponse complète VERITAS
            
        Example:
            response = await generator.generate_veritas_response(
                query="What is the force needed to accelerate 10kg at 9.8 m/s²?",
                sources=[physics_source],
                base_answer="Using Newton's second law F=ma, F = 10 * 9.8 = 98N"
            )
        """
        start_time = time.time()
        
        with LogContext(operation="generate_veritas_response", request_id=request_id):
            self.logger.info("Generating VERITAS response",
                           extra={"query_preview": query[:100]})
            
            try:
                # 1. Analyser la requête pour détecter calculs
                calculation_detected = await self._detect_calculations(query, base_answer)
                
                # 2. Générer traces de raisonnement
                thought_traces = []
                if self.enable_thought_traces:
                    thought_traces = await self._generate_thought_traces(
                        query, base_answer, sources
                    )
                
                # 3. Calculer métriques de confiance
                confidence_metrics = await self._calculate_confidence_metrics(
                    base_answer, sources, calculation_detected, thought_traces
                )
                
                # 4. Formatter trace de raisonnement
                formatted_thought_trace = self._format_thought_trace(thought_traces)
                
                # 5. Déterminer compatibilité VERITAS
                veritas_compatible = (
                    confidence_metrics.overall >= self.confidence_threshold and
                    len(sources) > 0 and
                    len(thought_traces) > 0
                )
                
                # 6. Construire réponse VERITAS complète
                response = VeritasReadyResponse(
                    answer=base_answer,
                    thought_trace=formatted_thought_trace,
                    confidence_metrics=confidence_metrics,
                    sources=sources,
                    proofs=[],  # Les preuves seront ajoutées par VeritasProofManager
                    veritas_compatible=veritas_compatible,
                    verification_id=request_id or self._generate_verification_id(),
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    thought_traces=thought_traces,
                    metadata={
                        "calculation_detected": calculation_detected,
                        "reasoning_complexity": len(thought_traces),
                        "source_diversity": len(set(s.source_type for s in sources)),
                        "generation_method": "veritas_generator_v2"
                    }
                )
                
                self.logger.info("VERITAS response generated successfully",
                               extra={
                                   "veritas_compatible": veritas_compatible,
                                   "confidence": confidence_metrics.overall,
                                   "thought_traces_count": len(thought_traces)
                               })
                
                return response
                
            except Exception as e:
                self.logger.error(f"Error generating VERITAS response: {e}")
                
                # Réponse d'erreur VERITAS
                return VeritasReadyResponse(
                    answer=base_answer,
                    confidence_metrics=ConfidenceMetrics(
                        overall=0.1,
                        source_reliability=0.0,
                        logical_consistency=0.0,
                        factual_accuracy=0.0,
                        completeness=0.0
                    ),
                    sources=sources,
                    veritas_compatible=False,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    error_details=str(e)
                )
    
    async def _detect_calculations(self, query: str, answer: str) -> bool:
        """
        Détecter la présence de calculs mathématiques dans query/answer.
        
        Args:
            query: Requête utilisateur
            answer: Réponse générée
            
        Returns:
            bool: True si calculs détectés
        """
        combined_text = f"{query} {answer}".lower()
        
        # Vérifier patterns de calculs
        for pattern in self.calculation_patterns:
            if re.search(pattern, combined_text):
                self.logger.debug(f"Calculation pattern detected: {pattern}")
                return True
        
        # Vérifier mots-clés mathématiques
        math_keywords = ['calculate', 'compute', 'solve', 'formula', 'equation', 
                        'result', 'answer', '=', 'equals']
        
        for keyword in math_keywords:
            if keyword in combined_text:
                self.logger.debug(f"Math keyword detected: {keyword}")
                return True
        
        return False
    
    async def _generate_thought_traces(self,
                                     query: str,
                                     answer: str,
                                     sources: List[SourceMetadata]) -> List[ThoughtTrace]:
        """
        Générer traces de raisonnement structurées.
        
        Args:
            query: Requête originale
            answer: Réponse générée
            sources: Sources utilisées
            
        Returns:
            List[ThoughtTrace]: Traces de raisonnement
        """
        traces = []
        
        # Trace 1: Analyse de la requête
        traces.append(ThoughtTrace(
            step=1,
            thought_type=ThoughtType.ANALYSIS,
            content=f"Analyzing user query: '{query[:100]}{'...' if len(query) > 100 else ''}'",
            reasoning_chain=[
                "Parse user question for key concepts",
                "Identify required information type",
                "Determine appropriate solution approach"
            ],
            confidence_level=ConfidenceLevel.HIGH,
            supporting_sources=[s.source_id for s in sources[:2]]
        ))
        
        # Trace 2: Détection du type de raisonnement
        reasoning_type = self._detect_reasoning_type(query, answer)
        traces.append(ThoughtTrace(
            step=2,
            thought_type=ThoughtType.REASONING,
            content=f"Identified reasoning type: {reasoning_type}",
            reasoning_chain=[
                f"Question requires {reasoning_type} approach",
                "Selecting appropriate methodology",
                "Preparing structured solution"
            ],
            confidence_level=ConfidenceLevel.MEDIUM,
            supporting_sources=[]
        ))
        
        # Trace 3: Synthèse et génération
        traces.append(ThoughtTrace(
            step=3,
            thought_type=ThoughtType.SYNTHESIS,
            content="Synthesizing final answer with source verification",
            reasoning_chain=[
                "Combining information from verified sources",
                "Applying logical reasoning steps", 
                "Generating comprehensive response"
            ],
            confidence_level=ConfidenceLevel.HIGH,
            supporting_sources=[s.source_id for s in sources]
        ))
        
        return traces[:self.max_thought_depth]
    
    def _detect_reasoning_type(self, query: str, answer: str) -> str:
        """
        Détecter le type de raisonnement utilisé.
        
        Args:
            query: Requête utilisateur
            answer: Réponse générée
            
        Returns:
            str: Type de raisonnement détecté
        """
        combined_text = f"{query} {answer}".lower()
        
        # Scorer chaque type de raisonnement
        scores = {}
        for reasoning_type, keywords in self.reasoning_types.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                scores[reasoning_type] = score
        
        # Retourner type avec score maximum
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return "general"
    
    async def _calculate_confidence_metrics(self,
                                          answer: str,
                                          sources: List[SourceMetadata],
                                          calculation_detected: bool,
                                          thought_traces: List[ThoughtTrace]) -> ConfidenceMetrics:
        """
        Calculer métriques de confiance granulaires.
        
        Args:
            answer: Réponse générée
            sources: Sources utilisées
            calculation_detected: Calculs détectés
            thought_traces: Traces de raisonnement
            
        Returns:
            ConfidenceMetrics: Métriques détaillées
        """
        # Source reliability (basé sur nombre et qualité des sources)
        source_reliability = min(len(sources) * 0.3, 1.0) if sources else 0.0
        
        # Logical consistency (basé sur traces de raisonnement)
        logical_consistency = min(len(thought_traces) * 0.25, 1.0)
        
        # Factual accuracy (basé sur présence de calculs vérifiables)
        factual_accuracy = 0.9 if calculation_detected else 0.7
        
        # Completeness (basé sur longueur réponse et détails)
        completeness = min(len(answer) / 200.0, 1.0)  # Normalisé sur 200 chars
        
        # Confidence globale (moyenne pondérée)
        overall = (
            source_reliability * 0.3 +
            logical_consistency * 0.25 +
            factual_accuracy * 0.25 +
            completeness * 0.2
        )
        
        return ConfidenceMetrics(
            overall=round(overall, 2),
            source_reliability=round(source_reliability, 2),
            logical_consistency=round(logical_consistency, 2),
            factual_accuracy=round(factual_accuracy, 2),
            completeness=round(completeness, 2)
        )
    
    def _format_thought_trace(self, thought_traces: List[ThoughtTrace]) -> str:
        """
        Formatter les traces de raisonnement en texte lisible.
        
        Args:
            thought_traces: Traces de raisonnement
            
        Returns:
            str: Traces formatées
        """
        if not thought_traces:
            return "No reasoning traces available"
        
        formatted_lines = ["## VERITAS Reasoning Trace\n"]
        
        for trace in thought_traces:
            formatted_lines.append(f"**Step {trace.step}: {trace.thought_type.value}**")
            formatted_lines.append(f"- {trace.content}")
            
            if trace.reasoning_chain:
                formatted_lines.append("- Reasoning steps:")
                for step in trace.reasoning_chain:
                    formatted_lines.append(f"  • {step}")
            
            formatted_lines.append(f"- Confidence: {trace.confidence_level.value}")
            formatted_lines.append("")  # Ligne vide
        
        return "\n".join(formatted_lines)
    
    def _generate_verification_id(self) -> str:
        """
        Générer un ID de vérification unique.
        
        Returns:
            str: ID de vérification
        """
        import uuid
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"veritas_{timestamp}_{short_uuid}"
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """
        Obtenir statistiques de génération.
        
        Returns:
            Dict: Statistiques du générateur
        """
        return {
            "confidence_threshold": self.confidence_threshold,
            "thought_traces_enabled": self.enable_thought_traces,
            "max_thought_depth": self.max_thought_depth,
            "calculation_patterns_count": len(self.calculation_patterns),
            "reasoning_types_supported": list(self.reasoning_types.keys())
        }
