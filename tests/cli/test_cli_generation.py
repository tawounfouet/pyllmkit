"""Tests for multimodal media saver and 'pyllmkit generate' CLI commands."""

from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.main import app
from pyllmkit.adapters.cli.media_saver import get_default_asset_path, save_output_media
from pyllmkit.domain.inference import (
    AudioOutput,
    ImageOutput,
    MultiPartOutput,
    TextOutput,
    VideoOutput,
)
from pyllmkit.domain.interactions import MediaSourceRef

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolate_history_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_db = tmp_path / "test_history.db"
    monkeypatch.setenv("PYLLMKIT_HISTORY_DB", str(test_db))


class TestMediaSaver:
    """Unit tests for media_saver.save_output_media."""

    def test_save_text_output(self, tmp_path: Path) -> None:
        target = tmp_path / "output.txt"
        out = TextOutput("Texte généré")
        result = save_output_media(out, target)
        assert result == target
        assert target.read_text(encoding="utf-8") == "Texte généré"

    def test_save_data_uri_image(self, tmp_path: Path) -> None:
        target = tmp_path / "subfolder" / "image.png"
        ref = MediaSourceRef(
            "data",
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        )
        out = ImageOutput(ref)
        result = save_output_media(out, target)
        assert result == target
        assert target.exists()
        assert len(target.read_bytes()) > 10

    def test_save_file_reference(self, tmp_path: Path) -> None:
        src = tmp_path / "source.wav"
        src.write_bytes(b"RIFFdummydata")
        target = tmp_path / "copied.wav"

        out = AudioOutput(MediaSourceRef("file", str(src)))
        result = save_output_media(out, target)
        assert result == target
        assert target.read_bytes() == b"RIFFdummydata"

    def test_save_file_reference_missing_raises_file_not_found(self, tmp_path: Path) -> None:
        missing_src = tmp_path / "missing.wav"
        out = AudioOutput(MediaSourceRef("file", str(missing_src)))
        with pytest.raises(FileNotFoundError):
            save_output_media(out, tmp_path / "dst.wav")

    def test_save_uri_refuses_untrusted_remote_download(self, tmp_path: Path) -> None:
        target = tmp_path / "downloaded.mp4"
        out = VideoOutput(MediaSourceRef("uri", "https://example.org/sample.mp4"))
        with (
            patch("urllib.request.urlopen", side_effect=AssertionError("No network permitted")),
            pytest.raises(ValueError, match="distant direct interdit"),
        ):
            save_output_media(out, target)
        assert not target.exists()


    def test_save_multipart_output(self, tmp_path: Path) -> None:
        target = tmp_path / "extracted_media.png"
        ref = MediaSourceRef(
            "data",
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        )
        multi = MultiPartOutput((TextOutput("Aperçu"), ImageOutput(ref)))
        result = save_output_media(multi, target)
        assert result == target
        assert target.exists()

    def test_save_multipart_text_only(self, tmp_path: Path) -> None:
        target = tmp_path / "all_text.txt"
        multi = MultiPartOutput((TextOutput("Premier"), TextOutput("Second")))
        result = save_output_media(multi, target)
        assert result == target
        assert target.read_text(encoding="utf-8") == "Premier"

    def test_invalid_data_uri_format_raises_error(self, tmp_path: Path) -> None:
        # Construct an object that bypasses domain validation to test defensive branch
        mock_out = MagicMock(spec=ImageOutput)
        mock_out.media = MagicMock(kind="data", value="corrupt_no_comma")
        with pytest.raises(ValueError, match="Format de Data URI invalide"):
            save_output_media(mock_out, tmp_path / "bad.png")

    def test_invalid_base64_is_rejected_without_creating_asset(self, tmp_path: Path) -> None:
        target = tmp_path / "bad.png"
        output = ImageOutput(MediaSourceRef("data", "data:image/png;base64,???"))
        with pytest.raises(ValueError, match="base64 invalide"):
            save_output_media(output, target)
        assert not target.exists()

    def test_media_bytes_cap_is_enforced(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("pyllmkit.adapters.cli.media_saver.MAX_MEDIA_DOWNLOAD_BYTES", 3)
        output = ImageOutput(MediaSourceRef("data", "data:image/png;base64,YWJjZA=="))
        target = tmp_path / "oversized.png"
        with pytest.raises(ValueError, match="volumineux"):
            save_output_media(output, target)
        assert not target.exists()

    def test_unsupported_media_kind_raises_error(self, tmp_path: Path) -> None:
        mock_out = MagicMock(spec=ImageOutput)
        mock_out.media = MagicMock(kind="asset", value="opaque-id")
        with pytest.raises(ValueError, match="non matérialisable"):
            save_output_media(mock_out, tmp_path / "asset.png")

    def test_unsupported_output_type_raises_error(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Type de sortie d'inférence non convertible"):
            save_output_media(cast(object, "plain_string"), tmp_path / "err.txt")  # type: ignore[arg-type]


class TestCliGenerateCommands:
    """End-to-end tests for pyllmkit generate subcommands."""

    def test_unexpected_generation_exception_does_not_echo_credentials(self) -> None:
        with patch(
            "pyllmkit.adapters.cli.commands.generate.create_cli_inference_service"
        ) as service_factory:
            service_factory.return_value.invoke.side_effect = RuntimeError(
                "unexpected failure with sk-proj-VERYPRIVATE123456789"
            )
            result = runner.invoke(app, ["generate", "image", "Une montagne"])
        assert result.exit_code == 2
        assert "VERYPRIVATE" not in result.stdout
        assert "Détails masqués" in result.stdout

    def test_generate_image_command_with_out(self, tmp_path: Path) -> None:
        out_file = tmp_path / "generated_cat.png"
        result = runner.invoke(
            app,
            ["generate", "image", "Un chat sur Mars", "--model", "dall-e-3", "--out", str(out_file)],
        )
        assert result.exit_code == 0
        assert "Image générée avec succès" in result.stdout
        assert "1024x1024" in result.stdout
        assert "$0.0400" not in result.stdout  # retired price is not a current quote
        assert "Fichier sauvegardé avec succès" in result.stdout
        assert out_file.exists()

    def test_generate_audio_command_with_out(self, tmp_path: Path) -> None:
        out_file = tmp_path / "speech.wav"
        result = runner.invoke(
            app,
            ["generate", "audio", "Bienvenue chez Seqens", "--model", "tts-1", "--out", str(out_file)],
        )
        assert result.exit_code == 0
        assert "Audio généré avec succès" in result.stdout
        assert "2.0 s" in result.stdout
        assert "caractères" in result.stdout
        assert "Fichier sauvegardé avec succès" in result.stdout
        assert out_file.exists()

    def test_generate_video_command_with_out(self, tmp_path: Path) -> None:
        out_file = tmp_path / "ocean.mp4"
        result = runner.invoke(
            app,
            ["generate", "video", "Une vague géante", "--model", "veo-2", "--out", str(out_file)],
        )
        assert result.exit_code == 0
        assert "Vidéo générée avec succès" in result.stdout
        assert "5.0 s" in result.stdout
        assert "1280x720" in result.stdout
        assert "$0.7500" not in result.stdout  # retired Veo has no operational price
        assert "Fichier sauvegardé avec succès" in result.stdout
        assert out_file.exists()

    def test_generate_unknown_model_fails_gracefully(self) -> None:
        result = runner.invoke(
            app,
            ["generate", "image", "Test", "--model", "nonexistent-model-xyz"],
        )
        assert result.exit_code == 1
        assert "Échec d'exécution" in result.stdout or "Erreur" in result.stdout

    def test_run_command_with_output_file_flag(self, tmp_path: Path) -> None:
        out_img = tmp_path / "run_image.png"
        result = runner.invoke(
            app,
            ["run", "Un aigle", "--model", "dall-e-3", "-o", str(out_img)],
        )
        assert result.exit_code == 0
        assert "Image générée avec succès" in result.stdout
        assert "Fichier sauvegardé avec succès" in result.stdout
        assert out_img.exists()

    def test_get_default_asset_path_resolution(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        assets_dir = tmp_path / "custom_assets"
        monkeypatch.setenv("PYLLMKIT_ASSETS_DIR", str(assets_dir))

        img = ImageOutput(MediaSourceRef("data", "data:image/png;base64,AAAA"))
        p_img = get_default_asset_path(img, run_id="12345678abcdef", model_name="dall-e-3")
        assert p_img.parent == assets_dir / "images"
        assert p_img.name.startswith("dall-e-3_")
        assert p_img.name.endswith(".png")

        audio = AudioOutput(MediaSourceRef("data", "data:audio/wav;base64,AAAA"))
        p_audio = get_default_asset_path(audio, run_id="12345678abcdef", model_name="tts-1")
        assert p_audio.parent == assets_dir / "audios"
        assert p_audio.name.startswith("tts-1_")
        assert p_audio.name.endswith(".wav")

        video = VideoOutput(MediaSourceRef("data", "data:video/mp4;base64,AAAA"))
        p_video = get_default_asset_path(video, run_id="12345678abcdef", model_name="veo-2")
        assert p_video.parent == assets_dir / "videos"
        assert p_video.name.startswith("veo-2_")
        assert p_video.name.endswith(".mp4")

        text = TextOutput("document text")
        p_text = get_default_asset_path(text, run_id="12345678abcdef", model_name="gpt-4o")
        assert p_text.parent == assets_dir / "documents"
        assert p_text.name.endswith(".txt")

        multi = MultiPartOutput((TextOutput("title"), img))
        p_multi = get_default_asset_path(multi, run_id="12345678abcdef", model_name="gpt-4o")
        assert p_multi.parent == assets_dir / "images"

    def test_generate_image_command_default_assets_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        assets_dir = tmp_path / "auto_assets"
        monkeypatch.setenv("PYLLMKIT_ASSETS_DIR", str(assets_dir))
        result = runner.invoke(
            app,
            ["generate", "image", "Un lion céleste", "--model", "dall-e-3"],
        )
        assert result.exit_code == 0
        assert "Image générée avec succès" in result.stdout
        assert "Fichier sauvegardé avec succès" in result.stdout
        assert (assets_dir / "images").exists()
        images = list((assets_dir / "images").glob("dall-e-3_*.png"))
        assert len(images) == 1

    def test_generate_audio_command_default_assets_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        assets_dir = tmp_path / "auto_assets"
        monkeypatch.setenv("PYLLMKIT_ASSETS_DIR", str(assets_dir))
        result = runner.invoke(
            app,
            ["generate", "audio", "Notification de fin de calcul", "--model", "tts-1"],
        )
        assert result.exit_code == 0
        assert "Audio généré avec succès" in result.stdout
        assert "Fichier sauvegardé avec succès" in result.stdout
        assert (assets_dir / "audios").exists()
        audios = list((assets_dir / "audios").glob("tts-1_*.wav"))
        assert len(audios) == 1

    def test_run_media_command_default_assets_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        assets_dir = tmp_path / "auto_assets"
        monkeypatch.setenv("PYLLMKIT_ASSETS_DIR", str(assets_dir))
        result = runner.invoke(
            app,
            ["run", "Dessine un château médiéval", "--model", "dall-e-3"],
        )
        assert result.exit_code == 0
        assert "Image générée avec succès" in result.stdout
        assert "Fichier sauvegardé avec succès" in result.stdout
        assert (assets_dir / "images").exists()
        images = list((assets_dir / "images").glob("dall-e-3_*.png"))
        assert len(images) == 1
