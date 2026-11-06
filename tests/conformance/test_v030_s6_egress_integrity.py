"""S6: endpoint integrity before credential resolution or native transport.

A hermetic test-only transport records all attempted requests. These tests
must never contact a provider, read real environment credentials or imply
that DNS/peer-IP/TLS are qualified by a MockTransport.
"""

import asyncio

import httpx
import pytest

from pyllmkit.adapters.inference.cloud_http import cloud_post_async, cloud_post_sync
from pyllmkit.adapters.inference.security import ProviderProfile
from pyllmkit.application.inference import InvocationPortError
from pyllmkit.protocols.credentials import CredentialRef, SecretValue
from tests.conformance.providers import adapter, prepared

_CLOUD_PROVIDERS = ("openai", "anthropic", "google", "xai", "mistral")
_BAD_DESTINATIONS = (
    "https://evil.example/v1/responses",
    "http://127.0.0.1:11434/api/chat",
    "https://api.openai.com.evil.example/v1/responses",
    "https://api.openai.com@evil.example/v1/responses",
)


class RecordingResolver:
    """A deliberately synthetic credential source: no environment reads."""

    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, reference: CredentialRef) -> SecretValue:
        assert isinstance(reference, CredentialRef)
        self.calls += 1
        return SecretValue("SYNTHETIC-NOT-A-REAL-KEY")


def _normal_url(provider: str, base: str) -> str:
    if provider == "google":
        return base + "/synthetic-text-model:generateContent"
    return base


@pytest.mark.parametrize("provider", _CLOUD_PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
@pytest.mark.parametrize("destination", _BAD_DESTINATIONS)
def test_cloud_rejects_any_unapproved_endpoint_before_secret_and_transport(
    provider: str, async_mode: bool, destination: str,
) -> None:
    requested: list[httpx.Request] = []

    def capture(request: httpx.Request) -> httpx.Response:
        requested.append(request)
        return httpx.Response(
            200, headers={"content-type": "application/json"},
            json={"unsafe": "transport contact must never happen"},
        )

    transport = httpx.MockTransport(capture)
    native = adapter(provider, transport=transport, async_mode=async_mode)
    resolver = RecordingResolver()
    options = {
        "prepared": prepared(provider),
        "config": native.config,
        "credentials": resolver,
        "profile": ProviderProfile(provider),
        "base_url": native.config.endpoint_url,
        "url": destination,
        "body": b"{}",
        "auth": "x-goog-api-key" if provider == "google" else "bearer",
        "test_transport": transport,
    }

    with pytest.raises(InvocationPortError, match="adapter_connection_invalid") as error:
        if async_mode:
            asyncio.run(cloud_post_async(**options))
        else:
            cloud_post_sync(**options)

    assert error.value.code == "adapter_connection_invalid"
    assert resolver.calls == 0
    assert requested == []


@pytest.mark.parametrize("provider", _CLOUD_PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
def test_cloud_valid_endpoint_still_works_with_synthetic_credential(
    provider: str, async_mode: bool,
) -> None:
    requests: list[httpx.Request] = []

    def capture(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200, headers={"content-type": "application/json"},
            content=b'{"result":"synthetic"}',
        )

    transport = httpx.MockTransport(capture)
    native = adapter(provider, transport=transport, async_mode=async_mode)
    resolver = RecordingResolver()
    options = {
        "prepared": prepared(provider),
        "config": native.config,
        "credentials": resolver,
        "profile": ProviderProfile(provider),
        "base_url": native.config.endpoint_url,
        "url": _normal_url(provider, native.config.endpoint_url),
        "body": b"{}",
        "auth": "x-goog-api-key" if provider == "google" else "bearer",
        "test_transport": transport,
    }
    raw = (
        asyncio.run(cloud_post_async(**options))
        if async_mode else cloud_post_sync(**options)
    )
    assert raw == b'{"result":"synthetic"}'
    assert len(requests) == 1
    assert resolver.calls == 1
    assert "SYNTHETIC-NOT-A-REAL-KEY" not in repr(native)


@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
def test_openai_config_mutated_after_construction_is_rejected_at_call(
    async_mode: bool,
) -> None:
    calls: list[httpx.Request] = []

    def capture(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            429, headers={"content-type": "application/json"},
            json={"error": "synthetic"},
        )

    native = adapter(
        "openai", transport=httpx.MockTransport(capture), async_mode=async_mode,
    )
    # Frozen dataclass immutability is not a security boundary against
    # deliberate object.__setattr__ tampering between init and use.
    object.__setattr__(native.config, "endpoint_url", "https://untrusted.example/v1/responses")
    with pytest.raises(InvocationPortError, match="adapter_connection_invalid") as error:
        if async_mode:
            asyncio.run(native.ainvoke(prepared("openai")))
        else:
            native.invoke(prepared("openai"))
    assert error.value.code == "adapter_connection_invalid"
    assert calls == []


_OLLAMA_MALFORMED_URLS = (
    "http://user:pass@127.0.0.1:11434/api/chat",
    "http://127.0.0.1:11434/api/chat?token=unsafe",
    "https://127.0.0.1:11434/api/chat",
    "http://[::1]:11434/api/chat#fragment",
)


@pytest.mark.parametrize("destination", _OLLAMA_MALFORMED_URLS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
def test_ollama_mutated_destination_is_rejected_as_noncanonical(
    destination: str, async_mode: bool,
) -> None:
    calls: list[httpx.Request] = []

    def capture(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            429, headers={"content-type": "application/json"},
            json={"error": "synthetic"},
        )

    native = adapter(
        "ollama", transport=httpx.MockTransport(capture), async_mode=async_mode,
    )
    object.__setattr__(native.config, "endpoint_url", destination)
    with pytest.raises(InvocationPortError, match="adapter_connection_invalid") as error:
        if async_mode:
            asyncio.run(native.ainvoke(prepared("ollama")))
        else:
            native.invoke(prepared("ollama"))
    assert error.value.code == "adapter_connection_invalid"
    assert calls == []
