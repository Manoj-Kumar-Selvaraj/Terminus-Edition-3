"""KMS encryption key manager and transparent data encryption (TDE) validator."""
from typing import Any, Dict, Optional
from rds.errors import ConfigurationError

class KMSEncryptionManager:
    """Manages KMS key validation and storage encryption posture."""

    DEFAULT_KMS_KEY_ARN = "arn:aws:kms:us-east-1:100000000000:key/rds-sovereign-default-key"

    @classmethod
    def validate_kms_key_authority(cls, kms_key_id: Optional[str] = None) -> str:
        """Validate KMS key identifier or assign default sovereign KMS key ARN."""
        key_arn = kms_key_id or cls.DEFAULT_KMS_KEY_ARN
        if not key_arn.startswith("arn:aws:kms:"):
            raise ConfigurationError(f"Invalid KMS key ARN format: '{key_arn}'")
        return key_arn

    @classmethod
    def encrypt_storage_volume_spec(cls, storage_spec: Dict[str, Any], kms_key_id: Optional[str] = None) -> Dict[str, Any]:
        """Apply KMS key encryption posture to storage volume specification."""
        key_arn = cls.validate_kms_key_authority(kms_key_id)
        spec = dict(storage_spec)
        spec["storage_encrypted"] = True
        spec["kms_key_id"] = key_arn
        return spec
