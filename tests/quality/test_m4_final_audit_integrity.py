"""M4: independently guard final gate evidence, ADR adoption and no-release boundary."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
QUALITY = DOCS / "quality"
MAIN_M4_SHA = "92874b2e97bcc130279e244bf1000c65a939d7e5"


def test_final_m4_report_covers_all_fourteen_mandatory_no_go_families() -> None:
    report = (QUALITY / "M4_GATE_REVIEW.md").read_text(encoding="utf-8")
    for number in range(1, 15):
        assert f"| **{number:02d}** |" in report
    for gate in range(6):
        assert f"P4-G{gate}" in report
        assert (QUALITY / f"P4_G{gate}_GATE_REVIEW.md").is_file()
    assert "GO TECHNIQUE AVEC RÉSERVES" in report
    assert "NO-GO" in report
    assert MAIN_M4_SHA in report
    assert "#42093041970" in report
    assert (QUALITY / "P4_POST_IMPLEMENTATION_REVIEW.md").is_file()


def test_eight_adr_are_present_and_accepted_with_qualified_evidence() -> None:
    root = DOCS / "adr"
    for number in range(22, 30):
        matches = list(root.glob(f"ADR-{number:03d}-*.md"))
        assert len(matches) == 1
        body = matches[0].read_text(encoding="utf-8")
        assert "ACCEPTED" in body
        assert "#42079191595" in body


def test_full_phase4_traceability_and_quality_gate_are_archived() -> None:
    register = (QUALITY / "PHASE_4_TRACEABILITY.md").read_text(encoding="utf-8")
    for number in range(1, 41):
        assert f"| {number:03d} |" in register
    assert "| **P4-G5** |" in register
    assert "| **M4** |" in register
    assert MAIN_M4_SHA in register
    assert "PENDING SHA" not in register
    precheck = (QUALITY / "M4_READINESS_PRECHECK.md").read_text(encoding="utf-8")
    assert "Clôturé" in precheck
    assert "M4_GATE_REVIEW.md" in precheck


def test_no_release_and_coverage_gate_are_enforced_by_source_metadata() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = config["project"]
    assert project["name"] == "pyllmkit"
    assert project["version"] == "0.1.0a2"
    assert project["dependencies"] == []
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "--cov-fail-under=95" in workflow
    for forbidden in ("twine upload", "gh release create", "pypa/gh-action-pypi-publish"):
        assert forbidden not in workflow
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "docs/quality/M4_GATE_REVIEW.md" in readme
    assert "docs/quality/M4_GATE_REVIEW.md" in roadmap
    assert "NO-GO" in readme
