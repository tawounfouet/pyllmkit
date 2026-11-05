"""Provider-agnostic streaming core: events, ordering and pure reduction."""

from .errors import (
    StreamDuplicateSequence,
    StreamLifecycleError,
    StreamLimitError,
    StreamOutOfOrder,
    StreamRunMismatch,
    StreamSequenceGap,
    StreamToolCallError,
    StreamValidationError,
)
from .events import (
    ResponseCancelled,
    ResponseCompleted,
    ResponseFailed,
    ResponseStarted,
    StreamEvent,
    TextDelta,
    ToolCallCompleted,
    ToolCallDelta,
    ToolCallStarted,
    UsageUpdated,
)
from .protocols import InferenceStream
from .reconstruction import (
    StreamState,
    StreamStatus,
    ToolCallProgress,
    observe_eof,
    reduce_event,
    reduce_stream,
)

__all__ = [
    "InferenceStream",
    "ResponseCancelled",
    "ResponseCompleted",
    "ResponseFailed",
    "ResponseStarted",
    "StreamDuplicateSequence",
    "StreamEvent",
    "StreamLifecycleError",
    "StreamLimitError",
    "StreamOutOfOrder",
    "StreamRunMismatch",
    "StreamSequenceGap",
    "StreamState",
    "StreamStatus",
    "StreamToolCallError",
    "StreamValidationError",
    "TextDelta",
    "ToolCallCompleted",
    "ToolCallDelta",
    "ToolCallProgress",
    "ToolCallStarted",
    "UsageUpdated",
    "observe_eof",
    "reduce_event",
    "reduce_stream",
]
