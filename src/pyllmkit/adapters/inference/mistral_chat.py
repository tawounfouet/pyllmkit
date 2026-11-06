"""Opt-in Mistral Chat Completions HTTPX adapters, sync/async."""

from __future__ import annotations

from dataclasses import dataclass, field

from pyllmkit.adapters.inference.cloud_http import (
    cloud_post_async,
    cloud_post_sync,
    require_live,
    validate_cloud_connection,
    validate_live_flag,
)
from pyllmkit.adapters.inference.mistral_chat_mapping import (
    decode_mistral_chat_response,
    encode_mistral_chat_request,
)
from pyllmkit.adapters.inference.security import ProviderConnectionConfig, ProviderProfile
from pyllmkit.application.inference import PreparedInvocation
from pyllmkit.domain.inference import InferenceResponse
from pyllmkit.protocols.credentials import CredentialResolverPort

_URL = "https://api.mistral.ai/v1/chat/completions"


@dataclass(frozen=True, slots=True)
class MistralChatAdapter:
    config: ProviderConnectionConfig = field(repr=False)
    credentials: CredentialResolverPort = field(repr=False)
    allow_live: bool = False
    _test_transport: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        validate_cloud_connection(
            self.config, self.credentials, profile=ProviderProfile.MISTRAL, base_url=_URL,
        )
        validate_live_flag(self.allow_live)

    def invoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        require_live(self.allow_live)
        body = encode_mistral_chat_request(prepared)
        raw = cloud_post_sync(
            prepared, self.config, self.credentials, profile=ProviderProfile.MISTRAL,
            base_url=_URL, url=_URL, body=body, auth="bearer",
            test_transport=self._test_transport,
        )
        return decode_mistral_chat_response(raw, prepared)


@dataclass(frozen=True, slots=True)
class AsyncMistralChatAdapter:
    config: ProviderConnectionConfig = field(repr=False)
    credentials: CredentialResolverPort = field(repr=False)
    allow_live: bool = False
    _test_transport: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        validate_cloud_connection(
            self.config, self.credentials, profile=ProviderProfile.MISTRAL, base_url=_URL,
        )
        validate_live_flag(self.allow_live)

    async def ainvoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        require_live(self.allow_live)
        body = encode_mistral_chat_request(prepared)
        raw = await cloud_post_async(
            prepared, self.config, self.credentials, profile=ProviderProfile.MISTRAL,
            base_url=_URL, url=_URL, body=body, auth="bearer",
            test_transport=self._test_transport,
        )
        return decode_mistral_chat_response(raw, prepared)
