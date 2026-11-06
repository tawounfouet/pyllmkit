"""Deterministic in-process adapter, explicitly NOT a live provider."""

from dataclasses import dataclass, field

from pyllmkit.application.inference import (
    InvocationCancelledError,
    InvocationPortError,
    PreparedInvocation,
)
from pyllmkit.domain.inference import InferenceResponse, TextOutput


@dataclass(slots=True)
class FakeInferenceAdapter:
    """A contract test double: no sockets, SDK imports, or provider discovery."""

    response_text: str = field(default="fake-response", repr=False)
    failure_code: str | None = None
    cancelled: bool = False
    calls: list[PreparedInvocation] = field(default_factory=list, repr=False)

    def invoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        self.calls.append(prepared)
        if self.cancelled:
            raise InvocationCancelledError()
        if self.failure_code is not None:
            raise InvocationPortError(self.failure_code)
        return InferenceResponse(prepared.context.run_id, TextOutput(self.response_text))


@dataclass(slots=True)
class AsyncFakeInferenceAdapter:
    """An awaitable test double that performs no network I/O."""

    response_text: str = field(default="fake-response", repr=False)
    failure_code: str | None = None
    cancelled: bool = False
    calls: list[PreparedInvocation] = field(default_factory=list, repr=False)

    async def ainvoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        self.calls.append(prepared)
        if self.cancelled:
            raise InvocationCancelledError()
        if self.failure_code is not None:
            raise InvocationPortError(self.failure_code)
        return InferenceResponse(prepared.context.run_id, TextOutput(self.response_text))
