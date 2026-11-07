"""Live HTTP adapter for OpenAI media generation (images and text-to-speech).

Endpoints:
- Images: ``POST https://api.openai.com/v1/images/generations``
  (``gpt-image-*``, ``chatgpt-image-*`` and legacy ``dall-e-*``)
- Audio TTS: ``POST https://api.openai.com/v1/audio/speech``
  (``gpt-4o-mini-tts``, ``tts-1``, ``tts-1-hd``)

The media kind is resolved from the deployment output modalities, not from the
model name, so any catalog entry declaring ``modalities_out: ["image"]`` works.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any

from pyllmkit.adapters.inference.media_http import (
    MediaDiagnostics,
    MediaGenerationOptions,
    as_dict,
    data_uri,
    extract_prompt,
    fail_output,
    fetch_provider_media_bytes,
    http_bytes,
    http_json,
    image_dimensions,
    media_output_kind,
    model_name_of,
    parse_size,
    resolve_secret,
    sniff_image_mime,
)
from pyllmkit.adapters.inference.media_lifecycle import require_live_media_model
from pyllmkit.adapters.inference.security import ProviderConnectionConfig
from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.domain.inference import (
    AudioOutput,
    FinishReason,
    FinishReasonCode,
    ImageOutput,
    InferenceResponse,
    Usage,
)
from pyllmkit.domain.interactions import MediaSourceRef
from pyllmkit.protocols.credentials import CredentialResolverPort

_BASE_URL = "https://api.openai.com/v1"
_GPT_IMAGE_QUALITIES = {"low", "medium", "high", "auto"}
_DALLE_QUALITIES = {"standard", "hd"}
_TTS_FORMAT_MIME = {"mp3": "audio/mpeg", "wav": "audio/wav", "opus": "audio/ogg", "aac": "audio/aac", "flac": "audio/flac"}


@dataclass(frozen=True, slots=True)
class OpenAIMediaAdapter:
    """Synchronous live transport for OpenAI Image Generation and TTS APIs."""

    config: ProviderConnectionConfig = field(repr=False)
    credentials: CredentialResolverPort = field(repr=False)
    allow_live: bool = False
    options: MediaGenerationOptions = field(default_factory=MediaGenerationOptions)
    diagnostics: MediaDiagnostics | None = field(default=None, repr=False)

    def invoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        if not self.allow_live:
            raise InvocationPortError("live_authorization_required")
        model_name = model_name_of(prepared)
        require_live_media_model(model_name)
        secret = resolve_secret(self.config, self.credentials)
        prompt = extract_prompt(prepared)

        kind = media_output_kind(prepared)
        if kind == "image":
            return self._image(prepared, model_name, prompt, secret)
        if kind == "audio":
            return self._tts(prepared, model_name, prompt, secret)
        raise fail_output(
            self.diagnostics,
            f"OpenAI : génération '{kind or 'text'}' non prise en charge par l'adaptateur média pour '{model_name}'",
            "unsupported_capability",
        )

    def _headers(self, secret: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {secret}"}

    def _image(self, prepared: PreparedInvocation, model: str, prompt: str, secret: str) -> InferenceResponse:
        opts = self.options
        is_dalle = model.startswith("dall-e")
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "n": 1}
        if is_dalle:
            # No "response_format": current API rejects it; url results are downloaded below.
            payload["size"] = opts.size or "1024x1024"
            if model == "dall-e-3":
                quality = opts.quality if opts.quality in _DALLE_QUALITIES else "standard"
                payload["quality"] = quality
        else:
            # gpt-image-* always returns b64_json and rejects response_format.
            if opts.size:
                payload["size"] = opts.size
            if opts.quality in _GPT_IMAGE_QUALITIES:
                payload["quality"] = opts.quality
            elif opts.quality == "hd":
                payload["quality"] = "high"
            elif opts.quality == "standard":
                payload["quality"] = "medium"

        body = http_json(
            f"{_BASE_URL}/images/generations",
            method="POST",
            headers=self._headers(secret),
            payload=payload,
            timeout=opts.request_timeout_seconds,
            diagnostics=self.diagnostics,
            secret=secret,
        )
        items = body.get("data")
        if not isinstance(items, list) or not items or not isinstance(items[0], dict):
            raise fail_output(self.diagnostics, "OpenAI : aucune image dans la réponse")
        item = items[0]
        b64 = item.get("b64_json")
        if isinstance(b64, str) and b64:
            raw = base64.b64decode(b64)
        elif isinstance(item.get("url"), str):
            raw = fetch_provider_media_bytes(item["url"], timeout=opts.request_timeout_seconds, diagnostics=self.diagnostics)
        else:
            raise fail_output(self.diagnostics, "OpenAI : image vide (ni b64_json ni url)")

        mime = sniff_image_mime(raw)
        width, height = image_dimensions(raw)
        if width is None:
            width, height = parse_size(payload.get("size"))
        usage_raw = as_dict(body.get("usage"))
        return InferenceResponse(
            prepared.context.run_id,
            ImageOutput(
                media=MediaSourceRef("data", data_uri(mime, raw)),
                mime_type=mime,
                width=width,
                height=height,
                revised_prompt=item.get("revised_prompt") if isinstance(item.get("revised_prompt"), str) else None,
            ),
            finish_reason=FinishReason(FinishReasonCode.STOP),
            usage=Usage(
                input_tokens=_int_or_none(usage_raw.get("input_tokens")),
                output_tokens=_int_or_none(usage_raw.get("output_tokens")),
                total_tokens=_int_or_none(usage_raw.get("total_tokens")),
                output_media_units=1,
            ),
        )

    def _tts(self, prepared: PreparedInvocation, model: str, prompt: str, secret: str) -> InferenceResponse:
        opts = self.options
        fmt = "mp3"
        payload: dict[str, Any] = {
            "model": model,
            "input": prompt,
            "voice": opts.voice or "alloy",
            "response_format": fmt,
        }
        # tts-1 / tts-1-hd reject "instructions"; gpt-4o-mini-tts accepts a speaking style.
        if opts.instructions and not model.startswith("tts-1"):
            payload["instructions"] = opts.instructions

        raw = http_bytes(
            f"{_BASE_URL}/audio/speech",
            method="POST",
            headers=self._headers(secret),
            payload=payload,
            timeout=opts.request_timeout_seconds,
            diagnostics=self.diagnostics,
            secret=secret,
        )
        if not raw:
            raise fail_output(self.diagnostics, "OpenAI TTS : flux audio vide")
        mime = _TTS_FORMAT_MIME[fmt]
        # ~150 words/minute; the API does not return a duration.
        est_duration = max(1.0, round(len(prompt.split()) / 2.5, 1))
        return InferenceResponse(
            prepared.context.run_id,
            AudioOutput(
                media=MediaSourceRef("data", data_uri(mime, raw)),
                mime_type=mime,
                duration_seconds=est_duration,
                transcript=prompt,
            ),
            finish_reason=FinishReason(FinishReasonCode.STOP),
            usage=Usage(input_characters=len(prompt), output_media_seconds=est_duration),
        )


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
