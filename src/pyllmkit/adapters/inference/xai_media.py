"""Live HTTP adapter for xAI Grok Imagine media generation.

- Images: ``POST https://api.x.ai/v1/images/generations`` (synchronous, ``b64_json``)
- Videos: ``POST https://api.x.ai/v1/videos/generations`` returns ``request_id``;
  ``GET https://api.x.ai/v1/videos/{request_id}`` is polled until ``status == "done"``,
  then the temporary MP4 URL is downloaded immediately.
"""

from __future__ import annotations

import base64
import time
from collections.abc import Callable
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
    http_json,
    image_dimensions,
    media_output_kind,
    model_name_of,
    resolve_secret,
    sniff_image_mime,
)
from pyllmkit.adapters.inference.media_lifecycle import require_live_media_model
from pyllmkit.adapters.inference.security import ProviderConnectionConfig
from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.domain.inference import (
    FinishReason,
    FinishReasonCode,
    ImageOutput,
    InferenceResponse,
    Usage,
    VideoOutput,
)
from pyllmkit.domain.interactions import MediaSourceRef
from pyllmkit.protocols.credentials import CredentialResolverPort

_BASE_URL = "https://api.x.ai/v1"
_VIDEO_RESOLUTIONS = {"480p": (854, 480), "720p": (1280, 720), "1080p": (1920, 1080)}


@dataclass(frozen=True, slots=True)
class XAIMediaAdapter:
    """Synchronous live transport for xAI image and video generation."""

    config: ProviderConnectionConfig = field(repr=False)
    credentials: CredentialResolverPort = field(repr=False)
    allow_live: bool = False
    options: MediaGenerationOptions = field(default_factory=MediaGenerationOptions)
    diagnostics: MediaDiagnostics | None = field(default=None, repr=False)
    sleep: Callable[[float], None] = field(default=time.sleep, repr=False)
    monotonic: Callable[[], float] = field(default=time.monotonic, repr=False)

    def invoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        if not self.allow_live:
            raise InvocationPortError("live_authorization_required")
        model = model_name_of(prepared)
        require_live_media_model(model)
        secret = resolve_secret(self.config, self.credentials)
        prompt = extract_prompt(prepared)
        kind = media_output_kind(prepared)
        if kind == "image":
            return self._image(prepared, model, prompt, secret)
        if kind == "video":
            return self._video(prepared, model, prompt, secret)
        raise fail_output(
            self.diagnostics,
            f"xAI : génération '{kind or 'text'}' non prise en charge pour '{model}'",
            "unsupported_capability",
        )

    def _headers(self, secret: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {secret}"}

    def _image(self, prepared: PreparedInvocation, model: str, prompt: str, secret: str) -> InferenceResponse:
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "n": 1, "response_format": "b64_json"}
        if self.options.aspect_ratio:
            payload["aspect_ratio"] = self.options.aspect_ratio
        if self.options.resolution:
            payload["resolution"] = self.options.resolution.lower()
        if self.options.quality in {"low", "medium", "auto"}:
            payload["quality"] = self.options.quality
        body = http_json(
            f"{_BASE_URL}/images/generations",
            method="POST",
            headers=self._headers(secret),
            payload=payload,
            timeout=self.options.request_timeout_seconds,
            diagnostics=self.diagnostics,
            secret=secret,
        )
        items = body.get("data")
        if not isinstance(items, list) or not items or not isinstance(items[0], dict):
            raise fail_output(self.diagnostics, "xAI : aucune image dans la réponse")
        item = items[0]
        if isinstance(item.get("b64_json"), str) and item["b64_json"]:
            raw = base64.b64decode(item["b64_json"])
        elif isinstance(item.get("url"), str) and item["url"]:
            raw = fetch_provider_media_bytes(item["url"], timeout=self.options.request_timeout_seconds, diagnostics=self.diagnostics)
        else:
            raise fail_output(self.diagnostics, "xAI : image vide (modération possible)", "content_filtered")
        mime = sniff_image_mime(raw, str(item.get("mime_type") or "image/jpeg"))
        width, height = image_dimensions(raw)
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
            usage=Usage(output_media_units=1),
        )

    def _video(self, prepared: PreparedInvocation, model: str, prompt: str, secret: str) -> InferenceResponse:
        opts = self.options
        payload: dict[str, Any] = {"model": model, "prompt": prompt}
        if opts.duration_seconds:
            payload["duration"] = opts.duration_seconds
        if opts.aspect_ratio:
            payload["aspect_ratio"] = opts.aspect_ratio
        if opts.resolution:
            payload["resolution"] = opts.resolution.lower()
        start = http_json(
            f"{_BASE_URL}/videos/generations",
            method="POST",
            headers=self._headers(secret),
            payload=payload,
            timeout=opts.request_timeout_seconds,
            diagnostics=self.diagnostics,
            secret=secret,
        )
        request_id = start.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise fail_output(self.diagnostics, "xAI vidéo : request_id absent de la réponse")

        deadline = self.monotonic() + opts.poll_timeout_seconds
        while True:
            status = http_json(
                f"{_BASE_URL}/videos/{request_id}",
                headers=self._headers(secret),
                timeout=opts.request_timeout_seconds,
                diagnostics=self.diagnostics,
                secret=secret,
            )
            state = str(status.get("status") or "pending").lower()
            if state == "done":
                break
            if state in {"failed", "expired"}:
                err = as_dict(status.get("error"))
                raise fail_output(
                    self.diagnostics,
                    f"xAI vidéo : {state} - {err.get('code', '')} {err.get('message', '')}".strip(),
                    "provider_not_completed",
                )
            if self.diagnostics is not None and isinstance(status.get("progress"), int):
                self.diagnostics.progress.append(f"{status['progress']}%")
            if self.monotonic() >= deadline:
                raise fail_output(
                    self.diagnostics,
                    f"xAI vidéo : non terminée après {opts.poll_timeout_seconds:.0f}s (request_id={request_id})",
                    "provider_timeout",
                )
            self.sleep(opts.poll_interval_seconds)

        video = as_dict(status.get("video"))
        url = video.get("url")
        if not isinstance(url, str) or not url:
            raise fail_output(self.diagnostics, "xAI vidéo : URL vide (refus de modération)", "content_filtered")
        raw = fetch_provider_media_bytes(url, timeout=opts.request_timeout_seconds, diagnostics=self.diagnostics)
        duration_raw = video.get("duration")
        duration = float(duration_raw) if isinstance(duration_raw, (int, float)) else (
            float(opts.duration_seconds) if opts.duration_seconds else None
        )
        width: int | None = None
        height: int | None = None
        if opts.aspect_ratio in (None, "16:9"):
            width, height = _VIDEO_RESOLUTIONS.get((opts.resolution or "480p").lower(), (None, None))
        return InferenceResponse(
            prepared.context.run_id,
            VideoOutput(
                media=MediaSourceRef("data", data_uri("video/mp4", raw)),
                mime_type="video/mp4",
                duration_seconds=duration,
                width=width,
                height=height,
            ),
            finish_reason=FinishReason(FinishReasonCode.STOP),
            usage=Usage(output_media_seconds=duration),
        )
