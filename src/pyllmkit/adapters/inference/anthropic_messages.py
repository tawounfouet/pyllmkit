"""Opt-in HTTPX adapter for Anthropic Messages API (P7 L7.5).

Cloud network access is never performed at import or construction. With
allow_live=False an invocation stops before resolving credentials or HTTPX.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pyllmkit.adapters.inference.anthropic_messages_mapping import (
    decode_anthropic_messages_response,
    encode_anthropic_messages_request,
)
from pyllmkit.adapters.inference.errors import normalize_http_failure
from pyllmkit.adapters.inference.media_mapping import request_bytes_limit
from pyllmkit.adapters.inference.security import ProviderConnectionConfig, ProviderProfile
from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.domain.inference import InferenceResponse
from pyllmkit.protocols.credentials import CredentialResolverPort, SecretValue

_OFFICIAL_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2026-10-21"
_MAX_REQUEST_BYTES = 1_048_576
_MAX_RESPONSE_BYTES = 2_097_152


def _httpx() -> Any:
    try:
        import httpx
    except ImportError:
        raise InvocationPortError("optional_dependency_missing") from None
    return httpx


def _validate(config: ProviderConnectionConfig, credentials: CredentialResolverPort) -> None:
    if (
        type(config) is not ProviderConnectionConfig
        or config.profile is not ProviderProfile.ANTHROPIC
        or config.endpoint_url != _OFFICIAL_URL
        or config.credential_ref is None
        or not config.verify_tls
        or config.follow_redirects
        or config.allow_local
    ):
        raise InvocationPortError("adapter_connection_invalid")
    if not isinstance(credentials, CredentialResolverPort):
        raise InvocationPortError("credential_resolver_invalid")


def _timeout(prepared: PreparedInvocation, config: ProviderConnectionConfig) -> float:
    remaining = (prepared.context.deadline - datetime.now(UTC)).total_seconds()
    if remaining <= 0:
        raise InvocationPortError("provider_timeout")
    return min(remaining, config.timeout_seconds)


def _body(prepared: PreparedInvocation) -> bytes:
    encoded = encode_anthropic_messages_request(prepared)
    if len(encoded) > request_bytes_limit(prepared):
        raise InvocationPortError("request_too_large")
    return encoded


def _secret(config: ProviderConnectionConfig, resolver: CredentialResolverPort) -> str:
    reference = config.credential_ref
    if reference is None:
        raise InvocationPortError("credential_unavailable")
    try:
        value = resolver.resolve(reference)
    except Exception:
        raise InvocationPortError("credential_unavailable") from None
    if type(value) is not SecretValue:
        raise InvocationPortError("credential_unavailable")
    return value.reveal()


def _headers(key: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {key}",
        "anthropic-version": _API_VERSION,
    }


def _check(status: int, content_type: str) -> None:
    if status != 200:
        raise normalize_http_failure(status)
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise InvocationPortError("provider_protocol_error")


def _collect(chunks: Any) -> bytes:
    payload = bytearray()
    for part in chunks:
        payload.extend(part)
        if len(payload) > _MAX_RESPONSE_BYTES:
            raise InvocationPortError("response_too_large")
    return bytes(payload)


async def _acollect(chunks: Any) -> bytes:
    payload = bytearray()
    async for part in chunks:
        payload.extend(part)
        if len(payload) > _MAX_RESPONSE_BYTES:
            raise InvocationPortError("response_too_large")
    return bytes(payload)


@dataclass(frozen=True, slots=True)
class AnthropicMessagesAdapter:
    """Synchronous Messages API adapter; off until explicit authorization."""

    config: ProviderConnectionConfig = field(repr=False)
    credentials: CredentialResolverPort = field(repr=False)
    allow_live: bool = False
    _test_transport: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _validate(self.config, self.credentials)
        if type(self.allow_live) is not bool:
            raise InvocationPortError("live_authorization_invalid")

    def invoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        if not self.allow_live:
            raise InvocationPortError("live_authorization_required")
        body = _body(prepared)
        timeout = _timeout(prepared, self.config)
        key = _secret(self.config, self.credentials)
        httpx = _httpx()
        try:
            with httpx.Client(
                trust_env=False, follow_redirects=False, verify=True,
                timeout=timeout, transport=self._test_transport,
            ) as client:
                with client.stream(
                    "POST", self.config.endpoint_url, content=body,
                    headers=_headers(key),
                ) as response:
                    _check(response.status_code, response.headers.get("content-type", ""))
                    data = _collect(response.iter_bytes())
        except InvocationPortError:
            raise
        except httpx.TimeoutException:
            raise InvocationPortError("provider_timeout") from None
        except httpx.ConnectError:
            raise InvocationPortError("connection_failure") from None
        except httpx.HTTPError:
            raise InvocationPortError("provider_protocol_error") from None
        return decode_anthropic_messages_response(data, prepared)


@dataclass(frozen=True, slots=True)
class AsyncAnthropicMessagesAdapter:
    """Async Messages API adapter; cancellable locally, not remotely guaranteed."""

    config: ProviderConnectionConfig = field(repr=False)
    credentials: CredentialResolverPort = field(repr=False)
    allow_live: bool = False
    _test_transport: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _validate(self.config, self.credentials)
        if type(self.allow_live) is not bool:
            raise InvocationPortError("live_authorization_invalid")

    async def ainvoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        if not self.allow_live:
            raise InvocationPortError("live_authorization_required")
        body = _body(prepared)
        timeout = _timeout(prepared, self.config)
        key = _secret(self.config, self.credentials)
        httpx = _httpx()
        try:
            async with asyncio.timeout(timeout):
                async with httpx.AsyncClient(
                    trust_env=False, follow_redirects=False, verify=True,
                    timeout=timeout, transport=self._test_transport,
                ) as client:
                    async with client.stream(
                        "POST", self.config.endpoint_url, content=body,
                        headers=_headers(key),
                    ) as response:
                        _check(response.status_code, response.headers.get("content-type", ""))
                        data = await _acollect(response.aiter_bytes())
        except InvocationPortError:
            raise
        except (TimeoutError, httpx.TimeoutException):
            raise InvocationPortError("provider_timeout") from None
        except httpx.ConnectError:
            raise InvocationPortError("connection_failure") from None
        except httpx.HTTPError:
            raise InvocationPortError("provider_protocol_error") from None
        return decode_anthropic_messages_response(data, prepared)
