"""Shared plumbing for live media-generation adapters (image, audio/TTS, video).

Zero runtime dependency: stdlib ``urllib`` only. Everything here is adapter-level
infrastructure; the domain never sees HTTP, secrets or provider payloads.

- ``MediaGenerationOptions``: per-invocation knobs (size, voice, duration...) that
  the canonical ``InferenceRequest`` deliberately does not model.
- ``MediaDiagnostics``: an opt-in sink where adapters record the *sanitized*
  provider error message, because ``InvocationPortError`` only carries a code.
- ``http_json`` / ``http_bytes``: single-attempt HTTP with status -> safe code mapping.
"""

from __future__ import annotations

import base64
import json
import re
import socket
import struct
import urllib.error
import urllib.request
from ipaddress import ip_address
from urllib.parse import urlsplit
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from pyllmkit.adapters.inference.security import ProviderConnectionConfig
from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.domain.interactions import Role, TextContent
from pyllmkit.domain.modalities import Modality
from pyllmkit.protocols.credentials import CredentialResolverPort, SecretValue

MediaKind = Literal["image", "audio", "video"]

USER_AGENT = "PyLLMKit/0.3.0"
MAX_PROVIDER_RESPONSE_BYTES = 160 * 1024 * 1024
MAX_MEDIA_DOWNLOAD_BYTES = 100 * 1024 * 1024
_MAX_ERROR_RESPONSE_BYTES = 8 * 1024
_TRUSTED_MEDIA_SUFFIXES = (
    "x.ai", "openai.com", "blob.core.windows.net",
    "googleapis.com", "googleusercontent.com",
)
_MAX_DETAIL_CHARS = 400
_SECRET_LIKE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|xai-[A-Za-z0-9]{8,}|AIza[0-9A-Za-z_\-]{20,}|AQ\.[A-Za-z0-9_\-]{10,})")


@dataclass(frozen=True, slots=True)
class MediaGenerationOptions:
    """Optional provider knobs for media generation; ``None`` means provider default."""

    size: str | None = None
    quality: str | None = None
    voice: str | None = None
    instructions: str | None = None
    aspect_ratio: str | None = None
    resolution: str | None = None
    duration_seconds: int | None = None
    request_timeout_seconds: float = 180.0
    poll_timeout_seconds: float = 900.0
    poll_interval_seconds: float = 5.0


@dataclass(slots=True)
class MediaDiagnostics:
    """Mutable sink holding the last sanitized provider failure for CLI display."""

    last_error: str | None = None
    http_status: int | None = None
    progress: list[str] = field(default_factory=list)

    def record(self, message: str, *, status: int | None = None, secret: str | None = None) -> None:
        self.last_error = sanitize_detail(message, secret)
        self.http_status = status


def sanitize_detail(message: str, secret: str | None = None) -> str:
    """Strip secrets and control characters, then truncate a provider message."""
    text = message
    if secret:
        text = text.replace(secret, "***")
    text = _SECRET_LIKE.sub("***", text)
    text = " ".join(text.split())
    if len(text) > _MAX_DETAIL_CHARS:
        text = text[: _MAX_DETAIL_CHARS - 3] + "..."
    return text


def resolve_secret(config: ProviderConnectionConfig, credentials: CredentialResolverPort) -> str:
    reference = config.credential_ref
    if reference is None:
        raise InvocationPortError("credential_unavailable")
    try:
        secret_obj = credentials.resolve(reference)
    except Exception:
        raise InvocationPortError("credential_unavailable") from None
    if type(secret_obj) is not SecretValue:
        raise InvocationPortError("credential_unavailable")
    return secret_obj.reveal()


def model_name_of(prepared: PreparedInvocation) -> str:
    return getattr(prepared, "native_model_alias", None) or prepared.resolution.deployment.model_id.value


def media_output_kind(prepared: PreparedInvocation) -> MediaKind | None:
    """Return the media kind a deployment produces, or ``None`` for text models.

    Routing is driven by declared output modalities, never by model-name substrings.
    """
    modes = prepared.resolution.deployment.modalities
    if modes is None or modes.can_output(Modality("text")):
        return None
    for kind in ("image", "audio", "video"):
        if modes.can_output(Modality(kind)):
            return kind  # type: ignore[return-value,unused-ignore]
    return None


