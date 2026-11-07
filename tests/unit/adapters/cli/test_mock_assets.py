"""Unit tests for standalone mock media generators (PNG, WAV, MP4)."""

import base64

from pyllmkit.adapters.cli.mock_assets import (
    create_mock_mp4,
    create_mock_png,
    create_mock_wav,
)


def test_create_mock_png_valid_structure() -> None:
    uri = create_mock_png(128, 128)
    assert uri.startswith("data:image/png;base64,")
    _, b64 = uri.split(",", 1)
    raw = base64.b64decode(b64)
    # Check PNG magic bytes
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    # Check IEND chunk
    assert b"IEND" in raw
    assert len(raw) > 500


def test_create_mock_wav_valid_structure() -> None:
    uri = create_mock_wav(duration=1.0, sample_rate=11025)
    assert uri.startswith("data:audio/wav;base64,")
    _, b64 = uri.split(",", 1)
    raw = base64.b64decode(b64)
    # Check RIFF and WAVE header
    assert raw.startswith(b"RIFF")
    assert b"WAVE" in raw[:16]
    assert b"fmt " in raw[:24]
    assert b"data" in raw
    assert len(raw) > 1000


def test_create_mock_mp4_valid_structure() -> None:
    uri = create_mock_mp4()
    assert uri.startswith("data:video/mp4;base64,")
    _, b64 = uri.split(",", 1)
    raw = base64.b64decode(b64)
    # Check MP4 ftyp and moov atoms
    assert b"ftyp" in raw[:32]
    assert b"moov" in raw
    assert len(raw) > 2000

