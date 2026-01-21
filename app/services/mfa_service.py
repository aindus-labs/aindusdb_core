"""
🔐 MFA Service - Multi-Factor Authentication
Implémentation TOTP et WebAuthn pour comptes admin

Créé : 20 janvier 2026
Objectif : Ajouter MFA aux comptes administrateurs
"""

import os
import secrets
import pyotp
import qrcode
from io import BytesIO
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import json
import base64

from app.core.database import db_manager
from app.core.security import security_service
import bcrypt


class MFAService:
    """Service pour l'authentification multi-facteurs."""
    
    def __init__(self):
        self.issuer_name = "AindusDB Core"
        self.totp_validity_window = 1  # Fenêtre de 30 secondes avant/après
    
    async def generate_totp_secret(self, user_id: str, email: str) -> Dict:
        """Générer un secret TOTP pour un utilisateur."""
        # Générer un secret aléatoire
        secret = pyotp.random_base32()
        
        # Créer l'URI TOTP
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=self.issuer_name
        )
        
        # Générer le QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        qr_buffer = BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(qr_buffer, format='PNG')
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
        
        # Sauvegarder en base de données
        query = """
        INSERT INTO user_mfa (user_id, mfa_type, secret, enabled, created_at)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (user_id, mfa_type) 
        DO UPDATE SET 
            secret = $3,
            updated_at = $5
        """
        await db_manager.execute(query, user_id, 'totp', secret, False, datetime.now())
        
        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_base64}",
            "manual_entry_key": secret,
            "instructions": {
                "step1": "Scanner le QR code avec Google Authenticator",
                "step2": "Ou entrer manuellement la clé dans votre app TOTP",
                "step3": "Entrer le code généré pour activer MFA"
            }
        }
    
    async def enable_totp(self, user_id: str, token: str) -> bool:
        """Activer TOTP après validation du token."""
        # Récupérer le secret
        query = "SELECT secret FROM user_mfa WHERE user_id = $1 AND mfa_type = $2"
        result = await db_manager.fetch_one(query, user_id, 'totp')
        
        if not result:
            return False
        
        secret = result['secret']
        totp = pyotp.TOTP(secret)
        
        # Valider le token
        if not totp.verify(token, valid_window=self.totp_validity_window):
            return False
        
        # Activer MFA
        update_query = """
        UPDATE user_mfa 
        SET enabled = true, activated_at = $1
        WHERE user_id = $2 AND mfa_type = $3
        """
        await db_manager.execute(update_query, datetime.now(), user_id, 'totp')
        
        # Mettre à jour le statut MFA de l'utilisateur
        await db_manager.execute(
            "UPDATE users SET mfa_enabled = true WHERE id = $1",
            user_id
        )
        
        return True
    
    async def verify_totp(self, user_id: str, token: str) -> bool:
        """Vérifier un token TOTP."""
        query = "SELECT secret FROM user_mfa WHERE user_id = $1 AND mfa_type = $2 AND enabled = true"
        result = await db_manager.fetch_one(query, user_id, 'totp')
        
        if not result:
            return False
        
        secret = result['secret']
        totp = pyotp.TOTP(secret)
        
        return totp.verify(token, valid_window=self.totp_validity_window)
    
    async def generate_backup_codes(self, user_id: int, count: int = 10) -> list:
        """Générer des codes de secours."""
        codes = []
        
        # Générer les codes
        for _ in range(count):
            code = f"{secrets.token_hex(3)}-{secrets.token_hex(3)}".upper()
            codes.append(code)
        
        # Hasher et sauvegarder
        hashed_codes = []
        for code in codes:
            hashed = bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()
            hashed_codes.append(hashed)
        
        # Supprimer anciens codes
        await db_manager.execute(
            "DELETE FROM user_backup_codes WHERE user_id = $1",
            user_id
        )
        
        # Insérer nouveaux codes
        for hashed_code in hashed_codes:
            await db_manager.execute(
                "INSERT INTO user_backup_codes (user_id, code_hash) VALUES ($1, $2)",
                user_id, hashed_code
            )
        
        return codes
    
    async def verify_backup_code(self, user_id: int, code: str) -> bool:
        """Vérifier un code de secours."""
        # Récupérer tous les codes de l'utilisateur
        query = "SELECT id, code_hash FROM user_backup_codes WHERE user_id = $1 AND used = false"
        codes = await db_manager.fetch_all(query, user_id)
        
        for code_record in codes:
            if bcrypt.checkpw(code.encode(), code_record['code_hash'].encode()):
                # Marquer comme utilisé
                await db_manager.execute(
                    "UPDATE user_backup_codes SET used = true, used_at = $1 WHERE id = $2",
                    datetime.now(), code_record['id']
                )
                return True
        
        return False
    
    async def disable_mfa(self, user_id: str, password: str, backup_code: Optional[str] = None) -> bool:
        """Désactiver MFA."""
        # Vérifier le mot de passe
        user = await db_manager.fetch_one(
            "SELECT password_hash FROM users WHERE id = $1",
            user_id
        )
        
        if not user or not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            return False
        
        # Si code de secours fourni, le vérifier
        if backup_code:
            if not await self.verify_backup_code(int(user_id), backup_code):
                return False
        
        # Désactiver MFA
        await db_manager.execute(
            "UPDATE user_mfa SET enabled = false WHERE user_id = $1",
            user_id
        )
        
        await db_manager.execute(
            "UPDATE users SET mfa_enabled = false WHERE id = $1",
            user_id
        )
        
        return True
    
    async def get_mfa_status(self, user_id: str) -> Dict:
        """Obtenir le statut MFA d'un utilisateur."""
        # Statut TOTP
        totp_status = await db_manager.fetch_one(
            "SELECT enabled, activated_at FROM user_mfa WHERE user_id = $1 AND mfa_type = $2",
            user_id, 'totp'
        )
        
        # Codes de secours restants
        backup_count = await db_manager.fetch_one(
            "SELECT COUNT(*) as count FROM user_backup_codes WHERE user_id = $1 AND used = false",
            int(user_id)
        )
        
        return {
            "mfa_enabled": bool(totp_status and totp_status['enabled']),
            "totp_enabled": bool(totp_status and totp_status['enabled']),
            "totp_activated_at": totp_status['activated_at'] if totp_status else None,
            "backup_codes_remaining": backup_count['count'] if backup_count else 0,
            "mfa_methods": {
                "totp": bool(totp_status and totp_status['enabled']),
                "backup_codes": backup_count['count'] > 0 if backup_count else False
            }
        }


