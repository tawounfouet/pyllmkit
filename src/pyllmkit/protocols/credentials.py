"""Provider-independent opaque credential contracts at the application boundary."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class SecurityConfigurationError(ValueError):
    """Sanitized configuration code without untrusted URL values."""


class CredentialResolutionError(ValueError):
    """Sanitized missing/unavailable credential code."""


@dataclass(frozen=True, slots=True, repr=False)
class CredentialRef:
    """Opaque identifier that is never the secret itself."""

    name: str = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.name) is not str
            or re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,79}", self.name) is None
        ):
            raise SecurityConfigurationError("invalid_credential_reference")

    def __repr__(self) -> str:
        return "CredentialRef(<redacted>)"


@dataclass(frozen=True, slots=True, repr=False, eq=False)
class SecretValue:
    """Infrastructure-only secret, identity semantics and redacted repr/str."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.value) is not str or not self.value:
            raise CredentialResolutionError("credential_unavailable")

    def __repr__(self) -> str:
        return "SecretValue(<redacted>)"

    def __str__(self) -> str:
        return "<redacted>"

    def reveal(self) -> str:
        """Only a trusted transport may use this; Python cannot zero memory."""
        return self.value


@runtime_checkable
class CredentialResolverPort(Protocol):
    """Resolve an opaque reference at the transport boundary, never in domain."""

    def resolve(self, reference: CredentialRef) -> SecretValue: ...
