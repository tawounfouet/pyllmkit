"""Deterministic in-memory fixture source, never live provider discovery."""

from dataclasses import dataclass

from pyllmkit.domain.registry.discovery import DiscoveryResult


@dataclass(frozen=True, slots=True)
class StaticDiscoverySource:
    """Returns the supplied immutable candidate batch without writing any registry."""

    result: DiscoveryResult

    def __post_init__(self) -> None:
        if not isinstance(self.result, DiscoveryResult):
            from pyllmkit.domain.errors import DomainValidationError

            raise DomainValidationError("result must be DiscoveryResult")

    def discover(self) -> DiscoveryResult:
        return self.result
