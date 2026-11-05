"""P6 L6.6: explicitly preview and import immutable offline catalog candidates."""

from datetime import UTC, datetime

from pyllmkit.adapters.registry import InMemoryCatalog, StaticDiscoverySource
from pyllmkit.application.registry import CatalogMergeService
from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import DiscoveryResult, MetadataSource, MetadataSourceKind

at = datetime(2026, 11, 5, 20, 0, tzinfo=UTC)
model = Model(ModelId("demo"), ModelIdentity(ModelFamily("sample")))
provider = InferenceProvider(ProviderId("p"), "Fixture")
source = StaticDiscoverySource(DiscoveryResult(
    MetadataSource(MetadataSourceKind.FIXTURE, "example-catalog"), at,
    models=(model,), providers=(provider,),
    deployments=(Deployment(DeploymentId("d"), model.id, provider.id),),
))
catalog = InMemoryCatalog()
merger = CatalogMergeService(catalog)
batch = source.discover()
plan = merger.preview(batch, now=at)
assert len(plan.additions) == 3 and catalog.models.list() == ()
applied = merger.apply(batch, plan, now=at)
assert applied.applied and catalog.snapshot().revision == 1
replay = merger.preview(batch, now=at)
assert replay.no_op and not merger.apply(batch, replay, now=at).applied
print("P6: one atomic import, deterministic idempotent replay")
