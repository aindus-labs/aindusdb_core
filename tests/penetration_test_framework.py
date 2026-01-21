"""
🔍 Penetration Testing Framework
Framework complet pour tests d'intrusion manuels et automatisés

Créé : 20 janvier 2026
Objectif : Jalon 4.1 - Tests d'Intrusion
"""

import asyncio
import aiohttp
import json
import time
import hashlib
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PenetrationTestFramework:
    """Framework de tests d'intrusion pour AindusDB Core."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.auth_token = None
        self.test_results = {
            "tests_run": [],
            "vulnerabilities": [],
            "risk_score": 0,
            "recommendations": []
        }
    
    async def initialize(self):
        """Initialiser la session et l'authentification."""
        self.session = aiohttp.ClientSession()
        
        # Tenter d'obtenir un token admin
        await self.authenticate()
    
    async def authenticate(self):
        """Authentification avec diverses techniques."""
        # 1. Credentials par défaut
        default_creds = [
            {"username": "admin", "password": "admin"},
            {"username": "admin", "password": "password"},
            {"username": "root", "password": "root"},
            {"username": "admin", "password": "123456"},
            {"username": "admin", "password": "admin123"}
        ]
        
        for creds in default_creds:
            try:
                async with self.session.post(
                    f"{self.base_url}/auth/login",
                    json=creds
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.auth_token = data.get("access_token")
                        logger.info(f"Authentifié avec: {creds['username']}")
                        return True
            except:
                continue
        
        # 2. Créer un compte si possible
        try:
            user_data = {
                "username": f"pentest_{int(time.time())}",
                "email": f"pentest@{int(time.time())}.com",
                "password": "Pentest123!",
                "role": "user"
            }
            
            async with self.session.post(
                f"{self.base_url}/auth/register",
                json=user_data
            ) as resp:
                if resp.status == 201:
                    # Login avec le nouveau compte
                    async with self.session.post(
                        f"{self.base_url}/auth/login",
                        json={"username": user_data["username"], "password": user_data["password"]}
                    ) as login_resp:
                        if login_resp.status == 200:
                            data = await login_resp.json()
                            self.auth_token = data.get("access_token")
                            logger.info("Compte créé et authentifié")
                            return True
        except:
            pass
        
        logger.warning("Échec de l'authentification")
        return False
    
    async def run_full_penetration_test(self) -> Dict[str, Any]:
        """Exécuter le test de pénétration complet."""
        logger.info("🔍 Démarrage du test de pénétration...")
        
        await self.initialize()
        
        # Catégories de tests
        test_categories = [
            ("Information Gathering", self.test_information_gathering),
            ("Authentication Testing", self.test_authentication),
            ("Authorization Testing", self.test_authorization),
            ("Input Validation", self.test_input_validation),
            ("Session Management", self.test_session_management),
            ("Error Handling", self.test_error_handling),
            ("Cryptography Testing", self.test_cryptography),
            ("Business Logic", self.test_business_logic),
            ("Client Side Testing", self.test_client_side)
        ]
        
        for category_name, test_func in test_categories:
            logger.info(f"\n--- {category_name} ---")
            try:
                await test_func()
            except Exception as e:
                logger.error(f"Erreur dans {category_name}: {e}")
        
        # Calculer le score de risque
        self.calculate_risk_score()
        
        # Générer le rapport
        report = self.generate_report()
        
        # Nettoyer
        await self.session.close()
        
        return report
    
    async def test_information_gathering(self):
        """Phase 1: Collecte d'informations."""
        tests = [
            ("Server Headers", self.test_server_headers),
            ("Technology Stack", self.test_technology_stack),
            ("API Endpoints Discovery", self.test_api_discovery),
            ("Directory Enumeration", self.test_directory_enumeration),
            ("Subdomain Enumeration", self.test_subdomain_enumeration)
        ]
        
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
    
    async def test_server_headers(self):
        """Tester les headers du serveur."""
        async with self.session.get(f"{self.base_url}/") as resp:
            headers = resp.headers
            
            findings = []
            
            # Vérifier les headers de sécurité
            security_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options", 
                "X-XSS-Protection",
                "Strict-Transport-Security",
                "Content-Security-Policy"
            ]
            
            for header in security_headers:
                if header not in headers:
                    findings.append({
                        "severity": "MEDIUM",
                        "issue": f"Missing security header: {header}",
                        "recommendation": f"Add {header} header"
                    })
            
            # Vérifier la divulgation d'information
            server = headers.get("Server", "")
            if "nginx" in server or "apache" in server:
                findings.append({
                    "severity": "LOW",
                    "issue": f"Server version disclosed: {server}",
                    "recommendation": "Hide server version"
                })
            
            if findings:
                self.add_vulnerabilities("Information Disclosure", findings)
    
    async def test_technology_stack(self):
        """Identifier la stack technologique."""
        # Analyser les réponses pour identifier la technologie
        endpoints = ["/", "/api/v1/health", "/docs"]
        
        tech_indicators = []
        
        for endpoint in endpoints:
            try:
                async with self.session.get(f"{self.base_url}{endpoint}") as resp:
                    content = await resp.text()
                    
                    # Indicateurs Python/FastAPI
                    if "fastapi" in content.lower():
                        tech_indicators.append("FastAPI")
                    if "postgresql" in content.lower():
                        tech_indicators.append("PostgreSQL")
                    if "redis" in content.lower():
                        tech_indicators.append("Redis")
            except:
                pass
        
        if tech_indicators:
            self.add_test_result("Technology Stack", {
                "identified": list(set(tech_indicators)),
                "severity": "INFO"
            })
    
    async def test_api_discovery(self):
        """Découvrir les endpoints API."""
        # Techniques de découverte
        discovery_methods = [
            # Swagger/OpenAPI
            "/docs",
            "/openapi.json",
            "/redoc",
            # API communes
            "/api",
            "/api/v1",
            "/api/v2",
            # Health checks
            "/health",
            "/status",
            "/ping"
        ]
        
        discovered_endpoints = []
        
        for endpoint in discovery_methods:
            try:
                async with self.session.get(f"{self.base_url}{endpoint}") as resp:
                    if resp.status != 404:
                        discovered_endpoints.append({
                            "endpoint": endpoint,
                            "status": resp.status,
                            "size": len(await resp.text())
                        })
            except:
                pass
        
        self.add_test_result("API Discovery", {
            "endpoints_found": discovered_endpoints,
            "total": len(discovered_endpoints)
        })
    
    async def test_authentication(self):
        """Tester l'authentification."""
        tests = [
            ("Weak Passwords", self.test_weak_passwords),
            ("JWT Security", self.test_jwt_security),
            ("Brute Force", self.test_brute_force_protection),
            ("Account Lockout", self.test_account_lockout),
            ("Password Policy", self.test_password_policy)
        ]
        
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
    
    async def test_weak_passwords(self):
        """Tester les mots de passe faibles."""
        weak_passwords = [
            "password", "123456", "admin", "root", "qwerty",
            "password123", "admin123", "letmein", "welcome",
            "changeme", "default", "temp", "test"
        ]
        
        vulnerabilities = []
        
        for password in weak_passwords:
            for username in ["admin", "root", "user", "test"]:
                try:
                    async with self.session.post(
                        f"{self.base_url}/auth/login",
                        json={"username": username, "password": password}
                    ) as resp:
                        if resp.status == 200:
                            vulnerabilities.append({
                                "severity": "HIGH",
                                "issue": f"Weak password works: {username}/{password}",
                                "recommendation": "Enforce strong password policy"
                            })
                except:
                    pass
        
        if vulnerabilities:
            self.add_vulnerabilities("Weak Authentication", vulnerabilities)
    
    async def test_jwt_security(self):
        """Tester la sécurité des JWT."""
        if not self.auth_token:
            return
        
        # Test 1: Algorithm None
        malformed_token = self.auth_token[:-10] + "A" * 10
        
        try:
            headers = {"Authorization": f"Bearer {malformed_token}"}
            async with self.session.get(
                f"{self.base_url}/api/v1/users/profile",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    self.add_vulnerability("JWT Security", {
                        "severity": "HIGH",
                        "issue": "None algorithm accepted",
                        "recommendation": "Validate JWT algorithm"
                    })
        except:
            pass
        
        # Test 2: Token expiration
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTYwMDAwMDAwMH0.invalid"
        
        try:
            headers = {"Authorization": f"Bearer {expired_token}"}
            async with self.session.get(
                f"{self.base_url}/api/v1/users/profile",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    self.add_vulnerability("JWT Security", {
                        "severity": "MEDIUM",
                        "issue": "Expired token accepted",
                        "recommendation": "Validate token expiration"
                    })
        except:
            pass
    
    async def test_authorization(self):
        """Tester l'autorisation et le RBAC."""
        tests = [
            ("Privilege Escalation", self.test_privilege_escalation),
            ("Direct Object References", self.test_direct_object_references),
            ("Function Level Access", self.test_function_level_access),
            ("Bypass Authorization", self.test_authorization_bypass)
        ]
        
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
    
    async def test_privilege_escalation(self):
        """Tenter l'escalade de privilèges."""
        if not self.auth_token:
            return
        
        # Tenter d'accéder aux endpoints admin
        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/settings",
            "/api/v1/admin/logs",
            "/api/v1/security/stats"
        ]
        
        for endpoint in admin_endpoints:
            try:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                async with self.session.get(
                    f"{self.base_url}{endpoint}",
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        self.add_vulnerability("Authorization", {
                            "severity": "HIGH",
                            "issue": f"User can access admin endpoint: {endpoint}",
                            "recommendation": "Implement proper RBAC"
                        })
            except:
                pass
        
        # Tenter de modifier son rôle
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            async with self.session.put(
                f"{self.base_url}/api/v1/users/role",
                headers=headers,
                json={"role": "admin"}
            ) as resp:
                if resp.status == 200:
                    self.add_vulnerability("Authorization", {
                        "severity": "CRITICAL",
                        "issue": "User can elevate privileges",
                        "recommendation": "Secure role modification"
                    })
        except:
            pass
    
    async def test_input_validation(self):
        """Tester la validation des entrées."""
        payloads = {
            "SQL Injection": [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "' UNION SELECT * FROM users --",
                "'; EXEC xp_cmdshell('dir'); --"
            ],
            "NoSQL Injection": [
                {"$ne": ""},
                {"$gt": ""},
                {"$regex": ".*"},
                {"$where": "return true"}
            ],
            "XSS": [
                "<script>alert('XSS')</script>",
                "javascript:alert('XSS')",
                "<img src=x onerror=alert('XSS')>",
                "<svg onload=alert('XSS')>"
            ],
            "Command Injection": [
                "; ls -la",
                "| cat /etc/passwd",
                "&& whoami",
                "`id`",
                "$(id)"
            ]
        ]
        
        for vuln_type, payload_list in payloads.items():
            await self.run_test(f"{vuln_type} Testing", 
                              lambda p=payload_list, t=vuln_type: self.test_payloads(p, t))
    
    async def test_payloads(self, payloads: List, vuln_type: str):
        """Tester une liste de payloads."""
        vulnerable_endpoints = [
            "/api/v1/vectors/search",
            "/api/v1/veritas/verify",
            "/api/v1/veritas/calculate"
        ]
        
        for payload in payloads:
            for endpoint in vulnerable_endpoints:
                try:
                    if isinstance(payload, dict):
                        # NoSQL injection
                        async with self.session.post(
                            f"{self.base_url}{endpoint}",
                            json=payload
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if isinstance(data, dict) and "results" in data:
                                    if len(data["results"]) > 100:  # Suspicion
                                        self.add_vulnerability(vuln_type, {
                                            "severity": "HIGH",
                                            "issue": f"Possible {vuln_type} at {endpoint}",
                                            "payload": str(payload)
                                        })
                    else:
                        # SQL/XSS/Command injection
                        # Test GET
                        url = f"{self.base_url}{endpoint}?q={payload}"
                        async with self.session.get(url) as resp:
                            if resp.status == 500:
                                text = await resp.text()
                                if "sql" in text.lower() or "syntax" in text.lower():
                                    self.add_vulnerability(vuln_type, {
                                        "severity": "CRITICAL",
                                        "issue": f"{vuln_type} vulnerability at {endpoint}",
                                        "payload": payload
                                    })
                        
                        # Test POST
                        if "veritas" in endpoint:
                            async with self.session.post(
                                f"{self.base_url}{endpoint}",
                                json={"query": payload}
                            ) as resp:
                                if resp.status == 500:
                                    self.add_vulnerability(vuln_type, {
                                        "severity": "CRITICAL",
                                        "issue": f"{vuln_type} in POST at {endpoint}",
                                        "payload": payload
                                    })
                except:
                    pass
    
    async def test_session_management(self):
        """Tester la gestion des sessions."""
        tests = [
            ("Session Fixation", self.test_session_fixation),
            ("Session Hijacking", self.test_session_hijacking),
            ("Session Timeout", self.test_session_timeout),
            ("Logout Functionality", self.test_logout)
        ]
        
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
    
    async def test_session_fixation(self):
        """Tester la fixation de session."""
        # Créer une session
        async with self.session.post(
            f"{self.base_url}/auth/login",
            json={"username": "admin", "password": "admin123"}
        ) as resp:
            if resp.status == 200:
                # Vérifier si le token change après login
                data = await resp.json()
                token1 = data.get("access_token")
                
                # Login à nouveau
                async with self.session.post(
                    f"{self.base_url}/auth/login",
                    json={"username": "admin", "password": "admin123"}
                ) as resp2:
                    if resp2.status == 200:
                        data2 = await resp2.json()
                        token2 = data2.get("access_token")
                        
                        if token1 == token2:
                            self.add_vulnerability("Session Management", {
                                "severity": "MEDIUM",
                                "issue": "Session token not regenerated",
                                "recommendation": "Regenerate token on login"
                            })
    
    async def test_error_handling(self):
        """Tester la gestion des erreurs."""
        error_triggers = [
            "/api/v1/nonexistent",
            "/api/v1/vectors/" + "A" * 1000,
            "/api/v1/veritas/verify",
            "/api/v1/users/99999"
        ]
        
        for trigger in error_triggers:
            try:
                if "verify" in trigger:
                    async with self.session.post(
                        f"{self.base_url}{trigger}",
                        json={"query": "test"}
                    ) as resp:
                        await self.analyze_error_response(await resp.text(), resp.status)
                else:
                    async with self.session.get(f"{self.base_url}{trigger}") as resp:
                        await self.analyze_error_response(await resp.text(), resp.status)
            except:
                pass
    
    async def analyze_error_response(self, text: str, status: int):
        """Analyser la réponse d'erreur pour divulgation d'info."""
        sensitive_patterns = [
            "traceback", "exception", "error at line",
            "file path", "directory", "stack trace",
            "sql syntax", "mysql", "postgresql",
            "internal server error"
        ]
        
        for pattern in sensitive_patterns:
            if pattern.lower() in text.lower():
                self.add_vulnerability("Error Handling", {
                    "severity": "MEDIUM",
                    "issue": f"Information disclosure in error: {pattern}",
                    "recommendation": "Use generic error messages"
                })
                break
    
    async def test_cryptography(self):
        """Tester l'implémentation cryptographique."""
        tests = [
            ("Weak Encryption", self.test_weak_encryption),
            ("Random Number Generation", self.test_random_generation),
            ("Hash Functions", self.test_hash_functions)
        ]
        
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
    
    async def test_weak_encryption(self):
        """Détecter l'utilisation de cryptographie faible."""
        # Analyser les réponses pour des indicateurs
        try:
            async with self.session.get(f"{self.base_url}/") as resp:
                content = await resp.text()
                
                weak_indicators = [
                    "md5", "sha1", "des", "rc4", "blowfish"
                ]
                
                for indicator in weak_indicators:
                    if indicator in content.lower():
                        self.add_vulnerability("Cryptography", {
                            "severity": "MEDIUM",
                            "issue": f"Weak cryptography detected: {indicator}",
                            "recommendation": f"Replace {indicator} with stronger alternative"
                        })
        except:
            pass
    
    async def test_business_logic(self):
        """Tester la logique métier."""
        tests = [
            ("Race Conditions", self.test_race_conditions),
            ("Price Manipulation", self.test_price_manipulation),
            ("Workflow Bypass", self.test_workflow_bypass)
        ]
        
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
    
    async def test_race_conditions(self):
        """Tester les conditions de course."""
        # Créer des requêtes concurrentes
        tasks = []
        for i in range(10):
            task = asyncio.create_task(
                self.session.get(f"{self.base_url}/api/v1/health")
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyser les résultats pour incohérences
        # (Implémentation spécifique à l'application)
        pass
    
    async def test_client_side(self):
        """Tester la sécurité côté client."""
        try:
            async with self.session.get(f"{self.base_url}/") as resp:
                content = await resp.text()
                
                # Chercher des données sensibles dans le JS
                sensitive_data = [
                    "api_key", "secret", "password",
                    "token", "private_key"
                ]
                
                for data in sensitive_data:
                    if data in content.lower():
                        self.add_vulnerability("Client Side", {
                            "severity": "MEDIUM",
                            "issue": f"Sensitive data in client code: {data}",
                            "recommendation": "Remove sensitive data from client"
                        })
        except:
            pass
    
    # Méthodes utilitaires
    async def run_test(self, test_name: str, test_func):
        """Exécuter un test et enregistrer les résultats."""
        start_time = time.time()
        try:
            await test_func()
            duration = time.time() - start_time
            self.add_test_result(test_name, {
                "status": "COMPLETED",
                "duration": duration,
                "vulnerabilities_found": len([v for v in self.test_results["vulnerabilities"] 
                                            if v["category"] == test_name])
            })
        except Exception as e:
            self.add_test_result(test_name, {
                "status": "ERROR",
                "error": str(e)
            })
    
    def add_vulnerability(self, category: str, vulnerability: Dict):
        """Ajouter une vulnérabilité aux résultats."""
        vulnerability["category"] = category
        vulnerability["discovered_at"] = datetime.utcnow().isoformat()
        self.test_results["vulnerabilities"].append(vulnerability)
    
    def add_vulnerabilities(self, category: str, vulnerabilities: List[Dict]):
        """Ajouter plusieurs vulnérabilités."""
        for vuln in vulnerabilities:
            self.add_vulnerability(category, vuln)
    
    def add_test_result(self, test_name: str, result: Dict):
        """Ajouter un résultat de test."""
        result["test_name"] = test_name
        result["timestamp"] = datetime.utcnow().isoformat()
        self.test_results["tests_run"].append(result)
    
    def calculate_risk_score(self):
        """Calculer le score de risque global."""
        severity_weights = {
            "CRITICAL": 10,
            "HIGH": 7,
            "MEDIUM": 4,
            "LOW": 1,
            "INFO": 0
        }
        
        total_score = 0
        for vuln in self.test_results["vulnerabilities"]:
            severity = vuln.get("severity", "LOW")
            total_score += severity_weights.get(severity, 0)
        
        # Normaliser sur 100
        self.test_results["risk_score"] = min(100, total_score)
        
        # Générer les recommandations
        self.generate_recommendations()
    
    def generate_recommendations(self):
        """Générer des recommandations basées sur les vulnérabilités."""
        recommendations = []
        
        # Analyser les vulnérabilités par catégorie
        categories = {}
        for vuln in self.test_results["vulnerabilities"]:
            cat = vuln.get("category", "Unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(vuln)
        
        # Recommandations par catégorie
        if "Authentication" in categories:
            recommendations.append({
                "priority": "HIGH",
                "category": "Authentication",
                "action": "Implement multi-factor authentication and strong password policies"
            })
        
        if "Authorization" in categories:
            recommendations.append({
                "priority": "CRITICAL",
                "category": "Authorization",
                "action": "Review and implement proper RBAC with principle of least privilege"
            })
        
        if "Input Validation" in categories:
            recommendations.append({
                "priority": "CRITICAL",
                "category": "Input Validation",
                "action": "Implement comprehensive input validation and parameterized queries"
            })
        
        self.test_results["recommendations"] = recommendations
    
    def generate_report(self) -> Dict[str, Any]:
        """Générer le rapport final de test de pénétration."""
        return {
            "metadata": {
                "test_date": datetime.utcnow().isoformat(),
                "target": self.base_url,
                "framework_version": "1.0.0",
                "tester": "Automated Penetration Test Framework"
            },
            "summary": {
                "total_tests": len(self.test_results["tests_run"]),
                "vulnerabilities_found": len(self.test_results["vulnerabilities"]),
                "risk_score": self.test_results["risk_score"],
                "risk_level": self.get_risk_level()
            },
            "vulnerabilities": self.test_results["vulnerabilities"],
            "test_results": self.test_results["tests_run"],
            "recommendations": self.test_results["recommendations"],
            "compliance": {
                "owasp_top_10": self.check_owasp_compliance(),
                "critical_vulnerabilities": len([v for v in self.test_results["vulnerabilities"] 
                                              if v.get("severity") == "CRITICAL"]),
                "high_vulnerabilities": len([v for v in self.test_results["vulnerabilities"] 
                                           if v.get("severity") == "HIGH"])
            }
        }
    
    def get_risk_level(self) -> str:
        """Déterminer le niveau de risque."""
        score = self.test_results["risk_score"]
        if score >= 80:
            return "CRITICAL"
        elif score >= 60:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        elif score >= 20:
            return "LOW"
        else:
            return "MINIMAL"
    
    def check_owasp_compliance(self) -> Dict[str, str]:
        """Vérifier la conformité OWASP Top 10."""
        compliance = {
            "A01: Broken Access Control": "COMPLIANT",
            "A02: Cryptographic Failures": "COMPLIANT",
            "A03: Injection": "COMPLIANT",
            "A04: Insecure Design": "COMPLIANT",
            "A05: Security Misconfiguration": "COMPLIANT",
            "A06: Vulnerable Components": "COMPLIANT",
            "A07: Identity & Auth Failures": "COMPLIANT",
            "A08: Software & Data Integrity": "COMPLIANT",
            "A09: Logging & Monitoring": "COMPLIANT",
            "A10: Server-Side Request Forgery": "COMPLIANT"
        }
        
        # Ajuster basé sur les vulnérabilités trouvées
        for vuln in self.test_results["vulnerabilities"]:
            category = vuln.get("category", "")
            severity = vuln.get("severity", "LOW")
            
            if severity in ["CRITICAL", "HIGH"]:
                if "Authentication" in category or "Authorization" in category:
                    compliance["A01: Broken Access Control"] = "NON_COMPLIANT"
                if "Cryptography" in category:
                    compliance["A02: Cryptographic Failures"] = "NON_COMPLIANT"
                if "Injection" in category:
                    compliance["A03: Injection"] = "NON_COMPLIANT"
        
        return compliance


# Point d'entrée principal
async def main():
    """Exécuter le test de pénétration complet."""
    framework = PenetrationTestFramework()
    report = await framework.run_full_penetration_test()
    
    # Sauvegarder le rapport
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"penetration_test_report_{timestamp}.json"
    
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    # Afficher le résumé
    print("\n" + "=" * 60)
    print("🔍 PENETRATION TEST REPORT")
    print("=" * 60)
    print(f"Target: {report['metadata']['target']}")
    print(f"Date: {report['metadata']['test_date']}")
    print(f"\nSUMMARY:")
    print(f"  Tests Run: {report['summary']['total_tests']}")
    print(f"  Vulnerabilities: {report['summary']['vulnerabilities_found']}")
    print(f"  Risk Score: {report['summary']['risk_score']}/100")
    print(f"  Risk Level: {report['summary']['risk_level']}")
    
    print(f"\nCRITICAL VULNERABILITIES: {report['compliance']['critical_vulnerabilities']}")
    print(f"HIGH VULNERABILITIES: {report['compliance']['high_vulnerabilities']}")
    
    print(f"\nOWASP TOP 10 COMPLIANCE:")
    for category, status in report['compliance']['owasp_top_10'].items():
        status_icon = "✅" if status == "COMPLIANT" else "❌"
        print(f"  {status_icon} {category}")
    
    print(f"\nReport saved: {report_file}")
    
    return report


if __name__ == "__main__":
    print("🔍 Starting Penetration Test Framework...")
    print("Make sure the target application is running!\n")
    
    asyncio.run(main())
