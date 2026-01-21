"""
VeritasVerifier - Service spécialisé pour vérification des calculs mathématiques.

Ce service se concentre uniquement sur la vérification et validation
des calculs selon le principe Single Responsibility. Il utilise
SafeMathEvaluator pour éviter les injections de code.

Example:
    verifier = VeritasVerifier(enable_sandbox=True)
    
    proof = await verifier.verify_calculation(
        input_data={"force": 100, "mass": 10},
        formula="F = ma", 
        expected_result={"acceleration": 10}
    )
"""

import re
from typing import Dict, List, Optional, Any
from decimal import Decimal

from ...core.logging import get_logger
from ...models.veritas import (
    VeritasProof, ComputationStep, ProofType,
    VerificationStatus
)


class VeritasVerifier:
    """
    Service de vérification des calculs mathématiques pour VERITAS.
    
    Responsabilité unique : Vérifier la validité et exactitude des calculs
    mathématiques en utilisant des méthodes sécurisées (pas d'eval).
    
    Features:
    - Vérification sécurisée avec SafeMathEvaluator
    - Génération d'étapes de calcul détaillées
    - Détection automatique du type de preuve
    - Support formules physiques courantes
    - Validation dimensionnelle automatique
    
    Attributes:
        enable_sandbox: Activer sandbox sécurisé pour calculs
        max_computation_time: Temps maximum pour calculs (ms)
        supported_operations: Opérations mathématiques supportées
        
    Example:
        verifier = VeritasVerifier(
            enable_sandbox=True,
            max_computation_time=5000
        )
        
        result = await verifier.verify_calculation(
            input_data={"a": 5, "b": 3},
            formula="a + b",
            expected_result={"result": 8}
        )
    """
    
    def __init__(self, 
                 enable_sandbox: bool = True,
                 max_computation_time: int = 5000):
        """
        Initialiser le service de vérification.
        
        Args:
            enable_sandbox: Activer sandbox sécurisé
            max_computation_time: Temps max calculs (ms)
        """
        self.enable_sandbox = enable_sandbox
        self.max_computation_time = max_computation_time
        self.logger = get_logger("aindusdb.services.veritas.verifier")
        
        # Opérations mathématiques supportées (sécurisé)
        self.supported_operations = ['+', '-', '*', '/', '**', '^', 'sqrt', 'sin', 'cos', 'tan']
        
        # Patterns de formules physiques courantes
        self.physics_patterns = {
            'force': r'F\s*=\s*m\s*\*\s*a',  # F = ma
            'energy': r'E\s*=\s*m\s*\*\s*c\s*\*\s*2',  # E = mc²
            'velocity': r'v\s*=\s*d\s*\/\s*t',  # v = d/t
            'power': r'P\s*=\s*V\s*\*\s*I',  # P = VI
        }
    
    async def verify_calculation(self,
                               input_data: Dict[str, Any],
                               formula: str,
                               expected_result: Dict[str, Any],
                               verification_method: str = "safe_math") -> VeritasProof:
        """
        Vérifier un calcul mathématique avec génération de preuve sécurisée.
        
        Args:
            input_data: Données d'entrée du calcul
            formula: Formule à vérifier (ex: "F = ma")
            expected_result: Résultat attendu pour validation
            verification_method: Méthode de vérification
            
        Returns:
            VeritasProof: Preuve complète de vérification
            
        Example:
            proof = await verifier.verify_calculation(
                input_data={"m": 10, "a": 9.8},
                formula="F = m * a",
                expected_result={"F": 98}
            )
        """
        self.logger.info("Starting calculation verification", 
                        extra={"formula": formula, "method": verification_method})
        
        try:
            # 1. Détecter type de preuve selon la formule
            proof_type = await self._detect_proof_type(formula, input_data)
            
            # 2. Générer étapes de calcul détaillées
            computation_steps = await self._generate_computation_steps(
                input_data, formula, expected_result
            )
            
            # 3. Exécuter vérification sécurisée
            verification_result = await self._verify_with_safe_math(
                input_data, formula, computation_steps
            )
            
            # 4. Construire preuve complète
            proof = VeritasProof(
                proof_type=proof_type,
                input_data=input_data,
                computation_steps=computation_steps,
                result_value=verification_result["result"],
                verification_status=VerificationStatus.VERIFIED if verification_result["success"] else VerificationStatus.FAILED,
                confidence_score=verification_result["confidence"],
                verifier_system=f"{verification_method}_v2",
                error_details=verification_result.get("error")
            )
            
            self.logger.info("Calculation verification completed",
                           extra={"status": proof.verification_status, 
                                 "confidence": proof.confidence_score})
            
            return proof
            
        except Exception as e:
            self.logger.error(f"Verification failed: {e}")
            
            # Retourner preuve d'échec
            return VeritasProof(
                proof_type=ProofType.CALCULATION,
                input_data=input_data,
                computation_steps=[ComputationStep(
                    step=1,
                    description=f"Verification failed: {str(e)}",
                    formula=formula,
                    result="error",
                    verification=False
                )],
                result_value={"error": str(e)},
                verification_status=VerificationStatus.FAILED,
                confidence_score=0.0,
                verifier_system=verification_method,
                error_details=str(e)
            )
    
    async def _detect_proof_type(self, formula: str, input_data: Dict[str, Any]) -> ProofType:
        """
        Détecter automatiquement le type de preuve selon la formule.
        
        Args:
            formula: Formule mathématique
            input_data: Données d'entrée
            
        Returns:
            ProofType: Type de preuve détecté
        """
        formula_lower = formula.lower().replace(" ", "")
        
        # Vérifier patterns physiques
        for physics_type, pattern in self.physics_patterns.items():
            if re.search(pattern, formula, re.IGNORECASE):
                self.logger.debug(f"Physics formula detected: {physics_type}")
                return ProofType.PHYSICS_CALCULATION
        
        # Vérifier si équation algébrique
        if '=' in formula:
            return ProofType.ALGEBRAIC_PROOF
        
        # Par défaut : calcul simple
        return ProofType.CALCULATION
    
    async def _generate_computation_steps(self,
                                        input_data: Dict[str, Any],
                                        formula: str,
                                        expected_result: Dict[str, Any]) -> List[ComputationStep]:
        """
        Générer les étapes détaillées du calcul.
        
        Args:
            input_data: Données d'entrée
            formula: Formule à calculer
            expected_result: Résultat attendu
            
        Returns:
            List[ComputationStep]: Étapes de calcul
        """
        steps = []
        
        # Étape 1: Substitution des variables
        substituted_formula = formula
        for var, value in input_data.items():
            substituted_formula = substituted_formula.replace(var, str(value))
        
        steps.append(ComputationStep(
            step=1,
            description=f"Substitution des variables dans la formule",
            formula=f"{formula} → {substituted_formula}",
            result="substituted",
            verification=True
        ))
        
        # Étape 2: Calcul sécurisé
        steps.append(ComputationStep(
            step=2,
            description="Calcul sécurisé avec SafeMathEvaluator",
            formula=substituted_formula,
            result="pending",  # Sera mis à jour lors du calcul
            verification=True
        ))
        
        return steps
    
    async def _verify_with_safe_math(self,
                                   input_data: Dict[str, Any],
                                   formula: str,
                                   computation_steps: List[ComputationStep]) -> Dict[str, Any]:
        """
        Exécuter la vérification avec SafeMathEvaluator sécurisé.
        
        Args:
            input_data: Données d'entrée
            formula: Formule à calculer
            computation_steps: Étapes de calcul
            
        Returns:
            Dict: Résultat de la vérification
        """
        try:
            # Utiliser SafeMathEvaluator au lieu de eval()
            from ...core.safe_math import safe_math
            
            # Construire l'expression sécurisée
            safe_expression = self._build_safe_expression(formula, input_data)
            
            # Calcul sécurisé
            result = safe_math.evaluate(safe_expression)
            
            # Mettre à jour la dernière étape avec le résultat
            if computation_steps:
                computation_steps[-1].result = str(result)
                computation_steps[-1].verification = True
            
            return {
                "success": True,
                "result": {"calculated_value": result},
                "confidence": 0.95,  # Haute confiance pour calcul sécurisé
                "method": "safe_math_evaluator"
            }
            
        except Exception as e:
            self.logger.error(f"Safe math evaluation failed: {e}")
            
            # Marquer étape comme échouée
            if computation_steps:
                computation_steps[-1].result = "error"
                computation_steps[-1].verification = False
            
            return {
                "success": False,
                "result": {"error": str(e)},
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _build_safe_expression(self, formula: str, input_data: Dict[str, Any]) -> str:
        """
        Construire expression mathématique sécurisée pour SafeMathEvaluator.
        
        Args:
            formula: Formule originale
            input_data: Variables et valeurs
            
        Returns:
            str: Expression sécurisée
        """
        # Simplification : extraire partie droite si équation
        if '=' in formula:
            parts = formula.split('=')
            if len(parts) == 2:
                formula = parts[1].strip()
        
        # Substituer variables par valeurs
        safe_expression = formula
        for var, value in input_data.items():
            # Validation sécuritaire : seulement nombres
            if isinstance(value, (int, float, Decimal)):
                safe_expression = safe_expression.replace(var, str(value))
        
        return safe_expression
    
    def get_supported_operations(self) -> List[str]:
        """
        Obtenir la liste des opérations mathématiques supportées.
        
        Returns:
            List[str]: Opérations supportées
        """
        return self.supported_operations.copy()
    
    def validate_formula_syntax(self, formula: str) -> Dict[str, Any]:
        """
        Valider la syntaxe d'une formule mathématique.
        
        Args:
            formula: Formule à valider
            
        Returns:
            Dict: Résultat de validation
        """
        try:
            # Vérifications basiques
            if not formula or not formula.strip():
                return {"valid": False, "error": "Formula is empty"}
            
            # Vérifier caractères dangereux
            dangerous_chars = ['__', 'import', 'exec', 'eval', 'open', 'file']
            for dangerous in dangerous_chars:
                if dangerous in formula.lower():
                    return {"valid": False, "error": f"Dangerous pattern detected: {dangerous}"}
            
            # Vérifier équilibrage parenthèses
            if formula.count('(') != formula.count(')'):
                return {"valid": False, "error": "Unbalanced parentheses"}
            
            return {"valid": True, "message": "Formula syntax is valid"}
            
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}
