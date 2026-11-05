"""P5-L5.1: typed stream events offline, not a provider invocation."""

from pyllmkit.domain.inference import InferenceRunId, Usage
from pyllmkit.domain.streaming import (
    ResponseCompleted,
    ResponseStarted,
    TextDelta,
    UsageUpdated,
)


def main() -> None:
    run_id = InferenceRunId("demo-stream-001")
    events = (
        ResponseStarted(run_id=run_id, sequence=0),
        TextDelta(run_id=run_id, sequence=1, delta="Bon"),
        TextDelta(run_id=run_id, sequence=2, delta="jour !"),
        UsageUpdated(run_id=run_id, sequence=3, usage=Usage(output_tokens=2)),
        ResponseCompleted(run_id=run_id, sequence=4),
    )
    print("typed events:", [event.kind for event in events])
    print("raw text deltas:", [event.delta for event in events if isinstance(event, TextDelta)])
    print("Note: ordering/lifecycle validation will be provided by L5.2.")


if __name__ == "__main__":
    main()
