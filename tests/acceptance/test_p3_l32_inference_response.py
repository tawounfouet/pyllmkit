"""P3-AC-008..013, L3.2: normalized inference response, no provider SDK."""

from typing import cast

import pytest

from pyllmkit.domain import (
    DomainValidationError,
    FinishReason,
    FinishReasonCode,
    InferenceResponse,
    InferenceRunId,
    TextOutput,
    Usage,
)


def test_p3_ac008_text_response_without_provider_sdk() -> None:
    response = InferenceResponse(InferenceRunId("run-008"), TextOutput("Bonjour !"))
    assert response.output.text == "Bonjour !"
    assert response.output.kind == "text"
    assert response.run_id.value == "run-008"


def test_p3_ac009_unknown_reason_preserves_native_and_is_not_stop() -> None:
    response = InferenceResponse(
        InferenceRunId("run-009"),
        TextOutput(""),
        FinishReason(FinishReasonCode.UNKNOWN, "unmapped_provider_code"),
    )
    assert response.finish_reason is not None
    assert response.finish_reason.code is FinishReasonCode.UNKNOWN
    assert response.finish_reason.native_reason == "unmapped_provider_code"
    assert response.finish_reason.code is not FinishReasonCode.STOP


def test_p3_ac010_usage_completely_absent_is_none() -> None:
    response = InferenceResponse(InferenceRunId("run-010"), TextOutput("ok"))
    assert response.usage is None
    assert response.finish_reason is None
    assert response.output.text == "ok"


def test_p3_ac011_partial_usage_never_infers_total() -> None:
    response = InferenceResponse(
        InferenceRunId("run-011"),
        TextOutput("ok"),
        usage=Usage(input_tokens=8, cached_input_tokens=0),
    )
    assert response.usage is not None
    assert response.usage.input_tokens == 8
    assert response.usage.cached_input_tokens == 0
    assert response.usage.output_tokens is None
    assert response.usage.total_tokens is None


@pytest.mark.parametrize("bad", [-1, True, 1.0])
def test_p3_ac012_negative_bool_and_float_usage_rejected(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="input_tokens"):
        Usage(input_tokens=cast(int, bad))


def test_p3_ac013_usage_excludes_pricing_and_cost() -> None:
    usage = Usage(input_tokens=5, output_tokens=0, total_tokens=2)
    assert usage.total_tokens == 2  # Observed, never recomputed to 5.
    assert not hasattr(usage, "pricing")
    assert not hasattr(usage, "cost")
    assert not hasattr(usage, "price")
