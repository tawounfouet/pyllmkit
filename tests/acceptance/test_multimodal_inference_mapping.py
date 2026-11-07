"""Acceptance tests for multimodal inference mapping across all providers."""

import json
from pathlib import Path

import pytest

from pyllmkit.adapters.inference import FakeInferenceAdapter
from pyllmkit.adapters.inference.anthropic_messages_mapping import (
    encode_anthropic_messages_request,
)
from pyllmkit.adapters.inference.google_gemini_mapping import (
    encode_gemini_request,
)
from pyllmkit.adapters.inference.mistral_chat_mapping import (
    encode_mistral_chat_request,
)
from pyllmkit.adapters.inference.ollama_mapping import (
    encode_ollama_request,
)
from pyllmkit.adapters.inference.openai_responses_mapping import (
    encode_openai_responses_request,
)
from pyllmkit.adapters.inference.xai_responses_mapping import (
    encode_xai_responses_request,
)
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import (
    InferenceService,
    InvocationPortError,
)
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import (
    DeploymentId,
    DeploymentTarget,
    GenerationConfig,
    GenerationSupportSnapshot,
    InferenceRequest,
    InferenceRunState,
    ParameterSupport,
)
from pyllmkit.domain.interactions import (
    AudioContent,
    Content,
    ImageContent,
    MediaSourceRef,
    Message,
    Role,
    TextContent,
    VideoContent,
)
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId


def _setup_multimodal_prepared(
    provider_name: str,
    modalities_in: tuple[str, ...],
    messages: tuple[Message, ...],
    alias: str = "test-model",
    config: GenerationConfig | None = None,
):
    catalog = InMemoryCatalog()
    in_mods = frozenset(Modality(m) for m in modalities_in)
    out_mods = frozenset({Modality("text")})
    mod_set = ModalitySet(in_mods, out_mods)

    model_id = ModelId("model-1")
    prov_id = ProviderId(provider_name)
    dep_id = DeploymentId("dep-1")

    catalog.models.register(Model(model_id, ModelIdentity(ModelFamily(provider_name)), modalities=mod_set))
    catalog.providers.register(InferenceProvider(prov_id, provider_name.capitalize(), modalities=mod_set))
    catalog.deployments.register(
        Deployment(dep_id, model_id, prov_id, DeploymentStatus.AVAILABLE, modalities=mod_set)
    )

    fake = FakeInferenceAdapter()
    svc = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        fake,
        {dep_id: alias},
    )
    req = InferenceRequest(DeploymentTarget(dep_id), messages, config)
    snap = (
        GenerationSupportSnapshot(
            DeploymentTarget(dep_id),
            (ParameterSupport("max_output_tokens", CapabilitySupport(SupportLevel.NATIVE)),),
        )
        if config is not None
        else None
    )
    result = svc.invoke(req, snap)
    assert result.run.state is InferenceRunState.COMPLETED
    return fake.calls[0]


def test_gemini_multimodal_mapping_image_audio_video(tmp_path: Path) -> None:
    # Prepare dummy file
    local_img = tmp_path / "test.png"
    local_img.write_bytes(b"\x89PNG\r\n\x1a\nfakeimagebytes")

    messages = (
        Message(
            Role.USER,
            Content((
                TextContent("Look and listen:"),
                ImageContent(MediaSourceRef("data", "data:image/jpeg;base64,aW1nZGF0YQ==")),
                ImageContent(MediaSourceRef("file", str(local_img))),
                AudioContent(MediaSourceRef("uri", "https://example.org/audio.wav"), format="wav"),
                VideoContent(MediaSourceRef("asset", "video-asset-id"), format="mp4"),
            )),
        ),
    )
    prep = _setup_multimodal_prepared(
        "google", ("text", "image", "audio", "video"), messages, "gemini-2.0-flash"
    )
    raw = encode_gemini_request(prep)
    payload = json.loads(raw.decode("utf-8"))

    parts = payload["contents"][0]["parts"]
    assert len(parts) == 5
    assert parts[0] == {"text": "Look and listen:"}
    assert parts[1] == {"inlineData": {"mimeType": "image/jpeg", "data": "aW1nZGF0YQ=="}}
    assert parts[2]["inlineData"]["mimeType"] == "image/png"
    assert parts[3] == {"fileData": {"fileUri": "https://example.org/audio.wav", "mimeType": "audio/wav"}}
    assert parts[4] == {"fileData": {"fileUri": "video-asset-id", "mimeType": "video/mp4"}}


