"""CLI media input parser for multimodal attachments (images, audio, video)."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import urlsplit

from pyllmkit.domain.interactions import (
    AudioContent,
    ContentPart,
    ImageContent,
    MediaSourceRef,
    VideoContent,
)

MAX_MEDIA_FILE_BYTES = 16 * 1024 * 1024  # 16 MiB; fits the 24 MiB base64 wire budget


def create_media_source_ref_from_input(raw: str) -> MediaSourceRef:
    """Detect whether input is a data URI, URL, or local file and create a MediaSourceRef."""
    clean = raw.strip()
    if clean.startswith("data:"):
        return MediaSourceRef(kind="data", value=clean)

    parsed = urlsplit(clean)
    if parsed.scheme in ("http", "https"):
        return MediaSourceRef(kind="uri", value=clean)

    path = Path(clean).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Fichier multimédia introuvable: {clean}")

    size = path.stat().st_size
    if size > MAX_MEDIA_FILE_BYTES:
        max_mb = MAX_MEDIA_FILE_BYTES // (1024 * 1024)
        raise ValueError(
            f"Fichier multimédia trop volumineux ({size / (1024 * 1024):.1f} Mo > {max_mb} Mo max): {clean}"
        )

    return MediaSourceRef(kind="file", value=str(path.resolve()))


def parse_cli_media_parts(
    images: list[str] | None = None,
    audio: str | None = None,
    video: str | None = None,
) -> list[ContentPart]:
    """Parse CLI media arguments into domain ContentParts."""
    parts: list[ContentPart] = []
    if images:
        for img_arg in images:
            ref = create_media_source_ref_from_input(img_arg)
            parts.append(ImageContent(source=ref))

    if audio:
        ref = create_media_source_ref_from_input(audio)
        guessed, _ = mimetypes.guess_type(ref.value)
        fmt = None
        if guessed and "/" in guessed:
            fmt = guessed.split("/")[-1].replace("mpeg", "mp3")
        parts.append(AudioContent(source=ref, format=fmt))

    if video:
        ref = create_media_source_ref_from_input(video)
        guessed, _ = mimetypes.guess_type(ref.value)
        fmt = None
        if guessed and "/" in guessed:
            fmt = guessed.split("/")[-1].replace("quicktime", "mov")
        parts.append(VideoContent(source=ref, format=fmt))

    return parts

