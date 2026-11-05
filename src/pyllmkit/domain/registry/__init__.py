"""Registry domain contracts, queries and pure effective resolution (P6 L6.2-L6.4)."""

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
]
