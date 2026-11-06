"""S2 initial six-native-provider error conformance (HTTPX MockTransport only).

Identical status-to-safe-code expectations against real sync and async
provider HTTP adapters. No live sockets, no environment credentials.
"""

import asyncio

import httpx
import pytest

from pyllmkit.application.inference import InvocationPortError

from tests.conformance.providers import (
    FAKE_SECRET,
    PROVIDERS,
    adapter,
    prepared,
)

_HTTP_ERRORS = (
    (400, "invalid_request"),
    (401, "authentication_failed"),
    (403, "permission_denied"),
    (404, "model_not_found"),
    (408, "provider_timeout"),
    (429, "rate_limited"),
    (500, "provider_overloaded"),
    (503, "provider_overloaded"),
    (504, "provider_timeout"),
)


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
@pytest.mark.parametrize(("status", "expected"), _HTTP_ERRORS)
def test_status_failure_has_one_safe_code_and_one_transport_attempt(
    provider: str, async_mode: bool, status: int, expected: str,
) -> None:
    calls: list[httpx.Request] = []
    secret_response_marker = "DO-NOT-LEAK-NATIVE-HTTP-BODY-SECRET"

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            status,
            headers={"content-type": "application/json"},
            json={"error": secret_response_marker},
        )

    transport = httpx.MockTransport(respond)
    case = prepared(provider)
    native = adapter(provider, transport=transport, async_mode=async_mode)

    with pytest.raises(InvocationPortError) as raised:
        if async_mode:
            asyncio.run(native.ainvoke(case))
        else:
            native.invoke(case)

    assert raised.value.code == expected
    assert str(raised.value) == expected
    assert secret_response_marker not in str(raised.value)
    assert FAKE_SECRET not in str(raised.value)
    assert len(calls) == 1


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
def test_explicit_live_opt_in_gate_prevents_even_mock_transport_contact(
    provider: str, async_mode: bool,
) -> None:
    calls: list[httpx.Request] = []

    def fail_if_contacted(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise AssertionError("mock transport must not be contacted")

    transport = httpx.MockTransport(fail_if_contacted)
    case = prepared(provider)
    native = adapter(
        provider,
        transport=transport,
        async_mode=async_mode,
        allow_live=False,
    )
    with pytest.raises(InvocationPortError) as raised:
        if async_mode:
            asyncio.run(native.ainvoke(case))
        else:
            native.invoke(case)
    assert raised.value.code == "live_authorization_required"
    assert calls == []
