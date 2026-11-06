"""S4 cross-provider response, usage and finish semantics, sync and async.

No provider-specific output is forced into a false universal STOP, no
partial token Usage is reconstructed and unsupported structured state
must fail closed. All HTTP endpoints use httpx.MockTransport only.
"""

import asyncio
from copy import deepcopy

import httpx
import pytest

from pyllmkit.application.inference import InvocationPortError
from pyllmkit.domain.inference import FinishReasonCode
from tests.conformance.providers import PROVIDERS, adapter, prepared
from tests.conformance.test_v030_s2_native_success_conformance import (
    _response_payload,
)

_SCENARIOS = (
    "usage_partial_zero", "usage_negative",
    "finish_length", "finish_unknown", "structured_or_filtered",
)
_UNKNOWN_RESPONSE_PROVIDERS = frozenset({"openai", "xai"})


def _fixture(provider: str, scenario: str) -> dict[str, object]:
    body = deepcopy(_response_payload(provider, include_usage=True))
    if scenario == "usage_partial_zero" or scenario == "usage_negative":
        value = 0 if scenario == "usage_partial_zero" else -1
        if provider == "openai":
            body["usage"] = {"input_tokens": value}
        elif provider == "anthropic":
            body["usage"] = {"input_tokens": value}
        elif provider == "google":
            body["usageMetadata"] = {"promptTokenCount": value}
        elif provider == "xai":
            body["usage"] = {"prompt_tokens": value}
        elif provider == "mistral":
            body["usage"] = {"prompt_tokens": value}
        else:
            body.pop("eval_count", None)
            body["prompt_eval_count"] = value
    elif scenario == "finish_length":
        if provider == "anthropic":
            body["stop_reason"] = "max_tokens"
        elif provider == "google":
            body["candidates"][0]["finishReason"] = "MAX_TOKENS"  # type: ignore[index]
        elif provider == "mistral":
            body["choices"][0]["finish_reason"] = "length"  # type: ignore[index]
        elif provider == "ollama":
            body["done_reason"] = "length"
    elif scenario == "finish_unknown":
        if provider == "anthropic":
            body["stop_reason"] = "new_vendor_reason"
        elif provider == "google":
            body["candidates"][0]["finishReason"] = "NEW_VENDOR_REASON"  # type: ignore[index]
        elif provider == "mistral":
            body["choices"][0]["finish_reason"] = "new_vendor_reason"  # type: ignore[index]
        elif provider == "ollama":
            body["done_reason"] = "new_vendor_reason"
    elif scenario == "structured_or_filtered":
        if provider in _UNKNOWN_RESPONSE_PROVIDERS:
            body["output"][0]["type"] = "function_call"  # type: ignore[index]
        elif provider == "anthropic":
            body["stop_reason"] = "tool_use"
        elif provider == "google":
            body["candidates"][0]["finishReason"] = "SAFETY"  # type: ignore[index]
        elif provider == "mistral":
            body["choices"][0]["finish_reason"] = "tool_calls"  # type: ignore[index]
        else:
            body["message"]["tool_calls"] = [{"function": {"name": "x"}}]  # type: ignore[index]
    else:
        raise AssertionError("unknown_qa_scenario")
    return body


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
@pytest.mark.parametrize("scenario", _SCENARIOS)
def test_native_response_usage_and_finish_semantics(
    provider: str, async_mode: bool, scenario: str,
) -> None:
    calls: list[httpx.Request] = []

    def reply(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200, headers={"content-type": "application/json"},
            json=_fixture(provider, scenario),
        )

    case = prepared(provider)
    transport = httpx.MockTransport(reply)
    native = adapter(provider, transport=transport, async_mode=async_mode)

    if scenario in ("usage_negative", "structured_or_filtered"):
        expected = (
            "provider_content_filtered"
            if scenario == "structured_or_filtered" and provider == "google"
            else "unsupported_provider_output"
            if scenario == "structured_or_filtered"
            else "provider_protocol_error"
        )
        with pytest.raises(InvocationPortError, match=expected) as caught:
            if async_mode:
                asyncio.run(native.ainvoke(case))
            else:
                native.invoke(case)
        assert caught.value.code == expected
        assert str(caught.value) == expected
    else:
        response = (
            asyncio.run(native.ainvoke(case)) if async_mode else native.invoke(case)
        )
        assert response.run_id == case.context.run_id
        assert response.finish_reason is not None
        if scenario == "usage_partial_zero":
            assert response.usage is not None
            assert response.usage.input_tokens == 0
            assert response.usage.output_tokens is None
            assert response.usage.total_tokens is None
            assert response.usage.cached_input_tokens is None
            assert response.usage.reasoning_tokens is None
        elif scenario == "finish_length":
            expected_finish = (
                FinishReasonCode.UNKNOWN
                if provider in _UNKNOWN_RESPONSE_PROVIDERS else FinishReasonCode.LENGTH
            )
            assert response.finish_reason.code is expected_finish
        else:
            assert response.finish_reason.code is FinishReasonCode.UNKNOWN
    assert len(calls) == 1
