"""Infrastructure-only secret resolution interface (P7 L7.2)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pyllmkit.adapters.inference.security import CredentialRef, SecretValue


@runtime_checkable
class CredentialResolverPort(Protocol):
    """Resolve an opaque reference at the transport edge, not in domain objects."""

    def resolve(self, reference: CredentialRef) -> SecretValue: ...
