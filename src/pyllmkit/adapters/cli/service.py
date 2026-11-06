"""Service factory for CLI inference operations."""

from collections.abc import Callable, Iterator
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
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import (
    InferenceService,
    PreparedInvocation,
    StreamingInferenceService,
)
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.inference import DeploymentId, FinishReason, FinishReasonCode
from pyllmkit.domain.streaming import (
    ResponseCompleted,
    ResponseStarted,
    StreamEvent,
    TextDelta,
)
from pyllmkit.protocols.inference import InferencePort, PreparedStreamingPort


@dataclass(slots=True)
class FakeStreamingAdapter:
    """Fake streaming adapter yielding text deltas for CLI simulation."""

    simulated_text: str

    def stream_prepared(self, prepared: PreparedInvocation) -> Iterator[StreamEvent]:
        run = prepared.context.run_id
        seq = 0
        yield ResponseStarted(run_id=run, sequence=seq)
        seq += 1
        words = self.simulated_text.split(" ")
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


def _make_live_sync_factory(
    prov_name: str,
    env_resolver: EnvCredentialResolver,
) -> Callable[[ProviderConnectionConfig], InferencePort]:
    if prov_name == "ollama":
        return lambda cfg: OllamaAdapter(cfg, allow_live=True)
    if prov_name == "openai":
        return lambda cfg: OpenAIResponsesAdapter(cfg, env_resolver, allow_live=True)
    if prov_name == "anthropic":
        return lambda cfg: AnthropicMessagesAdapter(cfg, env_resolver, allow_live=True)
    if prov_name == "google":
        return lambda cfg: GoogleGeminiAdapter(cfg, env_resolver, allow_live=True)
    if prov_name == "xai":
        return lambda cfg: XAIResponsesAdapter(cfg, env_resolver, allow_live=True)
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

    deployments = catalog.deployments.list()
    for dep in deployments:
        aliases[dep.id] = dep.model_id.value
        key = AdapterKey(dep.provider_id, dep.runtime)

        prov_name = dep.provider_id.value if dep.provider_id else "ollama"
        conn = connections.get(prov_name)
        if conn is None:
            continue

        if mock:
            # Deterministic mock adapter for offline and test runs
            simulated_text = (
                f"Bonjour ! Ceci est une réponse de simulation pour le modèle '{dep.model_id.value}' "
                f"via le fournisseur '{prov_name}' (mode offline)."
            )
            registry.register(
                AdapterRegistration(
                    key,
                    conn,
                    sync_factory=_make_sync_factory(simulated_text),
                )
            )
        else:
            registry.register(
                AdapterRegistration(
                    key,
                    conn,
                    sync_factory=_make_live_sync_factory(prov_name, _make_env_resolver()),
                )
            )

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
            simulated_text = (
                f"Bonjour ! Ceci est une réponse de simulation en flux continu pour le modèle '{dep.model_id.value}' "
                f"via le fournisseur '{prov_name}' (mode offline)."
            )
            bindings[dep.id] = FakeStreamingAdapter(simulated_text)
        else:
            creds = None if prov_name == "ollama" else env_resolver
            bindings[dep.id] = NativeProviderStreamingAdapter(
                config=conn,
                credentials=creds,
                allow_live=True,
            )

    return StreamingInferenceService(resolver, bindings, aliases)

