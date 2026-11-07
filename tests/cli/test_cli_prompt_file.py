"""Prompt files (--prompt-file / @path) for generate and run commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.commands import generate as generate_mod
from pyllmkit.adapters.cli.main import app
from pyllmkit.adapters.cli.prompt_file import (
    PromptFileError,
    load_prompt_file,
    parse_prompt_document,
    resolve_prompt,
)

runner = CliRunner()
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


@pytest.fixture(autouse=True)
def isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYLLMKIT_HISTORY_DB", str(tmp_path / "history.db"))
    monkeypatch.setenv("PYLLMKIT_ASSETS_DIR", str(tmp_path / "assets"))


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    def fake(prompt: str, model: str, mock: bool, output_file: str | None, options: Any,
             record_content: bool, expected_kind: str | None = None) -> None:
        seen.update(prompt=prompt, model=model, options=options, kind=expected_kind)

    monkeypatch.setattr(generate_mod, "_execute_generation", fake)
    return seen


def _write(tmp_path: Path, content: str, name: str = "p.md") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


# --------------------------------------------------------------------- parsing
def test_front_matter_and_comments_are_not_sent() -> None:
    doc = parse_prompt_document(
        "---\nmodel: gpt-image-2\naspect-ratio: 16:9\nduration: 6s\n---\n<!-- note -->\n# Titre\nCorps\n"
    )
    assert doc.text == "# Titre\nCorps"
    assert doc.settings == {"model": "gpt-image-2", "aspect_ratio": "16:9", "duration": 6}


def test_plain_file_without_front_matter() -> None:
    doc = parse_prompt_document("﻿Un simple prompt\n\n")
    assert doc.text == "Un simple prompt" and doc.settings == {}


@pytest.mark.parametrize(
    ("raw", "fragment"),
    [
        ("---\nmodle: x\n---\nhello", "inconnue"),
        ("---\nduration: long\n---\nhello", "entier"),
        ("---\ninstructions:\n  a: b\n---\nhello", "valeur simple"),
    ],
)
def test_invalid_front_matter(raw: str, fragment: str) -> None:
    with pytest.raises(PromptFileError, match=fragment):
        parse_prompt_document(raw)


def test_load_errors(tmp_path: Path) -> None:
    with pytest.raises(PromptFileError, match="introuvable"):
        load_prompt_file(tmp_path / "absent.md")
    bad = tmp_path / "latin1.md"
    bad.write_bytes("caf\xe9".encode("latin-1"))
    with pytest.raises(PromptFileError, match="UTF-8"):
        load_prompt_file(bad)


def test_resolve_combines_file_and_argument(tmp_path: Path) -> None:
    path = _write(tmp_path, "Style de base")
    assert resolve_prompt("Sujet : chat", str(path)).text == "Style de base\n\nSujet : chat"
    assert resolve_prompt(f"@{path}", None).text == "Style de base"
    assert resolve_prompt("texte direct", None).text == "texte direct"
    with pytest.raises(PromptFileError, match="vide"):
        resolve_prompt(None, None)
    with pytest.raises(PromptFileError, match="vide"):
        resolve_prompt(None, str(_write(tmp_path, "---\nmodel: x\n---\n<!-- rien -->", "empty.md")))


# --------------------------------------------------------------------- CLI precedence
def test_front_matter_fills_options_and_model(tmp_path: Path, captured: dict[str, Any]) -> None:
    path = _write(tmp_path, "---\nmodel: gemini-2.5-flash-image\naspect_ratio: 16:9\n---\nUn phare")
    result = runner.invoke(app, ["generate", "image", "-f", str(path)])
    assert result.exit_code == 0, result.output
    assert captured["prompt"] == "Un phare"
    assert captured["model"] == "gemini-2.5-flash-image"
    assert captured["options"].aspect_ratio == "16:9"


def test_cli_options_override_front_matter(tmp_path: Path, captured: dict[str, Any]) -> None:
    path = _write(tmp_path, "---\nmodel: gemini-2.5-flash-image\naspect_ratio: 16:9\n---\nUn phare")
    result = runner.invoke(
        app, ["generate", "image", "-f", str(path), "-m", "gpt-image-1-mini", "--aspect-ratio", "1:1"],
    )
    assert result.exit_code == 0, result.output
    assert captured["model"] == "gpt-image-1-mini"
    assert captured["options"].aspect_ratio == "1:1"


def test_default_model_when_none_given(tmp_path: Path, captured: dict[str, Any]) -> None:
    result = runner.invoke(app, ["generate", "video", f"@{_write(tmp_path, 'Une vague')}"])
    assert result.exit_code == 0, result.output
    assert captured["model"] == generate_mod.DEFAULT_VIDEO_MODEL
    assert captured["kind"] == "video"


def test_irrelevant_settings_are_reported_and_ignored(tmp_path: Path, captured: dict[str, Any]) -> None:
    path = _write(tmp_path, "---\nvoice: Kore\nduration: 5\n---\nBonjour")
    result = runner.invoke(app, ["generate", "audio", "-f", str(path)], env={"COLUMNS": "200"})
    assert result.exit_code == 0, result.output
    assert "Réglages ignorés" in result.output and "duration" in result.output
    assert captured["options"].voice == "Kore"
    assert captured["options"].duration_seconds is None


def test_out_of_range_duration_from_file(tmp_path: Path, captured: dict[str, Any]) -> None:
    path = _write(tmp_path, "---\nduration: 40\n---\nUne vague")
    result = runner.invoke(app, ["generate", "video", "-f", str(path)])
    assert result.exit_code == 2
    assert "invalid_prompt_file" in result.output
    assert not captured


def test_missing_prompt_file_exit_code(captured: dict[str, Any]) -> None:
    result = runner.invoke(app, ["generate", "image", "-f", "nope/absent.md"], env={"COLUMNS": "200"})
    assert result.exit_code == 2
    assert "introuvable" in result.output


# --------------------------------------------------------------------- end to end (mock)
@pytest.mark.parametrize(
    ("kind", "rel"),
    [
        ("image", "images/affiche_salon_tech.md"),
        ("audio", "audios/annonce_accueil.md"),
        ("video", "videos/teaser_produit.md"),
    ],
)
def test_bundled_example_prompts_run_offline(kind: str, rel: str, tmp_path: Path) -> None:
    out = tmp_path / f"out.{kind}"
    result = runner.invoke(app, ["generate", kind, "-f", str(PROMPTS_DIR / rel), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists() and out.stat().st_size > 0


def test_run_accepts_prompt_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "---\nmodel: gpt-image-2\n---\nRésume ce texte")
    result = runner.invoke(app, ["run", "-f", str(path)], env={"COLUMNS": "200"})
    assert result.exit_code == 0, result.output
    assert "ignoré par 'run'" in result.output
