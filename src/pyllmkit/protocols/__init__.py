"""Dependency-inversion contracts for provider-independent application services."""

from .credentials import CredentialResolverPort
from .inference import AsyncInferencePort, InferencePort
from .registry import (
    AtomicCatalogPort,
    DeploymentRegistryPort,
    DiscoverySourcePort,
    ModelRegistryPort,
    ProviderCatalogPort,
)

__all__ = [
    "InferencePort", "AsyncInferencePort", "CredentialResolverPort",
    "ModelRegistryPort", "DeploymentRegistryPort", "ProviderCatalogPort",
    "DiscoverySourcePort", "AtomicCatalogPort",
]
