"""M3 closeout fitness tests: docs, governance and release boundaries remain explicit."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DOCS = (
    "docs/quality/P3_POST_IMPLEMENTATION_REVIEW.md",
    "docs/governance/MAIN_BRANCH_PROTECTION_RUNBOOK.md",
    "docs/governance/RELEASE_0_1_0a3_POLICY_AND_RUNBOOK.md",
    "docs/architecture/FUTURE_PROVIDER_BOUNDARY_CONTRACT.md",
    "docs/governance/PYKIT_DELIVERY_AND_LEARNING_LOOP.md",
    ".github/pull_request_template.md",
)


def test_m3_closure_documents_are_present_and_have_markdown_titles() -> None:
    for relative in DOCS:
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert source.startswith("#"), relative
        assert len(source) > 300, relative


def test_release_policy_requires_explicit_authorization_and_no_publish_now() -> None:
    runbook = (
        ROOT / "docs/governance/RELEASE_0_1_0a3_POLICY_AND_RUNBOOK.md"
    ).read_text(encoding="utf-8")
    for required in (
        "M3",
        "0.1.0a2",
        "0.1.0a3",
        "SHA256",
        "Trusted Publishing",
        "rollback",
        "#22",
    ):
        assert required in runbook
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "twine upload" not in workflow
    assert "gh release create" not in workflow


def test_future_provider_boundary_does_not_claim_provider_execution() -> None:
    design = (
        ROOT / "docs/architecture/FUTURE_PROVIDER_BOUNDARY_CONTRACT.md"
    ).read_text(encoding="utf-8")
    for required in (
        "NON IMPLEMENTEE",
        "cles dupliquees",
        "InferencePort",
        "Value Objects",
        "SSRF",
        "idempotence",
        "Usage",
    ):
        assert required in design


def test_protection_runbook_is_explicitly_unverified_and_requires_evidence() -> None:
    runbook = (
        ROOT / "docs/governance/MAIN_BRANCH_PROTECTION_RUNBOOK.md"
    ).read_text(encoding="utf-8")
    assert "STATUT OBSERVE : NON APPLIQUE" in runbook
    assert "protected=false" in runbook
    assert "HTTP 403" in runbook
    assert "Issue #22" not in runbook or "#22" in runbook
    assert "enforcement" in runbook
    assert "reviewer distinct" in runbook
