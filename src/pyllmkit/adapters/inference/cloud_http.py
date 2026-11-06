"""P7 common opt-in cloud HTTP transport for strict provider-native JSON adapters.

This transport never performs automatic retries, routing, redirects or proxy
discovery. Callers must validate the exact endpoint and model alias. The
injected _test_transport is for hermetic MockTransport tests only.
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any

from pyllmkit.adapters.inference.errors import normalize_http_failure
from pyllmkit.adapters.inference.security import ProviderConnectionConfig, ProviderProfile
from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.protocols.credentials import CredentialResolverPort, SecretValue

_MAX_REQUEST_BYTES = 1_048_576
_MAX_RESPONSE_BYTES = 2_097_152


def validate_cloud_connection(
    config: ProviderConnectionConfig,
    credentials: CredentialResolverPort,
    *,
    profile: ProviderProfile,
    base_url: str,
) -> None:
    """Check a frozen config even if unsafe code mutated it after construction."""
    if (
        type(config) is not ProviderConnectionConfig
        or config.profile is not profile
        or config.endpoint_url != base_url
        or config.credential_ref is None
        or not config.verify_tls
        or config.follow_redirects
        or config.allow_local
    ):
        raise InvocationPortError("adapter_connection_invalid")
    if not isinstance(credentials, CredentialResolverPort):
        raise InvocationPortError("credential_resolver_invalid")


def _validate_destination(profile: ProviderProfile, base_url: str, url: str) -> None:
    if type(url) is not str:
        raise InvocationPortError("adapter_connection_invalid")
    if profile is ProviderProfile.GOOGLE:
        prefix = base_url + "/"
        if (
            not url.startswith(prefix)
            or re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}:generateContent",
                url[len(prefix):],
            ) is None
        ):
            raise InvocationPortError("adapter_connection_invalid")
    elif url != base_url:
        raise InvocationPortError("adapter_connection_invalid")


def validate_live_flag(value: bool) -> None:
    if type(value) is not bool:
        raise InvocationPortError("live_authorization_invalid")


def require_live(value: bool) -> None:
    if not value:
        raise InvocationPortError("live_authorization_required")


def require_body_limit(body: bytes) -> bytes:
    if type(body) is not bytes or len(body) > _MAX_REQUEST_BYTES:
        raise InvocationPortError("request_too_large")
    return body


def _httpx() -> Any:
    try:
        import httpx
    except ImportError:
        raise InvocationPortError("optional_dependency_missing") from None
    return httpx


def _timeout(prepared: PreparedInvocation, config: ProviderConnectionConfig) -> float:
    if type(prepared) is not PreparedInvocation:
        raise InvocationPortError("adapter_protocol_error")
    remaining = (prepared.context.deadline - datetime.now(UTC)).total_seconds()
    if remaining <= 0:
        raise InvocationPortError("provider_timeout")
    return min(remaining, config.timeout_seconds)


def _secret(config: ProviderConnectionConfig, resolver: CredentialResolverPort) -> str:
    ref = config.credential_ref
    if ref is None:
        raise InvocationPortError("credential_unavailable")
    try:
        value = resolver.resolve(ref)
    except Exception:
        raise InvocationPortError("credential_unavailable") from None
    if type(value) is not SecretValue:
        raise InvocationPortError("credential_unavailable")
    return value.reveal()


def _headers(value: str, auth: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if auth == "x-goog-api-key":
        headers["x-goog-api-key"] = value
    elif auth == "bearer":
        headers["Authorization"] = f"Bearer {value}"
    else:
        raise InvocationPortError("adapter_connection_invalid")
    return headers


def _check_response(status: int, content_type: str) -> None:
    if status != 200:
        raise normalize_http_failure(status)
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise InvocationPortError("provider_protocol_error")


def _read_bounded(chunks: Any) -> bytes:
    parts = bytearray()
    for chunk in chunks:
        parts.extend(chunk)
        if len(parts) > _MAX_RESPONSE_BYTES:
            raise InvocationPortError("response_too_large")
    return bytes(parts)


async def _aread_bounded(chunks: Any) -> bytes:
    parts = bytearray()
    async for chunk in chunks:
        parts.extend(chunk)
        if len(parts) > _MAX_RESPONSE_BYTES:
            raise InvocationPortError("response_too_large")
    return bytes(parts)


def cloud_post_sync(
    prepared: PreparedInvocation,
    config: ProviderConnectionConfig,
    credentials: CredentialResolverPort,
    *,
    profile: ProviderProfile,
    base_url: str,
    url: str,
    body: bytes,
    auth: str,
    test_transport: object | None = None,
) -> bytes:
    """Single bounded request; does not decode a provider-specific payload."""
    validate_cloud_connection(config, credentials, profile=profile, base_url=base_url)
    _validate_destination(profile, base_url, url)
    payload = require_body_limit(body)
    timeout = _timeout(prepared, config)
    key = _secret(config, credentials)
    httpx = _httpx()
    try:
        with httpx.Client(
            trust_env=False, follow_redirects=False, verify=True,
            timeout=timeout, transport=test_transport,
        ) as client:
            with client.stream(
                "POST", url, content=payload, headers=_headers(key, auth),
            ) as response:
                _check_response(response.status_code, response.headers.get("content-type", ""))
                return _read_bounded(response.iter_bytes())
    except InvocationPortError:
        raise
    except httpx.TimeoutException:
        raise InvocationPortError("provider_timeout") from None
    except httpx.ConnectError:
        raise InvocationPortError("connection_failure") from None
    except httpx.HTTPError:
        raise InvocationPortError("provider_protocol_error") from None


async def cloud_post_async(
    prepared: PreparedInvocation,
    config: ProviderConnectionConfig,
    credentials: CredentialResolverPort,
    *,
    profile: ProviderProfile,
    base_url: str,
    url: str,
    body: bytes,
    auth: str,
    test_transport: object | None = None,
) -> bytes:
    """Single async request, bounded additionally by a wall-clock deadline."""
    validate_cloud_connection(config, credentials, profile=profile, base_url=base_url)
    payload = require_body_limit(body)
    timeout = _timeout(prepared, config)
    key = _secret(config, credentials)
    httpx = _httpx()
    try:
        async with asyncio.timeout(timeout):
            async with httpx.AsyncClient(
                trust_env=False, follow_redirects=False, verify=True,
                timeout=timeout, transport=test_transport,
            ) as client:
                async with client.stream(
                    "POST", url, content=payload, headers=_headers(key, auth),
                ) as response:
                    _check_response(
                        response.status_code, response.headers.get("content-type", ""),
                    )
                    return await _aread_bounded(response.aiter_bytes())
    except InvocationPortError:
        raise
    except (TimeoutError, httpx.TimeoutException):
        raise InvocationPortError("provider_timeout") from None
    except httpx.ConnectError:
        raise InvocationPortError("connection_failure") from None
    except httpx.HTTPError:
        raise InvocationPortError("provider_protocol_error") from None
