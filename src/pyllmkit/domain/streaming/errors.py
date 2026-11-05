"""Bounded, payload-free streaming errors (ADR-031/032/038)."""

from pyllmkit.domain.errors import DomainValidationError


class StreamValidationError(DomainValidationError):
    """A streaming invariant was violated; do not disclose raw content."""


class StreamSequenceGap(StreamValidationError):
    """An event sequence number was skipped."""


class StreamDuplicateSequence(StreamValidationError):
    """The immediately preceding sequence number was repeated."""


class StreamOutOfOrder(StreamValidationError):
    """An earlier sequence number was received."""


class StreamRunMismatch(StreamValidationError):
    """The event's run ID does not match the stream's run ID."""


class StreamLifecycleError(StreamValidationError):
    """An event violates stream lifecycle or terminality."""


class StreamToolCallError(StreamValidationError):
    """A tool call is unknown, duplicated or closed."""


class StreamLimitError(StreamValidationError):
    """An explicit resource limit was exceeded."""
