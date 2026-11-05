"""P3-AC-021..028: strict Inference JSON v1 and compatibility regression."""

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from pyllmkit.domain import (
    INFERENCE_SCHEMA_VERSION,
    INTERACTION_SCHEMA_VERSION,
    Content,
    DomainValidationError,
    FinishReason,
    FinishReasonCode,
    GenerationConfig,
    ImageContent,
    InferenceFailure,
    InferenceRequest,
    InferenceResponse,
    InferenceRun,
    InferenceRunId,
    MediaSourceRef,
    Message,
    ModelId,
    ModelTarget,
    Role,
    TextContent,
    TextOutput,
    Usage,
    message_from_dict,
    message_to_dict,
    request_from_dict,
    request_to_dict,
    response_from_dict,
    response_to_dict,
    run_from_dict,
    run_to_dict,
)
from pyllmkit.domain.inference import InferenceRunState
from pyllmkit.domain.models.serialization import SCHEMA_VERSION as MODEL_SCHEMA_VERSION

T0 = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
T1 = T0 + timedelta(milliseconds=500)
T2 = T0 + timedelta(seconds=2)


def _request() -> InferenceRequest:
    message = Message(
        Role.USER,
        Content((
            TextContent("Bonjour 👋"),
            ImageContent(MediaSourceRef("asset", "image-001")),
            TextContent("Bonjour 👋"),
        )),
    )
    return InferenceRequest(
        ModelTarget(ModelId("example/model")),
        (message, message),
        GenerationConfig(
            temperature=0.0,
            top_p=1.0,
            top_k=1,
            max_output_tokens=123,
            seed=0,
            stop_sequences=("A", "A"),
            presence_penalty=0.0,
            frequency_penalty=-0.2,
        ),
    )


def _response(run_id: str = "run-123") -> InferenceResponse:
    return InferenceResponse(
        InferenceRunId(run_id),
        TextOutput("Résultat\n😀"),
        FinishReason(FinishReasonCode.UNKNOWN, "native_unknown_reason"),
        Usage(input_tokens=0, output_tokens=None, total_tokens=None, cached_input_tokens=0),
    )


def _runs() -> tuple[InferenceRun, ...]:
    created = InferenceRun(InferenceRunId("run-123"), _request())
    running = created.start(T0)
    streaming = running.begin_stream(T1)
    return (
        created,
        running,
        streaming,
        running.complete(_response(), T2),
        streaming.fail(InferenceFailure("provider_unavailable"), T2),
        streaming.cancel(T2, cancellation_reason_code="user_request"),
    )


def test_p3_ac021_request_json_roundtrip_preserves_order_and_all_config_values() -> None:
    request = _request()
    canonical = request_to_dict(request)
    assert canonical["schema_version"] == INFERENCE_SCHEMA_VERSION == 1
    assert canonical["object_type"] == "inference_request"
    assert canonical["messages"] == [
        message_to_dict(request.messages[0]),
        message_to_dict(request.messages[1]),
    ]
    restored = request_from_dict(json.loads(json.dumps(canonical, allow_nan=False)))
    assert restored == request
    assert request_to_dict(restored) == canonical
    assert restored.messages[0] == restored.messages[1]
    assert restored.messages[0].content.parts[0] == restored.messages[0].content.parts[2]
    assert restored.generation_config == request.generation_config


def test_p3_ac022_response_json_roundtrip_preserves_native_reason_and_nullable_usage() -> None:
    response = _response()
    canonical = response_to_dict(response)
    assert canonical["output"] == {"kind": "text", "text": "Résultat\n😀"}
    assert canonical["finish_reason"] == {
        "code": "unknown", "native_reason": "native_unknown_reason",
    }
    assert response_from_dict(json.loads(json.dumps(canonical, allow_nan=False))) == response
    assert response_to_dict(response_from_dict(canonical)) == canonical
    assert canonical["usage"]["input_tokens"] == 0
    assert canonical["usage"]["total_tokens"] is None


