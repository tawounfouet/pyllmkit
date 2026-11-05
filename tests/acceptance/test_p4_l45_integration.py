"""P4-AC-033..040: full Integration and Quality acceptance."""

import ast
import importlib
import importlib.metadata
import runpy
import tomllib
from pathlib import Path

import pytest

from pyllmkit import __version__
from pyllmkit.domain import (
    Content,
    InferenceRequest,
    Message,
    ModelId,
    ModelTarget,
    Role,
    TextContent,
)
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.structured_output import JsonResponseFormat, StructuredOutput
from pyllmkit.domain.tooling import (
    Tool,
    ToolArguments,
    ToolCall,
    ToolCallId,
    ToolResult,
    ToolSchema,
    ValidationStatus,
    attach_tool_result,
    validate_tool_call,
)
from pyllmkit.domain.tooling.serialization import (
    structured_output_from_dict,
    structured_output_to_dict,
)

ROOT = Path(__file__).resolve().parents[2]
DOMAIN = ROOT / "src" / "pyllmkit" / "domain"


def test_p4_ac033_domain_imports_no_executor_or_provider_sdk() -> None:
    forbidden = {"openai", "anthropic", "httpx", "requests", "subprocess", "socket"}
    paths = [
        *DOMAIN.glob("tooling/*.py"),
        *DOMAIN.glob("structured_output/*.py"),
        *DOMAIN.glob("tooling_inference/*.py"),
    ]
    assert paths
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            item.name.split(".")[0] for node in ast.walk(tree)
            if isinstance(node, ast.Import) for item in node.names
        }
        imported.update(
            (node.module or "").split(".")[0] for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        assert imported.isdisjoint(forbidden), str(path)
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["dependencies"] == []


def test_p4_ac034_domain_offline_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
        "MISTRAL_API_KEY", "AWS_ACCESS_KEY_ID",
    ):
        monkeypatch.delenv(key, raising=False)
    tool = Tool("demo", None, ToolSchema({"type": "object"}))
    call = ToolCall(ToolCallId("manual"), "demo", ToolArguments(parsed={}))
    assert validate_tool_call(call, (tool,)).status is ValidationStatus.VALID
    assert len(attach_tool_result(
        (call,), (), ToolResult(call.call_id, {"ok": True})
    )) == 1


def test_p4_ac035_complete_offline_workflow_executes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    runpy.run_path(str(ROOT / "examples" / "17_full_tooling_walkthrough.py"), run_name="__main__")
    assert "offline, no execution" in capsys.readouterr().out


def test_p4_ac036_readme_snippet_is_runnable() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split(
        "## Phase 4 : exemple complet hors ligne (P4-AC-036)", 1
    )[1].split("## État de qualification", 1)[0]
    fence = chr(96) * 3
    snippet = section.split(fence + "python\n", 1)[1].split("\n" + fence, 1)[0]
    ast.parse(snippet, filename="README#P4-AC-036")
    namespace: dict[str, object] = {"__name__": "__main__"}
    exec(compile(snippet, "README#P4-AC-036", "exec"), namespace)
    assert namespace["p4_decoded"].tools[0].name == "get_weather"
    assert namespace["p4_wire"]["object_type"] == "tooling_inference_intent"


def test_p4_ac037_packaging_public_api_and_metadata() -> None:
    for module in (
        "pyllmkit.domain.tooling", "pyllmkit.domain.structured_output",
        "pyllmkit.domain.tooling_inference", "pyllmkit.domain.tooling.serialization",
        "pyllmkit.domain.tooling_inference.serialization",
    ):
        assert importlib.import_module(module)
    package = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert package["version"] == __version__ == "0.1.0a2"
    assert importlib.metadata.version("pyllmkit") == package["version"]
    assert package["dependencies"] == []
    assert package["license"] == "MIT"
    assert (ROOT / "src" / "pyllmkit" / "py.typed").is_file()
    assert (ROOT / "LICENSE").is_file()
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert ".venv-wheel/bin/python examples/17_full_tooling_walkthrough.py" in ci
    assert ".venv-sdist/bin/python examples/17_full_tooling_walkthrough.py" in ci


def test_p4_ac038_hostile_schemas_are_rejected() -> None:
    with pytest.raises(DomainValidationError, match="unsupported keyword"):
        ToolSchema({"$ref": "https://example.invalid/schema"})
    cycle: dict[str, object] = {}
    cycle["items"] = cycle
    with pytest.raises(DomainValidationError, match="cyclic"):
        ToolSchema(cycle)
    nested: dict[str, object] = {}
    for _ in range(34):
        nested = {"items": nested}
    with pytest.raises(DomainValidationError, match="depth"):
        ToolSchema(nested)


def test_p4_ac039_sensitive_raw_not_leaked_in_repr_or_error() -> None:
    secret = "DO_NOT_EXPOSE_P4_SECRET"
    output = StructuredOutput(JsonResponseFormat(), raw=secret)
    encoded = structured_output_to_dict(output)
    encoded["validation_status"] = "valid"
    with pytest.raises(DomainValidationError) as exc:
        structured_output_from_dict(encoded)
    assert secret not in str(exc.value)
    assert secret not in repr(output)
    arguments = ToolArguments(raw=secret, parsed={"private": secret})
    result = ToolResult(ToolCallId("id"), {"private": secret}, is_error=True)
    assert secret not in repr(arguments) and secret not in repr(result)
    assert arguments.raw == secret


def test_p4_ac040_traceability_has_forty_cases_and_gates() -> None:
    trace = (ROOT / "docs" / "quality" / "PHASE_4_TRACEABILITY.md").read_text(encoding="utf-8")
    for number in range(1, 41):
        assert f"| {number:03d} |" in trace
    for gate in range(6):
        assert (ROOT / "docs" / "quality" / f"P4_G{gate}_GATE_REVIEW.md").is_file()
    assert "PENDING G5" in trace and "PENDING SHA" in trace
    assert (ROOT / "docs" / "quality" / "M4_READINESS_PRECHECK.md").is_file()


def test_l45_legacy_m3_request_still_roundtrips() -> None:
    from pyllmkit.domain import request_from_dict, request_to_dict

    request = InferenceRequest(ModelTarget(ModelId("offline")), (
        Message(Role.USER, Content((TextContent("x"),))),
    ))
    assert request_from_dict(request_to_dict(request)) == request
    assert "tools" not in request_to_dict(request)
