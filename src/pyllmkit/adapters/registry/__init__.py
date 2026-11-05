"""Deterministic, network-free registry and discovery adapters (P6)."""

from .discovery import StaticDiscoverySource
from .in_memory import (
    InMemoryCatalog,
    InMemoryDeploymentRegistry,
    InMemoryModelRegistry,
    InMemoryProviderCatalog,
)

__all__ = [
    "InMemoryCatalog", "InMemoryModelRegistry", "InMemoryDeploymentRegistry",
    "InMemoryProviderCatalog", "StaticDiscoverySource",
]
