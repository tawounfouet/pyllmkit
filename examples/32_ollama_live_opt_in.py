"""Manual Ollama smoke. NEVER contacts a server unless all opt-ins are set.

Run only on a workstation with a locally installed Ollama daemon.
No prompts or model outputs are logged.
"""

import os

from pyllmkit.adapters.inference import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    OllamaAdapter,
    ProviderConnectionConfig,
    RegisteredInferencePort,
)
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import InferenceService
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import DeploymentId, DeploymentTarget, InferenceRequest
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity


def main() -> None:
    if (
        os.environ.get("PYLLMKIT_LIVE_TESTS") != "1"
        or os.environ.get("PYLLMKIT_LIVE_PROVIDER") != "ollama"
        or os.environ.get("PYLLMKIT_ALLOW_LOCAL_LIVE") != "1"
    ):
        print("SKIP: live Ollama requires three explicit opt-in variables")
        return
    alias = os.environ.get("PYLLMKIT_OLLAMA_MODEL")
    if not alias:
        raise SystemExit("SKIP: explicit PYLLMKIT_OLLAMA_MODEL required")

    port_value = os.environ.get("PYLLMKIT_OLLAMA_PORT", "11434")
    if not port_value.isascii() or not port_value.isdecimal():
        raise SystemExit("SKIP: invalid local Ollama port")
    connection = ProviderConnectionConfig.ollama_local(port=int(port_value))

    catalog = InMemoryCatalog()
    text = frozenset((Modality("text"),))
    modalities = ModalitySet(text, text)
    model = ModelId("ollama-smoke-model")
    deployment = DeploymentId("ollama-smoke")
    catalog.models.register(Model(
        model, ModelIdentity(ModelFamily("local-smoke")), modalities=modalities,
    ))
    catalog.deployments.register(Deployment(
        deployment, model, status=DeploymentStatus.AVAILABLE,
        runtime="ollama", modalities=modalities,
    ))
    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(runtime="ollama"), connection,
        sync_factory=lambda cfg: OllamaAdapter(cfg, allow_live=True),
    ))
    service = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredInferencePort(registry), {deployment: alias},
    )
    result = service.invoke(InferenceRequest(
        DeploymentTarget(deployment),
        (Message(Role.USER, Content((TextContent("Reply with the single word OK."),))),),
    ))
    if result.response is None:
        code = result.run.failure.code if result.run.failure is not None else "unknown_failure"
        raise SystemExit(f"FAILED: Ollama local smoke, safe failure code={code}")
    assert result.response.run_id == result.run.run_id
    usage = result.response.usage
    print("PASS: locally observed Ollama call; response content withheld")
    print("run_state:", result.run.state.value)
    print("observed_input_tokens:", usage.input_tokens if usage is not None else None)
    print("observed_output_tokens:", usage.output_tokens if usage is not None else None)


if __name__ == "__main__":
    main()
