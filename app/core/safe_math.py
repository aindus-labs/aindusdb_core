"""
🔐 SafeMathEvaluator - Parser Mathématique Sécurisé
Remplacement sécurisé de eval() pour les calculs mathématiques

Créé : 20 janvier 2026
Objectif : Phase 2.1 - Éliminer la vulnérabilité d'injection de code
"""

import ast
import operator
import math
from typing import Union, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class SafeMathEvaluator:
    """
    Évaluateur d'expressions mathématiques sécurisé utilisant AST.
    
    Remplace eval() dangereux par parsing et validation strictes.
    Supporte uniquement les opérations mathématiques sûres.
    """
    
    # Opérateurs autorisés
    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    # Fonctions mathématiques autorisées
    ALLOWED_FUNCTIONS = {
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'asin': math.asin,
        'acos': math.acos,
        'atan': math.atan,
        'sinh': math.sinh,
        'cosh': math.cosh,
        'tanh': math.tanh,
        'sqrt': math.sqrt,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'abs': abs,
        'round': round,
        'ceil': math.ceil,
        'floor': math.floor,
        'factorial': math.factorial,
        'degrees': math.degrees,
        'radians': math.radians,
        'hypot': math.hypot,
        'atan2': math.atan2,
        'pow': math.pow,
        'fsum': math.fsum,
        'gcd': math.gcd,
        'lcm': math.lcm,
        'isnan': math.isnan,
        'isfinite': math.isfinite,
        'isinf': math.isinf,
    }
    
    # Constantes autorisées
    ALLOWED_CONSTANTS = {
        'pi': math.pi,
        'e': math.e,
        'tau': math.tau,
        'inf': math.inf,
        'nan': math.nan,
    }
    
    def __init__(self, max_expression_length: int = 500, max_nesting_depth: int = 10):
        """
        Initialiser l'évaluateur avec limites de sécurité.
        
        Args:
            max_expression_length: Longueur maximale de l'expression
            max_nesting_depth: Profondeur maximale d'imbrication
        """
        self.max_expression_length = max_expression_length
        self.max_nesting_depth = max_nesting_depth
        self._current_depth = 0
    
    def evaluate(self, expression: str, variables: Dict[str, float] = None) -> float:
        """
        Évaluer une expression mathématique en toute sécurité.
        
        Args:
            expression: Chaîne de caractères de l'expression
            variables: Variables autorisées (ex: {"x": 10, "y": 5})
            
        Returns:
            float: Résultat de l'évaluation
            
        Raises:
            ValueError: Si l'expression contient des éléments non autorisés
            SyntaxError: Si la syntaxe est invalide
        """
        # Validation initiale
        if not expression or not isinstance(expression, str):
            raise ValueError("Expression must be a non-empty string")
        
        if len(expression) > self.max_expression_length:
            raise ValueError(f"Expression too long (max {self.max_expression_length} chars)")
        
        # Nettoyage et validation basique
        expression = expression.strip()
        
        # Vérifier les patterns dangereux
        dangerous_patterns = [
            'import', 'exec', 'eval', '__', 'open', 'file', 'input',
            'subprocess', 'os', 'sys', 'globals', 'locals', 'vars',
            'getattr', 'setattr', 'delattr', 'hasattr', 'callable',
            'type', 'isinstance', 'issubclass', 'iter', 'next',
            'repr', 'str', 'bytes', 'bytearray', 'memoryview',
            'compile', 'complex', 'bool', 'int', 'float', 'list',
            'dict', 'set', 'frozenset', 'tuple', 'range', 'enumerate',
            'zip', 'map', 'filter', 'reduce', 'lambda', 'yield',
            'class', 'def', 'return', 'if', 'else', 'elif', 'for',
            'while', 'break', 'continue', 'pass', 'try', 'except',
            'finally', 'raise', 'assert', 'del', 'global', 'nonlocal'
        ]
        
        expression_lower = expression.lower()
        for pattern in dangerous_patterns:
            if pattern in expression_lower:
                raise ValueError(f"Dangerous keyword detected: {pattern}")
        
        # Parser l'expression
        try:
            tree = ast.parse(expression, mode='eval')
        except SyntaxError as e:
            raise SyntaxError(f"Invalid syntax: {e}")
        
        # Réinitialiser la profondeur
        self._current_depth = 0
        
        # Évaluer l'AST
        try:
            result = self._eval_node(tree.body, variables or {})
        except RecursionError:
            raise ValueError("Expression too complex (max nesting depth exceeded)")
        except ZeroDivisionError:
            raise ValueError("Division by zero")
        except OverflowError:
            raise ValueError("Numeric overflow")
        except Exception as e:
            logger.error(f"Error evaluating expression: {e}")
            raise ValueError(f"Evaluation error: {e}")
        
        # Validation du résultat
        if not isinstance(result, (int, float)):
            raise ValueError("Expression must evaluate to a number")
        
        if math.isnan(result):
            raise ValueError("Result is NaN")
        
        if math.isinf(result):
            raise ValueError("Result is infinite")
        
        return result
    
    def _eval_node(self, node, variables: Dict[str, float]) -> float:
        """Évaluer un nœud AST de manière récursive."""
        self._current_depth += 1
        
        if self._current_depth > self.max_nesting_depth:
            raise ValueError("Maximum nesting depth exceeded")
        
        try:
            # Nombre
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return float(node.value)
                else:
                    raise ValueError("Only numeric constants allowed")
            
            # Variable
            elif isinstance(node, ast.Name):
                if node.id in self.ALLOWED_CONSTANTS:
                    return float(self.ALLOWED_CONSTANTS[node.id])
                elif variables and node.id in variables:
                    value = variables[node.id]
                    if not isinstance(value, (int, float)):
                        raise ValueError(f"Variable {node.id} must be numeric")
                    return float(value)
                else:
                    raise ValueError(f"Unknown variable or constant: {node.id}")
            
            # Opération binaire
            elif isinstance(node, ast.BinOp):
                left = self._eval_node(node.left, variables)
                right = self._eval_node(node.right, variables)
                
                op_type = type(node.op)
                if op_type in self.ALLOWED_OPERATORS:
                    return self.ALLOWED_OPERATORS[op_type](left, right)
                else:
                    raise ValueError(f"Operator not allowed: {op_type}")
            
            # Opération unaire
            elif isinstance(node, ast.UnaryOp):
                operand = self._eval_node(node.operand, variables)
                op_type = type(node.op)
                if op_type in self.ALLOWED_OPERATORS:
                    return self.ALLOWED_OPERATORS[op_type](operand)
                else:
                    raise ValueError(f"Unary operator not allowed: {op_type}")
            
            # Appel de fonction
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name not in self.ALLOWED_FUNCTIONS:
                        raise ValueError(f"Function not allowed: {func_name}")
                    
                    # Évaluer les arguments
                    args = [self._eval_node(arg, variables) for arg in node.args]
                    
                    # Vérifier le nombre d'arguments
                    func = self.ALLOWED_FUNCTIONS[func_name]
                    try:
                        result = func(*args)
                        return float(result)
                    except Exception as e:
                        raise ValueError(f"Error calling function {func_name}: {e}")
                else:
                    raise ValueError("Only direct function calls allowed")
            
            # Parenthèses (expression)
            elif isinstance(node, ast.Expression):
                return self._eval_node(node.body, variables)
            
            # Autres types non autorisés
            else:
                raise ValueError(f"Expression type not allowed: {type(node)}")
        
        finally:
            self._current_depth -= 1
    
    def validate_expression(self, expression: str) -> Dict[str, Any]:
        """
        Valider une expression sans l'évaluer.
        
        Returns:
            Dict avec validity, error_message, et métadonnées
        """
        try:
            # Tenter d'évaluer avec variables vides
            self.evaluate(expression, {})
            return {
                "valid": True,
                "error": None,
                "length": len(expression),
                "complexity": self._estimate_complexity(expression)
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "length": len(expression),
                "complexity": self._estimate_complexity(expression)
            }
    
    def _estimate_complexity(self, expression: str) -> str:
        """Estimer la complexité d'une expression."""
        operators = sum(expression.count(op) for op in ['+', '-', '*', '/', '**', '%'])
        functions = len([f for f in self.ALLOWED_FUNCTIONS if f in expression])
        
        if operators <= 3 and functions == 0:
            return "simple"
        elif operators <= 10 and functions <= 2:
            return "moderate"
        else:
            return "complex"

# Instance globale
safe_math = SafeMathEvaluator()

# Fonction de commodité
def safe_eval(expression: str, variables: Dict[str, float] = None) -> float:
    """Évaluer une expression en toute sécurité."""
    return safe_math.evaluate(expression, variables)
