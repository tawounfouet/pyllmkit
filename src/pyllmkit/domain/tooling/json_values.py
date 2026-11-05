"""Deeply immutable JSON values for P4; no provider or execution dependencies."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from math import isfinite
from typing import TypeAlias, cast

from pyllmkit.domain.errors import DomainValidationError

MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 10_000
MAX_JSON_BYTES = 1_048_576


@dataclass(frozen=True, slots=True)
class FrozenArray:
    """Immutable JSON array; payload suppressed from repr."""

    items: tuple[FrozenJSON, ...] = field(repr=False)


@dataclass(frozen=True, slots=True)
class FrozenObject:
    """Immutable JSON object with deterministic key ordering."""

    items: tuple[tuple[str, FrozenJSON], ...] = field(repr=False)


JSONScalar: TypeAlias = None | bool | int | float | str
FrozenJSON: TypeAlias = JSONScalar | FrozenArray | FrozenObject


def thaw_json(value: FrozenJSON) -> object:
    """Produce a fresh plain-Python JSON tree; never expose internal storage."""
    if isinstance(value, FrozenArray):
        return [thaw_json(item) for item in value.items]
    if isinstance(value, FrozenObject):
        return {key: thaw_json(item) for key, item in value.items}
    return value


def freeze_json(value: object) -> FrozenJSON:
    """Copy, bound and freeze a JSON-compatible Python tree, rejecting cycles."""
    active: set[int] = set()
    nodes = 0

    def visit(item: object, depth: int) -> FrozenJSON:
        nonlocal nodes
        if depth > MAX_JSON_DEPTH:
            raise DomainValidationError("JSON depth limit exceeded")
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise DomainValidationError("JSON node limit exceeded")
        if item is None or type(item) in (bool, int, str):
            return cast(JSONScalar, item)
        if type(item) is float:
            if not isfinite(cast(float, item)):
                raise DomainValidationError("JSON number must be finite")
            return cast(float, item)
        if type(item) is list:
            ident = id(item)
            if ident in active:
                raise DomainValidationError("cyclic JSON value")
            active.add(ident)
            try:
                values = cast(list[object], item)
                return FrozenArray(tuple(visit(child, depth + 1) for child in values))
            finally:
                active.remove(ident)
        if type(item) is dict:
            ident = id(item)
            if ident in active:
                raise DomainValidationError("cyclic JSON value")
            active.add(ident)
            try:
                mapping = cast(dict[object, object], item)
                if any(type(key) is not str for key in mapping):
                    raise DomainValidationError("JSON object keys must be strings")
                keys = cast(list[str], sorted(mapping))
                return FrozenObject(tuple(
                    (key, visit(mapping[key], depth + 1)) for key in keys
                ))
            finally:
                active.remove(ident)
        raise DomainValidationError("value is not JSON-compatible")

    frozen = visit(value, 0)
    serialized = json.dumps(
        thaw_json(frozen), ensure_ascii=True, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )
    if len(serialized.encode("utf-8")) > MAX_JSON_BYTES:
        raise DomainValidationError("JSON size limit exceeded")
    return frozen
