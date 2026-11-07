"""Unit tests for live OpenAI multimodal generative adapter (DALL-E, TTS)."""

import io
import json
import socket
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from pyllmkit.adapters.cli.catalog import create_reference_catalog
from pyllmkit.adapters.cli.service import create_cli_inference_service
from pyllmkit.domain.inference import AudioOutput, ImageOutput, InferenceRequest, ModelTarget
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.models import ModelId


@pytest.fixture
def fake_openai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test123456789")


def test_openai_media_gpt_image_generation_success(fake_openai_env: None) -> None:
    catalog = create_reference_catalog()
    service = create_cli_inference_service(catalog, mock=False)

    req = InferenceRequest(
        ModelTarget(ModelId("gpt-image-2")),
        (Message(Role.USER, Content((TextContent("Un astronaute sur la Lune"),))),),
    )

    mock_resp_payload = {
        "data": [
            {
                "b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                "revised_prompt": "Un astronaute marchant sur la lune",
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_resp_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with (
        patch("socket.getaddrinfo", return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        ]),
        patch("urllib.request.build_opener") as opener,
    ):
        opener.return_value.open.return_value = mock_resp
        execution = service.invoke(req)

    assert execution.response is not None
    assert isinstance(execution.response.output, ImageOutput)
    # Dimensions are read from the real PNG header (1x1 fixture), not assumed.
    assert execution.response.output.width == 1
    assert execution.response.output.height == 1
    assert execution.response.output.revised_prompt == "Un astronaute marchant sur la lune"
    assert execution.response.usage is not None
    assert execution.response.usage.output_media_units == 1


def test_openai_media_tts_generation_success(fake_openai_env: None) -> None:
    catalog = create_reference_catalog()
    service = create_cli_inference_service(catalog, mock=False)

    req = InferenceRequest(
        ModelTarget(ModelId("tts-1")),
        (Message(Role.USER, Content((TextContent("Bonjour le monde"),))),),
    )

    mock_resp = MagicMock()
    mock_resp.read.return_value = b"FAKE_MP3_AUDIO_BYTES"
    mock_resp.__enter__.return_value = mock_resp

    with (
        patch("socket.getaddrinfo", return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        ]),
        patch("urllib.request.build_opener") as opener,
    ):
        opener.return_value.open.return_value = mock_resp
        execution = service.invoke(req)

    assert execution.response is not None
    assert isinstance(execution.response.output, AudioOutput)
    assert execution.response.output.mime_type == "audio/mpeg"
    assert execution.response.output.transcript == "Bonjour le monde"
    assert execution.response.usage is not None
    assert execution.response.usage.input_characters == len("Bonjour le monde")


def test_openai_media_handles_401_error(fake_openai_env: None) -> None:
    catalog = create_reference_catalog()
    service = create_cli_inference_service(catalog, mock=False)

    req = InferenceRequest(
        ModelTarget(ModelId("gpt-image-2")),
        (Message(Role.USER, Content((TextContent("Test error"),))),),
    )

    err = urllib.error.HTTPError("https://api.openai.com/v1/images/generations", 401, "Unauthorized", {}, io.BytesIO(b"{}"))
    with (
        patch("socket.getaddrinfo", return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        ]),
        patch("urllib.request.build_opener") as opener,
    ):
        opener.return_value.open.side_effect = err
        execution = service.invoke(req)

    assert execution.run.failure is not None
    assert execution.run.failure.code == "credential_unavailable"
