"""P7-AC-001..008: offline provider-agnostic invocation lifecycle."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from pyllmkit.adapters.inference import AsyncFakeInferenceAdapter, FakeInferenceAdapter
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import (
    AsyncInferenceService,
    InferenceService,
    InvocationContext,
    InvocationOptions,
    InvocationPreconditionError,
)
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import (
    DeploymentId,
    DeploymentTarget,
    EndpointId,
    EndpointTarget,
    GenerationConfig,
    GenerationSupportSnapshot,
    InferenceRequest,
    InferenceResponse,
    InferenceRunId,
    InferenceRunState,
    ModelTarget,
    ParameterSupport,
    TextOutput,
)
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import AmbiguousDeploymentError, NoCompatibleDeploymentError
from pyllmkit.protocols import AsyncInferencePort, InferencePort

NOW = datetime(2026, 11, 6, tzinfo=UTC)
TEXT = Modality("text")
MODALITIES = ModalitySet(frozenset((TEXT,)), frozenset((TEXT,)))


def _catalog(*ids: str) -> InMemoryCatalog:
    c = InMemoryCatalog()
    c.models.register(Model(
        ModelId("m"), ModelIdentity(ModelFamily("model-family")),
        modalities=MODALITIES,
    ))
    c.providers.register(InferenceProvider(
        ProviderId("p"), "provider", modalities=MODALITIES,
    ))
    for dep_id in ids:
        c.deployments.register(Deployment(
            DeploymentId(dep_id), ModelId("m"), ProviderId("p"),
            DeploymentStatus.AVAILABLE, modalities=MODALITIES,
        ))
    return c


def _request(target=None, config=None) -> InferenceRequest:  # type: ignore[no-untyped-def]
    return InferenceRequest(
        target or ModelTarget(ModelId("m")),
        (Message(Role.USER, Content((TextContent("confidential prompt"),))),),
        config,
    )


def _service(c: InMemoryCatalog, fake: FakeInferenceAdapter) -> InferenceService:
    return InferenceService(
        DeploymentResolver(c.models, c.deployments, c.providers),
        fake, {d.id: "native-private-model" for d in c.deployments.list()},
        run_id_factory=lambda: InferenceRunId("fixed-run"),
        attempt_id_factory=lambda: "attempt-1",
        clock=lambda: NOW,
    )


def test_p7_ac001_typed_fake_sync_port_and_no_network() -> None:
    fake = FakeInferenceAdapter("offline-only")
    assert isinstance(fake, InferencePort)
    result = _service(_catalog("d"), fake).invoke(_request())
    assert result.response is result.run.response
    assert result.response is not None
    assert result.response.output.text == "offline-only"
    assert len(fake.calls) == 1
    assert fake.calls[0].request is result.run.request
    assert fake.calls[0].native_model_alias == "native-private-model"
    assert fake.calls[0].context.deadline == NOW + timedelta(seconds=30)


def test_p7_ac002_async_port_has_same_result_contract() -> None:
    c = _catalog("d")
    fake = AsyncFakeInferenceAdapter("offline-only")
    assert isinstance(fake, AsyncInferencePort)
    svc = AsyncInferenceService(
        DeploymentResolver(c.models, c.deployments, c.providers),
        fake, {DeploymentId("d"): "native"},
        run_id_factory=lambda: InferenceRunId("fixed-run"),
        attempt_id_factory=lambda: "attempt-1",
        clock=lambda: NOW,
    )
    result = asyncio.run(svc.ainvoke(_request()))
    assert result.run.state is InferenceRunState.COMPLETED
    assert result.response is not None
    assert result.response.output.text == "offline-only"
    assert result.response.run_id == result.run.run_id


def test_p7_ac003_response_runid_matches_only_run_generated_by_service() -> None:
    fake = FakeInferenceAdapter()
    result = _service(_catalog("d"), fake).invoke(_request())
    assert result.run.run_id == fake.calls[0].context.run_id
    assert result.response is not None
    assert result.response.run_id == result.run.run_id


def test_p7_ac004_attempt_id_changes_but_runid_stays_the_same() -> None:
    fake = FakeInferenceAdapter()
    _service(_catalog("d"), fake).invoke(_request())
    ctx = fake.calls[0].context
    later = ctx.next_attempt("attempt-2")
    assert type(later) is InvocationContext
    assert later.run_id == ctx.run_id
    assert later.attempt_id != ctx.attempt_id
    with pytest.raises(ValueError, match="attempt_id"):
        ctx.next_attempt(ctx.attempt_id)
    with pytest.raises(ValueError, match="exactly one attempt"):
        InvocationOptions(max_attempts=2)


def test_p7_ac005_ambiguous_modeltarget_blocks_fake_before_invocation() -> None:
    fake = FakeInferenceAdapter()
    with pytest.raises(AmbiguousDeploymentError):
        _service(_catalog("one", "two"), fake).invoke(_request())
    assert fake.calls == []


def test_p7_ac006_exact_deployment_target_never_reroutes() -> None:
    c = _catalog("one", "two")
    fake = FakeInferenceAdapter()
    result = _service(c, fake).invoke(
        _request(DeploymentTarget(DeploymentId("two")))
    )
    assert result.run.state is InferenceRunState.COMPLETED
    assert fake.calls[0].context.deployment_id == DeploymentId("two")
    c.deployments.remove(DeploymentId("two"))
    c.deployments.register(Deployment(
        DeploymentId("two"), ModelId("m"), ProviderId("p"),
        DeploymentStatus.UNAVAILABLE, modalities=MODALITIES,
    ))
    with pytest.raises(NoCompatibleDeploymentError):
        _service(c, FakeInferenceAdapter()).invoke(
            _request(DeploymentTarget(DeploymentId("two")))
        )


def test_p7_ac007_unbound_endpoint_is_rejected_without_url_or_network() -> None:
    fake = FakeInferenceAdapter()
    malicious_id = EndpointId("http://169.254.169.254/metadata")
    with pytest.raises(InvocationPreconditionError, match="target_not_routable"):
        _service(_catalog("d"), fake).invoke(_request(EndpointTarget(malicious_id)))
    assert fake.calls == []


def test_p7_ac008_success_failure_cancel_and_invalid_response_terminal() -> None:
    c = _catalog("d")
    good = _service(c, FakeInferenceAdapter()).invoke(_request())
    assert good.run.state is InferenceRunState.COMPLETED
    failed = _service(c, FakeInferenceAdapter(failure_code="provider_unavailable")).invoke(
        _request()
    )
    assert failed.run.state is InferenceRunState.FAILED
    assert failed.run.failure is not None
    assert failed.run.failure.code == "provider_unavailable"
    assert failed.response is None
    cancelled = _service(c, FakeInferenceAdapter(cancelled=True)).invoke(_request())
    assert cancelled.run.state is InferenceRunState.CANCELLED

    class BadPort:
        def invoke(self, prepared):  # type: ignore[no-untyped-def]
            return InferenceResponse(InferenceRunId("other"), TextOutput("not-owned"))

    mismatched = _service(c, BadPort()).invoke(_request())  # type: ignore[arg-type]
    assert mismatched.run.state is InferenceRunState.FAILED
    assert mismatched.run.failure is not None
    assert mismatched.run.failure.code == "adapter_protocol_error"


def test_strict_generation_support_and_missing_binding_are_pre_io_failures() -> None:
    c = _catalog("d")
    fake = FakeInferenceAdapter()
    request = _request(config=GenerationConfig(temperature=0.2))
    with pytest.raises(InvocationPreconditionError, match="snapshot_missing"):
        _service(c, fake).invoke(request)
    unknown = GenerationSupportSnapshot(request.target)
    with pytest.raises(InvocationPreconditionError, match="unknown_generation_parameter"):
        _service(c, fake).invoke(request, unknown)
    supported = GenerationSupportSnapshot(
        request.target, (
            ParameterSupport("temperature", CapabilitySupport(SupportLevel.NATIVE)),
        ),
    )
    assert _service(c, fake).invoke(request, supported).response is not None
    assert len(fake.calls) == 1


def test_native_alias_and_raw_adapter_exceptions_are_never_exposed() -> None:
    c = _catalog("d")
    r = DeploymentResolver(c.models, c.deployments, c.providers)
    fake = FakeInferenceAdapter()
    no_alias = InferenceService(r, fake, {})
    with pytest.raises(InvocationPreconditionError, match="native_model_binding_missing"):
        no_alias.invoke(_request())
    assert fake.calls == []

    class ExplodingPort:
        def invoke(self, prepared):  # type: ignore[no-untyped-def]
            raise RuntimeError("confidential prompt key: SECRET-PRIVATE")

    guarded = _service(c, ExplodingPort()).invoke(_request())  # type: ignore[arg-type]
    assert guarded.run.failure is not None
    assert guarded.run.failure.code == "adapter_unexpected_error"
    assert "SECRET-PRIVATE" not in repr(guarded)
    assert "confidential prompt" not in repr(guarded)


def test_prepared_invocation_repr_does_not_expose_request_or_native_alias() -> None:
    fake = FakeInferenceAdapter()
    _service(_catalog("d"), fake).invoke(_request())
    prepared = fake.calls[0]
    assert "confidential prompt" not in repr(prepared)
    assert "native-private-model" not in repr(prepared)
