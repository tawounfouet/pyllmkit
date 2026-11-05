"""P6 L6.4: derive restrictive support and limits with provenance."""

from pyllmkit.domain.capabilities import (
    Capability,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    SupportLevel,
)
from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity, ModelLimits
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import CapabilityResolver, LimitResolver

tool = CapabilityId("tool_calling")
native = CapabilitySet((Capability(tool, CapabilitySupport(SupportLevel.NATIVE)),))
model = Model(
    ModelId("demo"), ModelIdentity(ModelFamily("sample")),
    capabilities=native, limits=ModelLimits(context_window=16384),
)
provider = InferenceProvider(
    ProviderId("p"), "Fixture", capabilities=native,
    limits=ModelLimits(context_window=12288),
)
deployment = Deployment(
    DeploymentId("d"), model.id, provider.id,
    capabilities=native, limits=ModelLimits(context_window=8192),
)
report = CapabilityResolver().resolve(model, deployment, provider, (tool,))
limits = LimitResolver().resolve(model, deployment, provider)
assert report.capabilities.supports(tool)
assert report.get(tool).level is SupportLevel.NATIVE
assert limits.limits.context_window == 8192
assert limits.get("context_window").confirmed
print("P6: native support and conservative 8192 context window derived")
