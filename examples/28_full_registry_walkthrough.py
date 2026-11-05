"""P6 L6.1-L6.6: discover, merge, search, resolve, trace without network."""

from datetime import UTC, datetime

from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.registry import (
    CatalogMergeService,
    CatalogSearchService,
    DeploymentResolver,
)
from pyllmkit.domain.capabilities import (
    Capability,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    SupportLevel,
)
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import DeploymentId, ModelTarget
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity, ModelLimits
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import (
    DeploymentRequirement,
    DiscoveryResult,
    MetadataSource,
    MetadataSourceKind,
    ModelQuery,
)

at = datetime(2026, 11, 5, 20, 0, tzinfo=UTC)
capability = CapabilityId("tool_calling")
native = CapabilitySet((Capability(capability, CapabilitySupport(SupportLevel.NATIVE)),))
model = Model(
    ModelId("logical/sample"), ModelIdentity(ModelFamily("sample")),
    capabilities=native, limits=ModelLimits(context_window=32768),
)
provider = InferenceProvider(
    ProviderId("local-provider"), "Offline provider description",
    capabilities=native, limits=ModelLimits(context_window=16384),
)
deployment = Deployment(
    DeploymentId("eu-01"), model.id, provider.id,
    capabilities=native, limits=ModelLimits(context_window=8192),
    status=DeploymentStatus.AVAILABLE, region="eu",
)
discovered = DiscoveryResult(
    MetadataSource(MetadataSourceKind.FIXTURE, "walkthrough"), at,
    providers=(provider,), models=(model,), deployments=(deployment,),
)
catalog = InMemoryCatalog()
merger = CatalogMergeService(catalog)
preview = merger.preview(discovered, now=at)
assert preview.can_apply and len(preview.additions) == 3
merger.apply(discovered, preview, now=at)
found = CatalogSearchService(catalog.models, catalog.deployments).find_models(
    ModelQuery(required_capabilities=(capability,))
)
assert found == (model,)
resolved = DeploymentResolver(
    catalog.models, catalog.deployments, catalog.providers
).resolve(
    ModelTarget(model.id),
    DeploymentRequirement(
        region="eu", required_capabilities=(capability,), min_context_window=4096
    ),
)
assert resolved.report.selected_id == deployment.id
assert resolved.limits.limits.context_window == 8192
assert resolved.capabilities.capabilities.supports(capability)
assert len(catalog.snapshot().provenance) == 3
print("P6: offline discovery -> atomic import -> search -> deterministic resolution")
