"""Default reference catalog provider for PyLLMKit CLI."""

from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.domain.capabilities import (
    Capability,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    SupportLevel,
)
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId

from .discovery import load_discovered_models
from .model_specs import get_model_spec

_PROVIDER_MODALITIES: dict[str, tuple[str, ...]] = {
    "google": ("text", "image", "audio", "video"),
    "openai": ("text", "image", "audio"),
    "anthropic": ("text", "image"),
    "xai": ("text", "image"),
    "mistral": ("text", "image"),
    "ollama": ("text", "image"),
}

_PROVIDER_OUTPUT_MODALITIES: dict[str, tuple[str, ...]] = {
    "google": ("text", "image", "audio", "video"),
    "openai": ("text", "image", "audio"),
    "anthropic": ("text",),
    "xai": ("text", "image", "video"),
    "mistral": ("text",),
    "ollama": ("text",),
}


def create_reference_catalog() -> InMemoryCatalog:
    """Instantiate an InMemoryCatalog with standard reference models, deployments and discovered models."""
    catalog = InMemoryCatalog()
    text_modes = ModalitySet(frozenset({Modality("text")}), frozenset({Modality("text")}))

    streaming_cap = CapabilitySet((
        Capability(
            CapabilityId("streaming"),
            CapabilitySupport(SupportLevel.NATIVE),
        ),
    ))

    # Reference models for the 6 canonical providers
    reference_models_data = [
        # Ollama (Local)
        ("llama3.2", "meta", "ollama", "ollama", "local"),
        ("llama3.1", "meta", "ollama", "ollama", "local"),
        ("llama3", "meta", "ollama", "ollama", "local"),
        ("mistral", "mistral", "ollama", "ollama", "local"),
        ("qwen2.5", "alibaba", "ollama", "ollama", "local"),
        ("phi3", "microsoft", "ollama", "ollama", "local"),
        ("deepseek-r1", "deepseek", "ollama", "ollama", "local"),

        # OpenAI (Cloud)
        ("gpt-4o", "openai", "openai", "cloud", "global"),
        ("gpt-4o-mini", "openai", "openai", "cloud", "global"),
        ("gpt-4-turbo", "openai", "openai", "cloud", "global"),
        ("gpt-4", "openai", "openai", "cloud", "global"),
        ("gpt-3.5-turbo", "openai", "openai", "cloud", "global"),
        ("o1", "openai", "openai", "cloud", "global"),
        ("o1-preview", "openai", "openai", "cloud", "global"),
        ("o1-mini", "openai", "openai", "cloud", "global"),
        ("o3-mini", "openai", "openai", "cloud", "global"),

        # Anthropic (Cloud)
        ("claude-3-5-sonnet", "anthropic", "anthropic", "cloud", "global"),
        ("claude-3-5-haiku", "anthropic", "anthropic", "cloud", "global"),
        ("claude-3-opus", "anthropic", "anthropic", "cloud", "global"),
        ("claude-3-sonnet", "anthropic", "anthropic", "cloud", "global"),
        ("claude-3-haiku", "anthropic", "anthropic", "cloud", "global"),

        # Google Gemini (Cloud)
        ("gemini-1.5-pro", "google", "google", "cloud", "global"),
        ("gemini-1.5-flash", "google", "google", "cloud", "global"),
        ("gemini-1.5-flash-8b", "google", "google", "cloud", "global"),
        ("gemini-2.0-flash", "google", "google", "cloud", "global"),
        ("gemini-2.0-flash-exp", "google", "google", "cloud", "global"),

        # Mistral AI (Cloud)
        ("mistral-large", "mistral", "mistral", "cloud", "global"),
        ("mistral-small", "mistral", "mistral", "cloud", "global"),
        ("codestral", "mistral", "mistral", "cloud", "global"),
        ("pixtral-12b", "mistral", "mistral", "cloud", "global"),
        ("open-mistral-7b", "mistral", "mistral", "cloud", "global"),

        # xAI (Cloud)
        ("grok-2", "xai", "xai", "cloud", "global"),
        ("grok-2-mini", "xai", "xai", "cloud", "global"),
        ("grok-beta", "xai", "xai", "cloud", "global"),

        # Media Generation (OpenAI, Google)
        ("dall-e-3", "openai", "openai", "cloud", "global"),
        ("dall-e-2", "openai", "openai", "cloud", "global"),
        ("tts-1", "openai", "openai", "cloud", "global"),
        ("tts-1-hd", "openai", "openai", "cloud", "global"),
        ("imagen-3", "google", "google", "cloud", "global"),
        ("veo-2", "google", "google", "cloud", "global"),
        ("veo-3.1-lite-generate-preview", "google", "google", "cloud", "global"),
        # Media generation models exposed by the live provider APIs (2026-11)
        ("gpt-image-1-mini", "openai", "openai", "cloud", "global"),
        ("gpt-image-1.5", "openai", "openai", "cloud", "global"),
        ("gpt-image-2", "openai", "openai", "cloud", "global"),
        ("gpt-4o-mini-tts", "openai", "openai", "cloud", "global"),
        ("gemini-2.5-flash-image", "google", "google", "cloud", "global"),
        ("gemini-3.1-flash-image", "google", "google", "cloud", "global"),
        ("gemini-3-pro-image", "google", "google", "cloud", "global"),
        ("gemini-nano-banana-2.1", "google", "google", "cloud", "global"),
        ("gemini-2.5-flash-preview-tts", "google", "google", "cloud", "global"),
        ("gemini-3.8-flash-tts", "google", "google", "cloud", "global"),
        ("grok-imagine-image", "xai", "xai", "cloud", "global"),
        ("grok-imagine-image-2.0", "xai", "xai", "cloud", "global"),
        ("grok-imagine-video", "xai", "xai", "cloud", "global"),
        ("grok-imagine-video-1.5", "xai", "xai", "cloud", "global"),
        ("gemini-omni-1.2-flash", "google", "google", "cloud", "global"),
        ("gemini-omni-1.1-flash", "google", "google", "cloud", "global"),
    ]

    for model_name, family, provider_name, runtime, region in reference_models_data:
        mid = ModelId(model_name)
        did = DeploymentId(f"dep-{model_name}")
        pid = None if provider_name == "ollama" else ProviderId(provider_name)

        spec = get_model_spec(model_name)
        if spec is not None:
            in_mods = frozenset(Modality(m) for m in spec.modalities_in)
            out_mods = frozenset(Modality(m) for m in spec.modalities_out)
            model_modes = ModalitySet(in_mods, out_mods)
        else:
            model_modes = text_modes

        if catalog.models.get(mid) is None:
            catalog.models.register(
                Model(
                    mid,
                    ModelIdentity(ModelFamily(family)),
                    capabilities=streaming_cap,
                    modalities=model_modes,
                )
            )

        if pid is not None and catalog.providers.get(pid) is None:
            prov_in = frozenset(
                Modality(m) for m in _PROVIDER_MODALITIES.get(provider_name, ("text",))
            )
            prov_out = frozenset(
                Modality(m) for m in _PROVIDER_OUTPUT_MODALITIES.get(provider_name, ("text",))
            )
            prov_modes = ModalitySet(prov_in, prov_out)
            catalog.providers.register(
                InferenceProvider(pid, provider_name, modalities=prov_modes)
            )

        if catalog.deployments.get(did) is None:
            catalog.deployments.register(
                Deployment(
                    did,
                    mid,
                    pid,
                    DeploymentStatus.AVAILABLE,
                    capabilities=streaming_cap,
                    modalities=model_modes,
                    runtime=runtime,
                    region=region,
                )
            )

    # Ingestion des modèles découverts via 'pyllmkit models sync'
    discovered = load_discovered_models()
    for item in discovered:
        mid_str = item.get("id")
        if not mid_str:
            continue
        mid = ModelId(mid_str)
        if catalog.models.get(mid) is not None:
            continue

        fam_str = item.get("family", "unknown")
        prov_str = item.get("provider", "openai")
        run_str = item.get("runtime", "cloud")
        reg_str = item.get("region", "global")

        did = DeploymentId(f"dep-{mid_str}")
        pid = None if prov_str == "ollama" else ProviderId(prov_str)

        spec = get_model_spec(mid_str)
        if spec is not None:
            in_mods = frozenset(Modality(m) for m in spec.modalities_in)
            out_mods = frozenset(Modality(m) for m in spec.modalities_out)
            disc_modes = ModalitySet(in_mods, out_mods)
        else:
            disc_modes = text_modes

        catalog.models.register(
            Model(
                mid,
                ModelIdentity(ModelFamily(fam_str)),
                capabilities=streaming_cap,
                modalities=disc_modes,
            )
        )

        if pid is not None and catalog.providers.get(pid) is None:
            prov_in = frozenset(
                Modality(m) for m in _PROVIDER_MODALITIES.get(prov_str, ("text",))
            )
            prov_modes = ModalitySet(prov_in, frozenset({Modality("text")}))
            catalog.providers.register(
                InferenceProvider(pid, prov_str, modalities=prov_modes)
            )

        if catalog.deployments.get(did) is None:
            catalog.deployments.register(
                Deployment(
                    did,
                    mid,
                    pid,
                    DeploymentStatus.AVAILABLE,
                    capabilities=streaming_cap,
                    modalities=disc_modes,
                    runtime=run_str,
                    region=reg_str,
                )
            )

    return catalog


def resolve_provider_for_model(
    catalog: InMemoryCatalog,
    model_name: str,
    deployment: Deployment | None = None,
) -> str:
    """Resolve the canonical provider identifier (e.g. ollama, openai, anthropic, etc.)."""
    dep = deployment
    if dep is None:
        dep = catalog.deployments.get(DeploymentId(f"dep-{model_name}"))
    if dep is None:
        for candidate in catalog.deployments.list():
            if candidate.model_id.value == model_name:
                dep = candidate
                break

    if dep is not None:
        if dep.provider_id is not None:
            return dep.provider_id.value
        if dep.runtime == "ollama":
            return "ollama"

    # Modèles taggés avec tag version / quant (ex: mistral:7b-instruct, llama3.2:3b)
    if ":" in model_name or model_name.startswith("ollama"):
        return "ollama"

    for item in load_discovered_models():
        if item.get("id") == model_name:
            prov = item.get("provider")
            if prov:
                return prov

    from pyllmkit.adapters.cli.model_specs import get_model_spec

    spec = get_model_spec(model_name)
    if spec is not None and spec.provider:
        return spec.provider

    return "openai"
