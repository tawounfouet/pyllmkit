"""Architectural fitness: P4 tool domain contains no executor, SDK or I/O."""

import ast
from pathlib import Path

from pyllmkit.domain.tooling import Tool, ToolChoice, ToolSchema
from tests.architecture.guard import forbidden_imports

TOOLING = Path(__file__).resolve().parents[2] / "src" / "pyllmkit" / "domain" / "tooling"


def test_tooling_module_is_importable_without_provider_sdk() -> None:
    assert Tool.__module__.startswith("pyllmkit.domain.tooling")
    assert ToolChoice.__module__.startswith("pyllmkit.domain.tooling")
    assert ToolSchema.__module__.startswith("pyllmkit.domain.tooling")


def test_tooling_domain_no_forbidden_imports_or_execution_helpers() -> None:
    assert TOOLING.exists()
    for source in TOOLING.glob("*.py"):
        assert forbidden_imports(source) == []
        tree = ast.parse(source.read_text(encoding="utf-8"))
        banned = {"subprocess", "socket", "httpx", "requests", "openai", "anthropic"}
        assert not any(
            isinstance(node, ast.Import) and any(n.name.split(".")[0] in banned for n in node.names)
            for node in ast.walk(tree)
        )
        assert not any(
            isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in banned
            for node in ast.walk(tree)
        )
