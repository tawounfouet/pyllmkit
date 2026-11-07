"""Gemini generateContent text-only mapping, preserving native and partial fields."""

from __future__ import annotations

import json
import re

from pyllmkit.adapters.inference.media_mapping import (
    check_part_modality,
    default_mime_for_part,
    extract_media_base64_and_mime,
)
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
from pyllmkit.domain.interactions import AudioContent, ImageContent, Role, TextContent, VideoContent

_ALIAS = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_FIELDS = {
    "temperature": "temperature",
    "top_p": "topP",
    "top_k": "topK",
    "max_output_tokens": "maxOutputTokens",
    "seed": "seed",
    "stop_sequences": "stopSequences",
    "presence_penalty": "presencePenalty",
    "frequency_penalty": "frequencyPenalty",
}
_FILTERED = frozenset({
    "SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT",
    "SPII", "IMAGE_SAFETY", "LANGUAGE",
})


def gemini_model_alias(prepared: PreparedInvocation) -> str:
    alias = prepared.native_model_alias
    if type(alias) is not str or _ALIAS.fullmatch(alias) is None:
        raise InvocationPortError("invalid_model_alias")
    return alias


def encode_gemini_request(prepared: PreparedInvocation) -> bytes:
    """No system/developer conflation, role merging, tool use or defaults."""
    if type(prepared) is not PreparedInvocation:
        raise InvocationPortError("adapter_protocol_error")
    gemini_model_alias(prepared)
    history: list[dict[str, object]] = []
    system: str | None = None
    previous: Role | None = None
    for index, message in enumerate(prepared.request.messages):
        if message.role is Role.SYSTEM:
            if index != 0 or system is not None:
                raise InvocationPortError("unsupported_message_structure")
            if len(message.content.parts) != 1 or type(message.content.parts[0]) is not TextContent:
                raise InvocationPortError("unsupported_message_structure")
            system = message.content.parts[0].text
            continue
        if message.role not in (Role.USER, Role.ASSISTANT):
            raise InvocationPortError("unsupported_message_role")
        if (previous is None and message.role is not Role.USER) or previous is message.role:
            raise InvocationPortError("unsupported_message_structure")

        if len(message.content.parts) > 1 and all(type(p) is TextContent for p in message.content.parts):
            raise InvocationPortError("unsupported_content_structure")

        parts_list: list[dict[str, object]] = []
        for part in message.content.parts:
            check_part_modality(prepared, part)
            if isinstance(part, TextContent):
                parts_list.append({"text": part.text})
            elif isinstance(part, (ImageContent, AudioContent, VideoContent)):
                source = part.source
                mime = default_mime_for_part(part)
                if source.kind in ("uri", "asset"):
                    parts_list.append({"fileData": {"fileUri": source.value, "mimeType": mime}})
                elif source.kind in ("data", "file"):
                    b64, detected_mime = extract_media_base64_and_mime(source, mime)
                    parts_list.append({"inlineData": {"mimeType": detected_mime, "data": b64}})
                else:
                    raise InvocationPortError("unsupported_media_source")
            else:
                raise InvocationPortError("unsupported_input_modality")

        previous = message.role
        history.append({
            "role": "user" if message.role is Role.USER else "model",
            "parts": parts_list,
        })
    if not history or previous is not Role.USER:
        raise InvocationPortError("unsupported_message_structure")
    payload: dict[str, object] = {
        "contents": history,
        "store": False,
    }
    if system is not None:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    generation: dict[str, object] = {
        "candidateCount": 1, "responseMimeType": "text/plain",
    }
    cfg = prepared.request.generation_config
    if cfg is not None:
        supported = {
            a.name: a.level for a in prepared.parameter_assessment.assessments
        }
        for key, native in _FIELDS.items():
            value = getattr(cfg, key)
            if value is not None:
                if supported.get(key) is not SupportLevel.NATIVE:
                    raise InvocationPortError("unknown_generation_parameter")
                generation[native] = value
    payload["generationConfig"] = generation
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _count(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise InvocationPortError("provider_protocol_error")
    return value


def decode_gemini_response(raw: bytes, prepared: PreparedInvocation) -> InferenceResponse:
    if type(raw) is not bytes or type(prepared) is not PreparedInvocation:
        raise InvocationPortError("provider_protocol_error")
    result = decode_provider_json_object(raw)
    feedback = result.get("promptFeedback")
    if feedback is not None:
        if type(feedback) is not dict:
            raise InvocationPortError("provider_protocol_error")
        if feedback.get("blockReason") is not None:
            raise InvocationPortError("provider_content_filtered")
    candidates = result.get("candidates")
    if type(candidates) is not list or len(candidates) != 1:
        raise InvocationPortError("unsupported_provider_output")
    candidate = candidates[0]
    if type(candidate) is not dict:
        raise InvocationPortError("provider_protocol_error")
    finish = candidate.get("finishReason")
    if type(finish) is not str:
        raise InvocationPortError("provider_not_completed")
    if finish in _FILTERED:
        raise InvocationPortError("provider_content_filtered")
    if finish == "MALFORMED_FUNCTION_CALL":
        raise InvocationPortError("unsupported_provider_output")
    if finish == "FINISH_REASON_UNSPECIFIED":
        raise InvocationPortError("provider_not_completed")
    if finish == "STOP":
        code = FinishReasonCode.STOP
    elif finish == "MAX_TOKENS":
        code = FinishReasonCode.LENGTH
    else:
        code = FinishReasonCode.UNKNOWN
    content = candidate.get("content")
    if type(content) is not dict or content.get("role") != "model":
        raise InvocationPortError("unsupported_provider_output")
    parts = content.get("parts")
    if type(parts) is not list or len(parts) != 1:
        raise InvocationPortError("unsupported_provider_output")
    part = parts[0]
    if (
        type(part) is not dict
        or set(part) - {"text", "thoughtSignature"}
        or type(part.get("text")) is not str
    ):
        raise InvocationPortError("unsupported_provider_output")
    if any(candidate.get(k) not in (None, [], {}) for k in (
        "citationMetadata", "groundingMetadata", "urlContextMetadata",
        "groundingAttributions", "logprobsResult",
    )):
        raise InvocationPortError("unsupported_provider_output")
    metadata = result.get("usageMetadata")
    usage = None
    if metadata is not None:
        if type(metadata) is not dict:
            raise InvocationPortError("provider_protocol_error")
        input_tokens = _count(metadata.get("promptTokenCount"))
        output_tokens = _count(metadata.get("candidatesTokenCount"))
        total = _count(metadata.get("totalTokenCount"))
        cached = _count(metadata.get("cachedContentTokenCount"))
        reasoning = _count(metadata.get("thoughtsTokenCount"))
        if any(x is not None for x in (input_tokens, output_tokens, total, cached, reasoning)):
            usage = Usage(
                input_tokens=input_tokens, output_tokens=output_tokens,
                total_tokens=total, cached_input_tokens=cached,
                reasoning_tokens=reasoning,
            )
    native = finish if re.fullmatch(r"[A-Z][A-Z0-9_]{0,59}", finish) else None
    return InferenceResponse(
        prepared.context.run_id, TextOutput(part["text"]),
        finish_reason=FinishReason(code, native), usage=usage,
    )
