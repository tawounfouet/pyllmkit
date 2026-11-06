"""Explicit adapter dispatch after strict M6 deployment resolution, without I/O."""

from dataclasses import dataclass, field

from pyllmkit.adapters.inference.registry import AdapterRegistry, AdapterRegistryError
from pyllmkit.application.inference.contracts import InvocationPortError, PreparedInvocation
from pyllmkit.domain.inference import InferenceResponse


@dataclass(frozen=True, slots=True)
class RegisteredInferencePort:
    """Sync port composed from a registry; no implicit routing or fallback."""

    registry: AdapterRegistry = field(repr=False)

    def invoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        if type(prepared) is not PreparedInvocation:
            raise TypeError("prepared_invocation_required")
        try:
            adapter = self.registry.resolve_sync(prepared.resolution.deployment)
        except AdapterRegistryError as error:
            raise InvocationPortError(error.code) from None
        return adapter.invoke(prepared)


@dataclass(frozen=True, slots=True)
class RegisteredAsyncInferencePort:
    """Async port that preserves exactly the prepared deployment and RunId."""

    registry: AdapterRegistry = field(repr=False)

    async def ainvoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        if type(prepared) is not PreparedInvocation:
            raise TypeError("prepared_invocation_required")
        try:
            adapter = self.registry.resolve_async(prepared.resolution.deployment)
        except AdapterRegistryError as error:
            raise InvocationPortError(error.code) from None
        return await adapter.ainvoke(prepared)
