"""Immutable raw and parsed tool arguments, without implicit JSON parsing."""

from dataclasses import dataclass, field

from pyllmkit.domain.errors import DomainValidationError

from .json_values import FrozenJSON, freeze_json, thaw_json

_ABSENT = object()


@dataclass(frozen=True, slots=True, init=False)
class ToolArguments:
    """A parsed JSON null is distinct from a missing parsed value (ADR-025).

    Construction does not validate the parsed value against any ToolSchema.
    Validation evidence is returned separately by validate_tool_call.
    """

    _raw: str | None = field(repr=False)
    _frozen: FrozenJSON = field(repr=False)
    _has_parsed: bool = field(repr=False)

    def __init__(self, raw: str | None = None, parsed: object = _ABSENT) -> None:
        if raw is not None and type(raw) is not str:
            raise DomainValidationError("ToolArguments.raw must be a string or None")
        if raw is not None and len(raw.encode("utf-8")) > 1_048_576:
            raise DomainValidationError("ToolArguments.raw size limit exceeded")
        present = parsed is not _ABSENT
        frozen = freeze_json(parsed) if present else None
        object.__setattr__(self, "_raw", raw)
        object.__setattr__(self, "_frozen", frozen)
        object.__setattr__(self, "_has_parsed", present)

    @property
    def raw(self) -> str | None:
        return self._raw

    @property
    def has_parsed(self) -> bool:
        return self._has_parsed

    @property
    def parsed(self) -> object:
        """Return a fresh JSON tree. Check has_parsed to disambiguate null."""
        return thaw_json(self._frozen) if self._has_parsed else None
