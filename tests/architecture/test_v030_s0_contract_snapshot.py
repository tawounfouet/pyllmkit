"""S0 v0.3.0 API inventory checks: provider-free, no invocation/network.

The assertions protect public entrypoints while the independent S1 profile
and S2 native MockTransport conformance matrix are being designed.
This does NOT claim six-provider behavioral parity.
"""

from inspect import isasyncgenfunction, iscoroutinefunction, signature

import pytest

from pyllmkit.adapters.inference import (
    AnthropicMessagesAdapter,
    AsyncAnthropicMessagesAdapter,
    AsyncGoogleGeminiAdapter,
    AsyncMistralChatAdapter,
    AsyncOllamaAdapter,
    AsyncOpenAIResponsesAdapter,
    AsyncXAIResponsesAdapter,
    GoogleGeminiAdapter,
    MistralChatAdapter,
    NativeProviderStreamingAdapter,
    OllamaAdapter,
    OpenAIResponsesAdapter,
    ProviderProfile,
    XAIResponsesAdapter,
    normalize_http_failure,
)
from pyllmkit.adapters.inference.anthropic_messages_mapping import (
    decode_anthropic_messages_response,
    encode_anthropic_messages_request,
)
from pyllmkit.adapters.inference.google_gemini_mapping import (
    decode_gemini_response,
    encode_gemini_request,
)
from pyllmkit.adapters.inference.mistral_chat_mapping import (
    decode_mistral_chat_response,
    encode_mistral_chat_request,
)
from pyllmkit.adapters.inference.ollama_mapping import (
    decode_ollama_response,
    encode_ollama_request,
)
from pyllmkit.adapters.inference.openai_responses_mapping import (
    decode_openai_responses_response,
    encode_openai_responses_request,
)
from pyllmkit.adapters.inference.xai_responses_mapping import (
    decode_xai_responses_response,
    encode_xai_responses_request,
)
from pyllmkit.application.inference import (
    AsyncInferenceService,
    AsyncStreamingInferenceService,
    InferenceService,
    StreamingInferenceService,
)
from pyllmkit.domain.inference import GENERATION_PARAMETER_NAMES
from pyllmkit.protocols.inference import (
    AsyncInferencePort,
    AsyncPreparedStreamingPort,
    InferencePort,
    PreparedStreamingPort,
)


@pytest.mark.parametrize(
    ("cls", "method", "names"),
    [
        (InferencePort, "invoke", ("self", "prepared")),
        (AsyncInferencePort, "ainvoke", ("self", "prepared")),
        (PreparedStreamingPort, "stream_prepared", ("self", "prepared")),
        (AsyncPreparedStreamingPort, "astream_prepared", ("self", "prepared")),
        (InferenceService, "invoke", ("self", "request", "support_snapshot")),
        (AsyncInferenceService, "ainvoke", ("self", "request", "support_snapshot")),
        (StreamingInferenceService, "open_stream", ("self", "request", "support_snapshot")),
        (
            AsyncStreamingInferenceService,
            "open_astream",
            ("self", "request", "support_snapshot"),
        ),
    ],
)
def test_public_inference_boundary_signature(cls: type, method: str, names: tuple[str, ...]) -> None:
    assert tuple(signature(getattr(cls, method)).parameters) == names


@pytest.mark.parametrize(
    ("sync_type", "async_type"),
    [
        (OpenAIResponsesAdapter, AsyncOpenAIResponsesAdapter),
        (AnthropicMessagesAdapter, AsyncAnthropicMessagesAdapter),
        (GoogleGeminiAdapter, AsyncGoogleGeminiAdapter),
        (XAIResponsesAdapter, AsyncXAIResponsesAdapter),
        (MistralChatAdapter, AsyncMistralChatAdapter),
        (OllamaAdapter, AsyncOllamaAdapter),
    ],
)
def test_six_native_adapter_entrypoints_exist(sync_type: type, async_type: type) -> None:
    assert tuple(signature(sync_type.invoke).parameters) == ("self", "prepared")
    assert tuple(signature(async_type.ainvoke).parameters) == ("self", "prepared")
    assert iscoroutinefunction(async_type.ainvoke)


def test_native_streaming_ports_are_pull_based() -> None:
    assert tuple(signature(NativeProviderStreamingAdapter.stream_prepared).parameters) == (
        "self", "prepared",
    )
    assert tuple(signature(NativeProviderStreamingAdapter.astream_prepared).parameters) == (
        "self", "prepared",
    )
    assert isasyncgenfunction(NativeProviderStreamingAdapter.astream_prepared)
    # Port's "async def" is a generator in the implementation, not a coroutine to await.
    assert not iscoroutinefunction(AsyncPreparedStreamingPort.astream_prepared)


def test_all_six_provider_profiles_exist() -> None:
    assert {profile.value for profile in ProviderProfile} == {
        "openai", "anthropic", "google", "xai", "mistral", "ollama",
    }


@pytest.mark.parametrize(
    ("encode", "decode"),
    [
        (encode_openai_responses_request, decode_openai_responses_response),
        (encode_anthropic_messages_request, decode_anthropic_messages_response),
        (encode_gemini_request, decode_gemini_response),
        (encode_xai_responses_request, decode_xai_responses_response),
        (encode_mistral_chat_request, decode_mistral_chat_response),
        (encode_ollama_request, decode_ollama_response),
    ],
)
def test_six_native_text_codec_pairs_exist(encode: object, decode: object) -> None:
    assert callable(encode)
    assert callable(decode)


def test_canonical_generation_parameter_inventory() -> None:
    assert set(GENERATION_PARAMETER_NAMES) == {
        "temperature", "top_p", "top_k", "max_output_tokens",
        "seed", "stop_sequences", "presence_penalty", "frequency_penalty",
    }


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "invalid_request"),
        (401, "authentication_failed"),
        (403, "permission_denied"),
        (404, "model_not_found"),
        (408, "provider_timeout"),
        (429, "rate_limited"),
        (500, "provider_overloaded"),
        (504, "provider_timeout"),
        (599, "provider_overloaded"),
        (302, "provider_protocol_error"),
    ],
)
def test_status_only_failure_baseline(status: int, code: str) -> None:
    error = normalize_http_failure(status)
    assert error.code == code
    assert str(error) == code


@pytest.mark.parametrize("bad_status", [0, -1, 600, 200.0, "401", True])
def test_invalid_status_is_rejected(bad_status: object) -> None:
    with pytest.raises(ValueError, match="invalid_http_status"):
        normalize_http_failure(bad_status)  # type: ignore[arg-type]
