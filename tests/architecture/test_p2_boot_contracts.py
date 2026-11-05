"""P2-BOOT fitness functions: verify ADRs and preserve core import boundaries.

These are architecture/document checks, not proof that L2.x is implemented.
"""

import ast
from pathlib import Path

from tests.architecture.guard import forbidden_imports

ROOT = Path(__file__).resolve().parents[2]
ADR_DIR = ROOT / "docs" / "adr"
INTERACTIONS = ROOT / "src" / "pyllmkit" / "domain" / "interactions"


def test_p2_boot_decision_records_exist_and_are_reviewable() -> None:
    for number in range(8, 14):
        candidates = sorted(ADR_DIR.glob(f"ADR-{number:03d}-*.md"))
        assert len(candidates) == 1, f"Expected one ADR-{number:03d}"
        content = candidates[0].read_text(encoding="utf-8")
        for section in (
            "Status:",
            "## Decision",
            "## Alternatives",
            "## Consequences",
            "## Acceptance Tests",
            "## Follow-ups",
        ):
            assert section in content, (candidates[0], section)
        status = next(line for line in content.splitlines() if line.startswith("- **Status:**"))
        assert any(state in status for state in ("PROPOSED", "ACCEPTED", "REVISED"))


def test_interaction_domain_future_imports_remain_provider_free() -> None:
    # The package is intentionally absent at BOOT; once added, this check activates.
    excluded = (
        "pyllmkit.domain.models",
        "pyllmkit.domain.capabilities",
        "pyllmkit.domain.tools",
        "pyllmkit.domain.inference",
    )
    for source in INTERACTIONS.rglob("*.py"):
        assert not forbidden_imports(source), source
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        package = source.parent.relative_to(ROOT / "src").parts
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    parent = package[: len(package) - node.level + 1]
                    base = ".".join((*parent, node.module or ""))
                else:
                    base = node.module or ""
                targets = [base, *(f"{base}.{alias.name}" for alias in node.names)]
            for target in targets:
                assert not any(
                    target == blocked or target.startswith(blocked + ".")
                    for blocked in excluded
                ), (source, target)


def test_p2_contract_and_traceability_are_available() -> None:
    required = (
        "docs/02_PYLLMKIT_PHASE_2_IMPLEMENTATION_PLAN.md",
        "docs/architecture/PHASE_2_INTERACTION_CONTRACTS.md",
        "docs/quality/PHASE_2_TRACEABILITY.md",
        "docs/quality/P2_BOOT_GATE_REVIEW.md",
    )
    for path in required:
        assert (ROOT / path).is_file(), path
