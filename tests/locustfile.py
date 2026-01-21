"""
🦗 Locust Load Testing File
Tests de charge avec profil de sécurité

Créé : 20 janvier 2026
Objectif : Jalon 3.3 - Tests Sécurité Automatisés
"""

from locust import HttpUser, task, between
import random
import json


class SecurityUser(HttpUser):
    """Utilisateur simulé pour les tests de charge."""
    
    wait_time = between(1, 3)
    token = None
    headers = {}
    
    def on_start(self):
        """Initialisation au démarrage."""
        # Tenter de s'authentifier
        self.login()
        
    def login(self):
        """Authentification de l'utilisateur."""
        response = self.client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            # Créer un compte si l'auth échoue
            self.create_user()
    
    def create_user(self):
        """Créer un nouvel utilisateur."""
        user_data = {
            "username": f"user_{random.randint(1000, 9999)}",
            "email": f"user{random.randint(1000, 9999)}@example.com",
            "password": "TestPass123!",
            "role": "user"
        }
        
        response = self.client.post("/auth/register", json=user_data)
        
        if response.status_code == 201:
            # Tenter de se connecter avec le nouvel utilisateur
            login_response = self.client.post("/auth/login", json={
                "username": user_data["username"],
                "password": user_data["password"]
            })
            
            if login_response.status_code == 200:
                data = login_response.json()
                self.token = data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}


class NormalUser(SecurityUser):
    """Utilisateur normal avec comportement standard."""
    
    @task(5)
    def view_health(self):
        """Consulter le endpoint de santé."""
        self.client.get("/api/v1/health")
    
    @task(3)
    def search_vectors(self):
        """Rechercher des vecteurs."""
        queries = ["test", "vector", "search", "data", "query"]
        query = random.choice(queries)
        self.client.get(f"/api/v1/vectors/search?q={query}")
    
    @task(2)
    def view_veritas_status(self):
        """Consulter le statut VERITAS."""
        if self.token:
            self.client.get("/api/v1/veritas/status", headers=self.headers)
    
    @task(1)
    def get_user_profile(self):
        """Consulter son profil."""
        if self.token:
            self.client.get("/api/v1/users/profile", headers=self.headers)


class AttackerUser(HttpUser):
    """Utilisateur malveillant simulant des attaques."""
    
    wait_time = between(0.5, 2)
    
    @task(4)
    def brute_force_login(self):
        """Tenter de forcer le login (brute force)."""
        usernames = ["admin", "root", "user", "test"]
        passwords = [
            "password", "123456", "admin", "root", "qwerty",
            f"guess{random.randint(1000, 9999)}"
        ]
        
        self.client.post("/auth/login", json={
            "username": random.choice(usernames),
            "password": random.choice(passwords)
        })
    
    @task(3)
    def sql_injection_attempts(self):
        """Tenter des injections SQL."""
        sqli_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "'; EXEC xp_cmdshell('dir'); --"
        ]
        
        payload = random.choice(sqli_payloads)
        self.client.get(f"/api/v1/vectors/search?q={payload}")
        
        # Aussi en POST
        self.client.post("/api/v1/veritas/verify", json={
            "query": payload
        })
    
    @task(2)
    def xss_attempts(self):
        """Tenter des injections XSS."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>"
        ]
        
        payload = random.choice(xss_payloads)
        self.client.get(f"/api/v1/health?search={payload}")
    
    @task(2)
    def path_traversal_attempts(self):
        """Tenter des path traversals."""
        paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        path = random.choice(paths)
        self.client.get(f"/api/v1/files?path={path}")
    
    @task(1)
    def dos_attack(self):
        """Simuler une attaque DoS."""
        # Requêtes lourdes
        for _ in range(5):
            self.client.post("/api/v1/veritas/calculate", json={
                "expression": "sin(" + "cos(" * 50 + "x" + ")" * 50 + ")"
            })
    
    @task(1)
    def scan_endpoints(self):
        """Scanner les endpoints à la recherche de vulnérabilités."""
        endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/config",
            "/api/v1/debug/info",
            "/api/v1/system/status",
            "/.env",
            "/config.json"
        ]
        
        for endpoint in endpoints:
            self.client.get(endpoint)


class RateLimitTester(HttpUser):
    """Utilisateur spécialisé pour tester le rate limiting."""
    
    wait_time = between(0.1, 0.5)
    
    @task
    def rapid_requests(self):
        """Faire des requêtes rapides pour tester le rate limiting."""
        self.client.get("/api/v1/health")
    
    @task
    def bypass_attempts(self):
        """Tenter de bypasser le rate limiting."""
        # Varier les headers
        headers_list = [
            {"X-Forwarded-For": f"192.168.1.{random.randint(1, 254)}"},
            {"X-Real-IP": f"10.0.0.{random.randint(1, 254)}"},
            {"User-Agent": f"Bot{random.randint(1000, 9999)}"},
            {}
        ]
        
        headers = random.choice(headers_list)
        self.client.get("/api/v1/health", headers=headers)


class PrivilegeEscalationTester(SecurityUser):
    """Utilisateur tentant l'escalade de privilèges."""
    
    @task(3)
    def access_admin_endpoints(self):
        """Tenter d'accéder aux endpoints admin."""
        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/settings",
            "/api/v1/admin/logs",
            "/api/v1/security/stats"
        ]
        
        for endpoint in admin_endpoints:
            # Sans token
            self.client.get(endpoint)
            
            # Avec token utilisateur normal
            if self.token:
                self.client.get(endpoint, headers=self.headers)
    
    @task(2)
    def modify_admin_data(self):
        """Tenter de modifier des données admin."""
        if self.token:
            # Tenter de promouvoir son compte
            self.client.put("/api/v1/users/role", 
                headers=self.headers,
                json={"role": "admin"}
            )
            
            # Tenter d'accéder à tous les utilisateurs
            self.client.get("/api/v1/admin/users", 
                headers=self.headers
            )


# Configuration des poids pour simuler un trafic réaliste
class WebsiteUser(HttpUser):
    """Mix d'utilisateurs réalistes."""
    
    task_set = {
        NormalUser: 70,      # 70% utilisateurs normaux
        AttackerUser: 20,    # 20% attaquants
        RateLimitTester: 5,  # 5% testeurs rate limit
        PrivilegeEscalationTester: 5  # 5% tentatives d'escalade
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Choisir aléatoirement le type d'utilisateur
        user_types = list(self.task_set.keys())
        weights = list(self.task_set.values())
        
        chosen_type = random.choices(user_types, weights=weights)[0]
        self.__class__ = chosen_type
