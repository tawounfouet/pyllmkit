"""P7 L7.6 strict incremental native protocols to M5 streaming observations.

No native payload is exposed through repr/exceptions. Unknown frames and
unrepresentable tool/reasoning state fail closed. Completion is explicit,
never inferred from EOF or the last received delta.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from pyllmkit.adapters.inference.anthropic_messages_mapping import (
    decode_anthropic_messages_response,
)
from pyllmkit.adapters.inference.google_gemini_mapping import decode_gemini_response
from pyllmkit.adapters.inference.mistral_chat_mapping import decode_mistral_chat_response
from pyllmkit.adapters.inference.ollama_mapping import decode_ollama_response
from pyllmkit.adapters.inference.openai_responses_mapping import (
    decode_openai_responses_response,
)
from pyllmkit.adapters.inference.security import ProviderProfile
from pyllmkit.adapters.inference.strict_json import decode_provider_json_object
from pyllmkit.adapters.inference.xai_responses_mapping import decode_xai_responses_response
from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.domain.inference import InferenceResponse

_MAX_TEXT_BYTES = 8 * 1024 * 1024
_MAX_DELTA_BYTES = 1_048_576
_MAX_NATIVE_EVENTS = 100_000


def decode_native_json(raw: str) -> dict[str, object]:
    if type(raw) is not str or len(raw.encode("utf-8")) > 262_144:
        raise InvocationPortError("provider_protocol_error")
    return decode_provider_json_object(raw)


def _dict(value: object) -> dict[str, object]:
    if type(value) is not dict:
        raise InvocationPortError("provider_protocol_error")
    return value


def _one(value: object) -> dict[str, object]:
    if type(value) is not list or len(value) != 1:
        raise InvocationPortError("unsupported_provider_output")
    return _dict(value[0])


def _str(value: object) -> str:
    if type(value) is not str:
        raise InvocationPortError("provider_protocol_error")
    return value


@dataclass(slots=True)
class NativeStreamDecoder:
    """One attempt's provider-specific streaming state, without network ownership."""

    profile: ProviderProfile
    prepared: PreparedInvocation = field(repr=False)
    _chunks: list[str] = field(default_factory=list, repr=False)
    _text_bytes: int = 0
    _events: int = 0
    _completed: bool = False
    _done_marker: bool = False
    _last_response: InferenceResponse | None = field(default=None, repr=False)
    _anthropic_started: bool = False
    _anthropic_block: bool = False
    _anthropic_block_closed: bool = False
    _anthropic_stop: str | None = None
    _anthropic_usage: dict[str, object] = field(default_factory=dict, repr=False)
    _mistral_reason: str | None = None
    _mistral_usage: dict[str, object] | None = field(default=None, repr=False)
    _gemini_finish: str | None = None
    _gemini_usage: object = field(default=None, repr=False)

    def _text(self) -> str:
        return "".join(self._chunks)

    def _append(self, delta: str) -> str:
        if type(delta) is not str:
            raise InvocationPortError("unsupported_provider_output")
        length = len(delta.encode("utf-8"))
        if length > _MAX_DELTA_BYTES or self._text_bytes + length > _MAX_TEXT_BYTES:
            raise InvocationPortError("stream_text_limit")
        self._text_bytes += length
        if delta:
            self._chunks.append(delta)
        return delta

    def _finalize(self, response: InferenceResponse) -> None:
        if self._completed:
            raise InvocationPortError("provider_protocol_error")
        if response.output.text != self._text():
            raise InvocationPortError("provider_stream_mismatch")
        self._last_response = response
        self._completed = True

    def push(self, kind: str, frame: dict[str, object]) -> str:
        """Process one native event. Returned text is an incremental delta."""
        if self._completed:
            raise InvocationPortError("provider_protocol_error")
        self._events += 1
        if self._events > _MAX_NATIVE_EVENTS:
            raise InvocationPortError("stream_event_limit")
        if self.profile is ProviderProfile.OLLAMA:
            return self._ollama(frame)
        if self.profile is ProviderProfile.GOOGLE:
            return self._gemini(frame)
        if self.profile in (ProviderProfile.OPENAI, ProviderProfile.XAI):
            return self._responses(kind, frame)
        if self.profile is ProviderProfile.ANTHROPIC:
            return self._anthropic(kind, frame)
        if self.profile is ProviderProfile.MISTRAL:
            return self._mistral(frame)
        raise InvocationPortError("adapter_connection_invalid")

    def marker(self, value: str) -> None:
        if value != "[DONE]" or self.profile not in (
            ProviderProfile.MISTRAL, ProviderProfile.OPENAI, ProviderProfile.XAI,
        ):
            raise InvocationPortError("provider_protocol_error")
        if self._done_marker:
            raise InvocationPortError("provider_protocol_error")
        self._done_marker = True
        if self.profile is ProviderProfile.MISTRAL:
            if self._mistral_reason is None:
                raise InvocationPortError("provider_not_completed")
            data: dict[str, object] = {
                "object": "chat.completion",
                "model": self.prepared.native_model_alias,
                "choices": [{
                    "index": 0,
                    "finish_reason": self._mistral_reason,
                    "message": {"role": "assistant", "content": self._text()},
                }],
            }
            if self._mistral_usage is not None:
                data["usage"] = self._mistral_usage
            response = decode_mistral_chat_response(
                json.dumps(data).encode(), self.prepared,
            )
            self._finalize(response)
        elif not self._completed:
            raise InvocationPortError("provider_not_completed")

    def finish(self) -> InferenceResponse:
        if not self._completed or self._last_response is None:
            raise InvocationPortError("provider_not_completed")
        if self.profile is ProviderProfile.MISTRAL and not self._done_marker:
            raise InvocationPortError("provider_not_completed")
        return self._last_response

    def _ollama(self, frame: dict[str, object]) -> str:
        if frame.get("error") is not None:
            raise InvocationPortError("provider_protocol_error")
        msg = _dict(frame.get("message"))
        if set(msg) - {"role", "content", "thinking", "tool_calls", "images"}:
            raise InvocationPortError("unsupported_provider_output")
        if msg.get("role") != "assistant" or type(msg.get("content")) is not str:
            raise InvocationPortError("unsupported_provider_output")
        if any(msg.get(k) not in (None, [], {}, "") for k in ("thinking", "tool_calls", "images")):
            raise InvocationPortError("unsupported_provider_output")
        if frame.get("model") not in (None, self.prepared.native_model_alias):
            raise InvocationPortError("provider_model_mismatch")
        delta = self._append(_str(msg["content"]))
        if frame.get("done") is True:
            final = dict(frame)
            final["message"] = {"role": "assistant", "content": self._text()}
            response = decode_ollama_response(
                json.dumps(final).encode(), self.prepared,
            )
            self._finalize(response)
        elif frame.get("done") is not False:
            raise InvocationPortError("provider_protocol_error")
        return delta

    def _gemini(self, frame: dict[str, object]) -> str:
        if frame.get("error") is not None:
            raise InvocationPortError("provider_protocol_error")
        feedback = frame.get("promptFeedback")
        if feedback is not None and _dict(feedback).get("blockReason") is not None:
            raise InvocationPortError("provider_content_filtered")
        cand = _one(frame.get("candidates"))
        contents = cand.get("content")
        delta = ""
        if contents is not None:
            part = _one(_dict(contents).get("parts"))
            if _dict(contents).get("role") != "model" or set(part) != {"text"}:
                raise InvocationPortError("unsupported_provider_output")
            delta = self._append(_str(part["text"]))
        if any(cand.get(k) not in (None, [], {}) for k in (
            "citationMetadata", "groundingMetadata", "urlContextMetadata", "logprobsResult",
        )):
            raise InvocationPortError("unsupported_provider_output")
        if cand.get("finishReason") is not None:
            reason = _str(cand["finishReason"])
            response = decode_gemini_response(
                json.dumps({
                    "candidates": [{
                        "finishReason": reason,
                        "content": {"role": "model", "parts": [{"text": self._text()}]},
                    }],
                    "usageMetadata": frame.get("usageMetadata"),
                    "promptFeedback": frame.get("promptFeedback"),
                }).encode(), self.prepared,
            )
            self._finalize(response)
        return delta

    def _responses(self, kind: str, frame: dict[str, object]) -> str:
        if frame.get("type") != kind:
            raise InvocationPortError("provider_protocol_error")
        if kind in ("response.created", "response.in_progress"):
            response = _dict(frame.get("response"))
            if (
                response.get("status") not in ("in_progress", "queued", None)
                or response.get("output") not in (None, [])
                or response.get("tools") not in (None, [])
                or response.get("error") is not None
                or response.get("store") is True
                or response.get("model") not in (None, self.prepared.native_model_alias)
            ):
                raise InvocationPortError("provider_protocol_error")
            return ""
        if kind in ("response.output_item.added", "response.output_item.done"):
            item = _dict(frame.get("item"))
            if (
                frame.get("output_index", 0) != 0
                or set(item) - {"id", "type", "status", "role", "content"}
                or item.get("type") != "message"
                or item.get("role") != "assistant"
            ):
                raise InvocationPortError("unsupported_provider_output")
            content = item.get("content")
            if content not in (None, []):
                if type(content) is not list or len(content) != 1:
                    raise InvocationPortError("unsupported_provider_output")
                part = _dict(content[0])
                if (
                    set(part) - {"type", "text", "annotations", "logprobs"}
                    or part.get("type") != "output_text"
                    or part.get("annotations") not in (None, [])
                    or part.get("logprobs") not in (None, [])
                ):
                    raise InvocationPortError("unsupported_provider_output")
                text = part.get("text")
                if kind == "response.output_item.done":
                    if text != self._text():
                        raise InvocationPortError("provider_stream_mismatch")
                elif text not in (None, ""):
                    raise InvocationPortError("unsupported_provider_output")
            return ""
        if kind in ("response.content_part.added", "response.content_part.done"):
            part = _dict(frame.get("part"))
            if (
                frame.get("output_index", 0) != 0
                or frame.get("content_index", 0) != 0
                or set(part) - {"type", "text", "annotations", "logprobs"}
                or part.get("type") != "output_text"
                or part.get("annotations") not in (None, [])
                or part.get("logprobs") not in (None, [])
            ):
                raise InvocationPortError("unsupported_provider_output")
            text = part.get("text")
            if kind == "response.content_part.done":
                if text is not None and text != self._text():
                    raise InvocationPortError("provider_stream_mismatch")
            elif text not in (None, ""):
                raise InvocationPortError("unsupported_provider_output")
            return ""
        if kind == "response.output_text.delta":
            if (
                frame.get("output_index") != 0
                or frame.get("content_index") != 0
                or set(frame) - {
                    "type", "sequence_number", "output_index", "content_index",
                    "item_id", "delta", "logprobs", "obfuscation",
                }
            ):
                raise InvocationPortError("unsupported_provider_output")
            if frame.get("logprobs") not in (None, []):
                raise InvocationPortError("unsupported_provider_output")
            return self._append(_str(frame.get("delta")))
        if kind == "response.output_text.done":
            if (
                frame.get("output_index") != 0
                or frame.get("content_index") != 0
                or _str(frame.get("text")) != self._text()
            ):
                raise InvocationPortError("provider_stream_mismatch")
            return ""
        if kind == "response.completed":
            full = _dict(frame.get("response"))
            decoder = (
                decode_openai_responses_response
                if self.profile is ProviderProfile.OPENAI
                else decode_xai_responses_response
            )
            native_response = decoder(json.dumps(full).encode(), self.prepared)
            self._finalize(native_response)
            return ""
        if kind in ("response.failed", "response.incomplete", "error"):
            raise InvocationPortError("provider_not_completed")
        raise InvocationPortError("unsupported_provider_output")

    def _anthropic(self, kind: str, frame: dict[str, object]) -> str:
        if frame.get("type") != kind:
            raise InvocationPortError("provider_protocol_error")
        if kind == "ping":
            if set(frame) != {"type"}:
                raise InvocationPortError("provider_protocol_error")
            return ""
        if kind == "message_start":
            if self._anthropic_started:
                raise InvocationPortError("provider_protocol_error")
            message = _dict(frame.get("message"))
            if (
                message.get("type") != "message"
                or message.get("role") != "assistant"
                or message.get("model") != self.prepared.native_model_alias
                or message.get("content") != []
            ):
                raise InvocationPortError("unsupported_provider_output")
            self._anthropic_started = True
            usage = message.get("usage")
            if usage is not None:
                self._anthropic_usage.update(_dict(usage))
            return ""
        if not self._anthropic_started:
            raise InvocationPortError("provider_protocol_error")
        if kind == "content_block_start":
            block = _dict(frame.get("content_block"))
            if (
                self._anthropic_block or self._anthropic_block_closed
                or frame.get("index") != 0 or block.get("type") != "text"
                or set(block) - {"type", "text"}
            ):
                raise InvocationPortError("unsupported_provider_output")
            self._anthropic_block = True
            return self._append(_str(block.get("text")))
        if kind == "content_block_delta":
            delta = _dict(frame.get("delta"))
            if (
                not self._anthropic_block or self._anthropic_block_closed
                or frame.get("index") != 0 or delta.get("type") != "text_delta"
                or set(delta) - {"type", "text"}
            ):
                raise InvocationPortError("unsupported_provider_output")
            return self._append(_str(delta.get("text")))
        if kind == "content_block_stop":
            if not self._anthropic_block or frame.get("index") != 0:
                raise InvocationPortError("provider_protocol_error")
            self._anthropic_block = False
            self._anthropic_block_closed = True
            return ""
        if kind == "message_delta":
            if not self._anthropic_block_closed or self._anthropic_stop is not None:
                raise InvocationPortError("provider_protocol_error")
            stop_delta = _dict(frame.get("delta"))
            if (
                set(stop_delta) - {"stop_reason", "stop_sequence"}
                or stop_delta.get("stop_sequence") not in (None, "")
            ):
                raise InvocationPortError("unsupported_provider_output")
            self._anthropic_stop = _str(stop_delta.get("stop_reason"))
            usage = frame.get("usage")
            if usage is not None:
                self._anthropic_usage.update(_dict(usage))
            return ""
        if kind == "message_stop":
            if not self._anthropic_block_closed or self._anthropic_stop is None:
                raise InvocationPortError("provider_not_completed")
            data = {
                "type": "message", "role": "assistant",
                "model": self.prepared.native_model_alias,
                "content": [{"type": "text", "text": self._text()}],
                "stop_reason": self._anthropic_stop,
                "usage": self._anthropic_usage or None,
            }
            response = decode_anthropic_messages_response(
                json.dumps(data).encode(), self.prepared,
            )
            self._finalize(response)
            return ""
        if kind == "error":
            raise InvocationPortError("provider_protocol_error")
        raise InvocationPortError("unsupported_provider_output")

    def _mistral(self, frame: dict[str, object]) -> str:
        if frame.get("error") is not None:
            raise InvocationPortError("provider_protocol_error")
        if frame.get("object") != "chat.completion.chunk":
            raise InvocationPortError("provider_protocol_error")
        if frame.get("model") != self.prepared.native_model_alias:
            raise InvocationPortError("provider_model_mismatch")
        choices = frame.get("choices")
        if choices == []:
            if self._mistral_reason is None or self._mistral_usage is not None:
                raise InvocationPortError("provider_protocol_error")
            self._mistral_usage = _dict(frame.get("usage"))
            return ""
        choice = _one(choices)
        if choice.get("index") != 0 or self._mistral_reason is not None:
            raise InvocationPortError("provider_protocol_error")
        delta = _dict(choice.get("delta"))
        if set(delta) - {
            "role", "content", "tool_calls", "reasoning_content", "refusal", "audio",
        }:
            raise InvocationPortError("unsupported_provider_output")
        if any(delta.get(k) not in (None, [], {}, "") for k in (
            "tool_calls", "reasoning_content", "refusal", "audio",
        )):
            raise InvocationPortError("unsupported_provider_output")
        if delta.get("role") not in (None, "assistant"):
            raise InvocationPortError("unsupported_provider_output")
        text = delta.get("content")
        fragment = "" if text is None else self._append(_str(text))
        finish = choice.get("finish_reason")
        if finish is not None:
            self._mistral_reason = _str(finish)
        if frame.get("usage") is not None:
            if self._mistral_usage is not None:
                raise InvocationPortError("provider_protocol_error")
            self._mistral_usage = _dict(frame["usage"])
        return fragment
