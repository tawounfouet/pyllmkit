"""P3-AC-030: README code is truly copy/paste runnable, not illustrative pseudo-code."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _readme_snippet(heading: str, next_heading: str) -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split(heading, 1)[1].split(next_heading, 1)[0]
    return section.split("```python\n", 1)[1].split("\n```", 1)[0]


def test_p3_ac030_readme_inference_walkthrough_compiles_and_executes() -> None:
    snippet = _readme_snippet(
        "## Phase 3 : exemple complet hors ligne (P3-AC-030)",
        "## Phase 2 text/image interaction API",
    )
    ast.parse(snippet, filename="README.md#p3-ac-030")
    namespace: dict[str, object] = {"__name__": "__main__"}
    exec(compile(snippet, "README.md#p3-ac-030", "exec"), namespace)
    assert namespace["wire"]["object_type"] == "inference_run"  # type: ignore[index]
    assert namespace["restored"].response == namespace["synthetic_response"]  # type: ignore[attr-defined]


def test_all_readme_python_snippets_are_valid_syntax() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    blocks = readme.split("```python\n")[1:]
    assert len(blocks) >= 4  # P3 + multiple M2/M1 examples
    for i, block in enumerate(blocks):
        snippet = block.split("\n```", 1)[0]
        assert r"\n" not in snippet, f"escaped newline in Python block {i + 1}"
        ast.parse(snippet, filename=f"README.md#python-{i + 1}")
