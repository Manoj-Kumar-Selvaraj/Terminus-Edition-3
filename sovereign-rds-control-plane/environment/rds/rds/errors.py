"""Error definitions for Sovereign RDS Control Plane."""

class RDSError(Exception):
    """Base error for sovereign RDS control plane."""
    pass

class ConfigurationError(RDSError):
    """Configuration error."""
    pass

class DatabaseError(RDSError):
    """Database connection or query error."""
    pass

class InvalidInstanceStateError(RDSError):
    """Raised when an operation requires AVAILABLE instance status."""
    pass

class StorageShrinkError(RDSError):
    """Raised when storage modification attempts to shrink allocated size."""
    pass

class DeletionProtectionError(RDSError):
    """Raised when DeleteDBInstance is called on a protected instance."""
    pass

class WALContinuityError(RDSError):
    """Raised when WAL segment sequence gap is detected."""
    pass

class PITRWindowError(RDSError):
    """Raised when PITR target timestamp is outside retention window."""
    pass

class ParameterGroupError(RDSError):
    """Raised when parameter application or validation fails."""
    pass

class ReplicationLagError(RDSError):
    """Raised when read replica lag exceeds maximum allowed threshold."""
    pass

class FailoverLeaseError(RDSError):
    """Raised when Multi-AZ failover lease acquisition fails."""
    pass

class EventOutboxError(RDSError):
    """Raised when event notification outbox dispatch fails."""
    pass

class CheckpointError(RDSError):
    """Raised when transaction WAL checkpoint recovery fails."""
    pass

class AuthorizationError(RDSError):
    """Raised when multi-tenant account or region isolation check fails."""
    pass
