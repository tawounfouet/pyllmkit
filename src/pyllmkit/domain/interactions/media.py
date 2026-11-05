"""Passive media source reference with syntactic validation only (ADR-011)."""

from dataclasses import dataclass
from ipaddress import IPv6Address
import re
from urllib.parse import urlsplit

from pyllmkit.domain.errors import DomainValidationError

_DNS_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")
_BAD_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")


def _valid_uri_host(host: str) -> bool:
    """Check host syntax without DNS, policy checks or network access."""
    if ":" in host:
        if "%" in host:
            return False  # scoped IPv6 zone identifiers need an adapter policy
        try:
            IPv6Address(host)
        except ValueError:
            return False
        return True

    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return False
    # A final dot is a valid DNS root terminator; empty labels are not.
    normalized = ascii_host[:-1] if ascii_host.endswith(".") else ascii_host
    if not normalized or len(ascii_host) > 254:
        return False
    return all(bool(_DNS_LABEL.fullmatch(label)) for label in normalized.split("."))


def _validate_http_uri(value: str) -> None:
    """Validate a passive HTTP(S) URI; never resolve or fetch the host."""
    if (
        not value
        or any(c.isspace() or ord(c) < 32 or c == "\\" for c in value)
        or _BAD_ESCAPE.search(value) is not None
    ):
        raise DomainValidationError("MediaSourceRef.uri must be a syntactically valid HTTP(S) URI")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        raise DomainValidationError(
            "MediaSourceRef.uri must be a syntactically valid HTTP(S) URI"
        ) from None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not host
        or not _valid_uri_host(host)
        or (port is not None and port == 0)
    ):
        raise DomainValidationError("MediaSourceRef.uri must be a syntactically valid HTTP(S) URI")


@dataclass(frozen=True, slots=True, repr=False)
class MediaSourceRef:
    """Immutable passive URI or asset ID, never loaded by the domain.

    The repr deliberately hides the value, which may contain confidential
    query parameters. A syntactically valid URI is not safe to dereference:
    SSRF protection, allowlists, auth and payload limits belong in adapters.
    """

    kind: str
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or self.kind not in {"uri", "asset"}:
            raise DomainValidationError("MediaSourceRef.kind must be 'uri' or 'asset'")
        if not isinstance(self.value, str):
            raise DomainValidationError("MediaSourceRef.value must be a string")
        if self.kind == "asset":
            if not self.value.strip():
                raise DomainValidationError("MediaSourceRef.asset must be nonblank")
        else:
            _validate_http_uri(self.value)

    def __repr__(self) -> str:
        """Hide the entire untrusted source value, including URI credentials."""
        return f"MediaSourceRef(kind={self.kind!r}, value=<redacted>)"
