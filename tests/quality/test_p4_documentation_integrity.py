"""L4.5 documentation integrity, real artifacts, and CI/publication separation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DOCS = (
    "docs/architecture/PHASE_4_TOOLING_AND_STRUCTURED_OUTPUT_CONTRACTS.md",
    "docs/architecture/TOOLING_JSON_SCHEMA_V1.md",
    "docs/concepts/tool-definition.md",
    "docs/concepts/tool-call.md",
    "docs/concepts/structured-output.md",
    "docs/api/tooling.md",
    "docs/api/tool-calling.md",
    "docs/api/structured-output.md",
    "docs/api/tooling-serialization.md",
    "docs/quality/PHASE_4_TRACEABILITY.md",
    "docs/quality/M4_READINESS_PRECHECK.md",
    "docs/quality/P4_G5_GATE_REVIEW.md",
)


def test_phase4_documentation_artifacts_exist() -> None:
    for relative in DOCS:
        path = ROOT / relative
        assert path.is_file(), f"missing Phase 4 artifact: {relative}"
        content = path.read_text(encoding="utf-8")
        assert content.startswith("#"), f"missing header: {relative}"
        assert len(content) >= 120, f"document unexpectedly short: {relative}"


def test_readme_links_to_phase4_concepts_api_and_quality() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for relative in DOCS[:10]:
        assert f"]({relative})" in readme, f"README link absent: {relative}"
    assert "P4-G4" in readme and "P4-G5" in readme
    assert "non qualifié" in readme.lower()
    assert "0.1.0a2" in readme


def test_ci_runs_13_through_17_and_never_publishes() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    examples = (
        "13_define_tools.py",
        "14_define_tool_call_and_result.py",
        "15_validate_structured_output.py",
        "16_tooling_json_round_trip.py",
        "17_full_tooling_walkthrough.py",
    )
    for name in examples:
        assert f"python examples/{name}" in ci
        assert f".venv-wheel/bin/python examples/{name}" in ci
        assert f".venv-sdist/bin/python examples/{name}" in ci
        assert (ROOT / "examples" / name).is_file()
    assert "python -m build" in ci
    assert "pypa/gh-action-pypi-publish" not in ci
    assert "twine upload" not in ci
    assert "gh release create" not in ci


def test_phase4_concept_relative_links_are_real() -> None:
    docs = ROOT / "docs" / "concepts"
    for name in ("tool-definition.md", "tool-call.md", "structured-output.md"):
        body = (docs / name).read_text(encoding="utf-8")
        for line in body.splitlines():
            for item in line.split("](")[1:]:
                raw = item.split(")", 1)[0]
                if raw.startswith(("http:", "https:", "#")):
                    continue
                assert (docs / raw).is_file(), f"broken link: {name} -> {raw}"
