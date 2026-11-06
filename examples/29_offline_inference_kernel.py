"""P7 L7.1: first provider-neutral invocation with an in-process fake (NO network)."""

from pyllmkit.adapters.inference import FakeInferenceAdapter
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import InferenceService
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import DeploymentId, DeploymentTarget, InferenceRequest
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity


def main() -> None:
    catalog = InMemoryCatalog()
    text = frozenset((Modality("text"),))
    modalities = ModalitySet(text, text)
    model_id = ModelId("sample-offline-model")
    deployment_id = DeploymentId("offline-deployment")
    catalog.models.register(Model(
        model_id, ModelIdentity(ModelFamily("example")), modalities=modalities,
    ))
    catalog.deployments.register(Deployment(
        deployment_id, model_id, status=DeploymentStatus.AVAILABLE,
        modalities=modalities, runtime="fake",
    ))
    request = InferenceRequest(
        DeploymentTarget(deployment_id),
        (Message(Role.USER, Content((TextContent("What is a RunId?"),))),),
    )
    adapter = FakeInferenceAdapter("This is a deterministic mock, not a live model.")
    service = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        adapter, {deployment_id: "synthetic-native-alias"},
    )
    execution = service.invoke(request)
    assert execution.response is not None
    assert execution.response.run_id == execution.run.run_id
    print("P7 L7.1 offline fake:", execution.run.state.value)
    print(execution.response.output.text)


if __name__ == "__main__":
    main()
