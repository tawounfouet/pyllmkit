"""PIR2-02: copy/paste the historical README domain example verbatim."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_domain_example_is_valid_executable_python() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("## Domain example", 1)[1].split("## Architecture", 1)[0]
    snippet = section.split("```python\n", 1)[1].split("\n```", 1)[0]
    assert r"\n" not in snippet
    ast.parse(snippet, filename="README.md#domain-example")
    exec(compile(snippet, "README.md#domain-example", "exec"), {"__name__": "__main__"})
