"""P3-L3.3 offline run lifecycle, no model or provider is contacted."""

from datetime import UTC, datetime, timedelta

from pyllmkit.domain import (
    Content,
    InferenceFailure,
    InferenceRequest,
    InferenceResponse,
    InferenceRun,
    InferenceRunId,
    InferenceRunState,
    Message,
    ModelId,
    ModelTarget,
    Role,
    TextContent,
    TextOutput,
)

request = InferenceRequest(
    ModelTarget(ModelId("offline/llm")),
    (Message(Role.USER, Content((TextContent("Bonjour"),))),),
)
at = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
created = InferenceRun(InferenceRunId("example-run"), request)
running = created.start(at)
completed = running.complete(
    InferenceResponse(created.run_id, TextOutput("Bonjour !")),
    at + timedelta(seconds=1),
)
assert (created.state, running.state, completed.state) == (
    InferenceRunState.CREATED,
    InferenceRunState.RUNNING,
    InferenceRunState.COMPLETED,
)
assert created == completed  # Entity identity, not snapshot state.
assert created.started_at is None
assert completed.finished_at == at + timedelta(seconds=1)

another = InferenceRun(InferenceRunId("different-run"), request)
failed = another.start(at).fail(InferenceFailure("model_unavailable"), at)
assert failed.state is InferenceRunState.FAILED
assert failed.response is None
print("L3.3 pure Run transitions validated offline; no model was invoked.")
