"""Versioned synthetic native SSE/NDJSON fixtures for v0.3.0 conformance.

These are not live provider captures. Their wire shapes are adapted from
tests/acceptance/test_p7_l76_native_streaming.py at Phase 7 baseline.
No fixtures contain credentials or user data.
"""

from __future__ import annotations

import json

PROVENANCE = {
    "fixture_version": "v030-s2-stream-v1",
    "source_kind": "synthetic",
    "derived_from": "tests/acceptance/test_p7_l76_native_streaming.py",
    "external_network": False,
}
_MODEL = "synthetic-text-model"
_TEXT = "Hello"


def _json(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _sse(event: str | None, data: object) -> str:
    prefix = f"event: {event}\n" if event is not None else ""
    return prefix + "data: " + _json(data) + "\n\n"


def stream_wire(provider: str, *, truncate: bool = False) -> bytes:
    """Fully formed or terminal-truncated wire fixture for a named provider."""
    if provider == "ollama":
        frames = [
            {"model": _MODEL, "message": {"role": "assistant", "content": "He"},
             "done": False},
            {"model": _MODEL, "message": {"role": "assistant", "content": "llo"},
             "done": False},
        ]
        if not truncate:
            frames.append({
                "model": _MODEL, "message": {"role": "assistant", "content": ""},
                "done": True, "done_reason": "stop",
                "prompt_eval_count": 3, "eval_count": 2,
            })
        return ("\n".join(map(_json, frames)) + "\n").encode("utf-8")
    if provider in {"openai", "xai"}:
        response: dict[str, object] = {
            "object": "response", "model": _MODEL, "status": "completed",
            "error": None, "incomplete_details": None, "store": False,
            "output": [{
                "type": "message", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": _TEXT, "annotations": []}],
            }],
        }
        if provider == "openai":
            response["usage"] = {
                "input_tokens": 3, "output_tokens": 2, "total_tokens": 5,
            }
        else:
            response["usage"] = {
                "prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5,
            }
        frames = [
            _sse("response.created", {
                "type": "response.created", "response": {"status": "in_progress"},
            }),
            _sse("response.output_text.delta", {
                "type": "response.output_text.delta",
                "output_index": 0, "content_index": 0, "delta": "He",
            }),
            _sse("response.output_text.delta", {
                "type": "response.output_text.delta",
                "output_index": 0, "content_index": 0, "delta": "llo",
            }),
            _sse("response.output_text.done", {
                "type": "response.output_text.done",
                "output_index": 0, "content_index": 0, "text": _TEXT,
            }),
        ]
        if not truncate:
            frames += [
                _sse("response.completed", {
                    "type": "response.completed", "response": response,
                }),
                "data: [DONE]\n\n",
            ]
        return "".join(frames).encode("utf-8")
    if provider == "anthropic":
        frames = [
            _sse("message_start", {
                "type": "message_start",
                "message": {
                    "type": "message", "role": "assistant", "model": _MODEL,
                    "content": [], "usage": {"input_tokens": 3},
                },
            }),
            _sse("content_block_start", {
                "type": "content_block_start", "index": 0,
                "content_block": {"type": "text", "text": ""},
            }),
            _sse("content_block_delta", {
                "type": "content_block_delta", "index": 0,
                "delta": {"type": "text_delta", "text": "He"},
            }),
            _sse("content_block_delta", {
                "type": "content_block_delta", "index": 0,
                "delta": {"type": "text_delta", "text": "llo"},
            }),
            _sse("content_block_stop", {
                "type": "content_block_stop", "index": 0,
            }),
        ]
        if not truncate:
            frames += [
                _sse("message_delta", {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn"},
                    "usage": {"output_tokens": 2},
                }),
                _sse("message_stop", {"type": "message_stop"}),
            ]
        return "".join(frames).encode("utf-8")
    if provider == "google":
        frames = [
            _sse(None, {
                "candidates": [{
                    "content": {"role": "model", "parts": [{"text": "He"}]},
                }],
            }),
            _sse(None, {
                "candidates": [{
                    "content": {"role": "model", "parts": [{"text": "llo"}]},
                    **({} if truncate else {"finishReason": "STOP"}),
                }],
                **({} if truncate else {
                    "usageMetadata": {
                        "promptTokenCount": 3, "candidatesTokenCount": 2,
                    },
                }),
            }),
        ]
        return "".join(frames).encode("utf-8")
    if provider == "mistral":
        frames = [
            _sse(None, {
                "object": "chat.completion.chunk", "model": _MODEL,
                "choices": [{"index": 0, "delta": {
                    "role": "assistant", "content": "He",
                }, "finish_reason": None}],
            }),
            _sse(None, {
                "object": "chat.completion.chunk", "model": _MODEL,
                "choices": [{"index": 0, "delta": {
                    "content": "llo",
                }, "finish_reason": None if truncate else "stop"}],
            }),
        ]
        if not truncate:
            frames += [
                _sse(None, {
                    "object": "chat.completion.chunk", "model": _MODEL,
                    "choices": [],
                    "usage": {
                        "prompt_tokens": 3, "completion_tokens": 2,
                        "total_tokens": 5,
                    },
                }),
                "data: [DONE]\n\n",
            ]
        return "".join(frames).encode("utf-8")
    raise ValueError("unknown_stream_fixture_provider")


def malformed_wire(provider: str) -> bytes:
    """An invalid JSON frame which must fail before provider completion."""
    if provider == "ollama":
        return b'{"invalid":\n'
    return b'data: {"invalid":\n\n'


def stream_mime(provider: str) -> str:
    return "application/x-ndjson" if provider == "ollama" else "text/event-stream"
