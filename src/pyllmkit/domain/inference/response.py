"""Immutable run-correlated inference result with no own lifecycle (ADR-014/017/018)."""

from dataclasses import dataclass, field

from pyllmkit.domain.errors import DomainValidationError

from .finish import FinishReason
from .identifiers import InferenceRunId
from .output import TextOutput
from .usage import Usage


@dataclass(frozen=True, slots=True)
class InferenceResponse:
    """One result for a supplied RunId, without provider metadata or I/O.

    L3.3 will validate that run.id matches response.run_id at completion.
    A response alone does not claim the run has actually completed.
    """

    run_id: InferenceRunId
    output: TextOutput = field(repr=False)
    finish_reason: FinishReason | None = None
    usage: Usage | None = None

    def __post_init__(self) -> None:
        if type(self.run_id) is not InferenceRunId:
            raise DomainValidationError("InferenceResponse.run_id must be InferenceRunId")
        if type(self.output) is not TextOutput:
            raise DomainValidationError("InferenceResponse.output must be TextOutput")
        if self.finish_reason is not None and type(self.finish_reason) is not FinishReason:
            raise DomainValidationError(
                "InferenceResponse.finish_reason must be FinishReason or None"
            )
        if self.usage is not None and type(self.usage) is not Usage:
            raise DomainValidationError("InferenceResponse.usage must be Usage or None")
