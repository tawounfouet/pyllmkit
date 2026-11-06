"""Offline, fail-closed provider connection and credential contracts (P7 L7.2).

This module validates configuration but NEVER creates network connections.
Actual DNS/IP pinning, TLS and redirect enforcement belong to L7.3+ transports.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from urllib.parse import urlsplit


class SecurityConfigurationError(ValueError):
    """A sanitized code; never embed untrusted URLs or credentials."""


class CredentialResolutionError(ValueError):
    """A sanitized code for missing or inaccessible credential values."""


@dataclass(frozen=True, slots=True, repr=False)
class CredentialRef:
    """Opaque key to a separately configured secret store, not a credential."""

    name: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.name) is not str or re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,79}", self.name) is None:
            raise SecurityConfigurationError("invalid_credential_reference")

    def __repr__(self) -> str:
        return "CredentialRef(<redacted>)"


@dataclass(frozen=True, slots=True, repr=False)
class SecretValue:
    """Secret retained only in infrastructure; explicit reveal by a trusted adapter."""

    value: str = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.value) is not str or not self.value:
            raise CredentialResolutionError("credential_unavailable")

    def __repr__(self) -> str:
        return "SecretValue(<redacted>)"

    def __str__(self) -> str:
        return "<redacted>"

    def reveal(self) -> str:
        """Restricted by convention to the trusted transport implementation."""
        return self.value


class EnvCredentialResolver:
    """Explicit alias -> environment variable mapping, read only on resolve().

    No automatic .env loading or implicit variable-name guesses. This is a
    developmental credential source, not an enterprise secret manager.
    """

    __slots__ = ("_references", "_environ")

    def __init__(
        self,
        references: Mapping[CredentialRef, str],
        *,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        if not isinstance(references, Mapping):
            raise SecurityConfigurationError("credential_mapping_invalid")
        mapping = dict(references)
        if any(
            type(key) is not CredentialRef
            or type(name) is not str
            or re.fullmatch(r"[A-Z][A-Z0-9_]*", name) is None
            for key, name in mapping.items()
        ):
            raise SecurityConfigurationError("credential_mapping_invalid")
        if environ is not None and not isinstance(environ, Mapping):
            raise SecurityConfigurationError("credential_source_invalid")
        self._references = mapping
        self._environ = os.environ if environ is None else environ

    def resolve(self, reference: CredentialRef) -> SecretValue:
        if type(reference) is not CredentialRef:
            raise CredentialResolutionError("invalid_credential_reference")
        name = self._references.get(reference)
        if name is None:
            raise CredentialResolutionError("credential_reference_unknown")
        secret = self._environ.get(name)
        if type(secret) is not str or not secret.strip():
            raise CredentialResolutionError("credential_unavailable")
        return SecretValue(secret)


class ProviderProfile(StrEnum):
    """Only contract-tested P7 pilot destinations, not provider identity."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


_OPENAI_URL = "https://api.openai.com/v1/responses"
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


@dataclass(frozen=True, slots=True)
class ProviderConnectionConfig:
    """Preflight-only destination; never asserts a successful TLS connection.

    Only exact official cloud endpoints or explicitly opted-in Ollama loopback
    IP literals are accepted. No alternate hosts, DNS resolution, proxy or
    redirects are authorized by this class.
    """

    profile: ProviderProfile
    endpoint_url: str = field(repr=False)
    credential_ref: CredentialRef | None = field(default=None, repr=False)
    allow_local: bool = False
    verify_tls: bool = True
    follow_redirects: bool = False
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if type(self.profile) is not ProviderProfile:
            raise SecurityConfigurationError("provider_profile_invalid")
        if type(self.endpoint_url) is not str or not self.endpoint_url:
            raise SecurityConfigurationError("endpoint_not_approved")
        if type(self.allow_local) is not bool:
            raise SecurityConfigurationError("local_authorization_invalid")
        if type(self.verify_tls) is not bool or not self.verify_tls:
            raise SecurityConfigurationError("tls_verification_required")
        if type(self.follow_redirects) is not bool or self.follow_redirects:
            raise SecurityConfigurationError("redirects_forbidden")
        if (
            type(self.timeout_seconds) is not float
            or not isfinite(self.timeout_seconds)
            or not (0.0 < self.timeout_seconds <= 120.0)
        ):
            raise SecurityConfigurationError("timeout_invalid")
        if self.credential_ref is not None and type(self.credential_ref) is not CredentialRef:
            raise SecurityConfigurationError("credential_reference_invalid")

        if self.profile is ProviderProfile.OPENAI:
            if self.endpoint_url != _OPENAI_URL:
                raise SecurityConfigurationError("endpoint_not_approved")
            if self.credential_ref is None:
                raise SecurityConfigurationError("credential_reference_required")
            if self.allow_local:
                raise SecurityConfigurationError("local_authorization_invalid")
        elif self.profile is ProviderProfile.ANTHROPIC:
            if self.endpoint_url != _ANTHROPIC_URL:
                raise SecurityConfigurationError("endpoint_not_approved")
            if self.credential_ref is None:
                raise SecurityConfigurationError("credential_reference_required")
            if self.allow_local:
                raise SecurityConfigurationError("local_authorization_invalid")
        else:
            if not self.allow_local:
                raise SecurityConfigurationError("local_opt_in_required")
            if self.credential_ref is not None:
                raise SecurityConfigurationError("ollama_auth_not_implemented")
            self._validate_local_endpoint()

    def _validate_local_endpoint(self) -> None:
        """Allow only IP literals 127.0.0.1 and ::1, with an explicit TCP port."""
        try:
            parsed = urlsplit(self.endpoint_url)
            port = parsed.port
        except ValueError:
            raise SecurityConfigurationError("endpoint_not_approved") from None
        if (
            parsed.scheme != "http"
            or parsed.hostname not in ("127.0.0.1", "::1")
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path != "/api/chat"
            or port is None
            or port < 1
            or port > 65535
        ):
            raise SecurityConfigurationError("endpoint_not_approved")
        expected_netloc = (
            f"[::1]:{port}" if parsed.hostname == "::1" else f"127.0.0.1:{port}"
        )
        if parsed.netloc != expected_netloc:
            raise SecurityConfigurationError("endpoint_not_approved")

    @classmethod
    def openai(cls, credential_ref: CredentialRef) -> ProviderConnectionConfig:
        return cls(ProviderProfile.OPENAI, _OPENAI_URL, credential_ref)

    @classmethod
    def anthropic(cls, credential_ref: CredentialRef) -> ProviderConnectionConfig:
        return cls(ProviderProfile.ANTHROPIC, _ANTHROPIC_URL, credential_ref)

    @classmethod
    def ollama_local(
        cls, *, port: int = 11434, ipv6: bool = False,
    ) -> ProviderConnectionConfig:
        if type(port) is not int or not 1 <= port <= 65535:
            raise SecurityConfigurationError("endpoint_not_approved")
        if type(ipv6) is not bool:
            raise SecurityConfigurationError("endpoint_not_approved")
        host = "[::1]" if ipv6 else "127.0.0.1"
        return cls(
            ProviderProfile.OLLAMA, f"http://{host}:{port}/api/chat",
            allow_local=True,
        )
