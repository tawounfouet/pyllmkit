"""Strict provider-native JSON text decoding at the adapter boundary.

RFC 8259-compatible object parsing. Native payloads may contain secrets
and prompts; failures must expose only a safe code. The domain never imports
this provider infrastructure module.
"""

from __future__ import annotations

import json
import re
from typing import NoReturn

from pyllmkit.application.inference import InvocationPortError

_SNAPSHOT_SUFFIX = re.compile(
    r"^(?:-(?:\d{4}-\d{2}-\d{2}|\d{8}|\d{4}|latest)|:[a-zA-Z0-9_.-]+)$"
)


def matches_model_alias(observed: object, expected_alias: str) -> bool:
    """Validate whether an observed model string matches the expected alias or a valid snapshot."""
    if type(observed) is not str or type(expected_alias) is not str:
        return False
    if observed == expected_alias:
        return True
    if observed.startswith(expected_alias):
        suffix = observed[len(expected_alias):]
        if _SNAPSHOT_SUFFIX.fullmatch(suffix):
            return True
    for suffix_trim in ("-latest", ":latest"):
        if expected_alias.endswith(suffix_trim):
            base = expected_alias[:-len(suffix_trim)]
            if observed == base or matches_model_alias(observed, base):
                return True
    return False



def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise InvocationPortError("provider_protocol_error")
        value[key] = item
    return value


def _reject_constant(_literal: str) -> NoReturn:
    """JSON NaN/Infinity/-Infinity are not standard JSON number values."""
    raise InvocationPortError("provider_protocol_error")


def decode_provider_json_object(raw: bytes | str) -> dict[str, object]:
    """Decode one native JSON object, rejecting duplicates at *every* depth.

    Never include raw response text, nonstandard constants or native error
    details in exception text or exception chaining.
    """
    if type(raw) not in (bytes, str):
        raise InvocationPortError("provider_protocol_error")
    try:
        payload = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, TypeError, RecursionError):
        raise InvocationPortError("provider_protocol_error") from None
    if type(payload) is not dict:
        raise InvocationPortError("provider_protocol_error")
    return payload
