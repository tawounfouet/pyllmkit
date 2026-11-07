"""Offline tests for live media-generation adapters (Google, xAI, OpenAI gpt-image).

HTTP is simulated by patching ``urllib.request.urlopen``; no network access.
"""

from __future__ import annotations

import base64
import io
import json
import socket
import struct
import urllib.error
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.catalog import create_reference_catalog
from pyllmkit.adapters.cli.main import app
from pyllmkit.adapters.cli.service import create_cli_inference_service
from pyllmkit.adapters.inference.media_http import (
    MediaDiagnostics,
    MediaGenerationOptions,
    pcm16_to_wav,
    sanitize_detail,
    wav_duration_seconds,
)
from pyllmkit.domain.inference import (
    AudioOutput,
    ImageOutput,
    InferenceRequest,
    ModelTarget,
    VideoOutput,
)
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.models import ModelId

PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture(autouse=True)
def fake_keys(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    monkeypatch.setenv("PYLLMKIT_HISTORY_DB", str(tmp_path / "history.db"))
    monkeypatch.setenv("PYLLMKIT_ASSETS_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test123456789")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaTEST-not-a-real-key-000000000")
    monkeypatch.setenv("XAI_API_KEY", "xai-testkey123456789")


def _resp(body: bytes | dict[str, Any]) -> MagicMock:
    raw = json.dumps(body).encode() if isinstance(body, dict) else body
    m = MagicMock()
    m.read.return_value = raw
    m.__enter__.return_value = m
    return m


class _Recorder:
    """urlopen double returning queued responses and recording requests."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.requests: list[Any] = []

    def __call__(self, req: Any, timeout: float | None = None) -> Any:
        self.requests.append(req)
        nxt = self.responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return _resp(nxt)

    def payload(self, i: int) -> dict[str, Any]:
        return json.loads(self.requests[i].data.decode())


def _request(model: str, prompt: str = "Un phare", system: str | None = None) -> InferenceRequest:
    msgs = []
    if system:
        msgs.append(Message(Role.SYSTEM, Content((TextContent(system),))))
    msgs.append(Message(Role.USER, Content((TextContent(prompt),))))
    return InferenceRequest(ModelTarget(ModelId(model)), tuple(msgs))


def _invoke(model: str, rec: _Recorder, *, options: MediaGenerationOptions | None = None,
            diagnostics: MediaDiagnostics | None = None, system: str | None = None) -> Any:
    service = create_cli_inference_service(
        create_reference_catalog(), mock=False, media_options=options, diagnostics=diagnostics,
    )
    public_dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
    with (
        patch("urllib.request.urlopen", side_effect=rec),
        patch("urllib.request.build_opener") as fake_opener,
        patch("socket.getaddrinfo", return_value=public_dns),
    ):
        fake_opener.return_value.open.side_effect = rec
        return service.invoke(_request(model, system=system))


# --------------------------------------------------------------------- OpenAI
def test_gpt_image_payload_and_real_dimensions() -> None:
    rec = _Recorder([{"data": [{"b64_json": base64.b64encode(PNG_1x1).decode()}],
                      "usage": {"input_tokens": 5, "output_tokens": 100, "total_tokens": 105}}])
    ex = _invoke("gpt-image-1-mini", rec, options=MediaGenerationOptions(size="1024x1536", quality="low"),
                 system="Tu es un assistant")
    out = ex.response.output
    assert isinstance(out, ImageOutput) and (out.width, out.height) == (1, 1)
    body = rec.payload(0)
    assert rec.requests[0].full_url.endswith("/v1/images/generations")
    assert body["prompt"] == "Un phare"  # system prompt is never the image prompt
    assert body["size"] == "1024x1536" and body["quality"] == "low"
    assert "response_format" not in body
    assert ex.response.usage.output_tokens == 100


def test_openai_tts_passes_voice_and_instructions() -> None:
    rec = _Recorder([b"ID3fake-mp3"])
    ex = _invoke("gpt-4o-mini-tts", rec, options=MediaGenerationOptions(voice="nova", instructions="joyeux"))
    assert isinstance(ex.response.output, AudioOutput)
    assert ex.response.output.mime_type == "audio/mpeg"
    body = rec.payload(0)
    assert body["voice"] == "nova" and body["instructions"] == "joyeux"


def test_text_model_still_routes_to_text_adapter() -> None:
    rec = _Recorder([RuntimeError("text adapter must not use media endpoint")])
    service = create_cli_inference_service(create_reference_catalog(), mock=False)
    with patch("pyllmkit.adapters.inference.openai_responses.OpenAIResponsesAdapter.invoke",
               side_effect=RuntimeError("text-path")) as text_invoke, patch("urllib.request.urlopen", side_effect=rec):
        ex = service.invoke(_request("gpt-4o"))
    assert text_invoke.called
    assert not rec.requests
    assert ex.run.failure is not None


def test_http_error_detail_is_recorded_and_sanitized() -> None:
    err = urllib.error.HTTPError(
        "https://api.openai.com/v1/images/generations", 400, "Bad Request", {},  # type: ignore[arg-type]
        io.BytesIO(json.dumps({"error": {"message": "The model 'dall-e-3' does not exist. key sk-proj-test123456789"}}).encode()),
    )
    diag = MediaDiagnostics()
    ex = _invoke("gpt-image-2", _Recorder([err]), diagnostics=diag)
    assert ex.run.failure.code == "model_not_found"
    assert diag.http_status == 400
    assert "does not exist" in (diag.last_error or "")
    assert "sk-proj-test123456789" not in (diag.last_error or "")


# --------------------------------------------------------------------- Google
def test_gemini_image_generate_content() -> None:
    rec = _Recorder([{
        "candidates": [{"content": {"parts": [
            {"text": "Voici"},
            {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(PNG_1x1).decode()}},
        ]}}],
        "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 1290, "totalTokenCount": 1294},
    }])
    ex = _invoke("gemini-3.1-flash-image", rec, options=MediaGenerationOptions(aspect_ratio="16:9"))
    out = ex.response.output
    assert isinstance(out, ImageOutput) and out.mime_type == "image/png"
    req = rec.requests[0]
    assert req.full_url.endswith("/models/gemini-3.1-flash-image:generateContent")
    assert req.get_header("X-goog-api-key")
    body = rec.payload(0)
    assert "IMAGE" in body["generationConfig"]["responseModalities"]
    assert body["generationConfig"]["imageConfig"] == {"aspectRatio": "16:9"}
    assert ex.response.usage.output_tokens == 1290


def test_gemini_tts_wraps_raw_pcm_into_wav() -> None:
    pcm = b"\x00\x00" * 24000  # 1 second mono 24 kHz
    rec = _Recorder([{"candidates": [{"content": {"parts": [
        {"inlineData": {"mimeType": "audio/L16;codec=pcm;rate=24000", "data": base64.b64encode(pcm).decode()}},
    ]}}]}])
    ex = _invoke("gemini-2.5-flash-preview-tts", rec, options=MediaGenerationOptions(voice="Puck"))
    out = ex.response.output
    assert isinstance(out, AudioOutput) and out.mime_type == "audio/wav"
    assert out.duration_seconds == 1.0
    raw = base64.b64decode(out.media.value.split(",", 1)[1])
    assert raw[:4] == b"RIFF" and raw[8:12] == b"WAVE"
    voice = rec.payload(0)["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"]
    assert voice == "Puck"


def test_gemini_blocked_prompt_maps_to_content_filtered() -> None:
    diag = MediaDiagnostics()
    ex = _invoke("gemini-3.1-flash-image", _Recorder([{"promptFeedback": {"blockReason": "SAFETY"}}]), diagnostics=diag)
    assert ex.run.failure.code == "content_filtered"
    assert "SAFETY" in (diag.last_error or "")


def test_veo_long_running_operation_polling() -> None:
    rec = _Recorder([
        {"name": "operations/abc"},
        {"name": "operations/abc", "done": False},
        {"name": "operations/abc", "done": True, "response": {"generateVideoResponse": {
            "generatedSamples": [{"video": {"uri": "https://generativelanguage.googleapis.com/v1beta/files/x:download"}}]}}},
        b"\x00\x00\x00\x18ftypmp42",
    ])
    ex = _invoke("veo-3.1-lite-generate-preview", rec, options=MediaGenerationOptions(poll_interval_seconds=0.0, duration_seconds=5))
    assert isinstance(ex.response.output, VideoOutput)
    assert rec.requests[0].full_url.endswith("/models/veo-3.1-lite-generate-preview:predictLongRunning")
    assert rec.requests[2].full_url.endswith("/v1beta/operations/abc")


# --------------------------------------------------------------------- xAI
def test_xai_image_b64() -> None:
    rec = _Recorder([{"data": [{"b64_json": base64.b64encode(PNG_1x1).decode(), "mime_type": "image/png"}]}])
    ex = _invoke("grok-imagine-image", rec, options=MediaGenerationOptions(aspect_ratio="1:1"))
    assert isinstance(ex.response.output, ImageOutput)
    body = rec.payload(0)
    assert body["response_format"] == "b64_json" and body["aspect_ratio"] == "1:1"


def test_xai_video_polls_until_done_then_downloads() -> None:
    rec = _Recorder([
        {"request_id": "req-1"},
        {"status": "pending", "progress": 40},
        {"status": "done", "video": {"url": "https://vidgen.x.ai/v.mp4", "duration": 6, "respect_moderation": True}},
        b"\x00\x00\x00\x18ftypmp42",
    ])
    diag = MediaDiagnostics()
    ex = _invoke("grok-imagine-video", rec, diagnostics=diag,
                 options=MediaGenerationOptions(poll_interval_seconds=0.0, duration_seconds=6, resolution="720p"))
    out = ex.response.output
    assert isinstance(out, VideoOutput) and out.duration_seconds == 6.0
    assert (out.width, out.height) == (1280, 720)
    assert rec.payload(0) == {"model": "grok-imagine-video", "prompt": "Un phare", "duration": 6, "resolution": "720p"}
    assert rec.requests[1].full_url.endswith("/v1/videos/req-1")
    assert diag.progress == ["40%"]


def test_xai_video_failed_status() -> None:
    diag = MediaDiagnostics()
    ex = _invoke("grok-imagine-video", _Recorder([
        {"request_id": "req-2"},
        {"status": "failed", "error": {"code": "invalid_argument", "message": "Prompt rejected"}},
    ]), diagnostics=diag, options=MediaGenerationOptions(poll_interval_seconds=0.0))
    assert ex.run.failure.code == "provider_not_completed"
    assert "Prompt rejected" in (diag.last_error or "")


def test_xai_video_poll_timeout() -> None:
    responses: list[Any] = [{"request_id": "req-3"}] + [{"status": "pending"}] * 5
    ex = _invoke("grok-imagine-video", _Recorder(responses),
                 options=MediaGenerationOptions(poll_interval_seconds=0.0, poll_timeout_seconds=0.0))
    assert ex.run.failure.code == "provider_timeout"


# --------------------------------------------------------------------- helpers & CLI
def test_wav_helpers_round_trip() -> None:
    wav = pcm16_to_wav(b"\x00\x00" * 12000, sample_rate=24000)
    assert struct.unpack("<I", wav[24:28])[0] == 24000
    assert wav_duration_seconds(wav) == 0.5


def test_sanitize_detail_redacts_and_truncates() -> None:
    out = sanitize_detail("bad key xai-ABCDEFGHIJKLMNOP " + "x" * 1000, secret=None)
    assert "xai-ABCDEFGHIJKLMNOP" not in out and len(out) <= 400


@pytest.mark.parametrize(
    ("argv", "fragment"),
    [
        (["generate", "image", "x", "-m", "veo-2"], "pas 'image'"),
        (["generate", "audio", "x", "-m", "gpt-image-1-mini"], "pas 'audio'"),
    ],
)
def test_generate_rejects_model_of_wrong_kind(argv: list[str], fragment: str) -> None:
    result = CliRunner().invoke(app, argv, env={"COLUMNS": "200"})
    assert result.exit_code == 1
    assert fragment in result.output


@pytest.mark.parametrize("kind", ["image", "audio", "video"])
def test_generate_defaults_work_offline(kind: str, tmp_path: Any) -> None:
    out = tmp_path / f"out.{kind}"
    result = CliRunner().invoke(app, ["generate", kind, "Bonjour", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists() and out.stat().st_size > 0



# --------------------------------------------------------------------- media_http error mapping
def _http_error(status: int, body: bytes) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x.test", status, "err", {}, io.BytesIO(body))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("status", "body", "code"),
    [
        (401, b'{"error": {"message": "bad key"}}', "credential_unavailable"),
        (403, b'{"error": "forbidden"}', "permission_denied"),
        (404, b'{"message": "nope"}', "model_not_found"),
        (429, b"slow down", "rate_limited"),
        (400, b'{"error": {"message": "blocked by safety system"}}', "content_filtered"),
        (422, b"[1, 2]", "invalid_request"),
        (503, b"", "provider_overloaded"),
        (302, b"{}", "provider_protocol_error"),
    ],
)
def test_http_status_mapping(status: int, body: bytes, code: str) -> None:
    from pyllmkit.adapters.inference.media_http import http_json
    from pyllmkit.application.inference import InvocationPortError

    diag = MediaDiagnostics()
    with patch("urllib.request.urlopen", side_effect=_http_error(status, body)), \
            pytest.raises(InvocationPortError) as info:
        http_json("https://x.test", diagnostics=diag)
    assert info.value.code == code
    assert diag.http_status == status


@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (TimeoutError(), "provider_timeout"),
        (urllib.error.URLError(TimeoutError()), "provider_timeout"),
        (urllib.error.URLError("dns failure"), "connection_failure"),
    ],
)
def test_network_failures(exc: Exception, code: str) -> None:
    from pyllmkit.adapters.inference.media_http import http_bytes
    from pyllmkit.application.inference import InvocationPortError

    diag = MediaDiagnostics()
    with patch("urllib.request.urlopen", side_effect=exc), pytest.raises(InvocationPortError) as info:
        http_bytes("https://x.test", diagnostics=diag)
    assert info.value.code == code
    assert diag.last_error


@pytest.mark.parametrize("raw", [b"not json", b"[1]"])
def test_invalid_json_is_protocol_error(raw: bytes) -> None:
    from pyllmkit.adapters.inference.media_http import http_json
    from pyllmkit.application.inference import InvocationPortError

    with patch("urllib.request.urlopen", return_value=_resp(raw)), pytest.raises(InvocationPortError) as info:
        http_json("https://x.test", diagnostics=MediaDiagnostics())
    assert info.value.code == "provider_protocol_error"


def test_image_helpers() -> None:
    from pyllmkit.adapters.inference.media_http import (
        image_dimensions,
        parse_size,
        sniff_image_mime,
    )

    jpeg = b"\xff\xd8" + b"\xff\xe0\x00\x04\x00\x00" + b"\xff\xc0\x00\x11\x08\x00\x20\x00\x40" + b"\x00" * 8
    assert image_dimensions(jpeg) == (64, 32)
    assert image_dimensions(PNG_1x1) == (1, 1)
    assert image_dimensions(b"GIF89a") == (None, None)
    assert sniff_image_mime(jpeg) == "image/jpeg"
    assert sniff_image_mime(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert sniff_image_mime(b"????", "image/gif") == "image/gif"
    assert parse_size("1024x1536") == (1024, 1536)
    assert parse_size("auto") == (None, None)
    assert parse_size("axb") == (None, None)
    assert wav_duration_seconds(b"short") is None


def test_missing_credential_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XAI_API_KEY")
    ex = _invoke("grok-imagine-image", _Recorder([]))
    assert ex.run.failure.code == "credential_unavailable"


def test_openai_image_url_fallback_and_empty_payload() -> None:
    rec = _Recorder([{"data": [{"url": "https://files.openai.com/img.png"}]}, PNG_1x1])
    ex = _invoke("gpt-image-2", rec)
    assert isinstance(ex.response.output, ImageOutput)
    assert rec.payload(0)["model"] == "gpt-image-2"
    diag = MediaDiagnostics()
    ex2 = _invoke("gpt-image-1-mini", _Recorder([{"data": []}]), diagnostics=diag)
    assert ex2.run.failure.code == "unsupported_provider_output"


# --------------------------------------------------------------------- Gemini Omni video
def test_gemini_omni_interactions_video() -> None:
    mp4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 32
    rec = _Recorder([{
        "status": "completed",
        "steps": [
            {"type": "thought", "signature": "abc"},
            {"type": "model_output", "content": [
                {"type": "video", "mime_type": "video/mp4", "data": base64.b64encode(mp4).decode()},
            ]},
        ],
        "usage": {"total_input_tokens": 13, "total_output_tokens": 5793, "total_tokens": 6323,
                  "total_thought_tokens": 517},
    }])
    ex = _invoke("gemini-omni-1.2-flash", rec, options=MediaGenerationOptions(
        duration_seconds=6, resolution="720p", aspect_ratio="9:16"))
    out = ex.response.output
    assert isinstance(out, VideoOutput) and out.duration_seconds == 6.0
    assert base64.b64decode(out.media.value.split(",", 1)[1]) == mp4
    assert rec.requests[0].full_url.endswith("/v1beta/interactions")
    assert rec.payload(0) == {
        "model": "gemini-omni-1.2-flash",
        "input": "Un phare",
        "response_format": {"type": "video", "aspect_ratio": "9:16", "resolution": "720p", "duration": "6s"},
    }
    assert ex.response.usage.output_tokens == 5793
    assert ex.response.usage.reasoning_tokens == 517


def test_gemini_omni_without_video_is_filtered() -> None:
    ex = _invoke("gemini-omni-1.2-flash", _Recorder([{"status": "completed", "steps": []}]))
    assert ex.run.failure.code == "content_filtered"


def test_gemini_omni_incomplete_status() -> None:
    ex = _invoke("gemini-omni-1.2-flash", _Recorder([{"status": "failed", "steps": []}]))
    assert ex.run.failure.code == "provider_not_completed"


def test_retired_veo_id_rejected_without_network() -> None:
    rec = _Recorder([])
    diag = MediaDiagnostics()
    ex = _invoke("veo-2", rec, diagnostics=diag)
    assert ex.run.failure.code == "model_retired"
    assert rec.requests == []
    assert diag.http_status is None


# --------------------------------------------------------------------- FinOps
def test_media_cost_never_assumes_quantities() -> None:
    from pyllmkit.adapters.cli.model_specs import compute_run_cost

    assert compute_run_cost("veo-2", None, None) == (None, "-")
    assert compute_run_cost("dall-e-3", None, None) == (None, "-")
    assert compute_run_cost("tts-1", None, None) == (None, "-")
    assert compute_run_cost("veo-2", None, None, output_media_seconds=2.0) == (None, "-")
    assert compute_run_cost("dall-e-3", None, None, output_media_units=2) == (None, "-")


def test_runs_list_does_not_bill_failed_or_mock_runs(tmp_path: Any) -> None:
    from pyllmkit.adapters.cli.storage import RunRecord, SqliteRunStore

    store = SqliteRunStore()
    base = {"prompt": "", "response_text": None, "input_tokens": None, "output_tokens": None,
            "duration_ms": 100.0, "created_at": "2026-11-07T03:00:00+00:00", "mode": "generate"}
    store.record_run(RunRecord(run_id="failedveo00000000", model_id="veo-2", provider="google",
                               state="failed", finish_reason="model_not_found", **base))
    store.record_run(RunRecord(run_id="mockdalle00000000", model_id="dall-e-3", provider="openai (mock)",
                               state="completed", finish_reason="stop", **base))
    store.record_run(RunRecord(run_id="livedalle00000000", model_id="dall-e-3", provider="openai",
                               state="completed", finish_reason="stop", **base))
    result = CliRunner().invoke(app, ["runs", "list"], env={"COLUMNS": "250"})
    assert result.exit_code == 0, result.output
    assert "$0.750" not in result.output
    assert "$0.04" not in result.output  # historical retired price is not a current quote
    shown = CliRunner().invoke(app, ["runs", "inspect", "failedveo00000000"], env={"COLUMNS": "200"})
    assert "non facturé" in shown.output
