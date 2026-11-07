"""Tests for multimodal CLI attachments (images, audio, video)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.main import app
from pyllmkit.adapters.cli.storage import SqliteRunStore

runner = CliRunner()


@pytest.fixture(autouse=True)
def setup_test_history_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_file = tmp_path / "test_history.db"
    monkeypatch.setenv("PYLLMKIT_HISTORY_DB", str(db_file))


def test_cli_run_with_image_file(tmp_path: Path) -> None:
    img_file = tmp_path / "sample.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\nsamplepngbytes")

    result = runner.invoke(app, ["run", "Que vois-tu ?", "--image", str(img_file), "--model", "gpt-4o"])
    assert result.exit_code == 0
    assert "Modalités" in result.output
    assert "image" in result.output


def test_cli_run_with_url_and_data_uri() -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "Analyse ces images",
            "--image",
            "https://example.org/a.jpg",
            "--image",
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "--model",
            "gpt-4o",
        ],
    )
    assert result.exit_code == 0
    assert "Modalités" in result.output
    assert "image (2)" in result.output


def test_cli_run_with_audio_and_video(tmp_path: Path) -> None:
    audio_file = tmp_path / "voice.wav"
    audio_file.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    video_file = tmp_path / "clip.mp4"
    video_file.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    result = runner.invoke(
        app,
        [
            "run",
            "Analyse l'audio et la vidéo",
            "--audio",
            str(audio_file),
            "--video",
            str(video_file),
            "--model",
            "gemini-2.0-flash",
        ],
    )
    assert result.exit_code == 0
    assert "Modalités" in result.output
    assert "audio" in result.output
    assert "video" in result.output


def test_cli_run_missing_media_file_error() -> None:
    result = runner.invoke(
        app,
        ["run", "Analyse", "--image", "/tmp/this_file_definitely_does_not_exist_12345.png"],
    )
    assert result.exit_code == 2
    assert "Erreur d'attachement multimédia" in result.output
    assert "Fichier multimédia introuvable" in result.output


def test_cli_stream_with_image_file(tmp_path: Path) -> None:
    img_file = tmp_path / "stream_img.jpg"
    img_file.write_bytes(b"\xff\xd8\xff\xe0testjpeg")

    result = runner.invoke(
        app,
        ["stream", "Décris l'image en streaming", "--image", str(img_file), "--model", "gpt-4o"],
    )
    assert result.exit_code == 0
    assert "Modalités" in result.output
    assert "image" in result.output


def test_cli_run_records_multimodal_content_in_store(tmp_path: Path) -> None:
    img_file = tmp_path / "stored.png"
    img_file.write_bytes(b"dummy")

    result = runner.invoke(
        app,
        [
            "run",
            "Message multimodal",
            "--image",
            str(img_file),
            "--record-content",
            "--model",
            "gpt-4o",
        ],
    )
    assert result.exit_code == 0

    store = SqliteRunStore()
    runs = [r for r in store.list_runs(limit=10) if r.prompt == "Message multimodal"]
    assert len(runs) >= 1
    target_run = runs[0]
    assert target_run.messages_json is not None
    parsed = json.loads(target_run.messages_json)
    user_msg = parsed[0]
    assert isinstance(user_msg["content"], list)
    types = [part["type"] for part in user_msg["content"]]
    assert "text" in types
    assert "image" in types


def test_cli_media_input_file_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pyllmkit.adapters.cli.media_input import create_media_source_ref_from_input

    dummy_file = tmp_path / "large.mp4"
    dummy_file.write_bytes(b"content")

    # Mock st_size to be 101 MB
    orig_stat = Path.stat

    def mock_stat(self: Path, *args, **kwargs):
        st = orig_stat(self, *args, **kwargs)
        if self.name == "large.mp4":
            import os

            return os.stat_result((
                st.st_mode,
                st.st_ino,
                st.st_dev,
                st.st_nlink,
                st.st_uid,
                st.st_gid,
                105 * 1024 * 1024,
                st.st_atime,
                st.st_mtime,
                st.st_ctime,
            ))
        return st

    monkeypatch.setattr(Path, "stat", mock_stat)
    with pytest.raises(ValueError, match="trop volumineux"):
        create_media_source_ref_from_input(str(dummy_file))


def test_cli_run_rejects_modality_when_model_is_text_only() -> None:
    result = runner.invoke(
        app,
        ["run", "Regarde", "--image", "https://example.org/a.png", "--model", "o1-mini"],
    )
    assert result.exit_code == 1
    assert "unsupported_input_modality" in result.output


def test_cli_stream_rejects_modality_when_model_is_text_only() -> None:
    result = runner.invoke(
        app,
        ["stream", "Regarde", "--image", "https://example.org/a.png", "--model", "o1-mini"],
    )
    assert result.exit_code == 1
    assert "unsupported_input_modality" in result.output


def test_cli_stream_missing_media_file_error() -> None:
    result = runner.invoke(
        app,
        ["stream", "Écoute", "--audio", "/nonexistent_voice_999.wav"],
    )
    assert result.exit_code == 2
    assert "Erreur d'attachement multimédia" in result.output


