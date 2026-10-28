"""Capabilities and modalities must not import a Model Entity or provider SDK."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "pyllmkit" / "domain"


def test_capability_and_modality_modules_do_not_import_models() -> None:
    import ast

    for package in ("capabilities", "modalities"):
        for source in (ROOT / package).glob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    assert all(
                        not n.name.startswith("pyllmkit.domain.models")
                        for n in node.names
                    ), source
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    assert not (node.module or "").startswith("pyllmkit.domain.models"), source