@pytest.mark.parametrize("state", list(InferenceRunState))
def test_run_v1_six_states_roundtrip_through_json_with_exact_payload(state: InferenceRunState) -> None:
    run = next(item for item in _runs() if item.state is state)
    canonical = run_to_dict(run)
    restored = run_from_dict(json.loads(json.dumps(canonical, allow_nan=False)))
    assert restored.run_id == run.run_id
    assert restored.request == run.request
    assert restored.state is state
    assert restored.started_at == run.started_at
    assert restored.streaming_started_at == run.streaming_started_at
    assert restored.finished_at == run.finished_at
    assert restored.response == run.response
    assert restored.failure == run.failure
    assert restored.cancellation_reason_code == run.cancellation_reason_code
    assert run_to_dict(restored) == canonical


def test_p3_ac023_unknown_version_and_extra_fields_are_rejected() -> None:
    payload = request_to_dict(_request())
    for version in (0, 2, True, None, "1"):
        bad = deepcopy(payload)
        bad["schema_version"] = version
        with pytest.raises(DomainValidationError):
            request_from_dict(bad)
    extra = deepcopy(payload)
    extra["provider_secret"] = "DO_NOT_ECHO"
    with pytest.raises(DomainValidationError) as exc:
        request_from_dict(extra)
    assert "DO_NOT_ECHO" not in str(exc.value)
    bad = response_to_dict(_response())
    bad["new_key"] = "DO_NOT_ECHO"
    with pytest.raises(DomainValidationError):
        response_from_dict(bad)
    run = run_to_dict(_runs()[3])
    run["state"] = "unrecognized"
    with pytest.raises(DomainValidationError):
        run_from_dict(run)


def test_p3_ac024_existing_interaction_and_model_v1_contracts_unchanged() -> None:
    assert INTERACTION_SCHEMA_VERSION == 1
    assert MODEL_SCHEMA_VERSION == 1
    message = _request().messages[0]
    canonical = message_to_dict(message)
    assert message_from_dict(json.loads(json.dumps(canonical, allow_nan=False))) == message
    assert canonical["object_type"] == "message"
    assert canonical["schema_version"] == 1
    assert INFERENCE_SCHEMA_VERSION == 1
    assert request_to_dict(_request())["object_type"] == "inference_request"


def test_p3_ac025_offline_construction_needs_no_credentials_or_io() -> None:
    run = _runs()[3]
    assert run_to_dict(run)["object_type"] == "inference_run"
    assert run_from_dict(run_to_dict(run)).state is InferenceRunState.COMPLETED
    assert not hasattr(run, "provider_client")
    assert not hasattr(run, "http_client")


def test_p3_ac026_root_and_subpackage_exports_alias_same_functions() -> None:
    from pyllmkit.domain.inference import request_from_dict as canonical_request_from_dict
    from pyllmkit.domain.inference import request_to_dict as canonical_request_to_dict
    from pyllmkit.domain.inference import response_from_dict as canonical_response_from_dict
    from pyllmkit.domain.inference import response_to_dict as canonical_response_to_dict
    from pyllmkit.domain.inference import run_from_dict as canonical_run_from_dict
    from pyllmkit.domain.inference import run_to_dict as canonical_run_to_dict

    assert request_from_dict is canonical_request_from_dict
    assert request_to_dict is canonical_request_to_dict
    assert response_from_dict is canonical_response_from_dict
    assert response_to_dict is canonical_response_to_dict
    assert run_from_dict is canonical_run_from_dict
    assert run_to_dict is canonical_run_to_dict


def test_p3_ac027_secrets_are_never_echoed_in_validation_errors() -> None:
    secret = "https://provider.example/secret?token=DONT_PRINT_ME"
    raw = request_to_dict(_request())
    raw["target"]["value"] = secret
    raw["messages"][0]["content"]["parts"][0]["kind"] = secret
    with pytest.raises(DomainValidationError) as exc:
        request_from_dict(raw)
    assert secret not in str(exc.value)
    assert "DONT_PRINT_ME" not in str(exc.value)

    response = response_to_dict(_response())
    response["finish_reason"]["code"] = secret
    with pytest.raises(DomainValidationError) as exc:
        response_from_dict(response)
    assert secret not in str(exc.value)


def test_p3_ac028_unknown_nested_content_kind_is_rejected_not_skipped() -> None:
    original = request_to_dict(_request())
    payload = deepcopy(original)
    payload["messages"][0]["content"]["parts"][1]["kind"] = "tool"
    with pytest.raises(DomainValidationError, match="nested Interaction message"):
        request_from_dict(payload)
    assert payload["messages"][0]["content"]["parts"] != (
        original["messages"][0]["content"]["parts"]
    )
