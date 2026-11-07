"""Service factory for CLI inference operations."""

from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass

from pyllmkit.adapters.inference import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    AnthropicMessagesAdapter,
    CredentialRef,
    EnvCredentialResolver,
    FakeInferenceAdapter,
    GoogleGeminiAdapter,
    MistralChatAdapter,
    NativeProviderStreamingAdapter,
    OllamaAdapter,
    OpenAIResponsesAdapter,
    ProviderConnectionConfig,
    RegisteredInferencePort,
    XAIResponsesAdapter,
)
from pyllmkit.adapters.inference.google_media import GoogleMediaAdapter
from pyllmkit.adapters.inference.media_http import (
    MediaDiagnostics,
    MediaGenerationOptions,
    media_output_kind,
)
from pyllmkit.adapters.inference.openai_media import OpenAIMediaAdapter
from pyllmkit.adapters.inference.xai_media import XAIMediaAdapter
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import (
    AsyncStreamingInferenceService,
    InferenceService,
    PreparedInvocation,
    StreamingInferenceService,
)
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.inference import (
    AudioOutput,
    DeploymentId,
    FinishReason,
    FinishReasonCode,
    ImageOutput,
    InferenceResponse,
    TextOutput,
    Usage,
    VideoOutput,
)
from pyllmkit.domain.interactions import MediaSourceRef
from pyllmkit.domain.modalities import Modality
from pyllmkit.domain.streaming import (
    ResponseCompleted,
    ResponseStarted,
    StreamEvent,
    TextDelta,
)
from pyllmkit.protocols.inference import (
    AsyncPreparedStreamingPort,
    InferencePort,
    PreparedStreamingPort,
)

from .mock_assets import create_mock_mp4, create_mock_png, create_mock_wav


@dataclass(slots=True)
class DynamicCliFakeInferenceAdapter:
    """Mock adapter reflecting the requested target model in offline mode."""

    def invoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        model_name = getattr(prepared, "native_model_alias", None) or (
            prepared.resolution.deployment.model_id.value if prepared.resolution else "unknown"
        )
        prov_name = (
            prepared.resolution.deployment.provider_id.value
            if (prepared.resolution and prepared.resolution.deployment.provider_id)
            else "ollama"
        )

        deployment = prepared.resolution.deployment if prepared.resolution else None
        modes = deployment.modalities if deployment else None

        if modes is not None and modes.can_output(Modality("image")) and not modes.can_output(Modality("text")):
            output = ImageOutput(
                media=MediaSourceRef(
                    "data",
                    create_mock_png(256, 256),
                ),
                mime_type="image/png",
                width=1024,
                height=1024,
                revised_prompt=f"Simulation de prompt révisé pour '{model_name}'",
            )
            return InferenceResponse(
                prepared.context.run_id,
                output,
                finish_reason=FinishReason(FinishReasonCode.STOP),
                usage=Usage(output_media_units=1),
            )

        if modes is not None and modes.can_output(Modality("audio")) and not modes.can_output(Modality("text")):
            first_msg_text = ""
            if prepared.request.messages and prepared.request.messages[0].content.parts:
                part0 = prepared.request.messages[0].content.parts[0]
                if hasattr(part0, "text"):
                    first_msg_text = getattr(part0, "text", "")
            output_aud = AudioOutput(
                media=MediaSourceRef(
                    "data",
                    create_mock_wav(duration=2.0),
                ),
                mime_type="audio/wav",
                duration_seconds=2.0,
                transcript=f"Ceci est une synthèse vocale simulée pour '{model_name}'.",
            )
            return InferenceResponse(
                prepared.context.run_id,
                output_aud,
                finish_reason=FinishReason(FinishReasonCode.STOP),
                usage=Usage(input_characters=len(first_msg_text) or 40, output_media_seconds=2.0),
            )

        if modes is not None and modes.can_output(Modality("video")) and not modes.can_output(Modality("text")):
            output_vid = VideoOutput(
                media=MediaSourceRef(
                    "data",
                    create_mock_mp4(),
                ),
                mime_type="video/mp4",
                duration_seconds=5.0,
                width=1280,
                height=720,
            )
            return InferenceResponse(
                prepared.context.run_id,
                output_vid,
                finish_reason=FinishReason(FinishReasonCode.STOP),
                usage=Usage(output_media_seconds=5.0),
            )

        simulated_text = (
            f"Bonjour ! Ceci est une réponse de simulation pour le modèle '{model_name}' "
            f"via le fournisseur '{prov_name}' (mode offline)."
        )
        return InferenceResponse(
            prepared.context.run_id,
            TextOutput(simulated_text),
            finish_reason=FinishReason(FinishReasonCode.STOP),
        )


