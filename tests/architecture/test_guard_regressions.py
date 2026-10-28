"""Negative tests proving that the architecture guard actually rejects bad code."""

from pathlib import Path

import pytest

from tests.architecture.guard import forbidden_imports, is_forbidden


def _write_domain_module(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "src" / "pyllmkit" / "domain" / "models" / "bad.py"
    path.parent.mkdir(parents=True)
    path.write_text(body, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "module",
    [
        "openai", "openai.resources", "anthropic", "google.genai",
        "requests.sessions", "http.client", "urllib.request", "socket",
        "os", "subprocess", "pyllmkit.providers.example",
        "pyllmkit.infrastructure", "pyllmkit.facade",
    ],
)
def test_forbidden_module_registry_matches_known_imports(module: str) -> None:
    assert is_forbidden(module)


@pytest.mark.parametrize(
    "source",
    [
        "import openai\n",
        "from anthropic import Client\n",
        "from ...providers import openai\n",
        "from ... import providers\n",
        "from pyllmkit.infrastructure import adapters\n",
        "import importlib\nclient = importlib.import_module('openai')\n",
        "from importlib import import_module\nclient = import_module('anthropic')\n",
        "client = __import__('requests')\n",
        "from os import environ\n",
    ],
)
def test_forbidden_imports_are_detected(tmp_path: Path, source: str) -> None:
    path = _write_domain_module(tmp_path, source)
    assert forbidden_imports(path), source


def test_allowed_domain_imports_remain_legal(tmp_path: Path) -> None:
    source = (
        "from dataclasses import dataclass\n"
        "from ..errors import DomainValidationError\n"
        "from pyllmkit.domain.capabilities import CapabilitySet\n"
    )
    assert forbidden_imports(_write_domain_module(tmp_path, source)) == []


def test_exact_prefix_not_substring(tmp_path: Path) -> None:
    assert not is_forbidden("requests_like")
    assert forbidden_imports(_write_domain_module(tmp_path, "import requests_like\n")) == []


def test_relative_guard_uses_innermost_package_when_repo_repeats_name(
    tmp_path: Path,
) -> None:
    """GitHub Actions uses a repo path such as pyllmkit/pyllmkit/src/pyllmkit."""
    path = (
        tmp_path / "pyllmkit" / "pyllmkit" / "src"
        / "pyllmkit" / "domain" / "models" / "bad.py"
    )
    path.parent.mkdir(parents=True)
    path.write_text("from ...providers import openai\n", encoding="utf-8")
    assert forbidden_imports(path), "relative import must resolve against inner package"
