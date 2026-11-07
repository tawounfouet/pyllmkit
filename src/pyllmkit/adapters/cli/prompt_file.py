"""Load detailed prompts from Markdown/text files for CLI commands.

A prompt file is plain UTF-8 text (typically ``prompts/*.md``) with an optional
YAML front matter block holding generation settings::

    ---
    model: gemini-2.5-flash-image
    aspect_ratio: 16:9
    ---
    # Affiche
    Une affiche rétro...

Rules:
- the front matter is never sent to the model;
- HTML comments (``<!-- ... -->``) are stripped, so authors can annotate freely;
- explicit CLI options always win over front matter values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import _parse_simple_yaml

MAX_PROMPT_FILE_BYTES = 1_000_000
_FRONT_MATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

# Front matter keys accepted for generation settings (hyphen or underscore).
SETTING_KEYS = frozenset({
    "model", "size", "quality", "aspect_ratio", "resolution",
    "voice", "instructions", "duration",
})


class PromptFileError(ValueError):
    """Raised when a prompt file cannot be used."""


@dataclass(frozen=True, slots=True)
class PromptDocument:
    """Prompt text plus the settings declared in its front matter."""

    text: str
    settings: dict[str, Any] = field(default_factory=dict)
    source: Path | None = None


def parse_prompt_document(raw: str, source: Path | None = None) -> PromptDocument:
    settings: dict[str, Any] = {}
    body = raw.lstrip("﻿")
    match = _FRONT_MATTER.match(body)
    if match:
        parsed = _parse_simple_yaml(match.group(1))
        for key, value in parsed.items():
            norm = str(key).strip().lower().replace("-", "_")
            if norm not in SETTING_KEYS:
                raise PromptFileError(
                    f"Clé d'en-tête inconnue '{key}' dans {source or 'le prompt'} "
                    f"(autorisées : {', '.join(sorted(SETTING_KEYS))})"
                )
            if isinstance(value, dict):
                raise PromptFileError(f"La clé '{key}' doit avoir une valeur simple")
            settings[norm] = value
        body = body[match.end():]
    if "duration" in settings:
        try:
            settings["duration"] = int(str(settings["duration"]).rstrip("s"))
        except ValueError:
            raise PromptFileError("'duration' doit être un nombre entier de secondes") from None
    text = _HTML_COMMENT.sub("", body).strip()
    return PromptDocument(text=text, settings=settings, source=source)


def load_prompt_file(path: str | Path) -> PromptDocument:
    file = Path(path).expanduser()
    if not file.is_file():
        raise PromptFileError(f"Fichier prompt introuvable : {file}")
    if file.stat().st_size > MAX_PROMPT_FILE_BYTES:
        raise PromptFileError(f"Fichier prompt trop volumineux (> {MAX_PROMPT_FILE_BYTES // 1000} ko) : {file}")
    try:
        raw = file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise PromptFileError(f"Le fichier prompt doit être encodé en UTF-8 : {file}") from None
    return parse_prompt_document(raw, source=file.resolve())


def resolve_prompt(prompt: str | None, prompt_file: str | None) -> PromptDocument:
    """Combine the positional prompt and/or a prompt file.

    - file only: the file body is the prompt;
    - argument only: unchanged behaviour (``@chemin.md`` is a shortcut for ``--prompt-file``);
    - both: the argument is appended to the file body as a complement.
    """
    if prompt is not None and prompt.startswith("@") and prompt_file is None and len(prompt) > 1:
        prompt_file, prompt = prompt[1:], None

    doc = load_prompt_file(prompt_file) if prompt_file else PromptDocument(text="")
    extra = (prompt or "").strip()
    text = f"{doc.text}\n\n{extra}".strip() if doc.text and extra else (doc.text or extra)
    if not text:
        raise PromptFileError("Prompt vide : fournissez un texte ou un fichier via --prompt-file")
    return PromptDocument(text=text, settings=doc.settings, source=doc.source)
