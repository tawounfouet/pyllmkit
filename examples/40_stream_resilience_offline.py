"""P7 L7.7 offline local cancellation, using existing M5 event objects."""

from pyllmkit.application.inference import StreamCancellationSignal
from pyllmkit.application.inference.streaming_resilience import iter_resilient
from pyllmkit.domain.inference import InferenceRunId
from pyllmkit.domain.streaming import (
    ResponseCancelled,
    ResponseCompleted,
    ResponseStarted,
    TextDelta,
)


def main() -> None:
    run = InferenceRunId("offline-cancellation-demo")
    signal = StreamCancellationSignal()

    def provider_simulation():
        yield ResponseStarted(run_id=run, sequence=0)
        yield TextDelta(run_id=run, sequence=1, delta="partial")
        yield ResponseCompleted(run_id=run, sequence=2)

    stream = iter_resilient(provider_simulation, run, signal)
    started, partial = next(stream), next(stream)
    assert isinstance(started, ResponseStarted)
    assert isinstance(partial, TextDelta)
    signal.cancel()
    end = list(stream)
    assert len(end) == 1 and isinstance(end[0], ResponseCancelled)
    assert end[0].run_id == run and end[0].sequence == 2
    print("P7 L7.7: local cancellation observed without provider network")


if __name__ == "__main__":
    main()
