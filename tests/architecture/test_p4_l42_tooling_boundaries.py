"""L4.2 domain fitness: no dependency on executable tools or provider runtimes."""

import ast
from pathlib import Path

from pyllmkit.domain.tooling import ToolArguments, ToolCall, ToolCallId, ToolResult
from tests.architecture.guard import forbidden_imports

ROOT = Path(__file__).resolve().parents[2]
TOOLING = ROOT / "src" / "pyllmkit" / "domain" / "tooling"


def test_tooling_calls_are_real_domain_types() -> None:
    for obj in (ToolArguments, ToolCall, ToolCallId, ToolResult):
        assert obj.__module__.startswith("pyllmkit.domain.tooling")


def test_tooling_domain_has_no_sdk_network_executor_or_io_imports() -> None:
    for path in TOOLING.glob("*.py"):
        assert forbidden_imports(path) == []
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden = {"subprocess", "socket", "httpx", "requests", "openai", "anthropic", "os"}
        imports = [
            item.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for item in node.names
        ]
        imports.extend(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        assert not (set(imports) & forbidden)
