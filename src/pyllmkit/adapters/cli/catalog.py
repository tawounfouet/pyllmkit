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


def create_reference_catalog() -> InMemoryCatalog:
    """Instantiate an InMemoryCatalog with standard reference models and deployments."""
    catalog = InMemoryCatalog()
    text_modes = ModalitySet(frozenset({Modality("text")}), frozenset({Modality("text")}))

    streaming_cap = CapabilitySet((
        Capability(
            CapabilityId("streaming"),
            CapabilitySupport(SupportLevel.NATIVE),
        ),
    ))

    # Reference models
    models_data = [
        ("llama3.2", "meta", "ollama", "ollama", "local"),
        ("gpt-4o", "openai", "openai", "cloud", "global"),
        ("claude-3-5-sonnet", "anthropic", "anthropic", "cloud", "global"),
        ("gemini-1.5-pro", "google", "google", "cloud", "global"),
        ("grok-2", "xai", "xai", "cloud", "global"),
        ("mistral-large", "mistral", "mistral", "cloud", "global"),
    ]

    for model_name, family, provider_name, runtime, region in models_data:
        mid = ModelId(model_name)
        did = DeploymentId(f"dep-{model_name}")
        pid = None if provider_name == "ollama" else ProviderId(provider_name)

        catalog.models.register(
            Model(
                mid,
                ModelIdentity(ModelFamily(family)),
                capabilities=streaming_cap,
                modalities=text_modes,
            )
        )

        if pid is not None and catalog.providers.get(pid) is None:
            catalog.providers.register(
                InferenceProvider(pid, provider_name, modalities=text_modes)
            )

        catalog.deployments.register(
            Deployment(
                did,
                mid,
                pid,
                DeploymentStatus.AVAILABLE,
                capabilities=streaming_cap,
                modalities=text_modes,
                runtime=runtime,
                region=region,
            )
        )

    return catalog

