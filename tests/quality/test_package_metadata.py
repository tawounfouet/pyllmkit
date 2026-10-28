"""P1 packaging and dependency assertions; no unapproved provider requirements."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_runtime_has_no_mandatory_provider_sdk_dependency() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["dependencies"] == []
    assert pyproject["project"]["requires-python"] == ">=3.11"


def test_typing_marker_is_present() -> None:
    assert (ROOT / "src" / "pyllmkit" / "py.typed").exists()


def test_pyproject_alpha_version_is_not_claimed_published() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == "0.1.0a1"
