"""P6 L6.1: typed offline provider and deployment descriptions only."""

from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.models import ModelId, ModelLimits
from pyllmkit.domain.providers import InferenceProvider, ProviderId

provider = InferenceProvider(
    ProviderId("offline-host"), "Offline catalog host",
    limits=ModelLimits(max_output_tokens=4096),
)
deployment = Deployment(
    DeploymentId("demo-eu"), ModelId("logical/model"), provider.id,
    status=DeploymentStatus.AVAILABLE, region="eu", runtime="fixture",
)
assert deployment.provider_id == provider.id
assert deployment.model_id == ModelId("logical/model")
assert deployment.status is DeploymentStatus.AVAILABLE
print("P6: provider and deployment are descriptive, not executable")
