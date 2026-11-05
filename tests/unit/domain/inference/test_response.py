"""ADR-014/017/018: immutable output correlated to exactly one RunId."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import DomainValidationError
from pyllmkit.domain.inference import (
    FinishReason,
    FinishReasonCode,
    InferenceResponse,
    InferenceRunId,
    TextOutput,
    Usage,
)


def test_response_with_only_required_values_and_empty_text() -> None:
    response = InferenceResponse(InferenceRunId("run-1"), TextOutput(""))
    assert response.run_id == InferenceRunId("run-1")
    assert response.output == TextOutput("")
    assert response.finish_reason is None
    assert response.usage is None
    assert not hasattr(response, "state")
    assert not hasattr(response, "provider")


def test_full_response_is_value_object_without_provider_exposure() -> None:
    response = InferenceResponse(
        InferenceRunId("run-77"),
        TextOutput("Réponse 🎉"),
        FinishReason(FinishReasonCode.UNKNOWN, "vendor_reason"),
        Usage(input_tokens=4, output_tokens=0),
    )
    copy = InferenceResponse(
        InferenceRunId("run-77"),
        TextOutput("Réponse 🎉"),
        FinishReason(FinishReasonCode.UNKNOWN, "vendor_reason"),
        Usage(input_tokens=4, output_tokens=0),
    )
    assert response == copy
    assert hash(response) == hash(copy)
    assert response.usage is not None
    assert response.usage.output_tokens == 0
    assert response.usage.total_tokens is None
    assert response.run_id.value == "run-77"
    assert "Réponse 🎉" not in repr(response)
    assert "vendor_reason" not in repr(response)


def test_run_identity_distinguishes_equivalent_outputs() -> None:
    first = InferenceResponse(InferenceRunId("run-one"), TextOutput("same"))
    second = InferenceResponse(InferenceRunId("run-two"), TextOutput("same"))
    assert first != second


@pytest.mark.parametrize("bad", ["", "  ", "\t", None, False, 0, {}])
def test_run_id_requires_exact_nonblank_string(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="InferenceRunId"):
        InferenceRunId(cast(str, bad))


def test_run_id_value_object_is_immutable_and_hashable() -> None:
    key = InferenceRunId("run-1")
    assert key == InferenceRunId("run-1")
    assert hash(key) == hash(InferenceRunId("run-1"))
    assert str(key) == "run-1"
    with pytest.raises(FrozenInstanceError):
        key.value = "run-2"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "bad", "error"),
    [
        ("run_id", None, "run_id"),
        ("run_id", "run-1", "run_id"),
        ("output", None, "output"),
        ("output", "text", "output"),
        ("finish_reason", "STOP", "finish_reason"),
        ("finish_reason", FinishReasonCode.STOP, "finish_reason"),
        ("usage", {}, "usage"),
        ("usage", 0, "usage"),
    ],
)
def test_response_fields_reject_wrong_type(field: str, bad: object, error: str) -> None:
    fields: dict[str, object] = {
        "run_id": InferenceRunId("run-1"), "output": TextOutput("x"),
        "finish_reason": None, "usage": None,
    }
    fields[field] = bad
    with pytest.raises(DomainValidationError, match=error):
        InferenceResponse(
            cast(InferenceRunId, fields["run_id"]),
            cast(TextOutput, fields["output"]),
            cast(FinishReason | None, fields["finish_reason"]),
            cast(Usage | None, fields["usage"]),
        )


def test_response_is_immutable_and_does_not_generate_run_id() -> None:
    response = InferenceResponse(InferenceRunId("explicit"), TextOutput("ok"))
    with pytest.raises(FrozenInstanceError):
        response.output = TextOutput("changed")  # type: ignore[misc]
    assert response.run_id.value == "explicit"
