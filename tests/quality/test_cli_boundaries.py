"""Static architecture checks for CLI layer boundaries."""

import ast
from pathlib import Path

FORBIDDEN_IN_DOMAIN = {"typer", "rich", "click", "prompt_toolkit"}
FORBIDDEN_IN_APPLICATION = {"typer", "rich", "click", "prompt_toolkit"}


def _collect_module_imports(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(node.module.split(".")[0])
    return imported_modules


def test_cli_dependencies_banned_from_domain() -> None:
    """Domain layer must have zero awareness of typer or rich."""
    src_dir = Path(__file__).parent.parent.parent / "src" / "pyllmkit" / "domain"
    for py_file in src_dir.rglob("*.py"):
        imports = _collect_module_imports(py_file)
        violations = imports.intersection(FORBIDDEN_IN_DOMAIN)
        assert not violations, f"Forbidden import(s) {violations} found in domain file: {py_file}"


def test_cli_dependencies_banned_from_application() -> None:
    """Application layer must have zero awareness of typer or rich."""
    src_dir = Path(__file__).parent.parent.parent / "src" / "pyllmkit" / "application"
    for py_file in src_dir.rglob("*.py"):
        imports = _collect_module_imports(py_file)
        violations = imports.intersection(FORBIDDEN_IN_APPLICATION)
        assert not violations, f"Forbidden import(s) {violations} found in application file: {py_file}"
