"""P5 L5.5 - typed event -> independent JSON-compatible dict -> replay."""

import json

from pyllmkit.domain.inference import InferenceRunId, Usage
from pyllmkit.domain.streaming import (
    ResponseCompleted,
    ResponseStarted,
    TextDelta,
    UsageUpdated,
    event_from_dict,
    event_to_dict,
    stream_from_dict,
    stream_to_dict,
)


def main() -> None:
    rid = InferenceRunId("offline-codec")
    events = (
        ResponseStarted(run_id=rid, sequence=0),
        TextDelta(run_id=rid, sequence=1, delta="Bonjour "),
        TextDelta(run_id=rid, sequence=2, delta="Python"),
        UsageUpdated(run_id=rid, sequence=3, usage=Usage(output_tokens=2)),
        ResponseCompleted(run_id=rid, sequence=4),
    )
    encoded = stream_to_dict(events, rid)
    decoded_id, decoded_events = stream_from_dict(json.loads(json.dumps(encoded)))
    assert (decoded_id, decoded_events) == (rid, events)
    for event in events:
        assert event_from_dict(event_to_dict(event)) == event
    print("Streaming JSON v1 replay status:", encoded["observed_status"])
    print("Number of typed events:", len(decoded_events))


if __name__ == "__main__":
    main()
