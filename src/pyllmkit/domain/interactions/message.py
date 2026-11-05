"""Immutable, provider-agnostic Message Value Object (ADR-009)."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError

from .content import Content
from .roles import Role


@dataclass(frozen=True, slots=True)
class Message:
    """Speaker Role + exactly one ordered Content; no required ID or Conversation."""

    role: Role
    content: Content

    def __post_init__(self) -> None:
        if not isinstance(self.role, Role):
            raise DomainValidationError("Message.role must be a canonical Role")
        if not isinstance(self.content, Content):
            raise DomainValidationError("Message.content must be a Content value object")
