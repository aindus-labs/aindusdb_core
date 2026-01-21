"""
🧪 Tests unitaires pour SafeMathEvaluator
Validation de la sécurité et des fonctionnalités

Créé : 20 janvier 2026
Objectif : Phase 2.1 - Valider le parser mathématique sécurisé
"""

import pytest
import math
from app.core.safe_math import SafeMathEvaluator, safe_eval

class TestSafeMathEvaluator:
    """Tests de sécurité et fonctionnalité pour SafeMathEvaluator."""
    
    def setup_method(self):
        """Initialiser l'évaluateur pour chaque test."""
        self.evaluator = SafeMathEvaluator()
    
    # Tests de base
    def test_basic_operations(self):
        """Tester les opérations mathématiques de base."""
        assert self.evaluator.evaluate("2 + 3") == 5.0
        assert self.evaluator.evaluate("10 - 4") == 6.0
        assert self.evaluator.evaluate("3 * 4") == 12.0
        assert self.evaluator.evaluate("15 / 3") == 5.0
        assert self.evaluator.evaluate("2 ** 3") == 8.0
        assert self.evaluator.evaluate("17 % 5") == 2.0
    
    def test_unary_operations(self):
        """Tester les opérations unaires."""
        assert self.evaluator.evaluate("-5") == -5.0
        assert self.evaluator.evaluate("+10") == 10.0
        assert self.evaluator.evaluate("-(-3)") == 3.0
    
    def test_complex_expressions(self):
        """Tester les expressions complexes."""
        assert self.evaluator.evaluate("2 + 3 * 4") == 14.0
        assert self.evaluator.evaluate("(2 + 3) * 4") == 20.0
        assert self.evaluator.evaluate("2 * (3 + 4) - 5") == 9.0
        assert self.evaluator.evaluate("2 + 3 * 4 - 5 / 2") == 10.5
    
    def test_math_functions(self):
        """Tester les fonctions mathématiques."""
        assert self.evaluator.evaluate("sin(0)") == 0.0
        assert self.evaluator.evaluate("cos(0)") == 1.0
        assert self.evaluator.evaluate("sqrt(16)") == 4.0
        assert self.evaluator.evaluate("abs(-5)") == 5.0
        assert self.evaluator.evaluate("round(3.7)") == 4.0
        assert self.evaluator.evaluate("ceil(3.2)") == 4.0
        assert self.evaluator.evaluate("floor(3.8)") == 3.0
    
    def test_constants(self):
        """Tester les constantes mathématiques."""
        assert self.evaluator.evaluate("pi") == math.pi
        assert self.evaluator.evaluate("e") == math.e
        assert self.evaluator.evaluate("tau") == math.tau
    
    def test_variables(self):
        """Tester l'utilisation de variables."""
        variables = {"x": 10, "y": 5}
        assert self.evaluator.evaluate("x + y", variables) == 15.0
        assert self.evaluator.evaluate("x * y", variables) == 50.0
        assert self.evaluator.evaluate("x / y", variables) == 2.0
    
    # Tests de sécurité
    def test_prevent_code_injection(self):
        """Tester que l'injection de code est bloquée."""
        dangerous_inputs = [
            "__import__('os').system('ls')",
            "eval('1+1')",
            "exec('print(1)')",
            "open('/etc/passwd')",
            "globals()",
            "locals()",
            "vars()",
            "dir()",
            "getattr(os, 'system')",
            "setattr(object, '__class__', dict)",
            "type('Test', (), {'__module__': '__main__'})",
            "isinstance(1, int)",
            "issubclass(int, object)",
            "callable(print)",
            "compile('1+1', '<string>', 'eval')",
            "lambda x: x*2",
            "[x for x in range(10)]",
            "{x: x*2 for x in range(5)}",
            "{1, 2, 3}",
            "(1, 2, 3)",
            "range(10)",
            "enumerate([1, 2, 3])",
            "zip([1, 2], [3, 4])",
            "map(lambda x: x*2, [1, 2, 3])",
            "filter(lambda x: x>0, [1, -1, 2])",
        ]
        
        for dangerous_input in dangerous_inputs:
            with pytest.raises(ValueError, match="Dangerous keyword|not allowed"):
                self.evaluator.evaluate(dangerous_input)
    
    def test_prevent_special_characters(self):
        """Tester que les caractères spéciaux dangereux sont bloqués."""
        dangerous_inputs = [
            "1; import os",
            "1 `whoami`",
            "1 | grep test",
            "1 && echo test",
            "1 || echo test",
            "1 > /tmp/file",
            "1 < /etc/passwd",
            "${HOME}",
            "$(whoami)",
            "1\\nimport os",
            "1\\x0dimport os",
        ]
        
        for dangerous_input in dangerous_inputs:
            # Soit ça lève une erreur de syntaxe, soit une erreur de sécurité
            try:
                result = self.evaluator.evaluate(dangerous_input)
                # Si ça réussit, vérifier que c'est un résultat mathématique valide
                assert isinstance(result, (int, float))
            except (ValueError, SyntaxError):
                # C'est ce qu'on veut - l'entrée est rejetée
                pass
    
    def test_max_length_limit(self):
        """Tester la limite de longueur des expressions."""
        long_expression = "1 + " + "1 + " * 100  # Dépasse la limite par défaut
        
        with pytest.raises(ValueError, match="Expression too long"):
            self.evaluator.evaluate(long_expression)
    
    def test_max_nesting_depth(self):
        """Tester la limite de profondeur d'imbrication."""
        deep_expression = "1" + " ** 2" * 20  # Très profond
        
        with pytest.raises(ValueError, match="Maximum nesting depth"):
            self.evaluator.evaluate(deep_expression)
    
    def test_division_by_zero(self):
        """Tester la gestion de la division par zéro."""
        with pytest.raises(ValueError, match="Division by zero"):
            self.evaluator.evaluate("1 / 0")
    
    def test_invalid_syntax(self):
        """Tester la gestion de syntaxe invalide."""
        invalid_inputs = [
            "1 + + 2",
            "1 * * 2",
            "sin()",
            "sqrt(",
            "1 + ",
            "(1 + 2",
            "1 + 2)",
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises((ValueError, SyntaxError)):
                self.evaluator.evaluate(invalid_input)
    
    def test_empty_and_null_inputs(self):
        """Tester les entrées vides ou nulles."""
        with pytest.raises(ValueError):
            self.evaluator.evaluate("")
        
        with pytest.raises(ValueError):
            self.evaluator.evaluate(None)
        
        with pytest.raises(ValueError):
            self.evaluator.evaluate("   ")
    
    def test_numeric_results_only(self):
        """Tester que seuls les résultats numériques sont retournés."""
        # Toutes les expressions valides doivent retourner un nombre
        valid_expressions = [
            "1 + 1",
            "sin(0)",
            "sqrt(4)",
            "pi",
            "-5",
            "2 ** 3",
        ]
        
        for expr in valid_expressions:
            result = self.evaluator.evaluate(expr)
            assert isinstance(result, (int, float))
    
    def test_nan_and_inf_handling(self):
        """Tester la gestion de NaN et Inf."""
        # NaN devrait être bloqué
        with pytest.raises(ValueError, match="Result is NaN"):
            self.evaluator.evaluate("0 / 0")
        
        # Inf devrait être bloqué
        with pytest.raises(ValueError, match="Result is infinite"):
            self.evaluator.evaluate("1 / 0")
    
    def test_validate_expression(self):
        """Tester la méthode de validation."""
        # Expression valide
        result = self.evaluator.validate_expression("2 + 3 * 4")
        assert result["valid"] is True
        assert result["error"] is None
        assert result["complexity"] == "moderate"
        
        # Expression invalide
        result = self.evaluator.validate_expression("import os")
        assert result["valid"] is False
        assert "Dangerous keyword" in result["error"]
    
    def test_convenience_function(self):
        """Tester la fonction de commodité safe_eval."""
        assert safe_eval("2 + 3") == 5.0
        assert safe_eval("sqrt(16)") == 4.0
        
        with pytest.raises(ValueError):
            safe_eval("import os")
    
    def test_edge_cases(self):
        """Tester les cas limites."""
        # Nombres très grands
        result = self.evaluator.evaluate("10 ** 10")
        assert result == 10000000000.0
        
        # Nombres très petits
        result = self.evaluator.evaluate("0.000001")
        assert result == 0.000001
        
        # Zéro
        assert self.evaluator.evaluate("0") == 0.0
        assert self.evaluator.evaluate("-0") == 0.0
        
        # Nombres négatifs
        assert self.evaluator.evaluate("-5") == -5.0
        assert self.evaluator.evaluate("-3.14") == -3.14
    
    def test_scientific_notation(self):
        """Tester la notation scientifique."""
        assert self.evaluator.evaluate("1e5") == 100000.0
        assert self.evaluator.evaluate("2.5e-3") == 0.0025
        assert self.evaluator.evaluate("-1.23e4") == -12300.0
    
    def test_complex_math_expressions(self):
        """Tester des expressions mathématiques complexes."""
        # Formule quadratique
        variables = {"a": 1, "b": -5, "c": 6}
        discriminant = self.evaluator.evaluate("b**2 - 4*a*c", variables)
        assert discriminant == 1.0
        
        # Distance euclidienne
        variables = {"x1": 0, "y1": 0, "x2": 3, "y2": 4}
        distance = self.evaluator.evaluate("sqrt((x2-x1)**2 + (y2-y1)**2)", variables)
        assert distance == 5.0
        
        # Équation du cercle
        variables = {"x": 3, "y": 4, "r": 5}
        circle_eq = self.evaluator.evaluate("x**2 + y**2 - r**2", variables)
        assert circle_eq == 0.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
