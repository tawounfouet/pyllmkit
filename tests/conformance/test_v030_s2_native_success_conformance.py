"""S2 six native success decoders: same observable contract, unique wire formats.

All traffic is injected httpx.MockTransport. The expected equality is
domain behavior (text, run ID, observed usage), not provider-native JSON.
"""

import asyncio

import httpx
import pytest

from pyllmkit.domain.inference import FinishReasonCode
from tests.conformance.providers import PROVIDERS, adapter, prepared

_TEXT = "Réponse synthétique: été ☀"
_ALIAS = "synthetic-text-model"


def _response_payload(provider: str, *, include_usage: bool = True) -> dict[str, object]:
    if provider == "openai":
        body: dict[str, object] = {
            "id": "resp_v030_test",
            "object": "response", "status": "completed", "model": _ALIAS,
            "error": None, "incomplete_details": None,
            "output": [{
                "type": "message", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": _TEXT, "annotations": []}],
            }],
        }
        if include_usage:
            body["usage"] = {
                "input_tokens": 7, "output_tokens": 3, "total_tokens": 10,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens_details": {"reasoning_tokens": 0},
            }
    elif provider == "anthropic":
        body = {
            "id": "msg_v030_test", "type": "message", "role": "assistant",
            "model": _ALIAS,
            "content": [{"type": "text", "text": _TEXT, "citations": None}],
            "stop_reason": "end_turn", "stop_sequence": None,
        }
        if include_usage:
            body["usage"] = {
                "input_tokens": 7, "output_tokens": 3,
                "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
            }
    elif provider == "google":
        body = {
            "candidates": [{
                "content": {"role": "model", "parts": [{"text": _TEXT}]},
                "finishReason": "STOP",
            }],
        }
        if include_usage:
            body["usageMetadata"] = {
                "promptTokenCount": 7, "candidatesTokenCount": 3,
                "totalTokenCount": 10,
                "cachedContentTokenCount": 0, "thoughtsTokenCount": 0,
            }
    elif provider == "xai":
        body = {
            "object": "response", "status": "completed", "model": _ALIAS,
            "store": False, "error": None,
            "output": [{
                "type": "message", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": _TEXT, "annotations": []}],
            }],
        }
        if include_usage:
            body["usage"] = {
                "prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10,
                "prompt_tokens_details": {"cached_tokens": 0},
                "completion_tokens_details": {"reasoning_tokens": 0},
            }
    elif provider == "mistral":
        body = {
            "object": "chat.completion", "model": _ALIAS,
            "choices": [{
                "index": 0, "finish_reason": "stop",
                "message": {
                    "role": "assistant", "content": _TEXT,
                    "tool_calls": None, "prefix": False,
                },
            }],
        }
        if include_usage:
            body["usage"] = {
                "prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10,
            }
    elif provider == "ollama":
        body = {
            "model": _ALIAS, "done": True,
            "message": {"role": "assistant", "content": _TEXT},
            "done_reason": "stop",
        }
        if include_usage:
            body["prompt_eval_count"] = 7
            body["eval_count"] = 3
    else:
        raise AssertionError(f"unsupported synthetic fixture profile: {provider}")
    return body


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
@pytest.mark.parametrize("include_usage", (False, True), ids=("usage_absent", "usage_present"))
def test_native_response_projection_is_consistent_and_lossless(
    provider: str, async_mode: bool, include_usage: bool,
) -> None:
    calls: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=_response_payload(provider, include_usage=include_usage),
        )

    case = prepared(provider)
    native = adapter(
        provider, transport=httpx.MockTransport(respond), async_mode=async_mode,
    )
    if async_mode:
        response = asyncio.run(native.ainvoke(case))
    else:
        response = native.invoke(case)

    assert response.run_id == case.context.run_id
    assert response.output.text == _TEXT
    assert response.finish_reason is not None
    expected_finish = (
        FinishReasonCode.UNKNOWN
        if provider in {"openai", "xai"}
        else FinishReasonCode.STOP
    )
    assert response.finish_reason.code is expected_finish
    if include_usage:
        assert response.usage is not None
        assert response.usage.input_tokens == 7
        assert response.usage.output_tokens == 3
    else:
        assert response.usage is None
    assert len(calls) == 1
