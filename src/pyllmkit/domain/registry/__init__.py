"""Registry domain contracts, queries, resolution and offline discovery (P6)."""

from .capability_resolution import (
    CapabilityEvidence,
    CapabilityResolver,
    EffectiveCapability,
    EffectiveCapabilityReport,
    EffectiveCapabilitySet,
    ResolutionReason,
)
from .constraints import ConstraintEvidence, ConstraintReport, ResolvedConstraint
from .discovery import (
    CatalogProvenance,
    DiscoveryResult,
    MetadataSource,
    MetadataSourceKind,
    validate_discovery_time,
)
from .errors import (
    RegistryConflictError,
    RegistryError,
    RegistryMergeRejectedError,
    RegistryReferenceError,
    RegistryReferenceInUseError,
    RegistryStaleSnapshotError,
)
from .limit_resolution import EffectiveLimit, EffectiveLimits, LimitEvidence, LimitResolver
from .merge import (
    CatalogChange,
    InvalidCatalogReference,
    MergePolicy,
    MergePreview,
    MergeResult,
    RegistryConflict,
    RegistrySnapshot,
)
from .queries import CapabilityMatchMode, DeploymentQuery, ModelQuery
from .selection import (
    AmbiguousDeploymentError,
    CandidateRejection,
    DeploymentNotFoundError,
    DeploymentRequirement,
    DeploymentResolutionError,
    DeploymentResolutionReport,
    ModelNotFoundError,
    NoCompatibleDeploymentError,
)

__all__ = [
    "RegistryError", "RegistryConflictError", "RegistryReferenceError",
    "RegistryReferenceInUseError", "RegistryMergeRejectedError",
    "RegistryStaleSnapshotError", "CapabilityMatchMode", "ModelQuery", "DeploymentQuery",
    "CapabilityEvidence", "CapabilityResolver", "EffectiveCapability",
    "EffectiveCapabilityReport", "EffectiveCapabilitySet", "ResolutionReason",
    "ConstraintEvidence", "ResolvedConstraint", "ConstraintReport", "LimitEvidence",
    "EffectiveLimit", "EffectiveLimits", "LimitResolver", "DeploymentRequirement",
    "DeploymentResolutionReport", "CandidateRejection", "DeploymentResolutionError",
    "ModelNotFoundError", "DeploymentNotFoundError", "NoCompatibleDeploymentError",
    "AmbiguousDeploymentError", "MetadataSourceKind", "MetadataSource",
    "CatalogProvenance", "DiscoveryResult", "validate_discovery_time",
    "MergePolicy", "RegistrySnapshot", "CatalogChange", "RegistryConflict",
    "InvalidCatalogReference", "MergePreview", "MergeResult",
]
