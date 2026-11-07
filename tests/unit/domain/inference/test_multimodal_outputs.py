"""Unit tests for multimodal inference outputs, extended Usage and serialization."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import cast

import pytest

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import (
    AudioOutput,
    ImageOutput,
    InferenceResponse,
    InferenceRun,
    InferenceRunId,
    ModelTarget,
    MultiPartOutput,
    TextOutput,
    Usage,
    VideoOutput,
    response_from_dict,
    response_to_dict,
    run_from_dict,
    run_to_dict,
)
from pyllmkit.domain.inference.request import InferenceRequest
from pyllmkit.domain.interactions import Content, MediaSourceRef, Message, Role, TextContent
from pyllmkit.domain.models import ModelId


def _sample_image_ref() -> MediaSourceRef:
    return MediaSourceRef("data", "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def _sample_audio_ref() -> MediaSourceRef:
    return MediaSourceRef("uri", "https://example.org/audio/sample.mp3")


def _sample_video_ref() -> MediaSourceRef:
    return MediaSourceRef("uri", "https://example.org/video/sample.mp4")


class TestImageOutput:
    """Validation and immutability for ImageOutput."""

    def test_valid_image_output_construction(self) -> None:
        ref = _sample_image_ref()
        output = ImageOutput(
            media=ref,
            mime_type="image/png",
            width=1024,
            height=1024,
            revised_prompt="An edited prompt",
        )
        assert output.kind == "image"
        assert output.media == ref
        assert output.mime_type == "image/png"
        assert output.width == 1024
        assert output.height == 1024
        assert output.revised_prompt == "An edited prompt"
        assert output == ImageOutput(media=ref, width=1024, height=1024, revised_prompt="An edited prompt")
        assert hash(output) == hash(ImageOutput(media=ref, width=1024, height=1024, revised_prompt="An edited prompt"))

    def test_image_output_immutability(self) -> None:
        output = ImageOutput(media=_sample_image_ref())
        with pytest.raises(FrozenInstanceError):
            output.width = 512  # type: ignore[misc]

    @pytest.mark.parametrize("bad_media", [None, "https://example.org", 123, {}])
    def test_image_output_rejects_invalid_media(self, bad_media: object) -> None:
        with pytest.raises(DomainValidationError, match="ImageOutput.media"):
            ImageOutput(media=cast(MediaSourceRef, bad_media))

    @pytest.mark.parametrize("bad_mime", ["", "text/plain", "audio/mp3", None, 123])
    def test_image_output_rejects_invalid_mime(self, bad_mime: object) -> None:
        with pytest.raises(DomainValidationError, match="ImageOutput.mime_type"):
            ImageOutput(media=_sample_image_ref(), mime_type=cast(str, bad_mime))

    @pytest.mark.parametrize("bad_dim", [0, -10, 1.5, "1024"])
    def test_image_output_rejects_invalid_dimensions(self, bad_dim: object) -> None:
        with pytest.raises(DomainValidationError, match="ImageOutput.width"):
            ImageOutput(media=_sample_image_ref(), width=cast(int, bad_dim))
        with pytest.raises(DomainValidationError, match="ImageOutput.height"):
            ImageOutput(media=_sample_image_ref(), height=cast(int, bad_dim))

    @pytest.mark.parametrize("bad_prompt", [123, True, []])
    def test_image_output_rejects_invalid_revised_prompt(self, bad_prompt: object) -> None:
        with pytest.raises(DomainValidationError, match="ImageOutput.revised_prompt"):
            ImageOutput(media=_sample_image_ref(), revised_prompt=cast(str, bad_prompt))


class TestAudioOutput:
    """Validation and immutability for AudioOutput."""

    def test_valid_audio_output_construction(self) -> None:
        ref = _sample_audio_ref()
        output = AudioOutput(
            media=ref,
            mime_type="audio/mpeg",
            duration_seconds=3.5,
            transcript="Hello world",
        )
        assert output.kind == "audio"
        assert output.media == ref
        assert output.mime_type == "audio/mpeg"
        assert output.duration_seconds == 3.5
        assert output.transcript == "Hello world"
        assert output == AudioOutput(media=ref, duration_seconds=3.5, transcript="Hello world")
        assert hash(output) == hash(AudioOutput(media=ref, duration_seconds=3.5, transcript="Hello world"))

    def test_audio_output_immutability(self) -> None:
        output = AudioOutput(media=_sample_audio_ref())
        with pytest.raises(FrozenInstanceError):
            output.transcript = "mutated"  # type: ignore[misc]

    @pytest.mark.parametrize("bad_media", [None, 456, "uri"])
    def test_audio_output_rejects_invalid_media(self, bad_media: object) -> None:
        with pytest.raises(DomainValidationError, match="AudioOutput.media"):
            AudioOutput(media=cast(MediaSourceRef, bad_media))

    @pytest.mark.parametrize("bad_mime", ["video/mp4", "text/plain", None])
    def test_audio_output_rejects_invalid_mime(self, bad_mime: object) -> None:
        with pytest.raises(DomainValidationError, match="AudioOutput.mime_type"):
            AudioOutput(media=_sample_audio_ref(), mime_type=cast(str, bad_mime))

    @pytest.mark.parametrize("bad_dur", [-1.0, -0.01, "3.5", []])
    def test_audio_output_rejects_invalid_duration(self, bad_dur: object) -> None:
        with pytest.raises(DomainValidationError, match="AudioOutput.duration_seconds"):
            AudioOutput(media=_sample_audio_ref(), duration_seconds=cast(float, bad_dur))

    @pytest.mark.parametrize("bad_transcript", [123, True, {}])
    def test_audio_output_rejects_invalid_transcript(self, bad_transcript: object) -> None:
        with pytest.raises(DomainValidationError, match="AudioOutput.transcript"):
            AudioOutput(media=_sample_audio_ref(), transcript=cast(str, bad_transcript))


class TestVideoOutput:
    """Validation and immutability for VideoOutput."""

    def test_valid_video_output_construction(self) -> None:
        ref = _sample_video_ref()
        output = VideoOutput(
            media=ref,
            mime_type="video/mp4",
            duration_seconds=12.0,
            width=1920,
            height=1080,
        )
        assert output.kind == "video"
        assert output.media == ref
        assert output.mime_type == "video/mp4"
        assert output.duration_seconds == 12.0
        assert output.width == 1920
        assert output.height == 1080
        assert output == VideoOutput(media=ref, duration_seconds=12.0, width=1920, height=1080)
        assert hash(output) == hash(VideoOutput(media=ref, duration_seconds=12.0, width=1920, height=1080))

    def test_video_output_immutability(self) -> None:
        output = VideoOutput(media=_sample_video_ref())
        with pytest.raises(FrozenInstanceError):
            output.duration_seconds = 1.0  # type: ignore[misc]

    @pytest.mark.parametrize("bad_media", [None, 789])
    def test_video_output_rejects_invalid_media(self, bad_media: object) -> None:
        with pytest.raises(DomainValidationError, match="VideoOutput.media"):
            VideoOutput(media=cast(MediaSourceRef, bad_media))

    @pytest.mark.parametrize("bad_mime", ["image/jpeg", None, 123])
    def test_video_output_rejects_invalid_mime(self, bad_mime: object) -> None:
        with pytest.raises(DomainValidationError, match="VideoOutput.mime_type"):
            VideoOutput(media=_sample_video_ref(), mime_type=cast(str, bad_mime))

    @pytest.mark.parametrize("bad_dur", [-5.0, "10", {}])
    def test_video_output_rejects_invalid_duration(self, bad_dur: object) -> None:
        with pytest.raises(DomainValidationError, match="VideoOutput.duration_seconds"):
            VideoOutput(media=_sample_video_ref(), duration_seconds=cast(float, bad_dur))

    @pytest.mark.parametrize("bad_dim", [0, -1, "1920"])
    def test_video_output_rejects_invalid_dimensions(self, bad_dim: object) -> None:
        with pytest.raises(DomainValidationError, match="VideoOutput.width"):
            VideoOutput(media=_sample_video_ref(), width=cast(int, bad_dim))
        with pytest.raises(DomainValidationError, match="VideoOutput.height"):
            VideoOutput(media=_sample_video_ref(), height=cast(int, bad_dim))


class TestMultiPartOutput:
    """Validation and immutability for MultiPartOutput."""

    def test_valid_multipart_output(self) -> None:
        t = TextOutput("Voice caption")
        a = AudioOutput(_sample_audio_ref())
        multi = MultiPartOutput(parts=(t, a))
        assert multi.kind == "multipart"
        assert multi.parts == (t, a)
        assert multi == MultiPartOutput(parts=(t, a))
        assert hash(multi) == hash(MultiPartOutput(parts=(t, a)))

    def test_multipart_immutability(self) -> None:
        multi = MultiPartOutput(parts=(TextOutput("one"),))
        with pytest.raises(FrozenInstanceError):
            multi.parts = ()  # type: ignore[misc]

    @pytest.mark.parametrize("bad_parts", [(), [], None, "text"])
    def test_multipart_rejects_empty_or_non_tuple(self, bad_parts: object) -> None:
        with pytest.raises(DomainValidationError, match="MultiPartOutput.parts"):
            MultiPartOutput(parts=cast(tuple, bad_parts))

    def test_multipart_rejects_invalid_elements(self) -> None:
        with pytest.raises(DomainValidationError, match="MultiPartOutput.parts"):
            MultiPartOutput(parts=cast(tuple, (TextOutput("ok"), "not_an_output")))


class TestInferenceResponseWithMedia:
    """InferenceResponse integration with media outputs."""

    def test_response_accepts_all_output_variants(self) -> None:
        run_id = InferenceRunId("run-multimodal-1")
        img_out = ImageOutput(_sample_image_ref())
        aud_out = AudioOutput(_sample_audio_ref())
        vid_out = VideoOutput(_sample_video_ref())
        multi_out = MultiPartOutput((TextOutput("Look"), img_out))

        resp_img = InferenceResponse(run_id, img_out)
        resp_aud = InferenceResponse(run_id, aud_out)
        resp_vid = InferenceResponse(run_id, vid_out)
        resp_multi = InferenceResponse(run_id, multi_out)

        assert resp_img.output == img_out
        assert resp_aud.output == aud_out
        assert resp_vid.output == vid_out
        assert resp_multi.output == multi_out

    def test_response_rejects_arbitrary_output(self) -> None:
        with pytest.raises(DomainValidationError, match="InferenceResponse.output"):
            InferenceResponse(InferenceRunId("run-bad"), cast(TextOutput, "plain_str"))


class TestUsageExtended:
    """Tests for extended Usage non-token fields."""

    def test_usage_with_media_metrics(self) -> None:
        usage = Usage(
            input_tokens=100,
            output_tokens=50,
            input_characters=450,
            output_media_units=1,
            output_media_seconds=4.5,
        )
        assert usage.input_characters == 450
        assert usage.output_media_units == 1
        assert usage.output_media_seconds == 4.5

    @pytest.mark.parametrize("bad_val", [-1, 1.5, "10", []])
    def test_usage_rejects_invalid_character_and_unit_counts(self, bad_val: object) -> None:
        with pytest.raises(DomainValidationError, match="Usage.input_characters"):
            Usage(input_characters=cast(int, bad_val))
        with pytest.raises(DomainValidationError, match="Usage.output_media_units"):
            Usage(output_media_units=cast(int, bad_val))

    @pytest.mark.parametrize("bad_sec", [-0.5, "4.5", {}])
    def test_usage_rejects_invalid_seconds(self, bad_sec: object) -> None:
        with pytest.raises(DomainValidationError, match="Usage.output_media_seconds"):
            Usage(output_media_seconds=cast(float, bad_sec))


class TestSerializationRoundtrip:
    """Serialization and deserialization round-trip for multimodal outputs."""

    def test_image_output_serialization_roundtrip(self) -> None:
        resp = InferenceResponse(
            InferenceRunId("run-img-001"),
            ImageOutput(
                media=_sample_image_ref(),
                mime_type="image/png",
                width=1024,
                height=1024,
                revised_prompt="Revised prompt",
            ),
            usage=Usage(output_media_units=1),
        )
        data = response_to_dict(resp)
        assert data["output"]["kind"] == "image"
        assert data["output"]["mime_type"] == "image/png"
        assert data["output"]["width"] == 1024
        assert data["usage"]["output_media_units"] == 1

        restored = response_from_dict(data)
        assert restored == resp
        assert response_to_dict(restored) == data

    def test_audio_output_serialization_roundtrip(self) -> None:
        resp = InferenceResponse(
            InferenceRunId("run-aud-001"),
            AudioOutput(
                media=_sample_audio_ref(),
                mime_type="audio/mpeg",
                duration_seconds=5.2,
                transcript="Hello there",
            ),
            usage=Usage(input_characters=11, output_media_seconds=5.2),
        )
        data = response_to_dict(resp)
        assert data["output"]["kind"] == "audio"
        assert data["output"]["duration_seconds"] == 5.2
        assert data["usage"]["input_characters"] == 11
        assert data["usage"]["output_media_seconds"] == 5.2

        restored = response_from_dict(data)
        assert restored == resp
        assert response_to_dict(restored) == data

    def test_video_output_serialization_roundtrip(self) -> None:
        resp = InferenceResponse(
            InferenceRunId("run-vid-001"),
            VideoOutput(
                media=_sample_video_ref(),
                mime_type="video/mp4",
                duration_seconds=10.0,
                width=1280,
                height=720,
            ),
            usage=Usage(output_media_seconds=10.0),
        )
        data = response_to_dict(resp)
        assert data["output"]["kind"] == "video"
        assert data["output"]["width"] == 1280

        restored = response_from_dict(data)
        assert restored == resp
        assert response_to_dict(restored) == data

    def test_multipart_output_serialization_roundtrip(self) -> None:
        resp = InferenceResponse(
            InferenceRunId("run-multi-001"),
            MultiPartOutput(
                parts=(
                    TextOutput("Explication textuelle"),
                    AudioOutput(_sample_audio_ref(), duration_seconds=3.0),
                )
            ),
        )
        data = response_to_dict(resp)
        assert data["output"]["kind"] == "multipart"
        assert len(data["output"]["parts"]) == 2

        restored = response_from_dict(data)
        assert restored == resp
        assert response_to_dict(restored) == data

    def test_multipart_nested_rejection_in_deserialization(self) -> None:
        payload = {
            "schema_version": 1,
            "object_type": "inference_response",
            "run_id": "run-nested",
            "output": {
                "kind": "multipart",
                "parts": [
                    {
                        "kind": "multipart",
                        "parts": [{"kind": "text", "text": "deep"}],
                    }
                ],
            },
            "finish_reason": None,
            "usage": None,
        }
        with pytest.raises(DomainValidationError, match="cannot nest multipart"):
            response_from_dict(payload)

    def test_unsupported_output_kind_rejection(self) -> None:
        payload = {
            "schema_version": 1,
            "object_type": "inference_response",
            "run_id": "run-unknown",
            "output": {"kind": "hologram", "data": "123"},
            "finish_reason": None,
            "usage": None,
        }
        with pytest.raises(DomainValidationError, match="unsupported Inference output kind"):
            response_from_dict(payload)

    def test_run_with_image_output_serialization_roundtrip(self) -> None:
        req = InferenceRequest(
            ModelTarget(ModelId("dall-e-3")),
            (Message(Role.USER, Content((TextContent("draw something"),))),),
        )
        resp = InferenceResponse(
            InferenceRunId("run-777"),
            ImageOutput(_sample_image_ref(), width=1024, height=1024),
        )
        now = datetime(2026, 11, 7, 10, 0, tzinfo=UTC)
        run = InferenceRun(InferenceRunId("run-777"), req).start(now).complete(resp, now)
        data = run_to_dict(run)
        restored = run_from_dict(data)
        assert restored == run
        assert run_to_dict(restored) == data
