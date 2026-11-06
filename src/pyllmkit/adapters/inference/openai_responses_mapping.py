"""Strict OpenAI Responses API text-only wire mapping (P7 L7.4 / ADR-054).

Canonical application data stays provider-independent. Never infer support,
execute tools, expose hidden reasoning, invent usage or treat completed as STOP.
"""

from __future__ import annotations

import json
import re

from pyllmkit.adapters.inference.strict_json import (
    decode_provider_json_object,
    matches_model_alias,
)
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

_MODEL_ALIAS = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+\-]{0,127}\Z")
_SUPPORTED_GENERATION = frozenset({"temperature", "top_p", "max_output_tokens"})


def encode_openai_responses_request(prepared: PreparedInvocation) -> bytes:
    """Encode full ordered message history with explicit privacy controls."""
    if type(prepared) is not PreparedInvocation:
        raise InvocationPortError("adapter_protocol_error")
    alias = prepared.native_model_alias
    if type(alias) is not str or _MODEL_ALIAS.fullmatch(alias) is None:
        raise InvocationPortError("invalid_model_alias")

    inputs: list[dict[str, str]] = []
    for message in prepared.request.messages:
        if message.role not in (Role.SYSTEM, Role.DEVELOPER, Role.USER, Role.ASSISTANT):
            raise InvocationPortError("unsupported_message_role")
        if len(message.content.parts) != 1:
            raise InvocationPortError("unsupported_content_structure")
        part = message.content.parts[0]
        if type(part) is not TextContent:
            raise InvocationPortError("unsupported_input_modality")
        inputs.append({"role": message.role.value, "content": part.text})

    payload: dict[str, object] = {
        "model": alias,
        "input": inputs,
        "store": False,
        "stream": False,
        "background": False,
        "tools": [],
        "tool_choice": "none",
        "parallel_tool_calls": False,
        "truncation": "disabled",
        "text": {"format": {"type": "text"}},
    }
    config = prepared.request.generation_config
    if config is not None:
        levels = {a.name: a.level for a in prepared.parameter_assessment.assessments}
        for name in (
            "temperature", "top_p", "top_k", "max_output_tokens",
            "seed", "stop_sequences", "presence_penalty", "frequency_penalty",
        ):
            value = getattr(config, name)
            if value is None:
                continue
            if name not in _SUPPORTED_GENERATION:
                raise InvocationPortError("unsupported_generation_parameter")
            if levels.get(name) is not SupportLevel.NATIVE:
                raise InvocationPortError("unknown_generation_parameter")
            payload[name] = value
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _observed_count(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise InvocationPortError("provider_protocol_error")
    return value


def _detail_count(details: object, name: str) -> int | None:
    if details is None:
        return None
    if type(details) is not dict:
        raise InvocationPortError("provider_protocol_error")
    return _observed_count(details.get(name))


def decode_openai_responses_response(raw: bytes, prepared: PreparedInvocation) -> InferenceResponse:
    """Require one completed assistant text, never suppress unsupported output."""
    if type(raw) is not bytes or type(prepared) is not PreparedInvocation:
        raise InvocationPortError("provider_protocol_error")
    payload = decode_provider_json_object(raw)
    status = payload.get("status")
    if status != "completed":
        if status in ("incomplete", "failed", "cancelled", "queued", "in_progress"):
            raise InvocationPortError("provider_not_completed")
        raise InvocationPortError("provider_protocol_error")
    if payload.get("error") is not None or payload.get("incomplete_details") is not None:
        raise InvocationPortError("provider_protocol_error")
    if not matches_model_alias(payload.get("model"), prepared.native_model_alias):
        raise InvocationPortError("provider_model_mismatch")

    outputs = payload.get("output")
    if type(outputs) is not list or len(outputs) != 1:
        raise InvocationPortError("unsupported_provider_output")
    message = outputs[0]
    if (
        type(message) is not dict
        or message.get("type") != "message"
        or message.get("role") != "assistant"
        or message.get("status") != "completed"
    ):
        raise InvocationPortError("unsupported_provider_output")
    content = message.get("content")
    if type(content) is not list or len(content) != 1:
        raise InvocationPortError("unsupported_provider_output")
    item = content[0]
    if (
        type(item) is not dict
        or item.get("type") != "output_text"
        or type(item.get("text")) is not str
    ):
        raise InvocationPortError("unsupported_provider_output")
    if item.get("annotations") not in (None, []) or item.get("logprobs") not in (None, []):
        raise InvocationPortError("unsupported_provider_output")

    native_usage = payload.get("usage")
    usage: Usage | None = None
    if native_usage is not None:
        if type(native_usage) is not dict:
            raise InvocationPortError("provider_protocol_error")
        input_tokens = _observed_count(native_usage.get("input_tokens"))
        output_tokens = _observed_count(native_usage.get("output_tokens"))
        total_tokens = _observed_count(native_usage.get("total_tokens"))
        cached = _detail_count(native_usage.get("input_tokens_details"), "cached_tokens")
        reasoning = _detail_count(native_usage.get("output_tokens_details"), "reasoning_tokens")
        if any(x is not None for x in (input_tokens, output_tokens, total_tokens, cached, reasoning)):
            usage = Usage(
                input_tokens=input_tokens, output_tokens=output_tokens,
                total_tokens=total_tokens, cached_input_tokens=cached,
                reasoning_tokens=reasoning,
            )
    # Responses status="completed" is lifecycle, not a native stop reason.
    return InferenceResponse(
        prepared.context.run_id,
        TextOutput(item["text"]),
        finish_reason=FinishReason(FinishReasonCode.UNKNOWN),
        usage=usage,
    )
