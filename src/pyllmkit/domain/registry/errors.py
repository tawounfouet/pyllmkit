"""Typed registry errors; no provider-specific or raw payload details."""

from pyllmkit.domain.errors import PyLLMKitError


class RegistryError(PyLLMKitError):
    """Registry operation could not be completed safely."""


class RegistryConflictError(RegistryError):
    """An existing canonical ID has a different complete metadata snapshot."""


class RegistryReferenceError(RegistryError):
    """A referenced Model or Provider has not been registered."""


class RegistryReferenceInUseError(RegistryError):
    """Deletion would orphan one or more registered Deployments."""


class RegistryMergeRejectedError(RegistryError):
    """Preview contains conflicts or invalid references; no changes were applied."""


class RegistryStaleSnapshotError(RegistryError):
    """A catalog write invalidated an earlier dry-run's expected revision."""
