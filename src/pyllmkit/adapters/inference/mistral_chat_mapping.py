"""Mistral Chat Completions text-only mapping, explicit and loss-averse."""

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
_SAFE_REASON = re.compile(r"[a-z][a-z0-9_]{0,39}\Z")
_OPTIONS = {
    "temperature": "temperature",
    "top_p": "top_p",
    "top_k": "top_k",
    "max_output_tokens": "max_tokens",
    "seed": "random_seed",
    "stop_sequences": "stop",
    "presence_penalty": "presence_penalty",
    "frequency_penalty": "frequency_penalty",
}


def encode_mistral_chat_request(prepared: PreparedInvocation) -> bytes:
    if type(prepared) is not PreparedInvocation:
        raise InvocationPortError("adapter_protocol_error")
    alias = prepared.native_model_alias
    if type(alias) is not str or _ALIAS.fullmatch(alias) is None:
        raise InvocationPortError("invalid_model_alias")
    messages: list[dict[str, str]] = []
    for position, message in enumerate(prepared.request.messages):
        if message.role not in (Role.SYSTEM, Role.USER, Role.ASSISTANT):
            raise InvocationPortError("unsupported_message_role")
        if message.role is Role.SYSTEM and position != 0:
            raise InvocationPortError("unsupported_message_structure")
        if len(message.content.parts) != 1:
            raise InvocationPortError("unsupported_content_structure")
        part = message.content.parts[0]
        if type(part) is not TextContent:
            raise InvocationPortError("unsupported_input_modality")
        messages.append({"role": message.role.value, "content": part.text})
    if messages[-1]["role"] != "user":
        raise InvocationPortError("unsupported_message_structure")
    payload: dict[str, object] = {
        "model": alias,
        "messages": messages,
        "stream": False,
        "n": 1,
        "tools": [],
        "tool_choice": "none",
        "parallel_tool_calls": False,
        "safe_prompt": False,
        "response_format": {"type": "text"},
    }
    cfg = prepared.request.generation_config
    if cfg is not None:
        supported = {a.name: a.level for a in prepared.parameter_assessment.assessments}
        for field, native in _OPTIONS.items():
            value = getattr(cfg, field)
            if value is not None:
                if supported.get(field) is not SupportLevel.NATIVE:
                    raise InvocationPortError("unknown_generation_parameter")
                payload[native] = value
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _count(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise InvocationPortError("provider_protocol_error")
    return value


def decode_mistral_chat_response(raw: bytes, prepared: PreparedInvocation) -> InferenceResponse:
    if type(raw) is not bytes or type(prepared) is not PreparedInvocation:
        raise InvocationPortError("provider_protocol_error")
    try:
        data = decode_provider_json_object(raw)
    except (ValueError, UnicodeError, TypeError, RecursionError):
        raise InvocationPortError("provider_protocol_error") from None
    if type(data) is not dict or data.get("object") != "chat.completion":
        raise InvocationPortError("provider_protocol_error")
    if data.get("model") != prepared.native_model_alias:
        raise InvocationPortError("provider_model_mismatch")
    choices = data.get("choices")
    if type(choices) is not list or len(choices) != 1:
        raise InvocationPortError("unsupported_provider_output")
    choice = choices[0]
    if type(choice) is not dict or choice.get("index") != 0:
        raise InvocationPortError("provider_protocol_error")
    reason = choice.get("finish_reason")
    if type(reason) is not str:
        raise InvocationPortError("provider_not_completed")
    if reason in ("tool_calls", "tool_call"):
        raise InvocationPortError("unsupported_provider_output")
    if reason == "error":
        raise InvocationPortError("provider_protocol_error")
    if reason == "stop":
        code = FinishReasonCode.STOP
    elif reason == "length":
        code = FinishReasonCode.LENGTH
    else:
        code = FinishReasonCode.UNKNOWN
    message = choice.get("message")
    if (
        type(message) is not dict
        or message.get("role") != "assistant"
        or type(message.get("content")) is not str
        or any(message.get(k) not in (None, [], {}) for k in (
            "tool_calls", "reasoning_content", "refusal", "audio",
        ))
        or message.get("prefix") not in (None, False)
    ):
        raise InvocationPortError("unsupported_provider_output")
    details = data.get("usage")
    usage = None
    if details is not None:
        if type(details) is not dict:
            raise InvocationPortError("provider_protocol_error")
        input_tokens = _count(details.get("prompt_tokens"))
        output_tokens = _count(details.get("completion_tokens"))
        total = _count(details.get("total_tokens"))
        cache = None
        prompt_details = details.get("prompt_tokens_details")
        if prompt_details is not None:
            if type(prompt_details) is not dict:
                raise InvocationPortError("provider_protocol_error")
            cache = _count(prompt_details.get("cached_tokens"))
        if any(v is not None for v in (input_tokens, output_tokens, total, cache)):
            usage = Usage(
                input_tokens=input_tokens, output_tokens=output_tokens,
                total_tokens=total, cached_input_tokens=cache,
            )
    native = reason if _SAFE_REASON.fullmatch(reason) is not None else None
    return InferenceResponse(
        prepared.context.run_id, TextOutput(message["content"]),
        finish_reason=FinishReason(code, native), usage=usage,
    )
