"""Canonical semantic interaction roles; no provider SDK role mapping (ADR-008)."""

from enum import StrEnum

from pyllmkit.domain.errors import DomainValidationError


class Role(StrEnum):
    """Five explicit semantic speaker roles, independent of provider wire formats."""

    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

    @classmethod
    def _missing_(cls, value: object) -> None:
        """Reject noncanonical role values without silently mapping to user."""
        raise DomainValidationError("Role must be a canonical interaction role")
