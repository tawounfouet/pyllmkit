"""P7 L7.6 opt-in HTTPX streaming transport for six provider protocols.

Pull-driven, bounded JSONL/SSE, no buffering of the entire HTTP response.
An injected transport is for deterministic tests only, NOT an SSRF/TLS proof.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterator
from dataclasses import dataclass, field

from pyllmkit.adapters.inference.anthropic_messages_mapping import (
    encode_anthropic_messages_request,
)
from pyllmkit.adapters.inference.cloud_http import (
    _headers,
    _httpx,
    _secret,
    _timeout,
    _validate_destination,
    require_body_limit,
    validate_cloud_connection,
    validate_live_flag,
)
from pyllmkit.adapters.inference.errors import normalize_http_failure
from pyllmkit.adapters.inference.google_gemini_mapping import (
    encode_gemini_request,
    gemini_model_alias,
)
from pyllmkit.adapters.inference.mistral_chat_mapping import encode_mistral_chat_request
from pyllmkit.adapters.inference.native_stream_mapping import (
    NativeStreamDecoder,
    decode_native_json,
)
from pyllmkit.adapters.inference.ollama_mapping import encode_ollama_request
from pyllmkit.adapters.inference.openai_responses_mapping import (
    encode_openai_responses_request,
)
from pyllmkit.adapters.inference.security import ProviderConnectionConfig, ProviderProfile
from pyllmkit.adapters.inference.xai_responses_mapping import encode_xai_responses_request
from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.domain.streaming import (
    ResponseCompleted,
    ResponseFailed,
    ResponseStarted,
    StreamEvent,
    TextDelta,
    UsageUpdated,
)
from pyllmkit.protocols.credentials import CredentialResolverPort

_MAX_WIRE_BYTES = 12 * 1024 * 1024
_MAX_LINE_BYTES = 262_144
_MAX_FRAMES = 100_000
_GOOGLE_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_ANHA_VERSION = "2026-10-21"
_CLOUD_BASE = {
    ProviderProfile.OPENAI: "https://api.openai.com/v1/responses",
    ProviderProfile.ANTHROPIC: "https://api.anthropic.com/v1/messages",
    ProviderProfile.GOOGLE: _GOOGLE_BASE,
    ProviderProfile.XAI: "https://api.x.ai/v1/responses",
    ProviderProfile.MISTRAL: "https://api.mistral.ai/v1/chat/completions",
}


def _bounded_lines(lines: Iterator[str]) -> Iterator[str]:
    used = 0
    for line in lines:
        if type(line) is not str:
            raise InvocationPortError("provider_protocol_error")
        size = len(line.encode("utf-8"))
        used += size + 1
        if size > _MAX_LINE_BYTES or used > _MAX_WIRE_BYTES:
            raise InvocationPortError("stream_wire_limit")
        yield line


async def _abounded_lines(lines: AsyncIterator[str]) -> AsyncIterator[str]:
    used = 0
    async for line in lines:
        if type(line) is not str:
            raise InvocationPortError("provider_protocol_error")
        size = len(line.encode("utf-8"))
        used += size + 1
        if size > _MAX_LINE_BYTES or used > _MAX_WIRE_BYTES:
            raise InvocationPortError("stream_wire_limit")
        yield line


def _sse_frames(lines: Iterator[str]) -> Iterator[tuple[str, str]]:
    event = "message"
    data: list[str] = []
    for line in lines:
        if line == "":
            if data:
                yield event, "\n".join(data)
            event, data = "message", []
        elif line.startswith(":"):
            continue
        elif line.startswith("event:"):
            if event != "message" or data:
                raise InvocationPortError("provider_protocol_error")
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
        else:
            raise InvocationPortError("provider_protocol_error")
    if data:
        raise InvocationPortError("provider_not_completed")


async def _asse_frames(lines: AsyncIterator[str]) -> AsyncIterator[tuple[str, str]]:
    event = "message"
    data: list[str] = []
    async for line in lines:
        if line == "":
            if data:
                yield event, "\n".join(data)
            event, data = "message", []
        elif line.startswith(":"):
            continue
        elif line.startswith("event:"):
            if event != "message" or data:
                raise InvocationPortError("provider_protocol_error")
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
        else:
            raise InvocationPortError("provider_protocol_error")
    if data:
        raise InvocationPortError("provider_not_completed")


def _native_payload(
    profile: ProviderProfile, prepared: PreparedInvocation,
) -> tuple[str, bytes]:
    if profile is ProviderProfile.OLLAMA:
        url = prepared.resolution.deployment.runtime
        if url != "ollama":
            raise InvocationPortError("adapter_connection_invalid")
        payload = json.loads(encode_ollama_request(prepared))
        target = ""
    elif profile is ProviderProfile.OPENAI:
        payload = json.loads(encode_openai_responses_request(prepared))
        target = _CLOUD_BASE[profile]
    elif profile is ProviderProfile.ANTHROPIC:
        payload = json.loads(encode_anthropic_messages_request(prepared))
        target = _CLOUD_BASE[profile]
    elif profile is ProviderProfile.GOOGLE:
        alias = gemini_model_alias(prepared)
        payload = json.loads(encode_gemini_request(prepared))
        target = f"{_GOOGLE_BASE}/{alias}:streamGenerateContent?alt=sse"
    elif profile is ProviderProfile.XAI:
        payload = json.loads(encode_xai_responses_request(prepared))
        target = _CLOUD_BASE[profile]
    elif profile is ProviderProfile.MISTRAL:
        payload = json.loads(encode_mistral_chat_request(prepared))
        target = _CLOUD_BASE[profile]
        payload["stream_options"] = {"include_usage": True}
    else:
        raise InvocationPortError("adapter_connection_invalid")
    if profile is not ProviderProfile.GOOGLE:
        payload["stream"] = True
    return target, require_body_limit(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
    )


def _response_header(profile: ProviderProfile, status: int, content_type: str) -> None:
    if status != 200:
        raise normalize_http_failure(status)
    mime = content_type.split(";", 1)[0].strip().lower()
    expected = (
        ("application/x-ndjson", "application/json")
        if profile is ProviderProfile.OLLAMA else ("text/event-stream",)
    )
    if mime not in expected:
        raise InvocationPortError("provider_protocol_error")


def _stream_headers(profile: ProviderProfile, key: str | None) -> dict[str, str]:
    if profile is ProviderProfile.OLLAMA:
        return {"Content-Type": "application/json", "Accept": "application/x-ndjson"}
    if key is None:
        raise InvocationPortError("credential_unavailable")
    headers = _headers(key, "x-goog-api-key" if profile is ProviderProfile.GOOGLE else "bearer")
    headers["Accept"] = "text/event-stream"
    if profile is ProviderProfile.ANTHROPIC:
        headers["anthropic-version"] = _ANHA_VERSION
    return headers


@dataclass(frozen=True, slots=True)
class NativeProviderStreamingAdapter:
    """One explicitly selected provider with sync and async prepared stream ports."""

    config: ProviderConnectionConfig = field(repr=False)
    credentials: CredentialResolverPort | None = field(default=None, repr=False)
    allow_live: bool = False
    _test_transport: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        validate_live_flag(self.allow_live)
        if type(self.config) is not ProviderConnectionConfig:
            raise InvocationPortError("adapter_connection_invalid")
        if self.config.profile is ProviderProfile.OLLAMA:
            if (
                self.config.runtime if hasattr(self.config, "runtime") else False
            ):
                raise InvocationPortError("adapter_connection_invalid")
            if not self.config.allow_local or self.config.credential_ref is not None:
                raise InvocationPortError("adapter_connection_invalid")
            if self.credentials is not None:
                raise InvocationPortError("credential_resolver_invalid")
        else:
            base = _CLOUD_BASE.get(self.config.profile)
            if base is None or self.credentials is None:
                raise InvocationPortError("adapter_connection_invalid")
            validate_cloud_connection(
                self.config, self.credentials,
                profile=self.config.profile, base_url=base,
            )

    def _request(
        self, prepared: PreparedInvocation,
    ) -> tuple[str, bytes, dict[str, str], float]:
        if not self.allow_live:
            raise InvocationPortError("live_authorization_required")
        target, body = _native_payload(self.config.profile, prepared)
        if self.config.profile is ProviderProfile.OLLAMA:
            from pyllmkit.adapters.inference.ollama import _preflight
            _preflight(prepared, self.config)
            target = self.config.endpoint_url
            key = None
        else:
            base = _CLOUD_BASE[self.config.profile]
            if self.config.profile is ProviderProfile.GOOGLE:
                import re
                if re.fullmatch(
                    re.escape(base) + r"/[A-Za-z0-9][A-Za-z0-9._-]{0,127}:streamGenerateContent\\?alt=sse",
                    target,
                ) is None:
                    raise InvocationPortError("adapter_connection_invalid")
            else:
                _validate_destination(self.config.profile, base, target)
            if self.credentials is None:
                raise InvocationPortError("credential_resolver_invalid")
            key = _secret(self.config, self.credentials)
        return target, body, _stream_headers(self.config.profile, key), _timeout(
            prepared, self.config,
        )

    def _frames(self, prepared: PreparedInvocation) -> Generator[tuple[str, str], None, None]:
        target, body, headers, timeout = self._request(prepared)
        httpx = _httpx()
        try:
            with httpx.Client(
                trust_env=False, follow_redirects=False, verify=True,
                timeout=timeout, transport=self._test_transport,
            ) as client:
                with client.stream(
                    "POST", target, content=body, headers=headers,
                ) as response:
                    _response_header(
                        self.config.profile, response.status_code,
                        response.headers.get("content-type", ""),
                    )
                    lines = _bounded_lines(response.iter_lines())
                    if self.config.profile is ProviderProfile.OLLAMA:
                        for line in lines:
                            if line:
                                yield "json", line
                    else:
                        yield from _sse_frames(lines)
        except InvocationPortError:
            raise
        except httpx.TimeoutException:
            raise InvocationPortError("provider_timeout") from None
        except httpx.ConnectError:
            raise InvocationPortError("connection_failure") from None
        except httpx.HTTPError:
            raise InvocationPortError("provider_protocol_error") from None

    async def _aframes(
        self, prepared: PreparedInvocation,
    ) -> AsyncGenerator[tuple[str, str], None]:
        target, body, headers, timeout = self._request(prepared)
        httpx = _httpx()
        try:
            async with asyncio.timeout(timeout):
                async with httpx.AsyncClient(
                    trust_env=False, follow_redirects=False, verify=True,
                    timeout=timeout, transport=self._test_transport,
                ) as client:
                    async with client.stream(
                        "POST", target, content=body, headers=headers,
                    ) as response:
                        _response_header(
                            self.config.profile, response.status_code,
                            response.headers.get("content-type", ""),
                        )
                        lines = _abounded_lines(response.aiter_lines())
                        if self.config.profile is ProviderProfile.OLLAMA:
                            async for line in lines:
                                if line:
                                    yield "json", line
                        else:
                            async for frame in _asse_frames(lines):
                                yield frame
        except InvocationPortError:
            raise
        except (TimeoutError, httpx.TimeoutException):
            raise InvocationPortError("provider_timeout") from None
        except httpx.ConnectError:
            raise InvocationPortError("connection_failure") from None
        except httpx.HTTPError:
            raise InvocationPortError("provider_protocol_error") from None

    def stream_prepared(self, prepared: PreparedInvocation) -> Iterator[StreamEvent]:
        """On early generator.close(), the nested HTTP context closes as well."""
        run = prepared.context.run_id
        seq = 0
        yield ResponseStarted(run_id=run, sequence=seq)
        seq += 1
        frames = self._frames(prepared)
        decoder = NativeStreamDecoder(self.config.profile, prepared)
        try:
            for kind, raw in frames:
                if raw == "[DONE]":
                    decoder.marker(raw)
                    continue
                frame = decode_native_json(raw)
                event = kind if kind != "message" else str(frame.get("type", "message"))
                delta = decoder.push(event, frame)
                if delta:
                    yield TextDelta(run_id=run, sequence=seq, delta=delta)
                    seq += 1
            complete = decoder.finish()
            if complete.usage is not None:
                yield UsageUpdated(
                    run_id=run, sequence=seq, usage=complete.usage, is_final=True,
                )
                seq += 1
            yield ResponseCompleted(
                run_id=run, sequence=seq, finish_reason=complete.finish_reason,
            )
        except InvocationPortError as error:
            yield ResponseFailed(run_id=run, sequence=seq, reason_code=error.code)
        except Exception:
            yield ResponseFailed(run_id=run, sequence=seq, reason_code="adapter_unexpected_error")
        finally:
            frames.close()

    async def astream_prepared(
        self, prepared: PreparedInvocation,
    ) -> AsyncIterator[StreamEvent]:
        run = prepared.context.run_id
        seq = 0
        yield ResponseStarted(run_id=run, sequence=seq)
        seq += 1
        frames = self._aframes(prepared)
        decoder = NativeStreamDecoder(self.config.profile, prepared)
        try:
            async for kind, raw in frames:
                if raw == "[DONE]":
                    decoder.marker(raw)
                    continue
                frame = decode_native_json(raw)
                event = kind if kind != "message" else str(frame.get("type", "message"))
                delta = decoder.push(event, frame)
                if delta:
                    yield TextDelta(run_id=run, sequence=seq, delta=delta)
                    seq += 1
            complete = decoder.finish()
            if complete.usage is not None:
                yield UsageUpdated(
                    run_id=run, sequence=seq, usage=complete.usage, is_final=True,
                )
                seq += 1
            yield ResponseCompleted(
                run_id=run, sequence=seq, finish_reason=complete.finish_reason,
            )
        except InvocationPortError as error:
            yield ResponseFailed(run_id=run, sequence=seq, reason_code=error.code)
        except Exception:
            yield ResponseFailed(run_id=run, sequence=seq, reason_code="adapter_unexpected_error")
        finally:
            await frames.aclose()
