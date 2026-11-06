"""P7 executable composition contracts, fake adapters and guarded endpoints."""

from pyllmkit.protocols.credentials import (
    CredentialRef,
    CredentialResolutionError,
    SecretValue,
    SecurityConfigurationError,
)

from .anthropic_messages import AnthropicMessagesAdapter, AsyncAnthropicMessagesAdapter
from .errors import normalize_http_failure
from .fake import AsyncFakeInferenceAdapter, FakeInferenceAdapter
from .ollama import AsyncOllamaAdapter, OllamaAdapter
from .openai_responses import AsyncOpenAIResponsesAdapter, OpenAIResponsesAdapter
from .registry import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    AdapterRegistryError,
)
from .routing import RegisteredAsyncInferencePort, RegisteredInferencePort
from .security import EnvCredentialResolver, ProviderConnectionConfig, ProviderProfile

__all__ = [
    "AnthropicMessagesAdapter",
    "AsyncAnthropicMessagesAdapter",
    "OpenAIResponsesAdapter",
    "AsyncOpenAIResponsesAdapter",
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