@dataclass(slots=True)
class FakeAsyncStreamingAdapter:
    """Fake async streaming adapter yielding text deltas for CLI simulation."""

    async def astream_prepared(
        self, prepared: PreparedInvocation,
    ) -> AsyncIterator[StreamEvent]:
        run = prepared.context.run_id
        model_name = getattr(prepared, "native_model_alias", None) or (
            prepared.resolution.deployment.model_id.value if prepared.resolution else "unknown"
        )
        prov_name = (
            prepared.resolution.deployment.provider_id.value
            if (prepared.resolution and prepared.resolution.deployment.provider_id)
            else "ollama"
        )
        simulated_text = (
            f"Bonjour ! Ceci est une réponse de simulation en flux continu pour le modèle '{model_name}' "
            f"via le fournisseur '{prov_name}' (mode offline)."
        )
        seq = 0
        yield ResponseStarted(run_id=run, sequence=seq)
        seq += 1
        words = simulated_text.split(" ")
        for i, word in enumerate(words):
            delta = word if i == 0 else f" {word}"
            yield TextDelta(run_id=run, sequence=seq, delta=delta)
            seq += 1
        yield ResponseCompleted(
            run_id=run,
            sequence=seq,
            finish_reason=FinishReason(FinishReasonCode.STOP),
        )


@dataclass(slots=True)
class FakeStreamingAdapter:
    """Fake streaming adapter yielding text deltas for CLI simulation."""

    def stream_prepared(self, prepared: PreparedInvocation) -> Iterator[StreamEvent]:
        run = prepared.context.run_id
        model_name = getattr(prepared, "native_model_alias", None) or (
            prepared.resolution.deployment.model_id.value if prepared.resolution else "unknown"
        )
        prov_name = (
            prepared.resolution.deployment.provider_id.value
            if (prepared.resolution and prepared.resolution.deployment.provider_id)
            else "ollama"
        )
        simulated_text = (
            f"Bonjour ! Ceci est une réponse de simulation en flux continu pour le modèle '{model_name}' "
            f"via le fournisseur '{prov_name}' (mode offline)."
        )
        seq = 0
        yield ResponseStarted(run_id=run, sequence=seq)
        seq += 1
        words = simulated_text.split(" ")
        for i, word in enumerate(words):
            delta = word if i == 0 else f" {word}"
            yield TextDelta(run_id=run, sequence=seq, delta=delta)
            seq += 1
        yield ResponseCompleted(
            run_id=run,
            sequence=seq,
            finish_reason=FinishReason(FinishReasonCode.STOP),
        )


def _make_sync_factory(text: str) -> Callable[[ProviderConnectionConfig], FakeInferenceAdapter]:
    def factory(_cfg: ProviderConnectionConfig) -> FakeInferenceAdapter:
        return FakeInferenceAdapter(text)

    return factory


