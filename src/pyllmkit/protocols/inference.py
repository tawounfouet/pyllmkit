"""Execution contracts independent of provider SDKs (P7 L7.1, ADR-050).

The PreparedInvocation type is owned by the application. TYPE_CHECKING keeps
runtime imports directed outward: application -> protocols -> domain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pyllmkit.domain.inference import InferenceResponse

if TYPE_CHECKING:
    from pyllmkit.application.inference.contracts import PreparedInvocation


@runtime_checkable
class InferencePort(Protocol):
    """One already-prepared synchronous invocation, without hidden resolution."""

    def invoke(self, prepared: PreparedInvocation) -> InferenceResponse: ...


@runtime_checkable
class AsyncInferencePort(Protocol):
    """One asynchronous invocation, with identical input and output invariants."""

    async def ainvoke(self, prepared: PreparedInvocation) -> InferenceResponse: ...