def test_openai_multimodal_mapping_image_and_audio() -> None:
    messages = (
        Message(
            Role.USER,
            Content((
                TextContent("Transcribe and describe:"),
                ImageContent(MediaSourceRef("uri", "https://example.org/photo.png")),
                AudioContent(MediaSourceRef("data", "data:audio/wav;base64,YXVkaW9kYXRh"), format="wav"),
            )),
        ),
    )
    prep = _setup_multimodal_prepared(
        "openai", ("text", "image", "audio"), messages, "gpt-4o"
    )
    raw = encode_openai_responses_request(prep)
    payload = json.loads(raw.decode("utf-8"))

    content = payload["input"][0]["content"]
    assert len(content) == 3
    assert content[0] == {"type": "input_text", "text": "Transcribe and describe:"}
    assert content[1] == {"type": "input_image", "image_url": "https://example.org/photo.png"}
    assert content[2] == {
        "type": "input_audio",
        "input_audio": {"data": "YXVkaW9kYXRh", "format": "wav"},
    }


def test_openai_rejects_video_capability() -> None:
    messages = (
        Message(
            Role.USER,
            Content((
                TextContent("Video query"),
                VideoContent(MediaSourceRef("uri", "https://example.org/v.mp4")),
            )),
        ),
    )
    prep = _setup_multimodal_prepared("openai", ("text", "video"), messages, "gpt-4o")
    with pytest.raises(InvocationPortError, match="unsupported_capability"):
        encode_openai_responses_request(prep)


def test_anthropic_multimodal_mapping_image_and_audio_rejection() -> None:
    img_data = "data:image/png;base64,YWJjZA=="
    messages = (
        Message(
            Role.USER,
            Content((
                TextContent("Image query"),
                ImageContent(MediaSourceRef("data", img_data)),
            )),
        ),
    )
    cfg = GenerationConfig(max_output_tokens=100)
    prep = _setup_multimodal_prepared(
        "anthropic", ("text", "image"), messages, "claude-3-5-sonnet", config=cfg
    )
    raw = encode_anthropic_messages_request(prep)
    payload = json.loads(raw.decode("utf-8"))

    content = payload["messages"][0]["content"]
    assert len(content) == 2
    assert content[0] == {"type": "text", "text": "Image query"}
    assert content[1] == {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": "YWJjZA=="},
    }

    # Audio should be rejected as unsupported_capability
    audio_msg = (
        Message(
            Role.USER,
            Content((
                AudioContent(MediaSourceRef("data", "data:audio/wav;base64,YXVkaW8=")),
            )),
        ),
    )
    audio_prep = _setup_multimodal_prepared(
        "anthropic", ("text", "audio"), audio_msg, "claude-3-5-sonnet", config=cfg
    )
    with pytest.raises(InvocationPortError, match="unsupported_capability"):
        encode_anthropic_messages_request(audio_prep)


def test_xai_and_mistral_multimodal_image_mapping() -> None:
    messages = (
        Message(
            Role.USER,
            Content((
                TextContent("Pic"),
                ImageContent(MediaSourceRef("uri", "https://example.org/pic.jpg")),
            )),
        ),
    )
    # xAI
    xai_prep = _setup_multimodal_prepared("xai", ("text", "image"), messages, "grok-vision-beta")
    xai_raw = encode_xai_responses_request(xai_prep)
    xai_payload = json.loads(xai_raw.decode("utf-8"))
    assert xai_payload["input"][0]["content"][1] == {
        "type": "image_url",
        "image_url": {"url": "https://example.org/pic.jpg"},
    }

    # Mistral
    mistral_prep = _setup_multimodal_prepared("mistral", ("text", "image"), messages, "pixtral-12b")
    mistral_raw = encode_mistral_chat_request(mistral_prep)
    mistral_payload = json.loads(mistral_raw.decode("utf-8"))
    assert mistral_payload["messages"][0]["content"][1] == {
        "type": "image_url",
        "image_url": "https://example.org/pic.jpg",
    }


def test_ollama_multimodal_image_mapping() -> None:
    messages = (
        Message(
            Role.USER,
            Content((
                TextContent("Describe image"),
                ImageContent(MediaSourceRef("data", "data:image/png;base64,b2xsYW1haW1n")),
            )),
        ),
    )
    prep = _setup_multimodal_prepared("ollama", ("text", "image"), messages, "llava")
    raw = encode_ollama_request(prep)
    payload = json.loads(raw.decode("utf-8"))

    msg = payload["messages"][0]
    assert msg["content"] == "Describe image"
    assert msg["images"] == ["b2xsYW1haW1n"]


def test_media_file_not_found_handling() -> None:
    messages = (
        Message(
            Role.USER,
            Content((
                ImageContent(MediaSourceRef("file", "/path/to/nonexistent_file_12345.png")),
            )),
        ),
    )
    prep = _setup_multimodal_prepared("google", ("text", "image"), messages, "gemini-2.0-flash")
    with pytest.raises(InvocationPortError, match="media_file_not_found"):
        encode_gemini_request(prep)


