"""P4-JSON-1 structural schema contract, deliberately smaller than JSON Schema."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import cast

from pyllmkit.domain.errors import DomainValidationError

from .json_values import FrozenObject, freeze_json, thaw_json

SCHEMA_PROFILE = "P4-JSON-1"
_ALLOWED = frozenset({
    "type", "properties", "required", "additionalProperties", "items",
    "enum", "const", "minItems", "maxItems", "minLength", "maxLength",
    "minimum", "maximum", "description", "title",
})
_TYPES = frozenset({"object", "array", "string", "integer", "number", "boolean", "null"})


def _invalid(message: str) -> None:
    raise DomainValidationError(f"invalid {SCHEMA_PROFILE} schema: {message}")


def _check_schema(schema: dict[str, object]) -> None:
    if set(schema) - _ALLOWED:
        _invalid("unsupported keyword")
    kind = schema.get("type")
    if kind is not None:
        if type(kind) is str:
            if kind not in _TYPES:
                _invalid("unknown JSON type")
        elif type(kind) is list:
            variants = cast(list[object], kind)
            if not variants or any(type(k) is not str or k not in _TYPES for k in variants):
                _invalid("invalid type union")
            if len(set(cast(list[str], variants))) != len(variants):
                _invalid("duplicate type in union")
        else:
            _invalid("type must be a string or array of strings")
    for name in ("title", "description"):
        if name in schema and type(schema[name]) is not str:
            _invalid(f"{name} must be a string")
    if "properties" in schema:
        props = schema["properties"]
        if type(props) is not dict:
            _invalid("properties must be an object")
        for child in cast(dict[str, object], props).values():
            if type(child) is not dict:
                _invalid("property schema must be an object")
            _check_schema(cast(dict[str, object], child))
    if "items" in schema:
        items = schema["items"]
        if type(items) is not dict:
            _invalid("items must be a schema object")
        _check_schema(cast(dict[str, object], items))
    if "required" in schema:
        req = schema["required"]
        if type(req) is not list:
            _invalid("required must be an array")
        members = cast(list[object], req)
        if any(type(item) is not str for item in members):
            _invalid("required elements must be strings")
        if len(set(cast(list[str], members))) != len(members):
            _invalid("duplicate required property")
    if "additionalProperties" in schema and type(schema["additionalProperties"]) is not bool:
        _invalid("additionalProperties must be a boolean")
    if "enum" in schema:
        values = schema["enum"]
        if type(values) is not list or not values:
            _invalid("enum must be a nonempty array")
        encoded = [
            json.dumps(item, sort_keys=True, allow_nan=False)
            for item in cast(list[object], values)
        ]
        if len(set(encoded)) != len(encoded):
            _invalid("duplicate enum value")
    for lower, upper in (("minItems", "maxItems"), ("minLength", "maxLength")):
        for key in (lower, upper):
            if key in schema and (type(schema[key]) is not int or cast(int, schema[key]) < 0):
                _invalid(f"{key} must be a nonnegative integer")
        if lower in schema and upper in schema and (
            cast(int, schema[lower]) > cast(int, schema[upper])
        ):
            _invalid("minimum bound exceeds maximum bound")
    for key in ("minimum", "maximum"):
        if key in schema and type(schema[key]) not in (int, float):
            _invalid(f"{key} must be a finite number")
    if "minimum" in schema and "maximum" in schema and (
        cast(float, schema["minimum"]) > cast(float, schema["maximum"])
    ):
        _invalid("minimum exceeds maximum")


@dataclass(frozen=True, slots=True, init=False)
class ToolSchema:
    """Validated, recursively immutable P4-JSON-1 argument schema."""

    _root: FrozenObject = field(repr=False)

    def __init__(self, value: dict[str, object]) -> None:
        frozen = freeze_json(value)
        if not isinstance(frozen, FrozenObject):
            _invalid("root must be an object")
        plain = cast(dict[str, object], thaw_json(frozen))
        _check_schema(plain)
        object.__setattr__(self, "_root", frozen)

    @property
    def profile(self) -> str:
        return SCHEMA_PROFILE

    @property
    def value(self) -> dict[str, object]:
        """Return a fresh JSON tree, never the stored immutable representation."""
        return cast(dict[str, object], thaw_json(self._root))
