"""Additional negative and boundary tests for P4-JSON-1 and L4.1 value objects."""

from dataclasses import FrozenInstanceError
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


@pytest.mark.parametrize("schema", [
    {"type": "alien"},
    {"type": True},
    {"type": []},
    {"type": ["string", "string"]},
    {"properties": []},
    {"properties": {"x": True}},
    {"items": []},
    {"required": "x"},
    {"required": ["x", "x"]},
    {"required": [1]},
    {"additionalProperties": {}},
    {"enum": []},
    {"enum": [1, 1]},
    {"minimum": True},
    {"minimum": 3, "maximum": 2},
    {"minItems": -1},
    {"minLength": True},
    {"minItems": 3, "maxItems": 1},
    {"minLength": 4, "maxLength": 1},
    {"title": 7},
    {"description": None},
    {"$schema": "https://json-schema.org/draft/2020-12/schema"},
    {"oneOf": [{"type": "string"}]},
])
def test_reject_structurally_invalid_profile_schemas(schema: dict[str, object]) -> None:
    with pytest.raises(DomainValidationError):
        ToolSchema(schema)


def test_nested_item_schema_validation() -> None:
    valid = ToolSchema({
        "type": "array", "minItems": 0, "maxItems": 5,
        "items": {"type": "object", "properties": {
            "id": {"type": "integer", "minimum": 1},
        }},
    })
    assert valid.value["type"] == "array"
    with pytest.raises(DomainValidationError, match="unknown JSON type"):
        ToolSchema({"items": {"type": "invalid"}})


def test_schema_detects_python_cycle_and_non_json_values() -> None:
    cyc: dict[str, object] = {}
    cyc["properties"] = cyc
    with pytest.raises(DomainValidationError, match="cyclic"):
        ToolSchema(cyc)
    with pytest.raises(DomainValidationError, match="JSON-compatible"):
        ToolSchema({"const": object()})
    with pytest.raises(DomainValidationError, match="keys must be strings"):
        ToolSchema(cast(dict[str, object], {1: "a"}))
    with pytest.raises(DomainValidationError, match="finite"):
        ToolSchema({"const": float("nan")})


def test_schema_depth_and_size_limits() -> None:
    obj: dict[str, object] = {}
    for _ in range(34):
        obj = {"items": obj}
    with pytest.raises(DomainValidationError, match="depth"):
        ToolSchema(obj)
    with pytest.raises(DomainValidationError, match="size"):
        ToolSchema({"description": "a" * 1_048_576})


def test_schema_node_limit() -> None:
    with pytest.raises(DomainValidationError, match="node limit"):
        ToolSchema({"enum": list(range(10_001))})


def test_immutable_and_nonrevealing_repr() -> None:
    schema = ToolSchema({"const": "SECRET_TOKEN"})
    tool = Tool("x", None, schema)
    with pytest.raises(FrozenInstanceError):
        tool.name = "other"  # type: ignore[misc]
    assert "SECRET_TOKEN" not in repr(schema)
    assert "SECRET_TOKEN" not in repr(tool)


@pytest.mark.parametrize("bad", ["", " ", "bad-tool", "é", "a" * 65])
def test_tool_name_policy(bad: str) -> None:
    with pytest.raises(DomainValidationError, match="Tool.name"):
        Tool(bad, None, ToolSchema({}))


def test_exact_type_checks_and_choice_errors() -> None:
    with pytest.raises(DomainValidationError, match="schema"):
        Tool("x", None, cast(ToolSchema, {}))
    with pytest.raises(DomainValidationError, match="description"):
        Tool("x", cast(str, 42), ToolSchema({}))
    with pytest.raises(DomainValidationError, match="tuple"):
        validate_tool_set(cast(tuple[Tool, ...], []))
    with pytest.raises(DomainValidationError, match="tuple"):
        validate_tool_set(cast(tuple[Tool, ...], (object(),)))
    with pytest.raises(DomainValidationError, match="ToolChoice.kind"):
        ToolChoice(cast(ToolChoiceKind, "auto"))
    with pytest.raises(DomainValidationError, match="Tool.name"):
        ToolChoice.specific("")
    with pytest.raises(DomainValidationError, match="only SPECIFIC"):
        ToolChoice(ToolChoiceKind.AUTO, "x")
    with pytest.raises(DomainValidationError, match="choice"):
        validate_tool_choice(cast(ToolChoice, 42), ())
    validate_tool_choice(None, ())
