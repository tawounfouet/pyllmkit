"""L2.3 passive URI/asset media refs, no I/O, no sensitive URL in repr."""

import socket
import urllib.request
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import DomainValidationError
from pyllmkit.domain.interactions import MediaSourceRef


def test_http_and_https_references_preserve_exact_values() -> None:
    for uri in (
        "http://example.org/image.png",
        "https://example.org/img?q=one%20two#fragment",
        "HTTPS://Example.Org:8443/image.png",
        "https://[2001:db8::1]:443/picture.png",
        "https://xn--bcher-kva.example/bild.jpg",
        "http://localhost:8080/image",
        "http://127.0.0.1/image",
    ):
        ref = MediaSourceRef(kind="uri", value=uri)
        assert ref.kind == "uri"
        assert ref.value == uri


def test_asset_reference_is_opaque_and_not_a_local_file_path() -> None:
    ref = MediaSourceRef(kind="asset", value=" asset-123 ")
    assert ref.kind == "asset"
    assert ref.value == " asset-123 "
    assert ref == MediaSourceRef("asset", " asset-123 ")
    assert hash(ref) == hash(MediaSourceRef("asset", " asset-123 "))


@pytest.mark.parametrize("bad", ["", " ", "\t\n", None, 42, b"raw"])
def test_asset_requires_nonblank_str(bad: object) -> None:
    with pytest.raises(DomainValidationError):
        MediaSourceRef(kind="asset", value=cast(str, bad))


@pytest.mark.parametrize(
    "uri",
    [
        "",
        "https:///image.png",
        "http://",
        "https:example.org/image.png",
        "ftp://example.org/a",
        "file:///etc/passwd",
        "data:image/png;base64,AAAA",
        "/var/tmp/image.png",
        "./image.png",
        "s3://bucket/key",
        "https://example.org:99999/image",
        "https://example.org:0/image",
        "https://example..org/image",
        "https://bad_host/image",
        "https://-bad.org/image",
        "https://example.org/a path",
        "https://example.org/%ZZ",
        "https://[not-ipv6]/image",
        "https://[fe80::1%25eth0]/image",
    ],
)
def test_invalid_uri_syntax_scheme_and_paths_are_rejected(uri: str) -> None:
    with pytest.raises(DomainValidationError, match="HTTP\\(S\\) URI"):
        MediaSourceRef(kind="uri", value=uri)


@pytest.mark.parametrize("kind", ["", "url", "file", "inline", "base64", None, 12])
def test_unknown_or_untyped_kind_rejected(kind: object) -> None:
    with pytest.raises(DomainValidationError, match="kind"):
        MediaSourceRef(kind=cast(str, kind), value="id-123")


def test_media_reference_is_frozen_value_and_has_no_data_bytes() -> None:
    source = MediaSourceRef("uri", "https://example.org/a.png")
    assert source == MediaSourceRef("uri", "https://example.org/a.png")
    with pytest.raises(FrozenInstanceError):
        source.value = "https://example.org/b.png"  # type: ignore[misc]
    with pytest.raises(TypeError):
        MediaSourceRef(kind="asset", value="a", uri="https://example.org/a")  # type: ignore[call-arg]


def test_full_url_never_appears_in_representation_or_validation_error() -> None:
    url = "https://alice:private-password@example.org/a.png?access_token=top-secret"
    source = MediaSourceRef("uri", url)
    assert "private-password" not in repr(source)
    assert "top-secret" not in repr(source)
    with pytest.raises(DomainValidationError) as exc:
        MediaSourceRef("uri", "file://example.org/secret?token=top-secret")
    assert "top-secret" not in str(exc.value)


def test_constructor_does_not_resolve_or_fetch_media(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("MediaSourceRef must never access the network")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    uri = MediaSourceRef("uri", "https://example.org/example.png")
    asset = MediaSourceRef("asset", "opaque-456")
    assert uri.value.endswith("example.png")
    assert asset.kind == "asset"
