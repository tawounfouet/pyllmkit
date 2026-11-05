"""Negative schema and invariant checks for independent Inference JSON v1."""

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from typing import cast

import pytest

from pyllmkit.domain import (
    Content,
    DomainValidationError,
    FinishReason,
    FinishReasonCode,
    GenerationConfig,
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
    Usage,
    request_from_dict,
    request_to_dict,
    response_from_dict,
    response_to_dict,
    run_from_dict,
    run_to_dict,
)

T0 = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
T1 = T0 + timedelta(seconds=1)
T2 = T0 + timedelta(seconds=2)


def request() -> InferenceRequest:
    return InferenceRequest(
        ModelTarget(ModelId("model/x")),
        (Message(Role.USER, Content((TextContent("my secret input"),))),),
        GenerationConfig(
            temperature=0.0,
            top_p=0.9,
            top_k=1,
            max_output_tokens=1,
            seed=0,
            stop_sequences=(),
            presence_penalty=0.0,
            frequency_penalty=-1.0,
        ),
    )


def response() -> InferenceResponse:
    return InferenceResponse(
        InferenceRunId("run-a"),
        TextOutput(""),
        FinishReason(FinishReasonCode.UNKNOWN, ""),
        Usage(input_tokens=0, output_tokens=None, total_tokens=None),
    )


def run(state: InferenceRunState) -> InferenceRun:
    fresh = InferenceRun(InferenceRunId("run-a"), request())
    if state is InferenceRunState.CREATED:
        return fresh
    running = fresh.start(T0)
    if state is InferenceRunState.RUNNING:
        return running
    streaming = running.begin_stream(T1)
    if state is InferenceRunState.STREAMING:
        return streaming
    if state is InferenceRunState.COMPLETED:
        return streaming.complete(response(), T2)
    if state is InferenceRunState.FAILED:
        return streaming.fail(InferenceFailure("timeout"), T2)
    return streaming.cancel(T2, "user_request")


@pytest.mark.parametrize("kind", ["request", "response", "run"])
def test_every_canonical_envelope_has_identical_required_fields(kind: str) -> None:
    obj = {
        "request": request_to_dict(request()),
        "response": response_to_dict(response()),
        "run": run_to_dict(run(InferenceRunState.COMPLETED)),
    }[kind]
    decode = {
        "request": request_from_dict,
        "response": response_from_dict,
        "run": run_from_dict,
    }[kind]
    for key in list(obj):
        bad = deepcopy(obj)
        del bad[key]
        with pytest.raises(DomainValidationError, match="missing|required"):
            decode(bad)
    extra = deepcopy(obj)
    extra["injected"] = "value"
    with pytest.raises(DomainValidationError, match="unknown"):
        decode(extra)


@pytest.mark.parametrize("bad", [0, False, 1.0, "1", None, 999])
def test_all_envelopes_reject_invalid_schema_version(bad: object) -> None:
    for canonical, decode in (
        (request_to_dict(request()), request_from_dict),
        (response_to_dict(response()), response_from_dict),
        (run_to_dict(run(InferenceRunState.RUNNING)), run_from_dict),
    ):
        payload = deepcopy(canonical)
        payload["schema_version"] = bad
        with pytest.raises(DomainValidationError, match="schema_version"):
            decode(payload)


def test_wrong_object_types_never_cross_decode_boundaries() -> None:
    for canonical, decode in (
        (request_to_dict(request()), request_from_dict),
        (response_to_dict(response()), response_from_dict),
        (run_to_dict(run(InferenceRunState.COMPLETED)), run_from_dict),
    ):
        payload = deepcopy(canonical)
        payload["object_type"] = "message"
        with pytest.raises(DomainValidationError, match="object_type"):
            decode(payload)


@pytest.mark.parametrize(
    ("target_kind", "id_value"),
    [
        ("model", "model-id"),
        ("deployment", "deploy-id"),
        ("endpoint", "endpoint-id"),
    ],
)
def test_all_target_kinds_preserve_identity(target_kind: str, id_value: str) -> None:
    obj = request_to_dict(request())
    obj["target"] = {"kind": target_kind, "value": id_value}
    restored = request_from_dict(json.loads(json.dumps(obj)))
    assert restored.target.kind == target_kind
    assert request_to_dict(restored)["target"] == {"kind": target_kind, "value": id_value}


