"""S3 cross-provider transport and malformed response error taxonomy.

These tests invoke actual sync/async native adapters with a deterministic
MockTransport. They never call a provider service or access process secrets.
"""

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest

from pyllmkit.application.inference import InvocationPortError
from tests.conformance.providers import FAKE_SECRET, PROVIDERS, adapter, prepared
from tests.conformance.test_v030_s2_native_success_conformance import _response_payload

_SECRET_MARKER = "SYNTHETIC-NATIVE-ERROR-CONFIDENTIAL-NOT-A-REAL-SECRET"

_TRANSPORT_EXCEPTIONS: tuple[tuple[type[httpx.HTTPError], str], ...] = (
    (httpx.ConnectError, "connection_failure"),
    (httpx.ReadTimeout, "provider_timeout"),
    (httpx.ReadError, "provider_protocol_error"),
    (httpx.RemoteProtocolError, "provider_protocol_error"),
)


def _call(
    provider: str,
    async_mode: bool,
    handler: Callable[[httpx.Request], httpx.Response],
) -> tuple[InvocationPortError, list[httpx.Request]]:
    calls: list[httpx.Request] = []

    def track(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return handler(request)

    native = adapter(
        provider, transport=httpx.MockTransport(track), async_mode=async_mode,
    )
    case = prepared(provider)
    with pytest.raises(InvocationPortError) as caught:
        if async_mode:
            asyncio.run(native.ainvoke(case))
        else:
            native.invoke(case)
    error = caught.value
    assert str(error) == error.code
    assert _SECRET_MARKER not in str(error)
    assert FAKE_SECRET not in str(error)
    return error, calls


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
@pytest.mark.parametrize(("failure_type", "safe_code"), _TRANSPORT_EXCEPTIONS)
def test_native_transport_error_is_sanitized_and_nonretryable(
    provider: str, async_mode: bool,
    failure_type: type[httpx.HTTPError], safe_code: str,
) -> None:
    def failure(_request: httpx.Request) -> httpx.Response:
        raise failure_type(_SECRET_MARKER)

    error, calls = _call(provider, async_mode, failure)
    assert error.code == safe_code
    assert len(calls) == 1


def _native_bytes(provider: str, scenario: str) -> tuple[int, str, bytes]:
    if scenario == "bad_mime":
        return 200, "text/plain", b'{"body": "do not parse"}'
    if scenario == "malformed":
        return 200, "application/json", b'{"bad": '
    if scenario == "response_too_large":
        return 200, "application/json", b"x" * (2_097_152 + 1)
    if scenario == "redirect":
        return 302, "application/json", b'{"error": "no redirect following"}'
    data = _response_payload(provider)
    if scenario == "duplicate_key":
        key = next(iter(data))
        encoded = json.dumps(data, ensure_ascii=False)
        first = json.dumps(key) + ":" + json.dumps(data[key], ensure_ascii=False) + ","
        return 200, "application/json", ("{" + first + encoded[1:]).encode()
    if scenario == "nonfinite_constant":
        if provider == "ollama":
            data["total_duration"] = float("nan")
        else:
            data["nonfinite_unused_probe"] = float("nan")
        return 200, "application/json", json.dumps(data).encode()
    raise AssertionError("unsupported_s3_scenario")


_RESPONSE_SCENARIOS = (
    ("bad_mime", "provider_protocol_error"),
    ("malformed", "provider_protocol_error"),
    ("response_too_large", "response_too_large"),
    ("redirect", "provider_protocol_error"),
    ("duplicate_key", "provider_protocol_error"),
    ("nonfinite_constant", "provider_protocol_error"),
)


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
@pytest.mark.parametrize(("scenario", "safe_code"), _RESPONSE_SCENARIOS)
def test_native_response_failure_is_strict_and_nonleaking(
    provider: str, async_mode: bool, scenario: str, safe_code: str,
) -> None:
    status, mime, raw = _native_bytes(provider, scenario)

    def responder(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=raw, headers={"content-type": mime})

    error, calls = _call(provider, async_mode, responder)
    assert error.code == safe_code
    assert len(calls) == 1
