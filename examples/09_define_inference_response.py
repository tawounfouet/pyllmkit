"""P3-L3.2 offline normalized result, not an actual inference run."""

from pyllmkit.domain import (
    FinishReason,
    FinishReasonCode,
    InferenceResponse,
    InferenceRunId,
    TextOutput,
    Usage,
)

response = InferenceResponse(
    run_id=InferenceRunId("example-offline-run"),
    output=TextOutput("Bonjour !"),
    finish_reason=FinishReason(FinishReasonCode.UNKNOWN, "nonstandard_finish"),
    usage=Usage(input_tokens=9, output_tokens=0),
)
assert response.output.kind == "text"
assert response.finish_reason is not None
assert response.finish_reason.code is FinishReasonCode.UNKNOWN
assert response.usage is not None
assert response.usage.total_tokens is None
print("L3.2 offline response constructed. No model was invoked.")
