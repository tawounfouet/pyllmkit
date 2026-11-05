"""G5 documentation gate: real paths, runnable examples and no release implication."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DOC_PATHS = (
    "docs/architecture/PHASE_3_INFERENCE_CONTRACTS.md",
    "docs/architecture/INFERENCE_JSON_SCHEMA_V1.md",
    "docs/concepts/inference-request.md",
    "docs/concepts/inference-response.md",
    "docs/concepts/inference-run.md",
    "docs/api/inference.md",
    "docs/quality/PHASE_3_TRACEABILITY.md",
    "docs/api/inference-request.md",
    "docs/api/inference-response.md",
    "docs/api/inference-run.md",
    "docs/api/inference-json-v1.md",
)


def test_all_approved_l35_documentation_artifacts_exist() -> None:
    for relative in DOC_PATHS:
        path = ROOT / relative
        assert path.is_file(), f"missing approved L3.5 artifact: {relative}"
        assert path.read_text(encoding="utf-8").startswith("#")


def test_readme_links_to_all_four_domain_api_components() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for relative in (
        "docs/api/inference-request.md",
        "docs/api/inference-response.md",
        "docs/api/inference-run.md",
        "docs/api/inference-json-v1.md",
        "docs/api/inference.md",
        "docs/quality/PHASE_3_TRACEABILITY.md",
    ):
        assert f"]({relative})" in readme


def test_regular_ci_has_no_release_or_publish_job() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "python -m build" in workflow
    assert "examples/11_round_trip_inference_json.py" in workflow
    assert "examples/12_full_inference_walkthrough.py" in workflow
    assert "python -m pytest" in workflow
    assert "twine upload" not in workflow
    assert "pypa/gh-action-pypi-publish" not in workflow
    assert "gh release create" not in workflow
