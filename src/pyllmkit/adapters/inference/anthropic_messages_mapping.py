"""Strict Anthropic Messages API text-only mapping for P7 L7.5 (ADR-054).

Pure wire-format conversion with no SDK, HTTP, hidden reasoning or tool calls.
Unsupported semantic mappings fail closed instead of altering message history.
"""

from __future__ import annotations

import json
import re

from pyllmkit.adapters.inference.strict_json import decode_provider_json_object
from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.domain.capabilities import SupportLevel
from pyllmkit.domain.inference import (
    FinishReason,
    FinishReasonCode,
    InferenceResponse,
    TextOutput,
    Usage,
)
from pyllmkit.domain.interactions import Role, TextContent

_MODEL_ALIAS = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}")
_SAFE_NATIVE_REASON = re.compile(r"[a-z][a-z0-9_]{0,39}")
_NATIVE_FIELDS = frozenset({
    "max_output_tokens", "temperature", "top_p", "top_k", "stop_sequences",
})
_USAGE_FIELDS = frozenset({
    "input_tokens", "output_tokens", "cache_read_input_tokens",
    "cache_creation_input_tokens", "output_tokens_details",
})


def _require_native(prepared: PreparedInvocation, name: str) -> None:
    levels = {
        item.name: item.level for item in prepared.parameter_assessment.assessments
    }
    if levels.get(name) is not SupportLevel.NATIVE:
        raise InvocationPortError("unknown_generation_parameter")


def encode_anthropic_messages_request(prepared: PreparedInvocation) -> bytes:
    """Single leading system part, alternating user/assistant, explicit max_tokens."""
    if type(prepared) is not PreparedInvocation:
        raise InvocationPortError("adapter_protocol_error")
    model = prepared.native_model_alias
    if type(model) is not str or _MODEL_ALIAS.fullmatch(model) is None:
        raise InvocationPortError("invalid_model_alias")
    config = prepared.request.generation_config
    if config is None or config.max_output_tokens is None:
        raise InvocationPortError("max_tokens_required")
    _require_native(prepared, "max_output_tokens")

    history: list[dict[str, object]] = []
    system_text: str | None = None
    previous_role: Role | None = None
    for idx, message in enumerate(prepared.request.messages):
        if len(message.content.parts) != 1:
            raise InvocationPortError("unsupported_content_structure")
        part = message.content.parts[0]
        if type(part) is not TextContent:
            raise InvocationPortError("unsupported_input_modality")
        if message.role is Role.SYSTEM:
            if idx != 0 or system_text is not None:
                raise InvocationPortError("unsupported_message_structure")
            system_text = part.text
            continue
        if message.role not in (Role.USER, Role.ASSISTANT):
            raise InvocationPortError("unsupported_message_role")
        if previous_role is None and message.role is not Role.USER:
            raise InvocationPortError("unsupported_message_structure")
        if previous_role is message.role:
            raise InvocationPortError("unsupported_message_structure")
        previous_role = message.role
        history.append({
            "role": message.role.value,
            "content": [{"type": "text", "text": part.text}],
        })
    if not history or previous_role is not Role.USER:
        raise InvocationPortError("unsupported_message_structure")

    payload: dict[str, object] = {
        "model": model,
        "max_tokens": config.max_output_tokens,
        "messages": history,
        "stream": False,
    }
    if system_text is not None:
        payload["system"] = [{"type": "text", "text": system_text}]
    for name in (
        "temperature", "top_p", "top_k", "stop_sequences",
        "seed", "presence_penalty", "frequency_penalty",
    ):
        value = getattr(config, name)
        if value is None:
            continue
        if name not in _NATIVE_FIELDS:
            raise InvocationPortError("unsupported_generation_parameter")
        _require_native(prepared, name)
        payload[name] = value
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _count(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise InvocationPortError("provider_protocol_error")
    return value


def _parse_usage(raw: object) -> Usage | None:
    if raw is None:
        return None
    if type(raw) is not dict:
        raise InvocationPortError("provider_protocol_error")
    input_tokens = _count(raw.get("input_tokens"))
    output_tokens = _count(raw.get("output_tokens"))
    cached = _count(raw.get("cache_read_input_tokens"))
    creation = _count(raw.get("cache_creation_input_tokens"))
    # Creation counts are not representable in the current Usage value object.
    if creation not in (None, 0):
        raise InvocationPortError("unsupported_provider_usage")
    output_details = raw.get("output_tokens_details")
    if output_details is not None and type(output_details) is not dict:
        raise InvocationPortError("provider_protocol_error")
    reasoning = (
        _count(output_details.get("thinking_tokens"))
        if output_details is not None
        else None
    )
    if any(x is not None for x in (input_tokens, output_tokens, cached, reasoning)):
        return Usage(
            input_tokens=input_tokens, output_tokens=output_tokens,
            cached_input_tokens=cached, reasoning_tokens=reasoning,
        )
    return None


def decode_anthropic_messages_response(
    raw: bytes, prepared: PreparedInvocation,
) -> InferenceResponse:
    """Require a single typed text block; preserve partial usage and native stop."""
    if type(raw) is not bytes or type(prepared) is not PreparedInvocation:
        raise InvocationPortError("provider_protocol_error")
    response = decode_provider_json_object(raw)
    if (response.get("type") != "message" or response.get("role") != "assistant"):
        raise InvocationPortError("provider_protocol_error")
    if response.get("model") != prepared.native_model_alias:
        raise InvocationPortError("provider_model_mismatch")
    stop = response.get("stop_reason")
    if type(stop) is not str:
        raise InvocationPortError("provider_protocol_error")
    if stop == "tool_use":
        raise InvocationPortError("unsupported_provider_output")
    if stop == "refusal":
        raise InvocationPortError("provider_refusal")
    if stop == "pause_turn":
        raise InvocationPortError("provider_not_completed")
    native_code = (
        stop if _SAFE_NATIVE_REASON.fullmatch(stop) is not None else None
    )
    if stop in ("end_turn", "stop_sequence"):
        finish_code = FinishReasonCode.STOP
    elif stop in ("max_tokens", "model_context_window_exceeded"):
        finish_code = FinishReasonCode.LENGTH
    else:
        finish_code = FinishReasonCode.UNKNOWN

    blocks = response.get("content")
    if type(blocks) is not list or len(blocks) != 1:
        raise InvocationPortError("unsupported_provider_output")
    block = blocks[0]
    if (
        type(block) is not dict
        or set(block) - {"type", "text", "citations"}
        or block.get("type") != "text"
        or type(block.get("text")) is not str
        or block.get("citations") not in (None, [])
    ):
        raise InvocationPortError("unsupported_provider_output")

    return InferenceResponse(
        prepared.context.run_id,
        TextOutput(block["text"]),
        finish_reason=FinishReason(finish_code, native_code),
        usage=_parse_usage(response.get("usage")),
    )