@dataclass(frozen=True, slots=True)
class MediaRoutingAdapter:
    """Dispatch to a media adapter when the deployment only outputs image/audio/video.

    Routing is based on the deployment's declared output modalities (catalog
    ``modalities_out``), never on model-name substrings.
    """

    text_adapter: InferencePort
    media_adapter: InferencePort

    def invoke(self, prepared: PreparedInvocation) -> InferenceResponse:
        if media_output_kind(prepared) is not None:
            return self.media_adapter.invoke(prepared)
        return self.text_adapter.invoke(prepared)


# Backward-compatible name (pre-0.3.x CLI wiring).
CompositeOpenAIAdapter = MediaRoutingAdapter


def _make_live_sync_factory(
    prov_name: str,
    env_resolver: EnvCredentialResolver,
    media_options: MediaGenerationOptions | None = None,
    diagnostics: MediaDiagnostics | None = None,
) -> Callable[[ProviderConnectionConfig], InferencePort]:
    opts = media_options or MediaGenerationOptions()
    if prov_name == "ollama":
        return lambda cfg: OllamaAdapter(cfg, allow_live=True)
    if prov_name == "openai":
        return lambda cfg: MediaRoutingAdapter(
            text_adapter=OpenAIResponsesAdapter(cfg, env_resolver, allow_live=True),
            media_adapter=OpenAIMediaAdapter(cfg, env_resolver, allow_live=True, options=opts, diagnostics=diagnostics),
        )
    if prov_name == "anthropic":
        return lambda cfg: AnthropicMessagesAdapter(cfg, env_resolver, allow_live=True)
    if prov_name == "google":
        return lambda cfg: MediaRoutingAdapter(
            text_adapter=GoogleGeminiAdapter(cfg, env_resolver, allow_live=True),
            media_adapter=GoogleMediaAdapter(cfg, env_resolver, allow_live=True, options=opts, diagnostics=diagnostics),
        )
    if prov_name == "xai":
        return lambda cfg: MediaRoutingAdapter(
            text_adapter=XAIResponsesAdapter(cfg, env_resolver, allow_live=True),
            media_adapter=XAIMediaAdapter(cfg, env_resolver, allow_live=True, options=opts, diagnostics=diagnostics),
        )
    if prov_name == "mistral":
        return lambda cfg: MistralChatAdapter(cfg, env_resolver, allow_live=True)
    raise ValueError(f"Unknown live provider: {prov_name}")


def _make_env_resolver() -> EnvCredentialResolver:
    return EnvCredentialResolver({
        CredentialRef("openai"): "OPENAI_API_KEY",
        CredentialRef("anthropic"): "ANTHROPIC_API_KEY",
        CredentialRef("google"): "GEMINI_API_KEY",
        CredentialRef("xai"): "XAI_API_KEY",
        CredentialRef("mistral"): "MISTRAL_API_KEY",
    })


def create_cli_inference_service(
    catalog: InMemoryCatalog,
    *,
    mock: bool = True,
    media_options: MediaGenerationOptions | None = None,
    diagnostics: MediaDiagnostics | None = None,
) -> InferenceService:
    """Instantiate an InferenceService configured for CLI operations."""
    resolver = DeploymentResolver(catalog.models, catalog.deployments, catalog.providers)
    registry = AdapterRegistry()
    aliases: dict[DeploymentId, str] = {}

    connections = {
        "ollama": ProviderConnectionConfig.ollama_local(),
        "openai": ProviderConnectionConfig.openai(CredentialRef("openai")),
        "anthropic": ProviderConnectionConfig.anthropic(CredentialRef("anthropic")),
        "google": ProviderConnectionConfig.google(CredentialRef("google")),
        "xai": ProviderConnectionConfig.xai(CredentialRef("xai")),
        "mistral": ProviderConnectionConfig.mistral(CredentialRef("mistral")),
    }

    registered_keys: set[AdapterKey] = set()
    deployments = catalog.deployments.list()
    for dep in deployments:
        aliases[dep.id] = dep.model_id.value
        key = AdapterKey(dep.provider_id, dep.runtime)

        if key in registered_keys:
            continue

        prov_name = dep.provider_id.value if dep.provider_id else "ollama"
        conn = connections.get(prov_name)
        if conn is None:
            continue

        if mock:
            registry.register(
                AdapterRegistration(
                    key,
                    conn,
                    sync_factory=lambda _cfg: DynamicCliFakeInferenceAdapter(),
                )
            )
        else:
            registry.register(
                AdapterRegistration(
                    key,
                    conn,
                    sync_factory=_make_live_sync_factory(
                        prov_name, _make_env_resolver(), media_options, diagnostics,
                    ),
                )
            )
        registered_keys.add(key)

    port = RegisteredInferencePort(registry)
    return InferenceService(resolver, port, aliases)