@pytest.mark.parametrize("kind", ["unknown", None, True, 0])
def test_invalid_target_kind_rejected(kind: object) -> None:
    payload = request_to_dict(request())
    payload["target"]["kind"] = kind
    with pytest.raises(DomainValidationError):
        request_from_dict(payload)


@pytest.mark.parametrize("value", [False, None, "", " ", 123])
def test_invalid_target_value_rejected(value: object) -> None:
    obj = request_to_dict(request())
    obj["target"]["value"] = value
    with pytest.raises(DomainValidationError):
        request_from_dict(obj)


def test_nested_target_and_config_extra_missing_keys_are_rejected() -> None:
    obj = request_to_dict(request())
    obj["target"]["secrets"] = "no echo"
    with pytest.raises(DomainValidationError, match="unknown"):
        request_from_dict(obj)
    obj = request_to_dict(request())
    del obj["target"]["value"]
    with pytest.raises(DomainValidationError, match="missing"):
        request_from_dict(obj)
    obj = request_to_dict(request())
    obj["generation_config"]["surprise"] = True
    with pytest.raises(DomainValidationError, match="unknown"):
        request_from_dict(obj)
    obj = request_to_dict(request())
    del obj["generation_config"]["seed"]
    with pytest.raises(DomainValidationError, match="missing"):
        request_from_dict(obj)


@pytest.mark.parametrize(
    ("key", "invalid"),
    [
        ("temperature", 0), ("temperature", True), ("temperature", float("nan")),
        ("temperature", float("inf")), ("top_p", 0.0), ("top_p", 2.0),
        ("top_p", False), ("max_output_tokens", 0),
        ("top_k", True), ("seed", 1.0), ("presence_penalty", float("-inf")),
        ("frequency_penalty", "0.0"), ("stop_sequences", ["", "ok"]),
        ("stop_sequences", "none"), ("stop_sequences", ["good", 1]),
    ],
)
def test_invalid_config_never_coerced(key: str, invalid: object) -> None:
    obj = request_to_dict(request())
    obj["generation_config"][key] = invalid
    with pytest.raises(DomainValidationError):
        request_from_dict(obj)


def test_null_config_distinct_from_config_with_all_nulls() -> None:
    obj = request_to_dict(request())
    obj["generation_config"] = None
    assert request_from_dict(obj).generation_config is None
    obj["generation_config"] = request_to_dict(
        InferenceRequest(request().target, request().messages, GenerationConfig())
    )["generation_config"]
    assert request_from_dict(obj).generation_config == GenerationConfig()
    assert request_to_dict(request_from_dict(obj))["generation_config"] is not None


@pytest.mark.parametrize("bad", [[], (), None, [5], [None], "not_a_list", {}])
def test_message_list_rejects_missing_or_invalid_messages(bad: object) -> None:
    obj = request_to_dict(request())
    obj["messages"] = bad
    with pytest.raises(DomainValidationError):
        request_from_dict(obj)


@pytest.mark.parametrize("invalid", ["bogus", True, None, 5])
def test_bad_nested_message_role_yields_sanitized_domain_error(invalid: object) -> None:
    obj = request_to_dict(request())
    obj["messages"][0]["role"] = invalid
    with pytest.raises(DomainValidationError, match="nested Interaction message"):
        request_from_dict(obj)


def test_nested_message_unknown_key_and_bad_media_kind_rejected() -> None:
    obj = request_to_dict(request())
    obj["messages"][0]["unapproved_extension"] = 42
    with pytest.raises(DomainValidationError, match="nested Interaction"):
        request_from_dict(obj)
    obj = request_to_dict(request())
    obj["messages"][0]["content"]["parts"][0]["kind"] = "tool_call"
    with pytest.raises(DomainValidationError, match="nested Interaction"):
        request_from_dict(obj)


@pytest.mark.parametrize("bad", [None, False, 4, {}, {"kind": "image", "text": ""}])
def test_response_output_requires_text_kind_and_exact_text(bad: object) -> None:
    obj = response_to_dict(response())
    obj["output"] = bad
    with pytest.raises(DomainValidationError):
        response_from_dict(obj)


def test_finish_unknown_distinct_from_absent_and_reject_bad_code() -> None:
    obj = response_to_dict(response())
    assert obj["finish_reason"] == {"code": "unknown", "native_reason": ""}
    obj["finish_reason"] = None
    assert response_from_dict(obj).finish_reason is None
    obj["finish_reason"] = {"code": "some_native_unknown", "native_reason": None}
    with pytest.raises(DomainValidationError, match="FinishReasonCode"):
        response_from_dict(obj)


