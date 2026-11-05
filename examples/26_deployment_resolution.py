"""P6 L6.5: select one explicit compatible deployment, never first-match."""

from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import DeploymentId, ModelTarget
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import DeploymentRequirement

catalog = InMemoryCatalog()
model = Model(ModelId("demo"), ModelIdentity(ModelFamily("sample")))
catalog.models.register(model)
catalog.providers.register(InferenceProvider(ProviderId("p"), "Fixture"))
catalog.deployments.register(Deployment(
    DeploymentId("only"), model.id, ProviderId("p"),
    status=DeploymentStatus.AVAILABLE, region="eu",
))
result = DeploymentResolver(
    catalog.models, catalog.deployments, catalog.providers
).resolve(
    ModelTarget(model.id), DeploymentRequirement(region="eu"),
)
assert result.deployment.id == DeploymentId("only")
assert result.report.selected_id == DeploymentId("only")
print("P6: exactly one catalog-declared deployment selected (not health-checked)")
