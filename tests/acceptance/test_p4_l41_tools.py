"""P4-AC-001..008: L4.1 tool declaration and choice acceptance (offline)."""

from typing import cast

import pytest

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.tooling import (
    Tool,
    ToolChoice,
    ToolChoiceKind,
    ToolSchema,
    validate_tool_choice,
    validate_tool_set,
)


def make_tool(name: str = "get_weather") -> Tool:
    return Tool(name, "Look up weather", ToolSchema({
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
        "additionalProperties": False,
    }))


def test_p4_ac001_declare_tool_without_callable_or_provider() -> None:
    tool = make_tool()
    assert tool.name == "get_weather"
    assert tool.schema.value["type"] == "object"
    assert not hasattr(tool, "execute")
    assert not hasattr(tool, "handler")


def test_p4_ac002_schema_validity_and_unsupported_ref() -> None:
    with pytest.raises(DomainValidationError, match="unsupported keyword"):
        ToolSchema({"$ref": "https://example.com/tool.json"})
    assert ToolSchema({"type": ["string", "null"]}).profile == "P4-JSON-1"


def test_p4_ac003_name_and_description_are_checked() -> None:
    with pytest.raises(DomainValidationError, match="Tool.name"):
        make_tool("bad-name!")
    with pytest.raises(DomainValidationError, match="description"):
        Tool("valid_name", " ", ToolSchema({}))


def test_p4_ac004_schema_is_immutable_under_alias_mutation() -> None:
    source: dict[str, object] = {"properties": {"city": {"type": "string"}}}
    schema = ToolSchema(source)
    cast(dict[str, object], source["properties"])["city"] = {"type": "integer"}
    assert schema.value["properties"] == {"city": {"type": "string"}}
    visible = schema.value
    cast(dict[str, object], visible["properties"]).clear()
    assert schema.value["properties"] == {"city": {"type": "string"}}
    assert "city" not in repr(schema)


def test_p4_ac005_duplicate_names_rejected() -> None:
    with pytest.raises(DomainValidationError, match="unique"):
        validate_tool_set((make_tool(), make_tool()))


def test_p4_ac006_choice_variants_are_distinct() -> None:
    tools = (make_tool(),)
    for kind in (ToolChoiceKind.AUTO, ToolChoiceKind.NONE, ToolChoiceKind.REQUIRED):
        validate_tool_choice(ToolChoice(kind), tools)
    assert ToolChoice.specific("get_weather").name == "get_weather"
    validate_tool_choice(ToolChoice.specific("get_weather"), tools)


def test_p4_ac007_specific_unknown_tool_rejected() -> None:
    with pytest.raises(DomainValidationError, match="declared"):
        validate_tool_choice(ToolChoice.specific("unknown"), (make_tool(),))


def test_p4_ac008_required_without_tools_rejected() -> None:
    with pytest.raises(DomainValidationError, match="REQUIRED"):
        validate_tool_choice(ToolChoice(ToolChoiceKind.REQUIRED), ())
    validate_tool_choice(ToolChoice(ToolChoiceKind.NONE), (make_tool(),))
