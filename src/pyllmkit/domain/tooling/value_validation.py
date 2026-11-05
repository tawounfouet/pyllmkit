"""Pure, bounded instance validation for the explicit P4-JSON-1 schema profile.

No network, imports from provider SDKs, JSON text parsing, or execution.
The returned codes are fixed and never include user-controlled payloads.
"""

from typing import cast

from .schema import ToolSchema


def _same_json(a: object, b: object) -> bool:
    """JSON Schema numeric equality without Python bool == int confusion."""
    if type(a) is bool or type(b) is bool:
        return type(a) is bool and type(b) is bool and a == b
    if type(a) in (int, float) and type(b) in (int, float):
        return a == b
    if type(a) is not type(b):
        return False
    if type(a) is list:
        left, right = cast(list[object], a), cast(list[object], b)
        return len(left) == len(right) and all(
            _same_json(x, y) for x, y in zip(left, right, strict=True)
        )
    if type(a) is dict:
        left_obj, right_obj = cast(dict[str, object], a), cast(dict[str, object], b)
        return left_obj.keys() == right_obj.keys() and all(
            _same_json(left_obj[k], right_obj[k]) for k in left_obj
        )
    return a == b


def _matches_type(value: object, kind: str) -> bool:
    if kind == "null":
        return value is None
    if kind == "boolean":
        return type(value) is bool
    if kind == "number":
        return type(value) in (int, float)
    if kind == "integer":
        return type(value) is int or (type(value) is float and value.is_integer())
    if kind == "string":
        return type(value) is str
    if kind == "array":
        return type(value) is list
    if kind == "object":
        return type(value) is dict
    return False


def _check(value: object, schema: dict[str, object]) -> str | None:
    kind = schema.get("type")
    if isinstance(kind, str):
        if not _matches_type(value, kind):
            return "type_mismatch"
    elif isinstance(kind, list):
        types = cast(list[str], kind)
        if not any(_matches_type(value, item) for item in types):
            return "type_mismatch"
    if "const" in schema and not _same_json(value, schema["const"]):
        return "const_mismatch"
    if "enum" in schema and not any(
        _same_json(value, item) for item in cast(list[object], schema["enum"])
    ):
        return "enum_mismatch"

    if type(value) is dict:
        obj = cast(dict[str, object], value)
        required = cast(list[str], schema.get("required", []))
        if any(key not in obj for key in required):
            return "required_missing"
        properties = cast(dict[str, object], schema.get("properties", {}))
        for key, item in obj.items():
            if key in properties:
                child = cast(dict[str, object], properties[key])
                error = _check(item, child)
                if error is not None:
                    return error
            elif schema.get("additionalProperties", True) is False:
                return "additional_property"
    elif type(value) is list:
        items = cast(list[object], value)
        if "minItems" in schema and len(items) < cast(int, schema["minItems"]):
            return "min_items"
        if "maxItems" in schema and len(items) > cast(int, schema["maxItems"]):
            return "max_items"
        if "items" in schema:
            child_schema = cast(dict[str, object], schema["items"])
            for item in items:
                error = _check(item, child_schema)
                if error is not None:
                    return error
    elif type(value) is str:
        string = value
        if "minLength" in schema and len(string) < cast(int, schema["minLength"]):
            return "min_length"
        if "maxLength" in schema and len(string) > cast(int, schema["maxLength"]):
            return "max_length"

    if type(value) in (int, float):
        number = cast(int | float, value)
        if "minimum" in schema and number < cast(int | float, schema["minimum"]):
            return "minimum"
        if "maximum" in schema and number > cast(int | float, schema["maximum"]):
            return "maximum"
    return None


def check_p4_json_value(value: object, schema: ToolSchema) -> str | None:
    """Return a bounded, payload-free failure code or None on a proven pass."""
    return _check(value, schema.value)
