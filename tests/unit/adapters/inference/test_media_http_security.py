"""Regression security boundaries for multimedia transport (no real network)."""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

import pytest

from pyllmkit.adapters.inference import media_http
from pyllmkit.application.inference import InvocationPortError


def _response(raw: bytes) -> MagicMock:
    response = MagicMock()
    response.read.return_value = raw
    response.__enter__.return_value = response
    return response


@pytest.mark.parametrize(
    "url",
    [
        "http://vidgen.x.ai/video.mp4",
        "https://127.0.0.1/video.mp4",
        "https://[::1]/video.mp4",
        "https://169.254.169.254/latest/meta-data",
        "https://evil.x.ai.attacker.invalid/video.mp4",
        "https://username:password@vidgen.x.ai/video.mp4",
        "https://vidgen.x.ai:444/video.mp4",
        "https://vidgen.x.ai/video.mp4#fragment",
        "https://localhost/video.mp4",
        "file:///etc/passwd",
    ],
)
def test_provider_download_rejects_untrusted_targets_before_dns(url: str) -> None:
    with (
        patch("socket.getaddrinfo", side_effect=AssertionError("unexpected DNS")) as dns,
        patch("urllib.request.build_opener", side_effect=AssertionError("unexpected network")),
        pytest.raises(InvocationPortError, match="unsafe_provider_destination"),
    ):
        media_http.fetch_provider_media_bytes(url)
    dns.assert_not_called()


def test_provider_download_rejects_private_dns_before_connection() -> None:
    dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
    with (
        patch("socket.getaddrinfo", return_value=dns),
        patch("urllib.request.build_opener", side_effect=AssertionError("network contacted")),
        pytest.raises(InvocationPortError, match="unsafe_provider_destination"),
    ):
        media_http.fetch_provider_media_bytes("https://vidgen.x.ai/out.mp4")


def test_provider_download_rejects_mixed_public_private_dns() -> None:
    dns = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443)),
    ]
    with (
        patch("socket.getaddrinfo", return_value=dns),
        patch("urllib.request.build_opener", side_effect=AssertionError("network contacted")),
        pytest.raises(InvocationPortError, match="unsafe_provider_destination"),
    ):
        media_http.fetch_provider_media_bytes("https://vidgen.x.ai/out.mp4")


def test_provider_download_uses_no_proxy_no_redirects_and_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(media_http, "MAX_MEDIA_DOWNLOAD_BYTES", 5)
    dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
    with (
        patch("socket.getaddrinfo", return_value=dns),
        patch("urllib.request.build_opener") as build,
    ):
        build.return_value.open.return_value = _response(b"012345")
        with pytest.raises(InvocationPortError, match="response_too_large"):
            media_http.fetch_provider_media_bytes("https://vidgen.x.ai/out.mp4")
        assert build.return_value.open.call_count == 1
        args = build.call_args.args
        assert any(isinstance(x, media_http._DenyMediaRedirect) for x in args)
        assert build.return_value.open.call_args.args[0].full_url.endswith("/out.mp4")


def test_provider_redirect_is_denied_without_following() -> None:
    handler = media_http._DenyMediaRedirect()
    request = media_http.urllib.request.Request("https://vidgen.x.ai/out.mp4")
    with pytest.raises(InvocationPortError, match="unsafe_provider_destination"):
        handler.redirect_request(
            request, None, 302, "redirect", {}, "http://127.0.0.1/internal",
        )


def test_api_response_body_is_bounded_instead_of_reading_entire_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(media_http, "MAX_PROVIDER_RESPONSE_BYTES", 3)
    response = _response(b"abcd")
    with (
        patch("urllib.request.urlopen", return_value=response),
        pytest.raises(InvocationPortError, match="response_too_large"),
    ):
        media_http.http_bytes("https://api.openai.com/v1/test")
    response.read.assert_called_once_with(4)


def test_media_data_uri_encoding_rejects_unbounded_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(media_http, "MAX_MEDIA_DOWNLOAD_BYTES", 2)
    with pytest.raises(InvocationPortError, match="response_too_large"):
        media_http.data_uri("video/mp4", b"123")
    assert media_http.data_uri("video/mp4", b"x") == "data:video/mp4;base64,eA=="


def test_unexpected_transport_exception_does_not_expose_secrets() -> None:
    with patch(
        "urllib.request.urlopen",
        side_effect=RuntimeError("authorization secret sk-proj-PRIVATE123456789"),
    ):
        with pytest.raises(InvocationPortError, match="provider_protocol_error") as error:
            media_http.http_bytes("https://api.x.ai/v1/test")
    assert "PRIVATE" not in str(error.value)


@pytest.mark.parametrize(
    "url",
    [
        "http://api.openai.com/v1/images/generations",
        "https://127.0.0.1/v1/images/generations",
        "https://api.openai.com.evil.example/v1/images/generations",
        "https://api.x.ai:8443/v1/videos/generations",
        "https://user:password@api.openai.com/v1/audio/speech",
    ],
)
def test_authenticated_api_rejects_bad_origin_before_dns(url: str) -> None:
    with (
        patch("socket.getaddrinfo", side_effect=AssertionError("DNS must not be used")) as dns,
        patch("urllib.request.build_opener", side_effect=AssertionError("No network")),
        pytest.raises(InvocationPortError, match="unsafe_provider_destination"),
    ):
        media_http.http_bytes(url, headers={"Authorization": "Bearer synthetic"})
    dns.assert_not_called()


def test_authenticated_api_pins_verified_peer_and_denies_redirect() -> None:
    dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
    with (
        patch("socket.getaddrinfo", return_value=dns),
        patch("urllib.request.build_opener") as build,
    ):
        build.return_value.open.return_value = _response(b"{}")
        media_http.http_bytes(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": "Bearer synthetic"},
            payload={"prompt": "offline"},
            method="POST",
        )
    args = build.call_args.args
    assert any(isinstance(x, media_http._PinnedHTTPSHandler) for x in args)
    assert any(isinstance(x, media_http._DenyMediaRedirect) for x in args)
    pinned = next(x for x in args if isinstance(x, media_http._PinnedHTTPSHandler))
    assert pinned._ip == "93.184.216.34"


def test_oversized_media_json_body_rejected_without_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(media_http, "MAX_PROVIDER_REQUEST_BYTES", 20)
    with (
        patch("urllib.request.urlopen", side_effect=AssertionError("unexpected network")) as http,
        patch("socket.getaddrinfo", side_effect=AssertionError("unexpected DNS")) as dns,
        pytest.raises(InvocationPortError, match="request_too_large"),
    ):
        media_http.http_bytes(
            "https://api.openai.com/v1/images/generations",
            payload={"prompt": "too many characters in this media request"},
            headers={"Authorization": "Bearer SYNTHETIC-TEST-NOT-REAL"},
            method="POST",
        )
    http.assert_not_called()
    dns.assert_not_called()