def extract_prompt(prepared: PreparedInvocation) -> str:
    """Join the USER text parts; system prompts must not become the image/TTS prompt."""
    user_texts: list[str] = []
    for msg in prepared.request.messages:
        if msg.role is not Role.USER:
            continue
        for part in msg.content.parts:
            if isinstance(part, TextContent) and part.text.strip():
                user_texts.append(part.text.strip())
    prompt = "\n".join(user_texts)
    if not prompt:
        raise InvocationPortError("unsupported_content_structure")
    return prompt


def system_instructions(prepared: PreparedInvocation) -> str | None:
    texts = [
        part.text.strip()
        for msg in prepared.request.messages
        if msg.role is Role.SYSTEM
        for part in msg.content.parts
        if isinstance(part, TextContent) and part.text.strip()
    ]
    return "\n".join(texts) or None


def _status_to_code(status: int, message: str) -> str:
    lowered = message.lower()
    if status == 401:
        return "credential_unavailable"
    if status == 403:
        return "permission_denied"
    if status == 404 or "does not exist" in lowered or "not found" in lowered:
        return "model_not_found"
    if status == 429:
        return "rate_limited"
    if status in (400, 422):
        if "safety" in lowered or "moderation" in lowered or "blocked" in lowered:
            return "content_filtered"
        return "invalid_request"
    if status >= 500:
        return "provider_overloaded"
    return "provider_protocol_error"


def _error_message_from_body(raw: bytes) -> str:
    try:
        body = json.loads(raw.decode("utf-8", errors="replace"))
    except (ValueError, UnicodeDecodeError):
        return raw.decode("utf-8", errors="replace")[:_MAX_DETAIL_CHARS]
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("status") or err)
        if isinstance(err, str):
            return err
        if "message" in body:
            return str(body["message"])
    return str(body)[:_MAX_DETAIL_CHARS]


def _read_bounded(response: Any, limit: int) -> bytes:
    """Bound memory even when Content-Length is absent, false or malicious."""
    content = response.read(limit + 1)
    if type(content) is not bytes:
        raise InvocationPortError("provider_protocol_error")
    if len(content) > limit:
        raise InvocationPortError("response_too_large")
    return content


def _open(
    request: urllib.request.Request,
    timeout: float,
    diagnostics: MediaDiagnostics | None,
    secret: str | None,
    *,
    opener: urllib.request.OpenerDirector | None = None,
    max_bytes: int = MAX_PROVIDER_RESPONSE_BYTES,
) -> bytes:
    try:
        if opener is None:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return _read_bounded(response, max_bytes)
        with opener.open(request, timeout=timeout) as response:
            return _read_bounded(response, max_bytes)
    except InvocationPortError:
        raise
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read(_MAX_ERROR_RESPONSE_BYTES) if exc.fp is not None else b""
        except Exception:
            raw = b""
        message = _error_message_from_body(raw) if raw else f"HTTP {exc.code}"
        if diagnostics is not None:
            diagnostics.record(f"HTTP {exc.code}: {message}", status=exc.code, secret=secret)
        raise InvocationPortError(_status_to_code(exc.code, message)) from None
    except TimeoutError:
        if diagnostics is not None:
            diagnostics.record(f"Délai réseau dépassé ({timeout:.0f}s)")
        raise InvocationPortError("provider_timeout") from None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            if diagnostics is not None:
                diagnostics.record(f"Délai réseau dépassé ({timeout:.0f}s)")
            raise InvocationPortError("provider_timeout") from None
        if diagnostics is not None:
            diagnostics.record("Connexion impossible", secret=secret)
        raise InvocationPortError("connection_failure") from None
    except Exception:
        # Transport exceptions can include signed URLs and credentials.
        raise InvocationPortError("provider_protocol_error") from None


class _DenyMediaRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a supplier URL to a different, potentially internal target."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        raise InvocationPortError("unsafe_provider_destination")


def _trusted_media_host(url: str) -> str:
    """Restrict downloaded media to supplier-controlled public HTTPS hosts."""
    if (
        type(url) is not str
        or len(url) > 8192
        or any(ord(ch) < 33 or ch == "\\" for ch in url)
    ):
        raise InvocationPortError("unsafe_provider_destination")
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        raise InvocationPortError("unsafe_provider_destination") from None
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or port not in (None, 443)
    ):
        raise InvocationPortError("unsafe_provider_destination")
    host = host.rstrip(".").lower()
    try:
        ip_address(host)
    except ValueError:
        pass
    else:
        raise InvocationPortError("unsafe_provider_destination")
    if not any(host == suffix or host.endswith("." + suffix) for suffix in _TRUSTED_MEDIA_SUFFIXES):
        raise InvocationPortError("unsafe_provider_destination")
    return host


