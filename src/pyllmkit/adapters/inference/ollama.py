"""Explicitly opted-in Ollama HTTP text adapters for loopback only (P7 L7.3).

HTTPX is optional, imported only at invocation. IP-literal endpoints, no
environment proxies or redirects, one attempt and bounded responses.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.domain.inference import InferenceResponse
from pyllmkit.adapters.inference.errors import normalize_http_failure
from pyllmkit.adapters.inference.ollama_mapping import (
    decode_ollama_response,
    encode_ollama_request,
)
from pyllmkit.adapters.inference.security import (
    ProviderConnectionConfig,
    ProviderProfile,
)

_MAX_REQUEST_BYTES = 1_048_576
_MAX_RESPONSE_BYTES = 2_097_152


def _import_httpx() -> Any:
    try:
        import httpx
    except ImportError:
        raise InvocationPortError("optional_dependency_missing") from None
    return httpx


def _checked_timeout(prepared: PreparedInvocation, config: ProviderConnectionConfig) -> float:
    """Apply remaining application deadline and bounded connection timeout."""
    remaining = (prepared.context.deadline - datetime.now(UTC)).total_seconds()
    if remaining <= 0:
        raise InvocationPortError("provider_timeout")
    return min(remaining, config.timeout_seconds)


def _preflight(prepared: PreparedInvocation, config: ProviderConnectionConfig) -> bytes:
    if type(config) is not ProviderConnectionConfig or config.profile is not ProviderProfile.OLLAMA:
        raise InvocationPortError("adapter_connection_invalid")
    if not config.allow_local or config.credential_ref is not None or config.follow_redirects:
        raise InvocationPortError("adapter_connection_invalid")
    # Defense in depth: re-validate immutable connection data before transport.
    from urllib.parse import urlsplit

    endpoint = urlsplit(config.endpoint_url)
    if endpoint.hostname not in ("127.0.0.1", "::1") or endpoint.path != "/api/chat":
        raise InvocationPortError("adapter_connection_invalid")
    body = encode_ollama_request(prepared)
    if len(body) > _MAX_REQUEST_BYTES:
        raise InvocationPortError("request_too_large")
    return body


def _require_content_type(value: str) -> None:
    if value.split(";", 1)[0].strip().lower() != "application/json":
        raise InvocationPortError("provider_protocol_error")


def _require_status(status: int) -> None:
    if status != 200:
        raise normalize_http_failure(status)


def _gather_bytes(chunks: Any) -> bytes:
    collected = bytearray()
    for chunk in chunks:
        collected.extend(chunk)
        if len(collected) > _MAX_RESPONSE_BYTES:
            raise InvocationPortError("response_too_large")
    return bytes(collected)


async def _agather_bytes(chunks: Any) -> bytes:
    collected = bytearray()
    async for chunk in chunks:
        collected.extend(chunk)
        if len(collected) > _MAX_RESPONSE_BYTES:
            raise InvocationPortError("response_too_large")
    return bytes(collected)


@dataclass(frozen=True, slots=True)
class OllamaAdapter:
    """Synchronous pilot. Default construction NEVER authorizes live I/O.

    _test_transport is a test-only injection point; external transports are not
    covered by the no-proxy/no-network proof. Do not use it in production.
    """

    config: ProviderConnectionConfig = field(repr=False)
    allow_live: bool = False
    _test_transport: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.config) is not ProviderConnectionConfig:
            raise InvocationPortError("adapter_connection_invalid")
        if type(self.allow_live) is not bool:
            raise InvocationPortError("live_authorization_invalid")

    def invoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        if not self.allow_live:
            raise InvocationPortError("live_authorization_required")
        body = _preflight(prepared, self.config)
        httpx = _import_httpx()
        timeout = _checked_timeout(prepared, self.config)
        try:
            with httpx.Client(
                trust_env=False, follow_redirects=False,
                timeout=timeout, transport=self._test_transport,
            ) as client:
                with client.stream(
                    "POST", self.config.endpoint_url, content=body,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                ) as response:
                    _require_status(response.status_code)
                    _require_content_type(response.headers.get("content-type", ""))
                    raw = _gather_bytes(response.iter_bytes())
        except InvocationPortError:
            raise
        except httpx.TimeoutException:
            raise InvocationPortError("provider_timeout") from None
        except httpx.ConnectError:
            raise InvocationPortError("connection_failure") from None
        except httpx.HTTPError:
            raise InvocationPortError("provider_protocol_error") from None
        return decode_ollama_response(raw, prepared)


@dataclass(frozen=True, slots=True)
class AsyncOllamaAdapter:
    """Asynchronous native request; task cancellation propagates naturally."""

    config: ProviderConnectionConfig = field(repr=False)
    allow_live: bool = False
    _test_transport: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.config) is not ProviderConnectionConfig:
            raise InvocationPortError("adapter_connection_invalid")
        if type(self.allow_live) is not bool:
            raise InvocationPortError("live_authorization_invalid")

    async def ainvoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        if not self.allow_live:
            raise InvocationPortError("live_authorization_required")
        body = _preflight(prepared, self.config)
        httpx = _import_httpx()
        remaining = _checked_timeout(prepared, self.config)
        try:
            async with asyncio.timeout(remaining):
                async with httpx.AsyncClient(
                    trust_env=False, follow_redirects=False,
                    timeout=remaining, transport=self._test_transport,
                ) as client:
                    async with client.stream(
                        "POST", self.config.endpoint_url, content=body,
                        headers={"Content-Type": "application/json", "Accept": "application/json"},
                    ) as response:
                        _require_status(response.status_code)
                        _require_content_type(response.headers.get("content-type", ""))
                        raw = await _agather_bytes(response.aiter_bytes())
        except InvocationPortError:
            raise
        except (TimeoutError, httpx.TimeoutException):
            raise InvocationPortError("provider_timeout") from None
        except httpx.ConnectError:
            raise InvocationPortError("connection_failure") from None
        except httpx.HTTPError:
            raise InvocationPortError("provider_protocol_error") from None
        return decode_ollama_response(raw, prepared)
