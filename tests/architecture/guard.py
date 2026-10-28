"""Static import guard for the provider-agnostic domain boundary.

This check prevents known direct SDK/IO imports. It is not a sandbox and does not
prove runtime isolation against dynamic imports; keep negative tests and CI checks.
"""

import ast
from pathlib import Path

BANNED_EXACT = frozenset(
    {
        "httpx", "requests", "socket", "openai", "anthropic", "google.genai",
        "mistralai", "ollama", "litellm", "langchain", "boto3",
        "urllib.request", "pyllmkit.providers", "pyllmkit.infrastructure",
        "pyllmkit.facade", "pyllmkit.application", "pyllmkit.protocols",
    }
)


def is_forbidden(module: str) -> bool:
    return any(module == blocked or module.startswith(blocked + ".") for blocked in BANNED_EXACT)


def forbidden_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if is_forbidden(alias.name):
                    found.append(f"{path}:{node.lineno}: {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            # Absolute module imports are checked; relative imports stay internal.
            if node.level == 0 and is_forbidden(node.module):
                found.append(f"{path}:{node.lineno}: {node.module}")
    return found
