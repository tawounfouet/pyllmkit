"""Architectural guard: P4 codecs are pure and do not modify M3 API."""

import ast
from pathlib import Path

from pyllmkit.domain.inference import InferenceRequest, InferenceResponse
from pyllmkit.domain.tooling_inference import ToolingInferenceIntent
from tests.architecture.guard import forbidden_imports

ROOT = Path(__file__).resolve().parents[2]
CODECS = [
    ROOT / "src/pyllmkit/domain/tooling/serialization.py",
    ROOT / "src/pyllmkit/domain/tooling_inference/composition.py",
    ROOT / "src/pyllmkit/domain/tooling_inference/serialization.py",
    ROOT / "src/pyllmkit/domain/tooling_inference/support.py",
]


def test_codec_modules_have_no_sdk_or_io_imports() -> None:
    for source in CODECS:
        assert source.is_file()
        assert forbidden_imports(source) == []
        tree = ast.parse(source.read_text(encoding="utf-8"))
        banned = {"os", "sys", "socket", "subprocess", "httpx", "requests", "openai", "anthropic"}
        root_names = {
            item.name.split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.Import)
            for item in node.names
        }
        root_names.update(
            (node.module or "").split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        )
        assert not (banned & root_names)


def test_existing_m3_models_still_have_only_qualified_fields() -> None:
    assert tuple(InferenceRequest.__dataclass_fields__) == (
        "target", "messages", "generation_config",
    )
    assert tuple(InferenceResponse.__dataclass_fields__) == (
        "run_id", "output", "finish_reason", "usage",
    )
    assert "ToolingInferenceIntent" not in InferenceRequest.__annotations__
    assert ToolingInferenceIntent is not InferenceRequest
