"""Live HTTP adapter for Google Gemini API media generation.

Supported families (all on ``https://generativelanguage.googleapis.com/v1beta``):
- Gemini image models (``gemini-*-image*``, ``nano-banana*``): ``:generateContent``
  with ``responseModalities`` IMAGE, bytes in ``inlineData``.
- Gemini TTS models (``gemini-*-tts``): ``:generateContent`` with AUDIO modality and
  ``speechConfig``; raw PCM s16le 24 kHz is wrapped into a WAV container.
- Imagen (``imagen-*``): ``:predict``.
- Gemini Omni (``gemini-omni-*``): Interactions API ``POST /v1beta/interactions``
  with ``response_format.type == "video"``; synchronous, base64 MP4 in
  ``steps[type=model_output].content[type=video].data``.
- Veo (``veo-*``): ``:predictLongRunning`` then operation polling and download.
  Veo 3.1 preview was shut down on 2026-10-22; Google points to Gemini Omni.

Imagen and Veo are only reachable when the API key/project has access to them;
otherwise the provider 404 is surfaced as ``model_not_found`` with its message.
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
    http_bytes,
    http_json,
    image_dimensions,
    media_output_kind,
    model_name_of,
    pcm16_to_wav,
    resolve_secret,
    sniff_image_mime,
    wav_duration_seconds,
)
from pyllmkit.adapters.inference.security import ProviderConnectionConfig
from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.domain.inference import (
    AudioOutput,
    FinishReason,
    FinishReasonCode,
    ImageOutput,
    InferenceResponse,
    Usage,
    VideoOutput,
)
from pyllmkit.domain.interactions import MediaSourceRef
from pyllmkit.protocols.credentials import CredentialResolverPort

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Short catalog ids -> native Gemini API model ids.
NATIVE_MODEL_ALIASES: dict[str, str] = {
    "imagen-3": "imagen-3.0-generate-002",
    "imagen-4": "imagen-4.0-generate-001",
    "veo-2": "veo-2.0-generate-001",
    "veo-3": "veo-3.0-generate-001",
}

DEFAULT_TTS_VOICE = "Kore"


@dataclass(frozen=True, slots=True)
class GoogleMediaAdapter:
    """Synchronous live transport for Gemini image, speech and video generation."""

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
        secret = resolve_secret(self.config, self.credentials)
        catalog_name = model_name_of(prepared)
        model = NATIVE_MODEL_ALIASES.get(catalog_name, catalog_name)
        prompt = extract_prompt(prepared)
        kind = media_output_kind(prepared)

        if kind == "image":
            if model.startswith("imagen"):
                return self._imagen(prepared, model, prompt, secret)
            return self._gemini_image(prepared, model, prompt, secret)
        if kind == "audio":
            return self._gemini_tts(prepared, model, prompt, secret)
        if kind == "video":
            if model.startswith("gemini-omni"):
                return self._omni_video(prepared, model, prompt, secret)
            return self._veo(prepared, model, prompt, secret)
        raise fail_output(
            self.diagnostics,
            f"Google : modalité de sortie non média pour '{catalog_name}'",
            "unsupported_capability",
        )

    # ------------------------------------------------------------------ helpers
    def _post(self, url: str, payload: dict[str, Any], secret: str) -> dict[str, Any]:
        return http_json(
            url,
            method="POST",
            headers={"x-goog-api-key": secret},
            payload=payload,
            timeout=self.options.request_timeout_seconds,
            diagnostics=self.diagnostics,
            secret=secret,
        )

    def _inline_parts(self, body: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
        candidates = body.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            feedback = body.get("promptFeedback") or {}
            reason = feedback.get("blockReason") if isinstance(feedback, dict) else None
            if reason:
                raise fail_output(self.diagnostics, f"Google : prompt bloqué ({reason})", "content_filtered")
            raise fail_output(self.diagnostics, "Google : réponse sans candidat")
        cand = candidates[0] if isinstance(candidates[0], dict) else {}
        parts = (cand.get("content") or {}).get("parts") or []
        inline = [p["inlineData"] for p in parts if isinstance(p, dict) and isinstance(p.get("inlineData"), dict)]
        texts = [p["text"] for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str)]
        if not inline:
            finish = cand.get("finishReason")
            detail = f"finishReason={finish}" if finish else "aucune donnée binaire"
            if texts:
                detail += f" ; texte du modèle : {texts[0][:200]}"
            code = "content_filtered" if finish in ("SAFETY", "PROHIBITED_CONTENT", "IMAGE_SAFETY") else "unsupported_provider_output"
            raise fail_output(self.diagnostics, f"Google : {detail}", code)
        return inline, texts

    @staticmethod
    def _usage_tokens(body: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
        meta = as_dict(body.get("usageMetadata"))

        def _i(key: str) -> int | None:
            v = meta.get(key)
            return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None

        return _i("promptTokenCount"), _i("candidatesTokenCount"), _i("totalTokenCount")

    # ------------------------------------------------------------------ image
    def _gemini_image(self, prepared: PreparedInvocation, model: str, prompt: str, secret: str) -> InferenceResponse:
        gen_config: dict[str, Any] = {"responseModalities": ["TEXT", "IMAGE"]}
        image_config: dict[str, Any] = {}
        if self.options.aspect_ratio:
            image_config["aspectRatio"] = self.options.aspect_ratio
        if self.options.resolution:
            image_config["imageSize"] = self.options.resolution.upper()
        if image_config:
            gen_config["imageConfig"] = image_config
        body = self._post(
            f"{_BASE_URL}/models/{model}:generateContent",
            {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": gen_config},
            secret,
        )
        inline, texts = self._inline_parts(body)
        blob = next((b for b in inline if str(b.get("mimeType", "")).startswith("image/")), inline[0])
        raw = base64.b64decode(str(blob.get("data", "")))
        if not raw:
            raise fail_output(self.diagnostics, "Google : image vide")
        mime = sniff_image_mime(raw, str(blob.get("mimeType") or "image/png"))
        width, height = image_dimensions(raw)
        in_tok, out_tok, tot_tok = self._usage_tokens(body)
        return InferenceResponse(
            prepared.context.run_id,
            ImageOutput(
                media=MediaSourceRef("data", data_uri(mime, raw)),
                mime_type=mime,
                width=width,
                height=height,
                revised_prompt=texts[0] if texts else None,
            ),
            finish_reason=FinishReason(FinishReasonCode.STOP),
            usage=Usage(input_tokens=in_tok, output_tokens=out_tok, total_tokens=tot_tok, output_media_units=1),
        )

    def _imagen(self, prepared: PreparedInvocation, model: str, prompt: str, secret: str) -> InferenceResponse:
        params: dict[str, Any] = {"sampleCount": 1}
        if self.options.aspect_ratio:
            params["aspectRatio"] = self.options.aspect_ratio
        body = self._post(
            f"{_BASE_URL}/models/{model}:predict",
            {"instances": [{"prompt": prompt}], "parameters": params},
            secret,
        )
        preds = body.get("predictions")
        if not isinstance(preds, list) or not preds or not isinstance(preds[0], dict):
            raise fail_output(self.diagnostics, "Imagen : aucune prédiction (prompt possiblement filtré)", "content_filtered")
        raw = base64.b64decode(str(preds[0].get("bytesBase64Encoded", "")))
        if not raw:
            raise fail_output(self.diagnostics, "Imagen : image vide")
        mime = sniff_image_mime(raw, str(preds[0].get("mimeType") or "image/png"))
        width, height = image_dimensions(raw)
        return InferenceResponse(
            prepared.context.run_id,
            ImageOutput(media=MediaSourceRef("data", data_uri(mime, raw)), mime_type=mime, width=width, height=height),
            finish_reason=FinishReason(FinishReasonCode.STOP),
            usage=Usage(output_media_units=1),
        )

    # ------------------------------------------------------------------ audio
    def _gemini_tts(self, prepared: PreparedInvocation, model: str, prompt: str, secret: str) -> InferenceResponse:
        text = f"{self.options.instructions}: {prompt}" if self.options.instructions else prompt
        voice = self.options.voice or DEFAULT_TTS_VOICE
        body = self._post(
            f"{_BASE_URL}/models/{model}:generateContent",
            {
                "contents": [{"role": "user", "parts": [{"text": text}]}],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
                },
            },
            secret,
        )
        inline, _ = self._inline_parts(body)
        blob = inline[0]
        raw = base64.b64decode(str(blob.get("data", "")))
        if not raw:
            raise fail_output(self.diagnostics, "Google TTS : flux audio vide")
        mime_raw = str(blob.get("mimeType") or "audio/L16;rate=24000").lower()
        if raw[:4] != b"RIFF":
            # Raw linear PCM ("audio/L16;codec=pcm;rate=24000"): wrap into WAV.
            rate = 24000
            for token in mime_raw.split(";"):
                key, _, value = token.strip().partition("=")
                if key == "rate" and value.isdigit():
                    rate = int(value)
            raw = pcm16_to_wav(raw, sample_rate=rate)
        duration = wav_duration_seconds(raw)
        in_tok, out_tok, tot_tok = self._usage_tokens(body)
        return InferenceResponse(
            prepared.context.run_id,
            AudioOutput(
                media=MediaSourceRef("data", data_uri("audio/wav", raw)),
                mime_type="audio/wav",
                duration_seconds=duration,
                transcript=prompt,
            ),
            finish_reason=FinishReason(FinishReasonCode.STOP),
            usage=Usage(
                input_tokens=in_tok, output_tokens=out_tok, total_tokens=tot_tok,
                input_characters=len(prompt), output_media_seconds=duration,
            ),
        )

    # ------------------------------------------------------------------ video
    def _omni_video(self, prepared: PreparedInvocation, model: str, prompt: str, secret: str) -> InferenceResponse:
        fmt: dict[str, Any] = {"type": "video"}
        if self.options.aspect_ratio:
            fmt["aspect_ratio"] = self.options.aspect_ratio
        if self.options.resolution:
            fmt["resolution"] = self.options.resolution.lower()
        if self.options.duration_seconds:
            fmt["duration"] = f"{self.options.duration_seconds}s"
        # Generation is synchronous and can take minutes: allow the polling budget.
        timeout = max(self.options.request_timeout_seconds, self.options.poll_timeout_seconds)
        body = http_json(
            f"{_BASE_URL}/interactions",
            method="POST",
            headers={"x-goog-api-key": secret},
            payload={"model": model, "input": prompt, "response_format": fmt},
            timeout=timeout,
            diagnostics=self.diagnostics,
            secret=secret,
        )
        status = str(body.get("status") or "")
        if status and status != "completed":
            raise fail_output(self.diagnostics, f"Gemini Omni : statut '{status}'", "provider_not_completed")
        video: dict[str, Any] = {}
        for step in body.get("steps") or []:
            if not isinstance(step, dict) or step.get("type") != "model_output":
                continue
            for item in step.get("content") or []:
                if isinstance(item, dict) and item.get("type") == "video":
                    video = item
        raw = b""
        if isinstance(video.get("data"), str) and video["data"]:
            raw = base64.b64decode(video["data"])
        elif isinstance(video.get("uri"), str) and video["uri"]:
            raw = http_bytes(
                video["uri"], headers={"x-goog-api-key": secret}, timeout=timeout,
                diagnostics=self.diagnostics, secret=secret,
            )
        if not raw:
            raise fail_output(self.diagnostics, "Gemini Omni : aucune vidéo produite (filtrage possible)", "content_filtered")
        usage = as_dict(body.get("usage"))

        def _i(key: str) -> int | None:
            v = usage.get(key)
            return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None

        duration = float(self.options.duration_seconds) if self.options.duration_seconds else None
        mime = str(video.get("mime_type") or "video/mp4")
        return InferenceResponse(
            prepared.context.run_id,
            VideoOutput(media=MediaSourceRef("data", data_uri(mime, raw)), mime_type=mime, duration_seconds=duration),
            finish_reason=FinishReason(FinishReasonCode.STOP),
            usage=Usage(
                input_tokens=_i("total_input_tokens"),
                output_tokens=_i("total_output_tokens"),
                total_tokens=_i("total_tokens"),
                reasoning_tokens=_i("total_thought_tokens"),
                output_media_seconds=duration,
            ),
        )

    def _veo(self, prepared: PreparedInvocation, model: str, prompt: str, secret: str) -> InferenceResponse:
        params: dict[str, Any] = {}
        if self.options.aspect_ratio:
            params["aspectRatio"] = self.options.aspect_ratio
        if self.options.duration_seconds:
            params["durationSeconds"] = self.options.duration_seconds
        if self.options.resolution:
            params["resolution"] = self.options.resolution
        payload: dict[str, Any] = {"instances": [{"prompt": prompt}]}
        if params:
            payload["parameters"] = params
        try:
            op = self._post(f"{_BASE_URL}/models/{model}:predictLongRunning", payload, secret)
        except InvocationPortError as exc:
            if exc.code == "model_not_found" and self.diagnostics is not None and self.diagnostics.last_error:
                self.diagnostics.last_error += " | Veo 3.1 preview est arrêté depuis le 2026-10-22 : utilisez -m gemini-omni-1.2-flash"
            raise
        name = op.get("name")
        if not isinstance(name, str) or not name:
            raise fail_output(self.diagnostics, "Veo : opération longue sans identifiant")

        deadline = self.monotonic() + self.options.poll_timeout_seconds
        while not op.get("done"):
            if self.monotonic() >= deadline:
                raise fail_output(self.diagnostics, f"Veo : génération non terminée après {self.options.poll_timeout_seconds:.0f}s", "provider_timeout")
            self.sleep(self.options.poll_interval_seconds)
            op = http_json(
                f"{_BASE_URL}/{name}",
                headers={"x-goog-api-key": secret},
                timeout=self.options.request_timeout_seconds,
                diagnostics=self.diagnostics,
                secret=secret,
            )
        if isinstance(op.get("error"), dict):
            raise fail_output(self.diagnostics, f"Veo : {op['error'].get('message', op['error'])}", "provider_not_completed")
        resp = op.get("response") or {}
        samples = ((resp.get("generateVideoResponse") or {}).get("generatedSamples")) or []
        uri = ((samples[0] or {}).get("video") or {}).get("uri") if samples else None
        if not isinstance(uri, str) or not uri:
            raise fail_output(self.diagnostics, "Veo : aucune vidéo produite (filtrage possible)", "content_filtered")
        raw = http_bytes(
            uri,
            headers={"x-goog-api-key": secret},
            timeout=self.options.request_timeout_seconds,
            diagnostics=self.diagnostics,
            secret=secret,
        )
        duration = float(self.options.duration_seconds) if self.options.duration_seconds else None
        return InferenceResponse(
            prepared.context.run_id,
            VideoOutput(media=MediaSourceRef("data", data_uri("video/mp4", raw)), mime_type="video/mp4", duration_seconds=duration),
            finish_reason=FinishReason(FinishReasonCode.STOP),
            usage=Usage(output_media_seconds=duration),
        )
