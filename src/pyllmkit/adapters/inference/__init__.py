"""L7.1 pure fake adapters for offline inference contract testing."""

from .fake import AsyncFakeInferenceAdapter, FakeInferenceAdapter

__all__ = ["FakeInferenceAdapter", "AsyncFakeInferenceAdapter"]
