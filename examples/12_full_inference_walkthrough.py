"""L3.5 end-to-end *offline domain* example, not actual model inference."""

import json
from datetime import UTC, datetime, timedelta

from pyllmkit.domain import (
    Content,
    FinishReason,
    FinishReasonCode,
    GenerationConfig,
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
    Usage,
    request_from_dict,
    request_to_dict,
    response_from_dict,
    response_to_dict,
    run_from_dict,
    run_to_dict,
)

request = InferenceRequest(
    target=ModelTarget(ModelId("example/model")),
    messages=(Message(Role.USER, Content((TextContent("Bonjour"),))),),
    generation_config=GenerationConfig(temperature=0.0),
)
request_roundtrip = request_from_dict(
    json.loads(json.dumps(request_to_dict(request), allow_nan=False))
)
assert request_roundtrip == request

run = InferenceRun(InferenceRunId("l35-offline"), request_roundtrip)
t0 = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
running = run.start(t0)
synthetic_response = InferenceResponse(
    run.run_id,
    TextOutput("Synthétique : aucun modèle n'a été appelé."),
    FinishReason(FinishReasonCode.UNKNOWN, "unmapped"),
    Usage(input_tokens=0, output_tokens=None, total_tokens=None),
)
assert response_from_dict(response_to_dict(synthetic_response)) == synthetic_response
completed = running.complete(synthetic_response, t0 + timedelta(seconds=1))
restored = run_from_dict(json.loads(json.dumps(run_to_dict(completed), allow_nan=False)))
assert restored.state is InferenceRunState.COMPLETED
assert restored.response == synthetic_response
assert restored.started_at == t0
assert restored.finished_at == t0 + timedelta(seconds=1)
assert run.state is InferenceRunState.CREATED
assert running.state is InferenceRunState.RUNNING

print("M1/M2/M3 integration PASS: pure, offline, synthetic response, JSON v1.")
