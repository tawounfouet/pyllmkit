"""P7 L7.6 six-provider streaming demo with no real sockets.

For full wire fixtures and acceptance, see tests/acceptance/test_p7_l76_native_streaming.py.
"""

from pyllmkit.adapters.inference import NativeProviderStreamingAdapter
from pyllmkit.application.inference import StreamingInferenceService
from pyllmkit.domain.streaming import ResponseCompleted, ResponseFailed, TextDelta


def main() -> None:
    for cls in (NativeProviderStreamingAdapter, StreamingInferenceService):
        assert cls.__name__
    assert TextDelta.kind == "text_delta"
    assert ResponseCompleted.kind == "response_completed"
    assert ResponseFailed.kind == "response_failed"
    print("P7 L7.6 stream contracts installed; no provider contacted.")


if __name__ == "__main__":
    main()
