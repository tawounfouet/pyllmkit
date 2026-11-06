"""Opt-in OpenAI Responses HTTP adapter. No network at import or construction.

The implementation calls the official Responses endpoint with exact URL/TLS,
store=false, no tools, bounded reply, no redirects/proxies/retries. HTTPX is
optional. An injected _test_transport is allowed only for offline tests.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pyllmkit.adapters.inference.errors import normalize_http_failure
from pyllmkit.adapters.inference.openai_responses_mapping import (
    decode_openai_responses_response,
    encode_openai_responses_request,
)
from pyllmkit.adapters.inference.security import (
    ProviderConnectionConfig,
    ProviderProfile,
)
from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.domain.inference import InferenceResponse
from pyllmkit.protocols.credentials import CredentialResolverPort, SecretValue

_MAX_REQUEST_BYTES = 1_048_576
_MAX_RESPONSE_BYTES = 2_097_152
_OFFICIAL_URL = "https://api.openai.com/v1/responses"


def _httpx() -> Any:
    try:
        import httpx
    except ImportError:
        raise InvocationPortError("optional_dependency_missing") from None
    return httpx


def _validate(config: ProviderConnectionConfig, resolver: CredentialResolverPort) -> None:
    if (
        type(config) is not ProviderConnectionConfig
        or config.profile is not ProviderProfile.OPENAI
        or config.endpoint_url != _OFFICIAL_URL
        or config.credential_ref is None
        or not config.verify_tls
        or config.follow_redirects
        or config.allow_local
    ):
        raise InvocationPortError("adapter_connection_invalid")
    if not isinstance(resolver, CredentialResolverPort):
        raise InvocationPortError("credential_resolver_invalid")


def _deadline(prepared: PreparedInvocation, config: ProviderConnectionConfig) -> float:
    remaining = (prepared.context.deadline - datetime.now(UTC)).total_seconds()
    if remaining <= 0:
        raise InvocationPortError("provider_timeout")
    return min(remaining, config.timeout_seconds)


def _authorize_secret(
    config: ProviderConnectionConfig, resolver: CredentialResolverPort,
) -> str:
    reference = config.credential_ref
    if reference is None:
        raise InvocationPortError("credential_unavailable")
    try:
        secret = resolver.resolve(reference)
    except Exception:
        # External resolvers may include a secret inside their exception.
        raise InvocationPortError("credential_unavailable") from None
    if type(secret) is not SecretValue:
        raise InvocationPortError("credential_unavailable")
    return secret.reveal()


def _prepare(prepared: PreparedInvocation) -> bytes:
    body = encode_openai_responses_request(prepared)
    if len(body) > _MAX_REQUEST_BYTES:
        raise InvocationPortError("request_too_large")
    return body


def _collect(chunks: Any) -> bytes:
    result = bytearray()
    for chunk in chunks:
        result.extend(chunk)
        if len(result) > _MAX_RESPONSE_BYTES:
            raise InvocationPortError("response_too_large")
    return bytes(result)


async def _acollect(chunks: Any) -> bytes:
    result = bytearray()
    async for chunk in chunks:
        result.extend(chunk)
        if len(result) > _MAX_RESPONSE_BYTES:
            raise InvocationPortError("response_too_large")
    return bytes(result)


def _check_response(status: int, content_type: str) -> None:
    if status != 200:
        raise normalize_http_failure(status)
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise InvocationPortError("provider_protocol_error")


@dataclass(frozen=True, slots=True)
class OpenAIResponsesAdapter:
    """Sync cloud transport: disabled until the owner opts into live use."""

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
        # Freeze is not a security boundary against object.__setattr__ mutation.
        _validate(self.config, self.credentials)
        body = _prepare(prepared)
        timeout = _deadline(prepared, self.config)
        secret = _authorize_secret(self.config, self.credentials)
        httpx = _httpx()
        try:
            with httpx.Client(
                trust_env=False, follow_redirects=False, verify=True,
                timeout=timeout, transport=self._test_transport,
            ) as client:
                with client.stream(
                    "POST", self.config.endpoint_url, content=body,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Authorization": f"Bearer {secret}",
                    },
                ) as response:
                    _check_response(
                        response.status_code, response.headers.get("content-type", ""),
                    )
                    raw = _collect(response.iter_bytes())
        except InvocationPortError:
            raise
        except httpx.TimeoutException:
            raise InvocationPortError("provider_timeout") from None
        except httpx.ConnectError:
            raise InvocationPortError("connection_failure") from None
        except httpx.HTTPError:
            raise InvocationPortError("provider_protocol_error") from None
        return decode_openai_responses_response(raw, prepared)


@dataclass(frozen=True, slots=True)
class AsyncOpenAIResponsesAdapter:
    """Native async cloud transport with wall-clock cancellation on deadline."""

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
        _validate(self.config, self.credentials)
        body = _prepare(prepared)
        timeout = _deadline(prepared, self.config)
        secret = _authorize_secret(self.config, self.credentials)
        httpx = _httpx()
        try:
            async with asyncio.timeout(timeout):
                async with httpx.AsyncClient(
                    trust_env=False, follow_redirects=False, verify=True,
                    timeout=timeout, transport=self._test_transport,
                ) as client:
                    async with client.stream(
                        "POST", self.config.endpoint_url, content=body,
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                            "Authorization": f"Bearer {secret}",
                        },
                    ) as response:
                        _check_response(
                            response.status_code, response.headers.get("content-type", ""),
                        )
                        raw = await _acollect(response.aiter_bytes())
        except InvocationPortError:
            raise
        except (TimeoutError, httpx.TimeoutException):
            raise InvocationPortError("provider_timeout") from None
        except httpx.ConnectError:
            raise InvocationPortError("connection_failure") from None
        except httpx.HTTPError:
            raise InvocationPortError("provider_protocol_error") from None
        return decode_openai_responses_response(raw, prepared)