def test_media_mapping_helpers_coverage(tmp_path: Path) -> None:
    from unittest.mock import MagicMock

    from pyllmkit.adapters.inference.media_mapping import (
        default_mime_for_part,
        extract_media_base64_and_mime,
        resolve_media_url_or_data,
    )

    # default_mime_for_part
    assert default_mime_for_part(ImageContent(MediaSourceRef("asset", "a"))) == "image/png"
    assert default_mime_for_part(AudioContent(MediaSourceRef("asset", "a"), format="wav")) == "audio/wav"
    assert default_mime_for_part(AudioContent(MediaSourceRef("asset", "a"), format="mp3")) == "audio/mp3"
    assert default_mime_for_part(AudioContent(MediaSourceRef("asset", "a"), format="flac")) == "audio/wav"
    assert default_mime_for_part(VideoContent(MediaSourceRef("asset", "a"), format="mov")) == "video/quicktime"
    assert default_mime_for_part(VideoContent(MediaSourceRef("asset", "a"), format="mp4")) == "video/mp4"
    assert default_mime_for_part(TextContent("txt")) == "application/octet-stream"

    # extract_media_base64_and_mime with plain text data URI
    b64, mime = extract_media_base64_and_mime(MediaSourceRef("data", "data:text/plain,helloworld"), "text/plain")
    assert mime == "text/plain"
    assert b64 == "aGVsbG93b3JsZA=="

    # extract_media_base64_and_mime with uri or asset raises unsupported_media_source
    with pytest.raises(InvocationPortError, match="unsupported_media_source"):
        extract_media_base64_and_mime(MediaSourceRef("uri", "https://example.org/a.png"), "image/png")
    with pytest.raises(InvocationPortError, match="unsupported_media_source"):
        extract_media_base64_and_mime(MediaSourceRef("asset", "asset-id"), "image/png")

    # resolve_media_url_or_data with file
    test_f = tmp_path / "img.webp"
    test_f.write_bytes(b"webpdata")
    url, m = resolve_media_url_or_data(MediaSourceRef("file", str(test_f)), "image/webp")
    assert url.startswith("data:image/webp;base64,")
    assert m == "image/webp"

    # resolve_media_url_or_data with data URI without mime in header
    url2, m2 = resolve_media_url_or_data(MediaSourceRef("data", "data:,somepayload"), "image/png")
    assert url2 == "data:,somepayload"
    assert m2 == "image/png"

    # resolve_media_url_or_data invalid kind
    bad_ref = MagicMock()
    bad_ref.kind = "unknown"
    bad_ref.value = "opaque"
    with pytest.raises(InvocationPortError, match="unsupported_media_source"):
        resolve_media_url_or_data(bad_ref, "image/png")

    # extract_media_base64_and_mime invalid kind
    with pytest.raises(InvocationPortError, match="unsupported_media_source"):
        extract_media_base64_and_mime(bad_ref, "image/png")

    # check_part_modality with None modalities
    from pyllmkit.adapters.inference.media_mapping import check_part_modality
    mock_prep = MagicMock()
    mock_prep.resolution.deployment.modalities = None
    check_part_modality(mock_prep, ImageContent(MediaSourceRef("asset", "a")))



def test_multimodal_wire_request_limit_is_separate_from_text_limit(tmp_path: Path) -> None:
    from pyllmkit.adapters.inference.media_mapping import (
        MAX_MULTIMODAL_REQUEST_BYTES,
        MAX_MULTIMODAL_SOURCE_BYTES,
        MAX_TEXT_REQUEST_BYTES,
        request_bytes_limit,
    )

    text = (Message(Role.USER, Content((TextContent("hello"),))),)
    prep_text = _setup_multimodal_prepared("ollama", ("text",), text, "llama3.2:1b")
    assert request_bytes_limit(prep_text) == MAX_TEXT_REQUEST_BYTES
    image = (Message(Role.USER, Content((
        TextContent("describe"),
        ImageContent(MediaSourceRef("data", "data:image/png;base64,YWJj")),
    ))),)
    prep_image = _setup_multimodal_prepared("ollama", ("text", "image"), image, "llava")
    assert request_bytes_limit(prep_image) == MAX_MULTIMODAL_REQUEST_BYTES

    huge = tmp_path / "too-large.png"
    with huge.open("wb") as target:
        target.truncate(MAX_MULTIMODAL_SOURCE_BYTES + 1)
    request = (Message(Role.USER, Content((
        ImageContent(MediaSourceRef("file", str(huge))),
    ))),)
    prepared = _setup_multimodal_prepared("ollama", ("text", "image"), request, "llava")
    with pytest.raises(InvocationPortError, match="request_too_large"):
        encode_ollama_request(prepared)
