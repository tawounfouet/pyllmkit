"""Architecture boundary regression checks."""

from pathlib import Path

from tests.architecture.guard import forbidden_imports, is_forbidden

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOMAIN_ROOT = PROJECT_ROOT / "src" / "pyllmkit" / "domain"


def test_domain_has_no_known_forbidden_imports() -> None:
    violations: list[str] = []
    for path in DOMAIN_ROOT.rglob("*.py"):
        violations.extend(forbidden_imports(path))
    assert not violations, "Forbidden domain imports:\n" + "\n".join(violations)


def test_guard_rejects_known_provider_imports() -> None:
    assert is_forbidden("openai")
    assert is_forbidden("requests.sessions")
    assert is_forbidden("pyllmkit.providers.anthropic")
    assert not is_forbidden("pyllmkit.domain.models")
