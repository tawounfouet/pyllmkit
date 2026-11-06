"""Explicitly opted-in Google Gemini generateContent sync/async adapters."""

from __future__ import annotations

from dataclasses import dataclass, field

from pyllmkit.adapters.inference.cloud_http import (
    cloud_post_async,
    cloud_post_sync,
    require_live,
    validate_cloud_connection,
    validate_live_flag,
)
from pyllmkit.adapters.inference.google_gemini_mapping import (
    decode_gemini_response,
    encode_gemini_request,
    gemini_model_alias,
)
from pyllmkit.adapters.inference.security import ProviderConnectionConfig, ProviderProfile
from pyllmkit.application.inference import PreparedInvocation
from pyllmkit.domain.inference import InferenceResponse
from pyllmkit.protocols.credentials import CredentialResolverPort

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


@dataclass(frozen=True, slots=True)
class GoogleGeminiAdapter:
    config: ProviderConnectionConfig = field(repr=False)
    credentials: CredentialResolverPort = field(repr=False)
    allow_live: bool = False
    _test_transport: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        validate_cloud_connection(
            self.config, self.credentials, profile=ProviderProfile.GOOGLE,
            base_url=_BASE_URL,
        )
        validate_live_flag(self.allow_live)

    def invoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        require_live(self.allow_live)
        alias = gemini_model_alias(prepared)
        payload = encode_gemini_request(prepared)
        raw = cloud_post_sync(
            prepared, self.config, self.credentials,
            profile=ProviderProfile.GOOGLE, base_url=_BASE_URL,
            url=f"{_BASE_URL}/{alias}:generateContent",
            body=payload, auth="x-goog-api-key", test_transport=self._test_transport,
        )
        return decode_gemini_response(raw, prepared)


@dataclass(frozen=True, slots=True)
class AsyncGoogleGeminiAdapter:
    config: ProviderConnectionConfig = field(repr=False)
    credentials: CredentialResolverPort = field(repr=False)
    allow_live: bool = False
    _test_transport: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        validate_cloud_connection(
            self.config, self.credentials, profile=ProviderProfile.GOOGLE,
            base_url=_BASE_URL,
        )
        validate_live_flag(self.allow_live)

    async def ainvoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        require_live(self.allow_live)
        alias = gemini_model_alias(prepared)
        payload = encode_gemini_request(prepared)
        raw = await cloud_post_async(
            prepared, self.config, self.credentials,
            profile=ProviderProfile.GOOGLE, base_url=_BASE_URL,
            url=f"{_BASE_URL}/{alias}:generateContent",
            body=payload, auth="x-goog-api-key", test_transport=self._test_transport,
        )
        return decode_gemini_response(raw, prepared)
