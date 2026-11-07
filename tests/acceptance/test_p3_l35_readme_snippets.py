"""P3-AC-030: keep the full inference walkthrough executable outside the short README."""

import ast
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_p3_ac030_full_inference_walkthrough_is_linked_and_runnable() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    path = ROOT / "examples/12_full_inference_walkthrough.py"
    assert "](examples/12_full_inference_walkthrough.py)" in readme
    namespace = runpy.run_path(str(path), run_name="__main__")
    assert namespace["request_roundtrip"] == namespace["request"]
    assert namespace["restored"].response == namespace["synthetic_response"]


def test_all_readme_python_snippets_are_valid_syntax() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    blocks = readme.split("```python\n")[1:]
    assert len(blocks) >= 1
    for i, block in enumerate(blocks):
        snippet = block.split("\n```", 1)[0]
        assert r"\n" not in snippet, f"escaped newline in Python block {i + 1}"
        ast.parse(snippet, filename=f"README.md#python-{i + 1}")
