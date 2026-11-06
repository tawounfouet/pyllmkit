"""S4 conversation history contract across six native request encoders.

The shared contract is conservative: no role or text may be silently
merged, reordered, re-labeled or discarded. Valid native restrictions
remain explicit rather than being faked into universal compatibility.
"""

import json
from dataclasses import replace

import pytest

from pyllmkit.adapters.inference.anthropic_messages_mapping import (
    encode_anthropic_messages_request,
)
from pyllmkit.adapters.inference.google_gemini_mapping import encode_gemini_request
from pyllmkit.adapters.inference.mistral_chat_mapping import encode_mistral_chat_request
from pyllmkit.adapters.inference.ollama_mapping import encode_ollama_request
from pyllmkit.adapters.inference.openai_responses_mapping import (
    encode_openai_responses_request,
)
from pyllmkit.adapters.inference.xai_responses_mapping import (
    encode_xai_responses_request,
)
from pyllmkit.application.inference import InvocationPortError, PreparedInvocation
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from tests.conformance.providers import PROVIDERS, prepared

_ENCODERS = {
    "openai": encode_openai_responses_request,
    "anthropic": encode_anthropic_messages_request,
    "google": encode_gemini_request,
    "xai": encode_xai_responses_request,
    "mistral": encode_mistral_chat_request,
    "ollama": encode_ollama_request,
}

_GOOD_HISTORY = (Role.SYSTEM, Role.USER, Role.ASSISTANT, Role.USER)
_RESTRICTED_SEQUENCE = frozenset({"anthropic", "google"})
_NO_DEVELOPER = frozenset({"anthropic", "google", "mistral", "ollama"})


def _case(provider: str, roles: tuple[Role, ...]) -> PreparedInvocation:
    base = prepared(provider)
    messages = tuple(
        Message(role, Content((TextContent(f"history_{index}_{role.value}_été"),)))
        for index, role in enumerate(roles)
    )
    return replace(base, request=replace(base.request, messages=messages))


def _wire_history(provider: str, raw: bytes) -> list[tuple[str, str]]:
    body = json.loads(raw)
    assert isinstance(body, dict)
    if provider in {"openai", "xai"}:
        data = body["input"]
    elif provider == "google":
        data = body["contents"]
    else:
        data = body["messages"]
    assert isinstance(data, list)
    values: list[tuple[str, str]] = []
    if provider == "anthropic" and "system" in body:
        blocks = body["system"]
        assert isinstance(blocks, list) and len(blocks) == 1
        values.append(("system", blocks[0]["text"]))
    elif provider == "google" and "systemInstruction" in body:
        values.append(("system", body["systemInstruction"]["parts"][0]["text"]))
    for part in data:
        assert isinstance(part, dict)
        role = part["role"]
        if provider == "google":
            role = "assistant" if role == "model" else role
            text = part["parts"][0]["text"]
        elif provider == "anthropic":
            text = part["content"][0]["text"]
        else:
            text = part["content"]
        assert isinstance(role, str) and isinstance(text, str)
        values.append((role, text))
    return values


@pytest.mark.parametrize("provider", PROVIDERS)
def test_supported_multiturn_text_history_is_lossless(provider: str) -> None:
    case = _case(provider, _GOOD_HISTORY)
    observed = _wire_history(provider, _ENCODERS[provider](case))
    assert observed == [
        (role.value, f"history_{index}_{role.value}_été")
        for index, role in enumerate(_GOOD_HISTORY)
    ]


_CASES: tuple[tuple[str, tuple[Role, ...]], ...] = (
    ("double_user", (Role.USER, Role.USER)),
    ("assistant_last", (Role.USER, Role.ASSISTANT)),
    ("system_not_first", (Role.USER, Role.SYSTEM, Role.USER)),
    ("double_system", (Role.SYSTEM, Role.SYSTEM, Role.USER)),
    ("developer", (Role.DEVELOPER, Role.USER)),
)


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize(("scenario", "roles"), _CASES)
def test_history_role_restrictions_are_explicit_not_coerced(
    provider: str, scenario: str, roles: tuple[Role, ...],
) -> None:
    case = _case(provider, roles)
    if scenario == "developer":
        prohibited = provider in _NO_DEVELOPER
        error = "unsupported_message_role"
    elif scenario == "double_user":
        prohibited = provider in _RESTRICTED_SEQUENCE
        error = "unsupported_message_structure"
    else:
        prohibited = provider in _RESTRICTED_SEQUENCE or provider == "mistral"
        error = "unsupported_message_structure"
    if prohibited:
        with pytest.raises(InvocationPortError, match=error):
            _ENCODERS[provider](case)
    else:
        observed = _wire_history(provider, _ENCODERS[provider](case))
        assert observed == [
            (role.value, f"history_{index}_{role.value}_été")
            for index, role in enumerate(roles)
        ]
