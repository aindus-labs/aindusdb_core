"""
VeritasProofManager - Service spécialisé pour gestion des preuves VERITAS.

Ce service se concentre uniquement sur la création, stockage, et récupération
des preuves VERITAS selon le principe Single Responsibility.

Example:
    proof_manager = VeritasProofManager(db_manager=db)
    
    await proof_manager.store_proof(proof, verification_id="abc123")
    proofs = await proof_manager.get_proofs_by_verification_id("abc123")
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from ...core.logging import get_logger
from ...core.database import DatabaseManager
from ...models.veritas import VeritasProof, ProofType, VerificationStatus


class VeritasProofManager:
    """
    Service de gestion des preuves VERITAS avec stockage persistant.
    
    Responsabilité unique : Gérer le cycle de vie complet des preuves
    VERITAS incluant création, stockage, récupération, et archivage.
    
    Features:
    - Stockage persistant des preuves en base PostgreSQL
    - Indexation optimisée pour recherche rapide
    - Sérialisation/désérialisation sécurisée JSON
    - Gestion des métadonnées et versions
    - API de recherche avancée par critères
    
    Attributes:
        db_manager: Gestionnaire de base de données
        table_name: Nom de la table des preuves
        enable_compression: Compression des preuves volumineuses
        
    Example:
        proof_manager = VeritasProofManager(
            db_manager=db_manager,
            enable_compression=True
        )
        
        # Stocker une preuve
        await proof_manager.store_proof(proof, "request_123")
        
        # Récupérer preuves par verification_id
        proofs = await proof_manager.get_proofs_by_verification_id("request_123")
    """
    
    def __init__(self, 
                 db_manager: DatabaseManager,
                 table_name: str = "veritas_proofs",
                 enable_compression: bool = False):
        """
        Initialiser le gestionnaire de preuves.
        
        Args:
            db_manager: Gestionnaire de base de données
            table_name: Nom de la table de stockage
            enable_compression: Activer compression des preuves
        """
        self.db_manager = db_manager
        self.table_name = table_name
        self.enable_compression = enable_compression
        self.logger = get_logger("aindusdb.services.veritas.proof_manager")
        
        # Cache local pour preuves récentes (éviter requêtes répétées)
        self._proof_cache = {}
        self._cache_max_size = 100
    
    async def store_proof(self, 
                         proof: VeritasProof, 
                         verification_id: str,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Stocker une preuve VERITAS en base de données.
        
        Args:
            proof: Preuve VERITAS à stocker
            verification_id: ID de vérification associé
            metadata: Métadonnées supplémentaires
            
        Returns:
            str: ID unique de la preuve stockée
            
        Example:
            proof_id = await proof_manager.store_proof(
                proof=calculation_proof,
                verification_id="req_20260120_001",
                metadata={"user_id": "user123", "session": "sess456"}
            )
        """
        try:
            # Sérialiser la preuve en JSON
            proof_json = self._serialize_proof(proof)
            
            # Générer ID unique pour la preuve
            proof_id = self._generate_proof_id(verification_id)
            
            # Préparer métadonnées enrichies
            enriched_metadata = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "proof_type": proof.proof_type.value,
                "verification_status": proof.verification_status.value,
                "confidence_score": proof.confidence_score,
                "verifier_system": proof.verifier_system,
                **(metadata or {})
            }
            
            # Requête d'insertion avec gestion des conflits
            query = f"""
            INSERT INTO {self.table_name} (
                proof_id, verification_id, proof_data, proof_type,
                verification_status, confidence_score, metadata, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (proof_id) DO UPDATE SET
                proof_data = EXCLUDED.proof_data,
                confidence_score = EXCLUDED.confidence_score,
                metadata = EXCLUDED.metadata,
                updated_at = CURRENT_TIMESTAMP
            """
            
            async with self.db_manager.get_connection() as conn:
                await conn.execute(
                    query,
                    proof_id,
                    verification_id,
                    proof_json,
                    proof.proof_type.value,
                    proof.verification_status.value,
                    proof.confidence_score,
                    json.dumps(enriched_metadata),
                    datetime.now(timezone.utc)
                )
            
            # Mettre à jour cache local
            self._update_cache(proof_id, proof)
            
            self.logger.info("Proof stored successfully",
                           extra={"proof_id": proof_id, "verification_id": verification_id})
            
            return proof_id
            
        except Exception as e:
            self.logger.error(f"Failed to store proof: {e}")
            raise
    
    async def get_proof_by_id(self, proof_id: str) -> Optional[VeritasProof]:
        """
        Récupérer une preuve par son ID unique.
        
        Args:
            proof_id: ID unique de la preuve
            
        Returns:
            Optional[VeritasProof]: Preuve si trouvée, None sinon
        """
        # Vérifier cache local d'abord
        if proof_id in self._proof_cache:
            return self._proof_cache[proof_id]
        
        try:
            query = f"SELECT proof_data FROM {self.table_name} WHERE proof_id = $1"
            
            async with self.db_manager.get_connection() as conn:
                row = await conn.fetchrow(query, proof_id)
            
            if row:
                proof = self._deserialize_proof(row['proof_data'])
                self._update_cache(proof_id, proof)
                return proof
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve proof {proof_id}: {e}")
            return None
    
    async def get_proofs_by_verification_id(self, verification_id: str) -> List[VeritasProof]:
        """
        Récupérer toutes les preuves d'une vérification.
        
        Args:
            verification_id: ID de vérification
            
        Returns:
            List[VeritasProof]: Liste des preuves
        """
        try:
            query = f"""
            SELECT proof_data, confidence_score 
            FROM {self.table_name} 
            WHERE verification_id = $1 
            ORDER BY confidence_score DESC, created_at DESC
            """
            
            async with self.db_manager.get_connection() as conn:
                rows = await conn.fetch(query, verification_id)
            
            proofs = []
            for row in rows:
                try:
                    proof = self._deserialize_proof(row['proof_data'])
                    proofs.append(proof)
                except Exception as e:
                    self.logger.warning(f"Failed to deserialize proof: {e}")
                    continue
            
            return proofs
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve proofs for verification {verification_id}: {e}")
            return []
    
    async def search_proofs(self,
                           proof_type: Optional[ProofType] = None,
                           verification_status: Optional[VerificationStatus] = None,
                           min_confidence: Optional[float] = None,
                           limit: int = 50) -> List[VeritasProof]:
        """
        Rechercher des preuves selon des critères.
        
        Args:
            proof_type: Type de preuve à filtrer
            verification_status: Statut de vérification
            min_confidence: Score minimum de confiance
            limit: Nombre maximum de résultats
            
        Returns:
            List[VeritasProof]: Preuves correspondant aux critères
        """
        try:
            conditions = []
            params = []
            param_count = 0
            
            # Construire conditions dynamiquement
            if proof_type:
                param_count += 1
                conditions.append(f"proof_type = ${param_count}")
                params.append(proof_type.value)
            
            if verification_status:
                param_count += 1
                conditions.append(f"verification_status = ${param_count}")
                params.append(verification_status.value)
            
            if min_confidence is not None:
                param_count += 1
                conditions.append(f"confidence_score >= ${param_count}")
                params.append(min_confidence)
            
            # Ajouter limite
            param_count += 1
            params.append(limit)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            query = f"""
            SELECT proof_data, confidence_score, created_at
            FROM {self.table_name}
            {where_clause}
            ORDER BY confidence_score DESC, created_at DESC
            LIMIT ${param_count}
            """
            
            async with self.db_manager.get_connection() as conn:
                rows = await conn.fetch(query, *params)
            
            proofs = []
            for row in rows:
                try:
                    proof = self._deserialize_proof(row['proof_data'])
                    proofs.append(proof)
                except Exception as e:
                    self.logger.warning(f"Failed to deserialize proof: {e}")
                    continue
            
            return proofs
            
        except Exception as e:
            self.logger.error(f"Failed to search proofs: {e}")
            return []
    
    def _serialize_proof(self, proof: VeritasProof) -> str:
        """
        Sérialiser une preuve VERITAS en JSON.
        
        Args:
            proof: Preuve à sérialiser
            
        Returns:
            str: JSON sérialisé
        """
        try:
            # Utiliser le modèle Pydantic pour sérialisation
            return proof.model_dump_json()
        except Exception as e:
            self.logger.error(f"Proof serialization failed: {e}")
            raise
    
    def _deserialize_proof(self, proof_json: str) -> VeritasProof:
        """
        Désérialiser une preuve depuis JSON.
        
        Args:
            proof_json: JSON à désérialiser
            
        Returns:
            VeritasProof: Preuve désérialisée
        """
        try:
            return VeritasProof.model_validate_json(proof_json)
        except Exception as e:
            self.logger.error(f"Proof deserialization failed: {e}")
            raise
    
    def _generate_proof_id(self, verification_id: str) -> str:
        """
        Générer un ID unique pour une preuve.
        
        Args:
            verification_id: ID de vérification
            
        Returns:
            str: ID unique de preuve
        """
        import uuid
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"proof_{verification_id}_{timestamp}_{short_uuid}"
    
    def _update_cache(self, proof_id: str, proof: VeritasProof):
        """
        Mettre à jour le cache local des preuves.
        
        Args:
            proof_id: ID de la preuve
            proof: Preuve à cacher
        """
        # Éviter dépassement de cache
        if len(self._proof_cache) >= self._cache_max_size:
            # Supprimer le plus ancien (FIFO)
            oldest_key = next(iter(self._proof_cache))
            del self._proof_cache[oldest_key]
        
        self._proof_cache[proof_id] = proof
    
    async def delete_proof(self, proof_id: str) -> bool:
        """
        Supprimer une preuve par son ID.
        
        Args:
            proof_id: ID de la preuve à supprimer
            
        Returns:
            bool: True si suppression réussie
        """
        try:
            query = f"DELETE FROM {self.table_name} WHERE proof_id = $1"
            
            async with self.db_manager.get_connection() as conn:
                result = await conn.execute(query, proof_id)
            
            # Supprimer du cache aussi
            if proof_id in self._proof_cache:
                del self._proof_cache[proof_id]
            
            deleted = result.split()[-1] == '1'  # 'DELETE 1'
            
            if deleted:
                self.logger.info(f"Proof deleted successfully: {proof_id}")
            else:
                self.logger.warning(f"No proof found to delete: {proof_id}")
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Failed to delete proof {proof_id}: {e}")
            return False
    
    async def get_proof_statistics(self) -> Dict[str, Any]:
        """
        Obtenir statistiques sur les preuves stockées.
        
        Returns:
            Dict: Statistiques des preuves
        """
        try:
            stats_query = f"""
            SELECT 
                COUNT(*) as total_proofs,
                COUNT(CASE WHEN verification_status = 'VERIFIED' THEN 1 END) as verified_proofs,
                COUNT(CASE WHEN verification_status = 'FAILED' THEN 1 END) as failed_proofs,
                AVG(confidence_score) as avg_confidence,
                MAX(confidence_score) as max_confidence,
                MIN(confidence_score) as min_confidence,
                COUNT(DISTINCT verification_id) as unique_verifications
            FROM {self.table_name}
            """
            
            async with self.db_manager.get_connection() as conn:
                row = await conn.fetchrow(stats_query)
            
            return {
                "total_proofs": row['total_proofs'] or 0,
                "verified_proofs": row['verified_proofs'] or 0,
                "failed_proofs": row['failed_proofs'] or 0,
                "success_rate": (row['verified_proofs'] or 0) / max(row['total_proofs'] or 1, 1),
                "avg_confidence": round(row['avg_confidence'] or 0.0, 3),
                "max_confidence": row['max_confidence'] or 0.0,
                "min_confidence": row['min_confidence'] or 0.0,
                "unique_verifications": row['unique_verifications'] or 0,
                "cache_size": len(self._proof_cache)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get proof statistics: {e}")
            return {"error": str(e)}
    
    def clear_cache(self):
        """Vider le cache local des preuves."""
        self._proof_cache.clear()
        self.logger.info("Proof cache cleared")
