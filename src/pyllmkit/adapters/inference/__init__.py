"""P7 executable composition contracts, fake adapters and guarded endpoints."""

from pyllmkit.protocols.credentials import (
    CredentialRef,
    CredentialResolutionError,
    SecretValue,
    SecurityConfigurationError,
)

from .errors import normalize_http_failure
from .ollama import AsyncOllamaAdapter, OllamaAdapter
from .fake import AsyncFakeInferenceAdapter, FakeInferenceAdapter
from .registry import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    AdapterRegistryError,
)
from .routing import RegisteredAsyncInferencePort, RegisteredInferencePort
from .security import EnvCredentialResolver, ProviderConnectionConfig, ProviderProfile

__all__ = [
    "OllamaAdapter",
    "AsyncOllamaAdapter",
    "AsyncFakeInferenceAdapter",
    "FakeInferenceAdapter",
    "AdapterKey",
    "AdapterRegistration",
    "AdapterRegistry",
    "AdapterRegistryError",
    "RegisteredInferencePort",
    "RegisteredAsyncInferencePort",
    "CredentialRef",
    "CredentialResolutionError",
    "EnvCredentialResolver",
    "ProviderConnectionConfig",
    "ProviderProfile",
    "SecretValue",
    "SecurityConfigurationError",
    "normalize_http_failure",
]
