"""Strict offline Inference JSON v1 round-trips, no provider execution."""

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
    ModelTarget(ModelId("example/model")),
    (Message(Role.USER, Content((TextContent("Bonjour"),))),),
    GenerationConfig(temperature=0.0, max_output_tokens=42),
)
decoded_request = request_from_dict(json.loads(json.dumps(request_to_dict(request), allow_nan=False)))
assert decoded_request == request

identity = InferenceRunId("offline-run-001")
response = InferenceResponse(
    identity, TextOutput("Bonjour !"),
    FinishReason(FinishReasonCode.UNKNOWN, "unknown_native"),
    Usage(input_tokens=0, output_tokens=4),
)
decoded_response = response_from_dict(
    json.loads(json.dumps(response_to_dict(response), allow_nan=False))
)
assert decoded_response == response

at = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
completed = InferenceRun(identity, decoded_request).start(at).complete(
    decoded_response, at + timedelta(seconds=2)
)
run_payload = run_to_dict(completed)
restored_run = run_from_dict(json.loads(json.dumps(run_payload, allow_nan=False)))
assert run_to_dict(restored_run) == run_payload
assert restored_run.finished_at == at + timedelta(seconds=2)
print("Inference JSON v1 Request/Response/Run round-trip PASS (offline, no model).")
