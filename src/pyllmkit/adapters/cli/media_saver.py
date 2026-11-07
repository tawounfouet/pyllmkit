"""Secure local filesystem materialization for generated inference outputs."""

import base64
import os
import urllib.request
from datetime import datetime
from pathlib import Path

from pyllmkit.adapters.cli.config import get_config
from pyllmkit.domain.inference import (
    AudioOutput,
    ImageOutput,
    InferenceOutput,
    MultiPartOutput,
    TextOutput,
    VideoOutput,
)


def get_default_asset_path(
    output: InferenceOutput,
    run_id: str,
    model_name: str | None = None,
) -> Path:
    """Compute deterministic default file path inside configured assets directory."""
    actual_output = output
    if isinstance(output, MultiPartOutput):
        for part in output.parts:
            if isinstance(part, (ImageOutput, AudioOutput, VideoOutput)):
                actual_output = part
                break
        else:
            if output.parts:
                actual_output = output.parts[0]

    # Precedence: PYLLMKIT_ASSETS_DIR > storage.assets_dir > ./assets
    cfg = get_config()
    if os.environ.get("PYLLMKIT_ASSETS_DIR"):
        base_dir = Path(os.environ["PYLLMKIT_ASSETS_DIR"]).expanduser().resolve()
    elif cfg.storage.assets_dir is not None:
        base_dir = cfg.storage.assets_dir
    else:
        base_dir = (Path.cwd() / "assets").resolve()

    if isinstance(actual_output, ImageOutput):
        category = "images"
        mime = getattr(actual_output, "mime_type", "image/png").lower()
        if actual_output.media.kind == "data" and actual_output.media.value.startswith("data:"):
            header = actual_output.media.value.split(";", 1)[0]
            data_mime = header.replace("data:", "").lower()
            if data_mime:
                mime = data_mime

        if "jpeg" in mime or "jpg" in mime:
            ext = ".jpg"
        elif "webp" in mime:
            ext = ".webp"
        else:
            ext = ".png"
    elif isinstance(actual_output, AudioOutput):
        category = "audios"
        mime = getattr(actual_output, "mime_type", "audio/mp3").lower()
        if actual_output.media.kind == "data" and actual_output.media.value.startswith("data:"):
            header = actual_output.media.value.split(";", 1)[0]
            data_mime = header.replace("data:", "").lower()
            if data_mime:
                mime = data_mime

        if "wav" in mime:
            ext = ".wav"
        elif "ogg" in mime:
            ext = ".ogg"
        else:
            ext = ".mp3"
    elif isinstance(actual_output, VideoOutput):
        category = "videos"
        ext = ".mp4"
    else:
        category = "documents"
        ext = ".txt"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = run_id[:8] if run_id else "gen"
    prefix = f"{model_name.replace('/', '_').replace(':', '_')}_" if model_name else ""
    filename = f"{prefix}{timestamp}_{short_id}{ext}"

    target_dir = base_dir / category
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / filename


def save_output_media(output: InferenceOutput, target_path: Path | str) -> Path:
    """Decode and write generated inference output to a local disk file."""
    path = Path(target_path).expanduser().resolve()
    if path.is_dir():
        # If target path is a directory, compute filename inside it
        sub_path = get_default_asset_path(output, run_id="export")
        path = path / sub_path.name
    else:
        path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(output, TextOutput):
        path.write_text(output.text, encoding="utf-8")
        return path

    if isinstance(output, (ImageOutput, AudioOutput, VideoOutput)):
        media_ref = output.media
        if media_ref.kind == "data":
            # RFC 2397 Data URI: data:<mime>;base64,<payload>
            if "," not in media_ref.value:
                raise ValueError("Format de Data URI invalide pour l'extraction binaire")
            _, b64_payload = media_ref.value.split(",", 1)
            raw_bytes = base64.b64decode(b64_payload)
            path.write_bytes(raw_bytes)
            return path

        if media_ref.kind == "file":
            src_file = Path(media_ref.value).expanduser().resolve()
            if not src_file.exists():
                raise FileNotFoundError(f"Fichier source introuvable : {src_file}")
            path.write_bytes(src_file.read_bytes())
            return path

        if media_ref.kind == "uri":
            with urllib.request.urlopen(media_ref.value, timeout=30) as resp:
                path.write_bytes(resp.read())
            return path

        raise ValueError(f"Type de référence média non matérialisable : '{media_ref.kind}'")

    if isinstance(output, MultiPartOutput):
        # Save first media part, fallback to text
        for part in output.parts:
            if isinstance(part, (ImageOutput, AudioOutput, VideoOutput)):
                return save_output_media(part, path)
        if output.parts:
            return save_output_media(output.parts[0], path)

    raise ValueError("Type de sortie d'inférence non convertible en fichier")