class WebAuthnService:
    """Service WebAuthn (clés de sécurité)."""
    
    def __init__(self):
        self.rp_name = "AindusDB Core"
        self.rp_id = "localhost"  # À configurer selon domaine
        self.rp_origin = "https://localhost:8000"  # À configurer
    
    async def begin_registration(self, user_id: str, email: str) -> Dict:
        """Commencer l'enregistrement WebAuthn."""
        # TODO: Implémenter WebAuthn complet
        # Nécessite webauthn-python
        return {
            "status": "not_implemented",
            "message": "WebAuthn sera implémenté dans la prochaine version"
        }


# Instance globale
mfa_service = MFAService()
webauthn_service = WebAuthnService()


# Middleware pour vérifier MFA
async def verify_mfa_for_admin(user_id: str, token: str) -> bool:
    """Vérifier MFA pour les actions admin."""
    # Vérifier si l'utilisateur est admin
    user = await db_manager.fetch_one(
        "SELECT is_admin, mfa_enabled FROM users WHERE id = $1",
        user_id
    )
    
    if not user:
        return False
    
    # Si admin et MFA activé, vérifier le token
    if user['is_admin'] and user['mfa_enabled']:
        return await mfa_service.verify_totp(user_id, token)
    
    # Sinon, autoriser
    return True
