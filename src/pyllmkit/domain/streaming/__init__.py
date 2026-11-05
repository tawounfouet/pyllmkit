"""Provider-agnostic streaming core: events, ordering and pure reduction."""

from .consumption import (
    MemoryAsyncInferenceStream,
    MemoryInferenceStream,
    consume_async_stream,
    consume_stream,
)
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
from .protocols import (
    AsyncInferenceStream,
    AsyncStreamingPort,
    InferenceStream,
    StreamingPort,
)
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
    "AsyncInferenceStream",
    "AsyncStreamingPort",
    "StreamingPort",
    "MemoryInferenceStream",
    "MemoryAsyncInferenceStream",
    "consume_stream",
    "consume_async_stream",
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
