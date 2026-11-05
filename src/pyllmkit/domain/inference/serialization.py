"""Strict, independent Inference JSON-compatible v1 codec (ADR-020).

Maps domain values to JSON-compatible dicts; the caller owns JSON text I/O.
All canonical fields, including nulls, are mandatory. Provider payloads,
implicit defaults, migrations, network access, and duplicate-key parsing
policies are outside this module.
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from re import fullmatch
from typing import cast

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.interactions import Message, message_from_dict, message_to_dict
from pyllmkit.domain.models import ModelId

from .config import GenerationConfig
from .failure import InferenceFailure
from .finish import FinishReason, FinishReasonCode
from .identifiers import InferenceRunId
from .output import TextOutput
from .request import InferenceRequest
from .response import InferenceResponse
from .run import InferenceRun, InferenceRunState
from .targets import (
    DeploymentId,
    DeploymentTarget,
    EndpointId,
    EndpointTarget,
    InferenceTarget,
    ModelTarget,
)
from .usage import Usage

INFERENCE_SCHEMA_VERSION = 1

_REQUEST_FIELDS = frozenset(
    {"schema_version", "object_type", "target", "messages", "generation_config"}
)
_RESPONSE_FIELDS = frozenset(
    {"schema_version", "object_type", "run_id", "output", "finish_reason", "usage"}
)
_RUN_FIELDS = frozenset(
    {
        "schema_version", "object_type", "run_id", "request", "attempt", "state",
        "started_at", "streaming_started_at", "finished_at", "response", "failure",
        "cancellation_reason_code",
    }
)
_TARGET_FIELDS = frozenset({"kind", "value"})
_OUTPUT_FIELDS = frozenset({"kind", "text"})
_REASON_FIELDS = frozenset({"code", "native_reason"})
_FAILURE_FIELDS = frozenset({"code"})
_CONFIG_FIELDS = frozenset(
    {
        "temperature", "top_p", "top_k", "max_output_tokens", "seed",
        "stop_sequences", "presence_penalty", "frequency_penalty",
    }
)
_USAGE_FIELDS = frozenset(
    {
        "input_tokens", "output_tokens", "total_tokens", "reasoning_tokens",
        "cached_input_tokens",
    }
)
_FLOAT_FIELDS = frozenset(
    {"temperature", "top_p", "presence_penalty", "frequency_penalty"}
)
_INT_CONFIG_FIELDS = frozenset({"top_k", "max_output_tokens", "seed"})
_TIMESTAMP_PATTERN = (
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})"
)


def _object(value: object, label: str) -> Mapping[str, object]:
    """Accept only an actual JSON object with exact string keys."""
    if not isinstance(value, dict) or any(type(k) is not str for k in value):
        raise DomainValidationError(f"{label} must be a JSON object with string keys")
    return cast(Mapping[str, object], value)


def _fields(
    value: object, expected: frozenset[str], label: str
) -> Mapping[str, object]:
    data = _object(value, label)
    if set(data) - expected:
        raise DomainValidationError(f"{label} contains unknown fields")
    if expected - set(data):
        raise DomainValidationError(f"{label} is missing required fields")
    return data


def _envelope(
    value: object, expected: frozenset[str], kind: str
) -> Mapping[str, object]:
    data = _fields(value, expected, kind)
    if type(data["schema_version"]) is not int or (
        data["schema_version"] != INFERENCE_SCHEMA_VERSION
    ):
        raise DomainValidationError("unsupported Inference schema_version")
    if type(data["object_type"]) is not str or data["object_type"] != kind:
        raise DomainValidationError("unsupported Inference object_type")
    return data


def _text(value: object, label: str) -> str:
    if type(value) is not str:
        raise DomainValidationError(f"{label} must be a string")
    return value


def _optional_text(value: object, label: str) -> str | None:
    return None if value is None else _text(value, label)


def _integer(value: object, label: str) -> int:
    if type(value) is not int:
        raise DomainValidationError(f"{label} must be an exact integer")
    return value


def _optional_integer(value: object, label: str) -> int | None:
    return None if value is None else _integer(value, label)


def _optional_float(value: object, label: str) -> float | None:
    if value is None:
        return None
    if type(value) is not float:
        raise DomainValidationError(f"{label} must be an exact float or null")
    return value


def _target_to_dict(target: InferenceTarget) -> dict[str, object]:
    if type(target) is ModelTarget:
        return {"kind": "model", "value": target.model_id.value}
    if type(target) is DeploymentTarget:
        return {"kind": "deployment", "value": target.deployment_id.value}
    if type(target) is EndpointTarget:
        return {"kind": "endpoint", "value": target.endpoint_id.value}
    raise DomainValidationError("unsupported Inference target type")


def _target_from_dict(value: object) -> InferenceTarget:
    data = _fields(value, _TARGET_FIELDS, "target")
    kind = _text(data["kind"], "target.kind")
    identity = _text(data["value"], "target.value")
    if kind == "model":
        return ModelTarget(ModelId(identity))
    if kind == "deployment":
        return DeploymentTarget(DeploymentId(identity))
    if kind == "endpoint":
        return EndpointTarget(EndpointId(identity))
    raise DomainValidationError("unsupported Inference target kind")


def _config_to_dict(config: GenerationConfig) -> dict[str, object]:
    if type(config) is not GenerationConfig:
        raise DomainValidationError("unsupported GenerationConfig type")
    return {
        "temperature": config.temperature,
        "top_p": config.top_p,
        "top_k": config.top_k,
        "max_output_tokens": config.max_output_tokens,
        "seed": config.seed,
        "stop_sequences": (
            list(config.stop_sequences) if config.stop_sequences is not None else None
        ),
        "presence_penalty": config.presence_penalty,
        "frequency_penalty": config.frequency_penalty,
    }


def _config_from_dict(value: object) -> GenerationConfig:
    data = _fields(value, _CONFIG_FIELDS, "generation_config")
    raw_stops = data["stop_sequences"]
    if raw_stops is not None and (
        not isinstance(raw_stops, list)
        or any(type(item) is not str for item in raw_stops)
    ):
        raise DomainValidationError("generation_config.stop_sequences must be an array or null")
    stops = (
        tuple(cast(list[str], raw_stops))
        if raw_stops is not None else None
    )
    return GenerationConfig(
        temperature=_optional_float(data["temperature"], "temperature"),
        top_p=_optional_float(data["top_p"], "top_p"),
        top_k=_optional_integer(data["top_k"], "top_k"),
        max_output_tokens=_optional_integer(data["max_output_tokens"], "max_output_tokens"),
        seed=_optional_integer(data["seed"], "seed"),
        stop_sequences=stops,
        presence_penalty=_optional_float(data["presence_penalty"], "presence_penalty"),
        frequency_penalty=_optional_float(data["frequency_penalty"], "frequency_penalty"),
    )


def request_to_dict(request: InferenceRequest) -> dict[str, object]:
    """Lossless canonical Request v1, nesting complete Interaction v1 messages."""
    if type(request) is not InferenceRequest:
        raise DomainValidationError("request_to_dict expects an InferenceRequest")
    return {
        "schema_version": INFERENCE_SCHEMA_VERSION,
        "object_type": "inference_request",
        "target": _target_to_dict(request.target),
        "messages": [message_to_dict(message) for message in request.messages],
        "generation_config": (
            _config_to_dict(request.generation_config)
            if request.generation_config is not None else None
        ),
    }


def request_from_dict(payload: Mapping[str, object]) -> InferenceRequest:
    """Strict Request decoder. Text parsing and duplicate-key policy belong to caller."""
    data = _envelope(payload, _REQUEST_FIELDS, "inference_request")
    raw_messages = data["messages"]
    if not isinstance(raw_messages, list) or not raw_messages:
        raise DomainValidationError("messages must be a nonempty JSON array")
    messages: list[Message] = []
    for raw in raw_messages:
        # M2's codec can emit ValueError on invalid Role. Do not disclose source data.
        try:
            message = message_from_dict(_object(raw, "message"))
        except (DomainValidationError, ValueError, TypeError):
            raise DomainValidationError("invalid nested Interaction message") from None
        messages.append(message)
    raw_config = data["generation_config"]
    return InferenceRequest(
        target=_target_from_dict(data["target"]),
        messages=tuple(messages),
        generation_config=(
            _config_from_dict(raw_config) if raw_config is not None else None
        ),
    )


def _reason_to_dict(reason: FinishReason) -> dict[str, object]:
    return {"code": reason.code.value, "native_reason": reason.native_reason}


def _reason_from_dict(value: object) -> FinishReason:
    data = _fields(value, _REASON_FIELDS, "finish_reason")
    code = _text(data["code"], "finish_reason.code")
    try:
        normalized = FinishReasonCode(code)
    except ValueError:
        raise DomainValidationError("unsupported FinishReasonCode") from None
    return FinishReason(
        code=normalized,
        native_reason=_optional_text(data["native_reason"], "finish_reason.native_reason"),
    )


def _usage_to_dict(usage: Usage) -> dict[str, object]:
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
    }


def _usage_from_dict(value: object) -> Usage:
    data = _fields(value, _USAGE_FIELDS, "usage")
    return Usage(
        input_tokens=_optional_integer(data["input_tokens"], "input_tokens"),
        output_tokens=_optional_integer(data["output_tokens"], "output_tokens"),
        total_tokens=_optional_integer(data["total_tokens"], "total_tokens"),
        reasoning_tokens=_optional_integer(data["reasoning_tokens"], "reasoning_tokens"),
        cached_input_tokens=_optional_integer(
            data["cached_input_tokens"], "cached_input_tokens"
        ),
    )


def response_to_dict(response: InferenceResponse) -> dict[str, object]:
    """Lossless normalized Response v1, with absence distinct from UNKNOWN."""
    if type(response) is not InferenceResponse:
        raise DomainValidationError("response_to_dict expects an InferenceResponse")
    return {
        "schema_version": INFERENCE_SCHEMA_VERSION,
        "object_type": "inference_response",
        "run_id": response.run_id.value,
        "output": {"kind": "text", "text": response.output.text},
        "finish_reason": (
            _reason_to_dict(response.finish_reason)
            if response.finish_reason is not None else None
        ),
        "usage": _usage_to_dict(response.usage) if response.usage is not None else None,
    }


def response_from_dict(payload: Mapping[str, object]) -> InferenceResponse:
    """Decode Response strictly without inferring finish reason or Usage totals."""
    data = _envelope(payload, _RESPONSE_FIELDS, "inference_response")
    output = _fields(data["output"], _OUTPUT_FIELDS, "output")
    if _text(output["kind"], "output.kind") != "text":
        raise DomainValidationError("unsupported Inference output kind")
    raw_reason, raw_usage = data["finish_reason"], data["usage"]
    return InferenceResponse(
        run_id=InferenceRunId(_text(data["run_id"], "run_id")),
        output=TextOutput(_text(output["text"], "output.text")),
        finish_reason=_reason_from_dict(raw_reason) if raw_reason is not None else None,
        usage=_usage_from_dict(raw_usage) if raw_usage is not None else None,
    )


def _time_to_json(value: datetime | None) -> str | None:
    if value is None:
        return None
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise DomainValidationError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _time_from_json(value: object, label: str) -> datetime | None:
    if value is None:
        return None
    raw = _text(value, label)
    if fullmatch(_TIMESTAMP_PATTERN, raw) is None:
        raise DomainValidationError(f"{label} must be a timezone-aware ISO 8601 timestamp")
    try:
        result = datetime.fromisoformat(raw)
    except ValueError:
        raise DomainValidationError(f"{label} is not a valid datetime") from None
    if result.tzinfo is None or result.utcoffset() is None:
        raise DomainValidationError(f"{label} must be timezone-aware")
    return result.astimezone(UTC)


def run_to_dict(run: InferenceRun) -> dict[str, object]:
    """Serialize all six states, preserving explicit nulls and terminal payloads."""
    if type(run) is not InferenceRun:
        raise DomainValidationError("run_to_dict expects an InferenceRun")
    return {
        "schema_version": INFERENCE_SCHEMA_VERSION,
        "object_type": "inference_run",
        "run_id": run.run_id.value,
        "request": request_to_dict(run.request),
        "attempt": run.attempt,
        "state": run.state.value,
        "started_at": _time_to_json(run.started_at),
        "streaming_started_at": _time_to_json(run.streaming_started_at),
        "finished_at": _time_to_json(run.finished_at),
        "response": response_to_dict(run.response) if run.response is not None else None,
        "failure": {"code": run.failure.code} if run.failure is not None else None,
        "cancellation_reason_code": run.cancellation_reason_code,
    }


def run_from_dict(payload: Mapping[str, object]) -> InferenceRun:
    """Rebuild validated Run snapshot; never bypass aggregate invariants."""
    data = _envelope(payload, _RUN_FIELDS, "inference_run")
    state = _text(data["state"], "run.state")
    try:
        run_state = InferenceRunState(state)
    except ValueError:
        raise DomainValidationError("unsupported InferenceRun state") from None
    raw_response, raw_failure = data["response"], data["failure"]
    failure = None
    if raw_failure is not None:
        failure_data = _fields(raw_failure, _FAILURE_FIELDS, "failure")
        failure = InferenceFailure(_text(failure_data["code"], "failure.code"))
    return InferenceRun(
        run_id=InferenceRunId(_text(data["run_id"], "run_id")),
        request=request_from_dict(_object(data["request"], "request")),
        attempt=_integer(data["attempt"], "attempt"),
        state=run_state,
        started_at=_time_from_json(data["started_at"], "started_at"),
        streaming_started_at=_time_from_json(
            data["streaming_started_at"], "streaming_started_at"
        ),
        finished_at=_time_from_json(data["finished_at"], "finished_at"),
        response=(
            response_from_dict(_object(raw_response, "response"))
            if raw_response is not None else None
        ),
        failure=failure,
        cancellation_reason_code=_optional_text(
            data["cancellation_reason_code"], "cancellation_reason_code"
        ),
    )
