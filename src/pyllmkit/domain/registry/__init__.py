"""Registry domain, queries, pure resolutions and selection evidence (P6)."""

from .capability_resolution import (
    CapabilityEvidence,
    CapabilityResolver,
    EffectiveCapability,
    EffectiveCapabilityReport,
    EffectiveCapabilitySet,
    ResolutionReason,
)
from .constraints import ConstraintEvidence, ConstraintReport, ResolvedConstraint
from .errors import (
    RegistryConflictError,
    RegistryError,
    RegistryReferenceError,
    RegistryReferenceInUseError,
)
from .limit_resolution import EffectiveLimit, EffectiveLimits, LimitEvidence, LimitResolver
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
    "RegistryError",
    "RegistryConflictError",
    "RegistryReferenceError",
    "RegistryReferenceInUseError",
    "CapabilityMatchMode",
    "ModelQuery",
    "DeploymentQuery",
    "CapabilityEvidence",
    "CapabilityResolver",
    "EffectiveCapability",
    "EffectiveCapabilityReport",
    "EffectiveCapabilitySet",
    "ResolutionReason",
    "ConstraintEvidence",
    "ResolvedConstraint",
    "ConstraintReport",
    "LimitEvidence",
    "EffectiveLimit",
    "EffectiveLimits",
    "LimitResolver",
    "DeploymentRequirement",
    "DeploymentResolutionReport",
    "CandidateRejection",
    "DeploymentResolutionError",
    "ModelNotFoundError",
    "DeploymentNotFoundError",
    "NoCompatibleDeploymentError",
    "AmbiguousDeploymentError",
]
