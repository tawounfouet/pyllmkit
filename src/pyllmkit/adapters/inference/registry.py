"""Explicit executable adapter registrations, distinct from P6 provider catalogs."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from pyllmkit.adapters.inference.security import (
    ProviderConnectionConfig,
    ProviderProfile,
)
from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.providers import ProviderId
from pyllmkit.protocols.inference import AsyncInferencePort, InferencePort


class AdapterRegistryError(LookupError):
    """Code-only registry and composition failure, with no SDK error details."""


@dataclass(frozen=True, slots=True)
class AdapterKey:
    """Exact deployment binding: provider identity and/or named local runtime."""

    provider_id: ProviderId | None = None
    runtime: str | None = None

    def __post_init__(self) -> None:
        if self.provider_id is None and self.runtime is None:
            raise AdapterRegistryError("adapter_key_empty")
        if self.provider_id is not None and type(self.provider_id) is not ProviderId:
            raise AdapterRegistryError("adapter_key_invalid")
        if self.runtime is not None and (
            type(self.runtime) is not str
            or re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", self.runtime) is None
        ):
            raise AdapterRegistryError("adapter_key_invalid")

    @classmethod
    def from_deployment(cls, deployment: Deployment) -> AdapterKey:
        if type(deployment) is not Deployment:
            raise AdapterRegistryError("deployment_invalid")
        return cls(deployment.provider_id, deployment.runtime)


SyncAdapterFactory = Callable[[ProviderConnectionConfig], InferencePort]
AsyncAdapterFactory = Callable[[ProviderConnectionConfig], AsyncInferencePort]


@dataclass(frozen=True, slots=True)
class AdapterRegistration:
    """One explicit connection profile and lazily invoked adapter factory."""

    key: AdapterKey
    connection: ProviderConnectionConfig = field(repr=False)
    sync_factory: SyncAdapterFactory | None = field(default=None, repr=False)
    async_factory: AsyncAdapterFactory | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.key) is not AdapterKey:
            raise AdapterRegistryError("adapter_key_invalid")
        if type(self.connection) is not ProviderConnectionConfig:
            raise AdapterRegistryError("connection_invalid")
        if self.sync_factory is None and self.async_factory is None:
            raise AdapterRegistryError("adapter_factory_missing")
        if self.sync_factory is not None and not callable(self.sync_factory):
            raise AdapterRegistryError("adapter_factory_invalid")
        if self.async_factory is not None and not callable(self.async_factory):
            raise AdapterRegistryError("adapter_factory_invalid")
        if self.connection.profile is ProviderProfile.OLLAMA:
            if self.key.runtime != "ollama":
                raise AdapterRegistryError("adapter_profile_mismatch")
        elif self.key.provider_id is None:
            raise AdapterRegistryError("adapter_profile_mismatch")


class AdapterRegistry:
    """In-memory composition registry; never performs discovery or I/O."""

    __slots__ = ("_registrations",)

    def __init__(self) -> None:
        self._registrations: dict[AdapterKey, AdapterRegistration] = {}

    def register(self, registration: AdapterRegistration) -> None:
        if type(registration) is not AdapterRegistration:
            raise AdapterRegistryError("registration_invalid")
        if registration.key in self._registrations:
            raise AdapterRegistryError("adapter_already_registered")
        self._registrations[registration.key] = registration

    def list_keys(self) -> tuple[AdapterKey, ...]:
        return tuple(sorted(
            self._registrations,
            key=lambda key: (
                "" if key.provider_id is None else key.provider_id.value,
                "" if key.runtime is None else key.runtime,
            ),
        ))

    def _lookup(self, deployment: Deployment) -> AdapterRegistration:
        key = AdapterKey.from_deployment(deployment)
        try:
            return self._registrations[key]
        except KeyError:
            raise AdapterRegistryError("adapter_not_registered") from None

    def resolve_sync(self, deployment: Deployment) -> InferencePort:
        registration = self._lookup(deployment)
        factory = registration.sync_factory
        if factory is None:
            raise AdapterRegistryError("sync_adapter_unavailable")
        try:
            port = factory(registration.connection)
        except Exception:
            raise AdapterRegistryError("adapter_initialization_failed") from None
        if not isinstance(port, InferencePort):
            raise AdapterRegistryError("adapter_factory_invalid")
        return port

    def resolve_async(self, deployment: Deployment) -> AsyncInferencePort:
        registration = self._lookup(deployment)
        factory = registration.async_factory
        if factory is None:
            raise AdapterRegistryError("async_adapter_unavailable")
        try:
            port = factory(registration.connection)
        except Exception:
            raise AdapterRegistryError("adapter_initialization_failed") from None
        if not isinstance(port, AsyncInferencePort):
            raise AdapterRegistryError("adapter_factory_invalid")
        return port
