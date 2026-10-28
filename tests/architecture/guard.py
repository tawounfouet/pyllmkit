"""Static fitness function for the provider-agnostic Domain Core.

Detects forbidden direct/relative imports and literal dynamic imports. This is
an architecture lint check, not a sandbox or proof against all runtime behavior.
"""

import ast
from pathlib import Path

BANNED_EXACT = frozenset(
    {
        "httpx",
        "requests",
        "socket",
        "aiohttp",
        "http.client",
        "urllib.request",
        "openai",
        "anthropic",
        "google.genai",
        "google.generativeai",
        "mistralai",
        "ollama",
        "vllm",
        "litellm",
        "langchain",
        "boto3",
        "subprocess",
        "os",
        "pyllmkit.providers",
        "pyllmkit.infrastructure",
        "pyllmkit.facade",
        "pyllmkit.application",
        "pyllmkit.protocols",
    }
)


def is_forbidden(module: str) -> bool:
    """Match full module segments rather than accidental string prefixes."""
    return any(module == blocked or module.startswith(blocked + ".") for blocked in BANNED_EXACT)


def _from_module(path: Path, node: ast.ImportFrom) -> str:
    """Resolve Python relative-import module names from the package path.

    A file below a directory named pyllmkit has package context. Unknown file
    locations return the raw module name and are checked conservatively.
    """
    if node.level == 0:
        return node.module or ""
    parts = path.parent.parts
    if "pyllmkit" not in parts:
        return node.module or ""
    # Choose the innermost package, not the outer repository directory.
    index = len(parts) - 1 - parts[::-1].index("pyllmkit")
    package = parts[index:]
    if node.level > len(package):
        return node.module or ""
    root = package[: len(package) - (node.level - 1)]
    return ".".join((*root, *(node.module.split(".") if node.module else ())))


def _literal_import(node: ast.Call) -> str | None:
    """Catch __import__('provider') and importlib.import_module('provider')."""
    if not node.args or not isinstance(node.args[0], ast.Constant):
        return None
    value = node.args[0].value
    if not isinstance(value, str):
        return None
    func = node.func
    if isinstance(func, ast.Name) and func.id in {"__import__", "import_module"}:
        return value
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "import_module"
        and isinstance(func.value, ast.Name)
        and func.value.id == "importlib"
    ):
        return value
    return None


def forbidden_imports(path: Path) -> list[str]:
    """List known prohibited imports, including literal dynamic ones."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if is_forbidden(alias.name):
                    found.append(f"{path}:{node.lineno}: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = _from_module(path, node)
            if is_forbidden(module):
                found.append(f"{path}:{node.lineno}: {module}")
            else:
                for alias in node.names:
                    submodule = f"{module}.{alias.name}" if module else alias.name
                    if is_forbidden(submodule):
                        found.append(f"{path}:{node.lineno}: {submodule}")
        elif isinstance(node, ast.Call):
            module = _literal_import(node)
            if module is not None and is_forbidden(module):
                found.append(f"{path}:{node.lineno}: dynamic:{module}")
    return found
