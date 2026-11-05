"""Normalized completion reasons and optional verbatim native reason (ADR-017)."""

from dataclasses import dataclass, field
from enum import StrEnum

from pyllmkit.domain.errors import DomainValidationError


class FinishReasonCode(StrEnum):
    """Closed semantic taxonomy; independent of a Run's lifecycle state."""

    STOP = "stop"
    LENGTH = "length"
    TOOL_CALL = "tool_call"
    CONTENT_FILTER = "content_filter"
    CANCELLED = "cancelled"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FinishReason:
    """Known code with optional native source reason; no implicit STOP mapping."""

    code: FinishReasonCode
    native_reason: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.code) is not FinishReasonCode:
            raise DomainValidationError("FinishReason.code must be FinishReasonCode")
        if self.native_reason is not None and type(self.native_reason) is not str:
            raise DomainValidationError("FinishReason.native_reason must be str or None")