def fetch_provider_media_bytes(
    url: str,
    *,
    timeout: float = 60.0,
    diagnostics: MediaDiagnostics | None = None,
) -> bytes:
    """Fail closed for untrusted asset URLs: trusted HTTPS host, public DNS, no redirects.

    The preflight does not pin the actual peer IP. Live DNS/TLS pinning is still
    an operational release gate, not a guarantee of this helper.
    """
    host = _trusted_media_host(url)
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(
            not ip_address(item[4][0]).is_global for item in addresses
        ):
            raise InvocationPortError("unsafe_provider_destination")
    except (OSError, ValueError):
        raise InvocationPortError("unsafe_provider_destination") from None
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _DenyMediaRedirect(),
    )
    return _open(
        request, timeout, diagnostics, None, opener=opener,
        max_bytes=MAX_MEDIA_DOWNLOAD_BYTES,
    )


def http_bytes(
    url: str,
    *,
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    payload: Mapping[str, Any] | None = None,
    timeout: float = 60.0,
    diagnostics: MediaDiagnostics | None = None,
    secret: str | None = None,
) -> bytes:
    all_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        all_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=all_headers, method=method)
    return _open(request, timeout, diagnostics, secret)


def http_json(
    url: str,
    *,
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    payload: Mapping[str, Any] | None = None,
    timeout: float = 60.0,
    diagnostics: MediaDiagnostics | None = None,
    secret: str | None = None,
) -> dict[str, Any]:
    raw = http_bytes(
        url, method=method, headers=headers, payload=payload,
        timeout=timeout, diagnostics=diagnostics, secret=secret,
    )
    try:
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        if diagnostics is not None:
            diagnostics.record("Réponse JSON invalide reçue du fournisseur")
        raise InvocationPortError("provider_protocol_error") from None
    if not isinstance(body, dict):
        raise InvocationPortError("provider_protocol_error")
    return body


def as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def fail_output(diagnostics: MediaDiagnostics | None, message: str, code: str = "unsupported_provider_output") -> InvocationPortError:
    if diagnostics is not None:
        diagnostics.record(message)
    return InvocationPortError(code)


def data_uri(mime_type: str, raw: bytes) -> str:
    if len(raw) > MAX_MEDIA_DOWNLOAD_BYTES:
        raise InvocationPortError("response_too_large")
    return f"data:{mime_type};base64,{base64.b64encode(raw).decode('ascii')}"


def parse_size(size: str | None) -> tuple[int | None, int | None]:
    if not size or "x" not in size:
        return None, None
    w, _, h = size.lower().partition("x")
    if w.isdigit() and h.isdigit():
        return int(w), int(h)
    return None, None


def sniff_image_mime(raw: bytes, fallback: str = "image/png") -> str:
    if raw.startswith(b"\x89PNG"):
        return "image/png"
    if raw.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return fallback


def image_dimensions(raw: bytes) -> tuple[int | None, int | None]:
    """Read PNG/JPEG dimensions from headers (best effort, no decoding)."""
    if raw.startswith(b"\x89PNG") and len(raw) >= 24:
        w, h = struct.unpack(">II", raw[16:24])
        return int(w), int(h)
    if raw.startswith(b"\xff\xd8"):
        i = 2
        while i + 9 < len(raw):
            if raw[i] != 0xFF:
                i += 1
                continue
            marker = raw[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", raw[i + 5 : i + 9])
                return int(w), int(h)
            seg_len = struct.unpack(">H", raw[i + 2 : i + 4])[0]
            i += 2 + seg_len
    return None, None


def pcm16_to_wav(pcm: bytes, sample_rate: int = 24000, channels: int = 1) -> bytes:
    """Wrap raw signed 16-bit little-endian PCM in a RIFF/WAV container."""
    byte_rate = sample_rate * channels * 2
    header = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, channels * 2, 16)
    header += b"data" + struct.pack("<I", len(pcm))
    return header + pcm


def wav_duration_seconds(wav: bytes) -> float | None:
    if len(wav) < 44 or wav[:4] != b"RIFF":
        return None
    try:
        channels, sample_rate = struct.unpack("<HI", wav[22:28])
        bits = struct.unpack("<H", wav[34:36])[0]
        idx = wav.find(b"data", 12)
        if idx < 0 or not sample_rate or not channels or not bits:
            return None
        size = struct.unpack("<I", wav[idx + 4 : idx + 8])[0]
        return float(round(int(size) / (int(sample_rate) * int(channels) * (int(bits) // 8)), 2))
    except struct.error:
        return None
