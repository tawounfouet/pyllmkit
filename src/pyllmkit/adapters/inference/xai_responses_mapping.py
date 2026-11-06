"""xAI Responses strict text-only mapping (not deprecated Chat Completions).

xAI Responses may return encrypted reasoning items. They are explicitly
rejected here because InferenceResponse does not preserve opaque reasoning.
No silent loss of encrypted state, tool calls, or privacy flags is permitted.
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

_ALIAS = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}\Z")
_NATIVE_CONFIG = frozenset({"temperature", "top_p", "max_output_tokens"})


def encode_xai_responses_request(prepared: PreparedInvocation) -> bytes:
    if type(prepared) is not PreparedInvocation:
        raise InvocationPortError("adapter_protocol_error")
    alias = prepared.native_model_alias
    if type(alias) is not str or _ALIAS.fullmatch(alias) is None:
        raise InvocationPortError("invalid_model_alias")
    messages: list[dict[str, str]] = []
    for message in prepared.request.messages:
        if message.role not in (Role.SYSTEM, Role.DEVELOPER, Role.USER, Role.ASSISTANT):
            raise InvocationPortError("unsupported_message_role")
        if len(message.content.parts) != 1:
            raise InvocationPortError("unsupported_content_structure")
        part = message.content.parts[0]
        if type(part) is not TextContent:
            raise InvocationPortError("unsupported_input_modality")
        messages.append({"role": message.role.value, "content": part.text})
    payload: dict[str, object] = {
        "model": alias,
        "input": messages,
        "store": False,
        "stream": False,
        "background": False,
        "tools": [],
        "tool_choice": "none",
        "parallel_tool_calls": False,
        "truncation": "disabled",
        "text": {"format": {"type": "text"}},
    }
    cfg = prepared.request.generation_config
    if cfg is not None:
        supported = {a.name: a.level for a in prepared.parameter_assessment.assessments}
        for field in (
            "temperature", "top_p", "top_k", "max_output_tokens",
            "seed", "stop_sequences", "presence_penalty", "frequency_penalty",
        ):
            value = getattr(cfg, field)
            if value is None:
                continue
            if field not in _NATIVE_CONFIG:
                raise InvocationPortError("unsupported_generation_parameter")
            if supported.get(field) is not SupportLevel.NATIVE:
                raise InvocationPortError("unknown_generation_parameter")
            payload[field] = value
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _count(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise InvocationPortError("provider_protocol_error")
    return value


def _nested_count(details: object, name: str) -> int | None:
    if details is None:
        return None
    if type(details) is not dict:
        raise InvocationPortError("provider_protocol_error")
    return _count(details.get(name))


def decode_xai_responses_response(
    raw: bytes, prepared: PreparedInvocation,
) -> InferenceResponse:
    if type(raw) is not bytes or type(prepared) is not PreparedInvocation:
        raise InvocationPortError("provider_protocol_error")
    try:
        data = decode_provider_json_object(raw)
    except (UnicodeError, ValueError, TypeError, RecursionError):
        raise InvocationPortError("provider_protocol_error") from None
    if type(data) is not dict or data.get("object") != "response":
        raise InvocationPortError("provider_protocol_error")
    if data.get("status") != "completed":
        if data.get("status") in ("incomplete", "in_progress", "queued", "failed"):
            raise InvocationPortError("provider_not_completed")
        raise InvocationPortError("provider_protocol_error")
    if data.get("error") is not None or data.get("incomplete_details") is not None:
        raise InvocationPortError("provider_protocol_error")
    if data.get("store") is True:
        raise InvocationPortError("provider_privacy_policy_violation")
    if data.get("model") != prepared.native_model_alias:
        raise InvocationPortError("provider_model_mismatch")
    output = data.get("output")
    if type(output) is not list or len(output) != 1:
        raise InvocationPortError("unsupported_provider_output")
    message = output[0]
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
    block = content[0]
    if (
        type(block) is not dict
        or block.get("type") != "output_text"
        or type(block.get("text")) is not str
        or block.get("annotations") not in (None, [])
        or block.get("logprobs") not in (None, [])
    ):
        raise InvocationPortError("unsupported_provider_output")
    usage = None
    details = data.get("usage")
    if details is not None:
        if type(details) is not dict:
            raise InvocationPortError("provider_protocol_error")
        input_tokens = _count(details.get("prompt_tokens"))
        output_tokens = _count(details.get("completion_tokens"))
        total = _count(details.get("total_tokens"))
        cached = _nested_count(details.get("prompt_tokens_details"), "cached_tokens")
        reasoning = _nested_count(details.get("completion_tokens_details"), "reasoning_tokens")
        if any(x is not None for x in (input_tokens, output_tokens, total, cached, reasoning)):
            usage = Usage(
                input_tokens=input_tokens, output_tokens=output_tokens,
                total_tokens=total, cached_input_tokens=cached,
                reasoning_tokens=reasoning,
            )
    # A completed Responses lifecycle is NOT a STOP generation reason.
    return InferenceResponse(
        prepared.context.run_id, TextOutput(block["text"]),
        finish_reason=FinishReason(FinishReasonCode.UNKNOWN), usage=usage,
    )
