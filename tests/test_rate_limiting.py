"""
🧪 Tests Rate Limiting & Protection DDoS
Validation du middleware de rate limiting avancé

Créé : 20 janvier 2026
Objectif : Tester Jalon 3.1
"""

import asyncio
import aiohttp
import time
from typing import List, Dict
import json

# Configuration
BASE_URL = "http://localhost:8000"
CONCURRENT_REQUESTS = 50
TOTAL_REQUESTS = 200


class RateLimitTester:
    """Testeur de rate limiting."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.results = {
            "successful": 0,
            "rate_limited": 0,
            "errors": 0,
            "response_times": []
        }
    
    async def test_basic_rate_limit(self):
        """Tester le rate limiting basique."""
        print("\n🧪 Test 1: Rate Limiting Basique")
        print("=" * 50)
        
        async with aiohttp.ClientSession() as session:
            # Envoyer 10 requêtes rapidement
            tasks = []
            for i in range(10):
                task = self._make_request(session, "/api/v1/health")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyser les résultats
            rate_limited = 0
            successful = 0
            
            for result in results:
                if isinstance(result, Exception):
                    print(f"❌ Erreur: {result}")
                    self.results["errors"] += 1
                elif result.get("status") == 429:
                    rate_limited += 1
                    print(f"⏱️  Rate limit: {result.get('retry_after')}s")
                elif result.get("status") == 200:
                    successful += 1
            
            print(f"\n✅ Succès: {successful}")
            print(f"⏱️  Rate limités: {rate_limited}")
            
            # Vérifier que le rate limiting fonctionne
            if rate_limited > 0:
                print("✅ Rate limiting ACTIF")
            else:
                print("⚠️  Rate limiting INACTIF")
    
    async def test_brute_force_protection(self):
        """Tester la protection brute force."""
        print("\n🛡️  Test 2: Protection Brute Force")
        print("=" * 50)
        
        async with aiohttp.ClientSession() as session:
            # Simuler 20 tentatives de login échouées
            for i in range(20):
                login_data = {
                    "username": "admin",
                    "password": f"wrong_password_{i}"
                }
                
                result = await self._make_request(
                    session, 
                    "/auth/login",
                    method="POST",
                    json=login_data
                )
                
                if result.get("status") == 429:
                    print(f"🚫 Brute force bloqué après {i+1} tentatives")
                    break
                elif result.get("status") == 401:
                    print(f"❌ Tentative {i+1}: Échec authentification")
                
                await asyncio.sleep(0.1)  # 100ms entre tentatives
    
    async def test_ddos_protection(self):
        """Tester la protection DDoS."""
        print("\n🌊 Test 3: Protection DDoS")
        print("=" * 50)
        
        print(f"Envoi de {CONCURRENT_REQUESTS} requêtes concurrentes...")
        
        async with aiohttp.ClientSession() as session:
            # Créer beaucoup de requêtes simultanées
            tasks = []
            start_time = time.time()
            
            for i in range(CONCURRENT_REQUESTS):
                task = self._make_request(session, "/api/v1/health")
                tasks.append(task)
            
            # Exécuter toutes les requêtes
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Analyser
            successful = sum(1 for r in results if isinstance(r, dict) and r.get("status") == 200)
            rate_limited = sum(1 for r in results if isinstance(r, dict) and r.get("status") == 429)
            errors = sum(1 for r in results if isinstance(r, Exception))
            
            print(f"\n⏱️  Durée totale: {duration:.2f}s")
            print(f"📊 Requêtes/seconde: {CONCURRENT_REQUESTS/duration:.0f}")
            print(f"✅ Succès: {successful}")
            print(f"⏱️  Rate limités: {rate_limited}")
            print(f"❌ Erreurs: {errors}")
            
            if rate_limited > CONCURRENT_REQUESTS * 0.5:
                print("✅ Protection DDoS ACTIVE")
            else:
                print("⚠️  Protection DDoS pourrait être renforcée")
    
    async def test_endpoints_specifics(self):
        """Tester les limits par endpoint."""
        print("\n🎯 Test 4: Limits Spécifiques par Endpoint")
        print("=" * 50)
        
        endpoints = [
            ("/auth/login", "POST", {"username": "test", "password": "test"}, "5/minute"),
            ("/api/v1/veritas/verify", "POST", {"query": "test"}, "10/minute"),
            ("/api/v1/health", "GET", None, "100/minute")
        ]
        
        for endpoint, method, data, expected_limit in endpoints:
            print(f"\n📍 Test {endpoint} (limit: {expected_limit})")
            
            async with aiohttp.ClientSession() as session:
                # Envoyer le double de la limite
                limit_num = int(expected_limit.split("/")[0])
                tasks = []
                
                for i in range(limit_num * 2):
                    task = self._make_request(session, endpoint, method=method, json=data)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                successful = sum(1 for r in results if isinstance(r, dict) and r.get("status") == 200)
                rate_limited = sum(1 for r in results if isinstance(r, dict) and r.get("status") == 429)
                
                print(f"   ✅ Succès: {successful}/{limit_num}")
                print(f"   ⏱️  Rate limités: {rate_limited}")
    
    async def test_headers(self):
        """Tester les headers de rate limit."""
        print("\n📋 Test 5: Headers Rate Limit")
        print("=" * 50)
        
        async with aiohttp.ClientSession() as session:
            # Faire une requête pour vérifier les headers
            async with session.get(f"{self.base_url}/api/v1/health") as response:
                headers = dict(response.headers)
                
                print("Headers reçus:")
                for header in ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]:
                    if header in headers:
                        print(f"  {header}: {headers[header]}")
                    else:
                        print(f"  {header}: ❌ Manquant")
    
    async def _make_request(
        self, 
        session: aiohttp.ClientSession, 
        path: str, 
        method: str = "GET",
        json: Dict = None
    ) -> Dict:
        """Faire une requête HTTP."""
        try:
            url = f"{self.base_url}{path}"
            
            if method == "GET":
                async with session.get(url) as response:
                    return {
                        "status": response.status,
                        "headers": dict(response.headers),
                        "retry_after": response.headers.get("Retry-After")
                    }
            elif method == "POST":
                async with session.post(url, json=json) as response:
                    return {
                        "status": response.status,
                        "headers": dict(response.headers),
                        "retry_after": response.headers.get("Retry-After")
                    }
        except Exception as e:
            return {"error": str(e)}
    
    async def run_all_tests(self):
        """Exécuter tous les tests."""
        print("🚀 DÉMARRAGE TESTS RATE LIMITING")
        print("=" * 60)
        
        await self.test_basic_rate_limit()
        await self.test_brute_force_protection()
        await self.test_ddos_protection()
        await self.test_endpoints_specifics()
        await self.test_headers()
        
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ DES TESTS")
        print("=" * 60)
        print(f"✅ Requêtes réussies: {self.results['successful']}")
        print(f"⏱️  Rate limitées: {self.results['rate_limited']}")
        print(f"❌ Erreurs: {self.results['errors']}")
        
        if self.results["rate_limited"] > 0:
            print("\n✅ Rate limiting fonctionne correctement")
        else:
            print("\n⚠️  Rate limiting ne semble pas actif")


async def main():
    """Fonction principale."""
    tester = RateLimitTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("⚠️  Assurez-vous que le serveur est démarré:")
    print("   uvicorn app.main:app --reload")
    print()
    
    asyncio.run(main())
