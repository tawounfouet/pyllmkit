"""Registry domain errors and pure query values (P6 L6.2/L6.3)."""

from .errors import (
    RegistryConflictError,
    RegistryError,
    RegistryReferenceError,
    RegistryReferenceInUseError,
)
from .queries import CapabilityMatchMode, DeploymentQuery, ModelQuery

__all__ = [
    "RegistryError",
    "RegistryConflictError",
    "RegistryReferenceError",
    "RegistryReferenceInUseError",
    "CapabilityMatchMode",
    "ModelQuery",
    "DeploymentQuery",
]
