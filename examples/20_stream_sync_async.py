"""P5 L5.4: offline sync and async event streams have identical semantics."""

import asyncio

from pyllmkit.domain.inference import InferenceRunId, Usage
from pyllmkit.domain.streaming import (
    MemoryAsyncInferenceStream,
    MemoryInferenceStream,
    ResponseCompleted,
    ResponseStarted,
    TextDelta,
    UsageUpdated,
    consume_async_stream,
    consume_stream,
)


async def main() -> None:
    rid = InferenceRunId("example-l54")
    events = (
        ResponseStarted(run_id=rid, sequence=0),
        TextDelta(run_id=rid, sequence=1, delta="Bonjour "),
        TextDelta(run_id=rid, sequence=2, delta="les agents"),
        UsageUpdated(run_id=rid, sequence=3, usage=Usage(output_tokens=3)),
        ResponseCompleted(run_id=rid, sequence=4),
    )
    synchronous = consume_stream(MemoryInferenceStream(rid, events))
    asynchronous = await consume_async_stream(MemoryAsyncInferenceStream(rid, events))
    assert asynchronous == synchronous
    assert asynchronous.is_complete
    print("sync + async:", asynchronous.text)
    interrupted = await consume_async_stream(
        MemoryAsyncInferenceStream(rid, events), max_events=2
    )
    assert not interrupted.is_complete
    print("interrupted stream status:", interrupted.status.value)


if __name__ == "__main__":
    asyncio.run(main())
