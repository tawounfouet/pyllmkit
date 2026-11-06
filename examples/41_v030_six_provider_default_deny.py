"""v0.3.0 default-deny smoke: six providers, no HTTPX and no API keys.

This is a security diagnostic of the *opt-in gate*, not an inference demo.
It intentionally passes a placeholder object: authorization must reject
before parsing the request or resolving any credential.
For genuine offline invocation see 38_six_provider_offline_registry.py.
"""

import asyncio

from pyllmkit.adapters.inference import (
    AnthropicMessagesAdapter,
    AsyncAnthropicMessagesAdapter,
    AsyncGoogleGeminiAdapter,
    AsyncMistralChatAdapter,
    AsyncOllamaAdapter,
    AsyncOpenAIResponsesAdapter,
    AsyncXAIResponsesAdapter,
    CredentialRef,
    EnvCredentialResolver,
    GoogleGeminiAdapter,
    MistralChatAdapter,
    OllamaAdapter,
    OpenAIResponsesAdapter,
    ProviderConnectionConfig,
    XAIResponsesAdapter,
)
from pyllmkit.application.inference import InvocationPortError


def _must_refuse(operation) -> None:
    try:
        operation()
    except InvocationPortError as error:
        assert error.code == "live_authorization_required"
        assert str(error) == error.code
    else:
        raise AssertionError("an unauthorized operation was not refused")


async def _amust_refuse(operation) -> None:
    try:
        await operation()
    except InvocationPortError as error:
        assert error.code == "live_authorization_required"
        assert str(error) == error.code
    else:
        raise AssertionError("an unauthorized async operation was not refused")


def main() -> None:
    ref = CredentialRef("synthetic-example-no-secret")
    # Explicit empty environment: no credential can be resolved.
    credentials = EnvCredentialResolver({ref: "PYLLMKIT_NO_REAL_KEY"}, environ={})
    providers = (
        ("openai", ProviderConnectionConfig.openai(ref),
         OpenAIResponsesAdapter, AsyncOpenAIResponsesAdapter),
        ("anthropic", ProviderConnectionConfig.anthropic(ref),
         AnthropicMessagesAdapter, AsyncAnthropicMessagesAdapter),
        ("google", ProviderConnectionConfig.google(ref),
         GoogleGeminiAdapter, AsyncGoogleGeminiAdapter),
        ("xai", ProviderConnectionConfig.xai(ref),
         XAIResponsesAdapter, AsyncXAIResponsesAdapter),
        ("mistral", ProviderConnectionConfig.mistral(ref),
         MistralChatAdapter, AsyncMistralChatAdapter),
    )

    async def check_async() -> None:
        for name, config, _sync_cls, async_cls in providers:
            instance = async_cls(config, credentials)
            assert instance.allow_live is False
            await _amust_refuse(lambda instance=instance: instance.ainvoke(None))
            print(f"{name} async: default deny")

        local = AsyncOllamaAdapter(ProviderConnectionConfig.ollama_local())
        assert local.allow_live is False
        await _amust_refuse(lambda: local.ainvoke(None))
        print("ollama async: default deny")

    for name, config, sync_cls, _async_cls in providers:
        instance = sync_cls(config, credentials)
        assert instance.allow_live is False
        _must_refuse(lambda instance=instance: instance.invoke(None))
        print(f"{name} sync: default deny")

    local = OllamaAdapter(ProviderConnectionConfig.ollama_local())
    assert local.allow_live is False
    _must_refuse(lambda: local.invoke(None))
    print("ollama sync: default deny")
    asyncio.run(check_async())
    print("12 guards verified offline; 0 sockets, 0 real credentials.")


if __name__ == "__main__":
    main()
