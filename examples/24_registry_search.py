"""P6 L6.2/L6.3: deterministic typed search over in-memory registries."""

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
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import DeploymentQuery, ModelQuery

catalog = InMemoryCatalog()
chat = CapabilityId("chat")
model = Model(
    ModelId("demo"), ModelIdentity(ModelFamily("sample")),
    capabilities=CapabilitySet((Capability(chat, CapabilitySupport(SupportLevel.NATIVE)),)),
)
catalog.models.register(model)
catalog.providers.register(InferenceProvider(ProviderId("p"), "Local fixture"))
catalog.deployments.register(Deployment(
    DeploymentId("d"), model.id, ProviderId("p"), status=DeploymentStatus.AVAILABLE,
))
assert catalog.models.find(ModelQuery(required_capabilities=(chat,))) == (model,)
assert tuple(x.id.value for x in catalog.deployments.find(
    DeploymentQuery(status=DeploymentStatus.AVAILABLE)
)) == ("d",)
print("P6: catalog search is deterministic and offline")
