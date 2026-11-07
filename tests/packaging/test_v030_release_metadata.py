"""Pin the owner-authorized v0.3.0 source-tag metadata without live calls."""

import tomllib
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_v030_release_version_matches_installed_metadata() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["name"] == "pyllmkit"
    assert project["project"]["version"] == "0.3.0"
    assert version("pyllmkit") == "0.3.0"


def test_v030_git_tag_scope_is_documented() -> None:
    notes = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    decision = (
        ROOT / "docs/milestones/0.3.0/18_V030_TAG_SCOPE_AND_AUTHORIZATION_2026-11-07.md"
    ).read_text(encoding="utf-8")
    assert "## [0.3.0] - 2026-11-07" in notes
    assert "AUTHORIZATION: GIT_TAG_v0.3.0_ONLY" in decision
    assert "provider-live" in readme
    assert "PyPI" in notes and "PyPI" in decision
