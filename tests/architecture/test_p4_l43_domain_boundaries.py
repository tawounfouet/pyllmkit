"""L4.3 architecture fitness: no provider, execution or I/O in structured output."""

import ast
from pathlib import Path

from pyllmkit.domain.structured_output import (
    JsonResponseFormat,
    SchemaResponseFormat,
    StructuredOutput,
    TextResponseFormat,
    validate_structured_output,
)
from tests.architecture.guard import forbidden_imports

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src" / "pyllmkit" / "domain" / "structured_output"


def test_public_output_types_importable_without_provider() -> None:
    assert JsonResponseFormat.__module__.startswith("pyllmkit.domain.structured_output")
    assert SchemaResponseFormat.__module__.startswith("pyllmkit.domain.structured_output")
    assert TextResponseFormat.__module__.startswith("pyllmkit.domain.structured_output")
    assert StructuredOutput.__module__.startswith("pyllmkit.domain.structured_output")
    assert callable(validate_structured_output)


def test_no_forbidden_imports_or_execution_modules() -> None:
    for path in MODULE.glob("*.py"):
        assert forbidden_imports(path) == []
        tree = ast.parse(path.read_text(encoding="utf-8"))
        disallowed = {"subprocess", "socket", "httpx", "requests", "openai", "anthropic", "os"}
        imported = {
            name.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for name in node.names
        }
        imported |= {
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert imported.isdisjoint(disallowed)
