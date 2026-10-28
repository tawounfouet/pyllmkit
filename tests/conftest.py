"""Project test isolation: never use network or provider credentials.

The guard applies throughout each pytest test (not during pytest startup).
Its scope is a test-environment assertion, not a machine/network sandbox.
"""

import socket

import pytest


@pytest.fixture(autouse=True)
def offline_domain_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make network attempts fail immediately and hide known LLM credentials."""

    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("Network access is forbidden in PyLLMKit Phase 1 tests")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket.socket, "connect_ex", reject_network)
    monkeypatch.setattr(socket.socket, "bind", reject_network)
    monkeypatch.setattr(socket, "create_connection", reject_network)
    for key in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "MISTRAL_API_KEY",
        "XAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AZURE_OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
