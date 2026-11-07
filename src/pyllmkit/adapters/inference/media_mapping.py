"""Passive media reference encoding helpers for inference adapters."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.domain.interactions import (
    AudioContent,
    ContentPart,
    ImageContent,
    MediaSourceRef,
    TextContent,
    VideoContent,
)


# The old 1 MiB text boundary is intentionally unchanged. Base64-encoded
# multimodal messages require a separate, explicit and still finite budget.
MAX_MULTIMODAL_SOURCE_BYTES = 16 * 1024 * 1024
MAX_MULTIMODAL_REQUEST_BYTES = 24 * 1024 * 1024
MAX_TEXT_REQUEST_BYTES = 1_048_576


def request_bytes_limit(prepared: PreparedInvocation) -> int:
    """Select the bounded wire-body budget from the validated request modalities."""
    for message in prepared.request.messages:
        if any(type(part) in (ImageContent, AudioContent, VideoContent)
               for part in message.content.parts):
            return MAX_MULTIMODAL_REQUEST_BYTES
    return MAX_TEXT_REQUEST_BYTES


def check_part_modality(prepared: PreparedInvocation, part: ContentPart) -> None:
    """Verify that the deployment explicitly accepts the part modality.

    If the deployment declares input modalities and does not accept part.modality,
    raise InvocationPortError('unsupported_input_modality').
    """
    modalities = prepared.resolution.deployment.modalities
    if modalities is not None:
        if modalities.accepts_input(part.modality) is False:
            raise InvocationPortError("unsupported_input_modality")


def extract_media_base64_and_mime(
    source: MediaSourceRef,
    default_mime: str,
) -> tuple[str, str]:
    """Extract (base64_payload, mime_type) from a MediaSourceRef without network I/O."""
    if source.kind == "data":
        val = source.value
        if len(val) > MAX_MULTIMODAL_REQUEST_BYTES:
            raise InvocationPortError("request_too_large")
        header, _, payload = val.partition(",")
        mime = default_mime
        is_b64 = False
        if header.startswith("data:"):
            meta = header[5:]
            parts = meta.split(";")
            if parts[0]:
                mime = parts[0]
            if "base64" in parts:
                is_b64 = True
        if is_b64:
            b64_str = payload
        else:
            b64_str = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        return b64_str, mime

    if source.kind == "file":
        path = Path(source.value)
        if not path.is_file():
            raise InvocationPortError("media_file_not_found")
        if path.stat().st_size > MAX_MULTIMODAL_SOURCE_BYTES:
            raise InvocationPortError("request_too_large")
        guessed, _ = mimetypes.guess_type(source.value)
        mime = guessed or default_mime
        data = path.read_bytes()
        if len(data) > MAX_MULTIMODAL_SOURCE_BYTES:
            raise InvocationPortError("request_too_large")
        b64_str = base64.b64encode(data).decode("ascii")
        return b64_str, mime

    if source.kind in ("uri", "asset"):
        # For uri or asset when base64 is strictly needed (offline boundary)
        raise InvocationPortError("unsupported_media_source")

    raise InvocationPortError("unsupported_media_source")


def resolve_media_url_or_data(
    source: MediaSourceRef,
    default_mime: str,
) -> tuple[str, str]:
    """Resolve a URL (or data URI) and mime type suitable for OpenAI / xAI / Mistral."""
    if source.kind in ("uri", "asset"):
        guessed, _ = mimetypes.guess_type(source.value)
        return source.value, guessed or default_mime

    if source.kind == "data":
        header, _, _ = source.value.partition(",")
        mime = default_mime
        if header.startswith("data:"):
            meta = header[5:].split(";")[0]
            if meta:
                mime = meta
        return source.value, mime

    if source.kind == "file":
        b64_str, mime = extract_media_base64_and_mime(source, default_mime)
        return f"data:{mime};base64,{b64_str}", mime

    raise InvocationPortError("unsupported_media_source")


def default_mime_for_part(part: ContentPart) -> str:
    """Return canonical fallback MIME type for a given ContentPart."""
    if isinstance(part, ImageContent):
        return "image/png"
    if isinstance(part, AudioContent):
        if part.format == "wav":
            return "audio/wav"
        if part.format == "mp3":
            return "audio/mp3"
        return "audio/wav"
    if isinstance(part, VideoContent):
        if part.format == "mov":
            return "video/quicktime"
        return "video/mp4"
    return "application/octet-stream"
