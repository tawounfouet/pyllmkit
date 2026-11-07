"""Pure, strict Ollama /api/chat text-only mapping (P7 L7.3, ADR-054).

No I/O or third-party dependencies. Unexpected native structured output is
rejected, not silently discarded.
"""

from __future__ import annotations

import json
import re

from pyllmkit.adapters.inference.media_mapping import (
    check_part_modality,
    default_mime_for_part,
    extract_media_base64_and_mime,
)
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
from pyllmkit.domain.interactions import AudioContent, ImageContent, Role, TextContent, VideoContent

_ALLOWED_RESPONSE_FIELDS = frozenset({
    "model", "created_at", "message", "done", "done_reason",
    "total_duration", "load_duration", "prompt_eval_count",
    "prompt_eval_cached_count", "prompt_eval_duration", "eval_count",
    "eval_duration", "logprobs",
})
_ALLOWED_MESSAGE_FIELDS = frozenset({
    "role", "content", "thinking", "tool_calls", "images",
})
_OPTION_NAMES = {
    "temperature": "temperature",
    "top_p": "top_p",
    "top_k": "top_k",
    "max_output_tokens": "num_predict",
    "seed": "seed",
    "stop_sequences": "stop",
}


def encode_ollama_request(prepared: PreparedInvocation) -> bytes:
    """Strict single-text-part role mapping, with explicit model alias."""
    if type(prepared) is not PreparedInvocation:
        raise InvocationPortError("adapter_protocol_error")
    model = prepared.native_model_alias
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/+\\-]{0,127}", model) is None:
        raise InvocationPortError("invalid_model_alias")
    messages: list[dict[str, object]] = []
    for message in prepared.request.messages:
        if message.role not in (Role.SYSTEM, Role.USER, Role.ASSISTANT):
            raise InvocationPortError("unsupported_message_role")

        if len(message.content.parts) > 1 and all(type(p) is TextContent for p in message.content.parts):
            raise InvocationPortError("unsupported_content_structure")

        if len(message.content.parts) == 1 and type(message.content.parts[0]) is TextContent:
            check_part_modality(prepared, message.content.parts[0])
            messages.append({"role": message.role.value, "content": message.content.parts[0].text})
            continue

        text_blocks: list[str] = []
        images: list[str] = []
        for part in message.content.parts:
            check_part_modality(prepared, part)
            if type(part) is TextContent:
                text_blocks.append(part.text)
            elif type(part) is ImageContent:
                b64, _ = extract_media_base64_and_mime(part.source, default_mime_for_part(part))
                images.append(b64)
            elif type(part) in (AudioContent, VideoContent):
                raise InvocationPortError("unsupported_capability")
            else:
                raise InvocationPortError("unsupported_input_modality")

        msg_dict: dict[str, object] = {
            "role": message.role.value,
            "content": "".join(text_blocks),
        }
        if images:
            msg_dict["images"] = images
        messages.append(msg_dict)

    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
    }
    config = prepared.request.generation_config
    if config is not None:
        levels = {a.name: a.level for a in prepared.parameter_assessment.assessments}
        options: dict[str, object] = {}
        for field in (
            "temperature", "top_p", "top_k", "max_output_tokens",
            "seed", "stop_sequences", "presence_penalty", "frequency_penalty",
        ):
            value = getattr(config, field)
            if value is None:
                continue
            native = _OPTION_NAMES.get(field)
            if native is None:
                raise InvocationPortError("unsupported_generation_parameter")
            if levels.get(field) is not SupportLevel.NATIVE:
                raise InvocationPortError("unknown_generation_parameter")
            options[native] = value
        if options:
            payload["options"] = options
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _token_count(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise InvocationPortError("provider_protocol_error")
    return value


def decode_ollama_response(
    raw: bytes,
    prepared: PreparedInvocation,
) -> InferenceResponse:
    """Return only text, observed usage and sanitized native finish semantics."""
    if type(raw) is not bytes or type(prepared) is not PreparedInvocation:
        raise InvocationPortError("provider_protocol_error")
    data = decode_provider_json_object(raw)
    if set(data) - _ALLOWED_RESPONSE_FIELDS:
        raise InvocationPortError("provider_protocol_error")
    if data.get("done") is not True:
        raise InvocationPortError("provider_protocol_error")
    native_model = data.get("model")
    if native_model is not None and not matches_model_alias(native_model, prepared.native_model_alias):
        raise InvocationPortError("provider_model_mismatch")
    message = data.get("message")
    if type(message) is not dict or set(message) - _ALLOWED_MESSAGE_FIELDS:
        raise InvocationPortError("provider_protocol_error")
    if message.get("role") != "assistant" or type(message.get("content")) is not str:
        raise InvocationPortError("provider_protocol_error")
    if any(
        message.get(field) not in (None, "", [], {})
        for field in ("thinking", "tool_calls", "images")
    ) or data.get("logprobs") not in (None, [], {}):
        raise InvocationPortError("unsupported_provider_output")

    done_reason = data.get("done_reason")
    if done_reason is not None and type(done_reason) is not str:
        raise InvocationPortError("provider_protocol_error")
    safe_reason = (
        done_reason
        if done_reason is not None
        and re.fullmatch(r"[a-z][a-z0-9_]{0,39}", done_reason)
        else None
    )
    code = (
        FinishReasonCode.STOP if done_reason == "stop"
        else FinishReasonCode.LENGTH if done_reason == "length"
        else FinishReasonCode.UNKNOWN
    )
    prompt_tokens = _token_count(data.get("prompt_eval_count"))
    output_tokens = _token_count(data.get("eval_count"))
    cached_tokens = _token_count(data.get("prompt_eval_cached_count"))
    usage = (
        Usage(
            input_tokens=prompt_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_tokens,
        )
        if any(value is not None for value in (prompt_tokens, output_tokens, cached_tokens))
        else None
    )
    return InferenceResponse(
        prepared.context.run_id,
        TextOutput(message["content"]),
        finish_reason=FinishReason(code, safe_reason),
        usage=usage,
    )
