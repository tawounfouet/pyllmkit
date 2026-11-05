"""Lightweight stream protocol identity; consumers and adapters are L5.4."""

from collections.abc import Iterator
from typing import Protocol

from pyllmkit.domain.inference import InferenceRunId

from .events import StreamEvent


class InferenceStream(Protocol):
    """Behavioral typed stream abstraction, not an InferenceRun aggregate."""

    @property
    def run_id(self) -> InferenceRunId:
        ...

    def __iter__(self) -> Iterator[StreamEvent]:
        ...