@pytest.mark.parametrize("bad", [-1, True, False, 1.0, "1", float("nan")])
def test_usage_rejects_non_integer_or_negative_tokens(bad: object) -> None:
    obj = response_to_dict(response())
    obj["usage"]["input_tokens"] = bad
    with pytest.raises(DomainValidationError):
        response_from_dict(obj)


def test_usage_missing_and_unknown_fields_rejected() -> None:
    obj = response_to_dict(response())
    del obj["usage"]["total_tokens"]
    with pytest.raises(DomainValidationError, match="missing"):
        response_from_dict(obj)
    obj = response_to_dict(response())
    obj["usage"]["cost_usd"] = 0
    with pytest.raises(DomainValidationError, match="unknown"):
        response_from_dict(obj)


@pytest.mark.parametrize("state", list(InferenceRunState))
def test_six_states_have_valid_strict_json_roundtrip(state: InferenceRunState) -> None:
    original = run(state)
    restored = run_from_dict(run_to_dict(original))
    assert run_to_dict(restored) == run_to_dict(original)
    assert restored.run_id == original.run_id
    assert restored.state is state


@pytest.mark.parametrize(
    ("state", "field", "replacement"),
    [
        (InferenceRunState.CREATED, "started_at", "2026-11-05T10:00:00+00:00"),
        (InferenceRunState.RUNNING, "finished_at", "2026-11-05T10:00:00+00:00"),
        (InferenceRunState.STREAMING, "streaming_started_at", None),
        (InferenceRunState.COMPLETED, "response", None),
        (InferenceRunState.FAILED, "failure", None),
        (InferenceRunState.CANCELLED, "response", {"bad": "payload"}),
    ],
)
def test_invalid_run_state_payload_combinations_rejected(
    state: InferenceRunState, field: str, replacement: object
) -> None:
    obj = run_to_dict(run(state))
    obj[field] = replacement
    with pytest.raises(DomainValidationError):
        run_from_dict(obj)


@pytest.mark.parametrize("invalid", ["2026-11-05T10:00:00", "bad", 0, False, [], "2026-13-05T10:00:00+00:00"])
def test_timestamp_requires_valid_aware_iso8601(invalid: object) -> None:
    obj = run_to_dict(run(InferenceRunState.RUNNING))
    obj["started_at"] = invalid
    with pytest.raises(DomainValidationError):
        run_from_dict(obj)


def test_timestamps_are_normalized_to_utc_preserving_instant() -> None:
    tz = timezone(timedelta(hours=5, minutes=30))
    date = datetime(2026, 11, 5, 18, 30, tzinfo=tz)
    start = InferenceRun(InferenceRunId("run-a"), request()).start(date)
    encoded = run_to_dict(start)
    assert encoded["started_at"] == "2026-11-05T13:00:00+00:00"
    decoded = run_from_dict(encoded)
    assert decoded.started_at == date
    assert decoded.started_at is not None
    assert decoded.started_at.tzinfo == UTC


def test_reversed_timestamps_rejected_on_six_state_invariants() -> None:
    obj = run_to_dict(run(InferenceRunState.COMPLETED))
    obj["finished_at"] = "2026-11-05T09:59:00+00:00"
    with pytest.raises(DomainValidationError, match="precedes"):
        run_from_dict(obj)
    obj = run_to_dict(run(InferenceRunState.FAILED))
    obj["streaming_started_at"] = "2026-11-05T12:00:00+00:00"
    with pytest.raises(DomainValidationError, match="precedes"):
        run_from_dict(obj)


def test_run_correlation_and_failure_object_strict() -> None:
    obj = run_to_dict(run(InferenceRunState.COMPLETED))
    obj["response"]["run_id"] = "wrong-run"
    with pytest.raises(DomainValidationError, match="run_id"):
        run_from_dict(obj)
    obj = run_to_dict(run(InferenceRunState.FAILED))
    obj["failure"]["native_error"] = "secret"
    with pytest.raises(DomainValidationError, match="unknown"):
        run_from_dict(obj)


def test_encoder_rejects_incorrect_domain_root_types() -> None:
    with pytest.raises(DomainValidationError):
        request_to_dict(cast(InferenceRequest, None))
    with pytest.raises(DomainValidationError):
        response_to_dict(cast(InferenceResponse, {}))
    with pytest.raises(DomainValidationError):
        run_to_dict(cast(InferenceRun, "run"))