def create_cli_streaming_service(
    catalog: InMemoryCatalog,
    *,
    mock: bool = True,
) -> StreamingInferenceService:
    """Instantiate a StreamingInferenceService configured for CLI operations."""
    resolver = DeploymentResolver(catalog.models, catalog.deployments, catalog.providers)
    bindings: dict[DeploymentId, PreparedStreamingPort] = {}
    aliases: dict[DeploymentId, str] = {}

    connections = {
        "ollama": ProviderConnectionConfig.ollama_local(),
        "openai": ProviderConnectionConfig.openai(CredentialRef("openai")),
        "anthropic": ProviderConnectionConfig.anthropic(CredentialRef("anthropic")),
        "google": ProviderConnectionConfig.google(CredentialRef("google")),
        "xai": ProviderConnectionConfig.xai(CredentialRef("xai")),
        "mistral": ProviderConnectionConfig.mistral(CredentialRef("mistral")),
    }

    env_resolver = _make_env_resolver()

    deployments = catalog.deployments.list()
    for dep in deployments:
        aliases[dep.id] = dep.model_id.value
        prov_name = dep.provider_id.value if dep.provider_id else "ollama"
        conn = connections.get(prov_name)
        if conn is None:
            continue

        if mock:
            bindings[dep.id] = FakeStreamingAdapter()
        else:
            creds = None if prov_name == "ollama" else env_resolver
            bindings[dep.id] = NativeProviderStreamingAdapter(
                config=conn,
                credentials=creds,
                allow_live=True,
            )

    return StreamingInferenceService(resolver, bindings, aliases)


def create_cli_async_streaming_service(
    catalog: InMemoryCatalog,
    *,
    mock: bool = True,
) -> AsyncStreamingInferenceService:
    """Instantiate an AsyncStreamingInferenceService configured for CLI operations."""
    resolver = DeploymentResolver(catalog.models, catalog.deployments, catalog.providers)
    bindings: dict[DeploymentId, AsyncPreparedStreamingPort] = {}
    aliases: dict[DeploymentId, str] = {}

    connections = {
        "ollama": ProviderConnectionConfig.ollama_local(),
        "openai": ProviderConnectionConfig.openai(CredentialRef("openai")),
        "anthropic": ProviderConnectionConfig.anthropic(CredentialRef("anthropic")),
        "google": ProviderConnectionConfig.google(CredentialRef("google")),
        "xai": ProviderConnectionConfig.xai(CredentialRef("xai")),
        "mistral": ProviderConnectionConfig.mistral(CredentialRef("mistral")),
    }

    env_resolver = _make_env_resolver()

    deployments = catalog.deployments.list()
    for dep in deployments:
        aliases[dep.id] = dep.model_id.value
        prov_name = dep.provider_id.value if dep.provider_id else "ollama"
        conn = connections.get(prov_name)
        if conn is None:
            continue

        if mock:
            bindings[dep.id] = FakeAsyncStreamingAdapter()
        else:
            creds = None if prov_name == "ollama" else env_resolver
            bindings[dep.id] = NativeProviderStreamingAdapter(
                config=conn,
                credentials=creds,
                allow_live=True,
            )

    return AsyncStreamingInferenceService(resolver, bindings, aliases)

