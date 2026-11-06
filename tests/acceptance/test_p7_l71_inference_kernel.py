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

def test_non_text_part_is_rejected_before_adapter() -> None:
    from pyllmkit.domain.interactions import ImageContent, MediaSourceRef

    fake = FakeInferenceAdapter()
    invalid = InferenceRequest(
        ModelTarget(ModelId("m")),
        (Message(Role.USER, Content((ImageContent(MediaSourceRef("asset", "image-1")),))),),
    )
    with pytest.raises(InvocationPreconditionError, match="unsupported_input_modality"):
        _service(_catalog("d"), fake).invoke(invalid)
    assert fake.calls == []


@pytest.mark.parametrize("timeout", (0.0, -1.0, float("nan"), float("inf"), 1, "30"))
def test_options_reject_unsafe_timeouts(timeout) -> None:  # type: ignore[no-untyped-def]
    from pyllmkit.domain.errors import DomainValidationError

    with pytest.raises(DomainValidationError, match="timeout_seconds"):
        InvocationOptions(timeout_seconds=timeout)


@pytest.mark.parametrize("attempts", (0, 2, -1, True, "1"))
def test_options_reject_implicit_retries(attempts) -> None:  # type: ignore[no-untyped-def]
    from pyllmkit.domain.errors import DomainValidationError

    with pytest.raises(DomainValidationError, match="one attempt"):
        InvocationOptions(max_attempts=attempts)


def test_context_validates_ids_deadline_and_new_attempt() -> None:
    from dataclasses import replace

    from pyllmkit.domain.errors import DomainValidationError

    fake = FakeInferenceAdapter()
    _service(_catalog("d"), fake).invoke(_request())
    ctx = fake.calls[0].context
    with pytest.raises(DomainValidationError, match="run_id"):
        replace(ctx, run_id="run")
    with pytest.raises(DomainValidationError, match="deployment_id"):
        replace(ctx, deployment_id="deployment")
    with pytest.raises(DomainValidationError, match="provider_id"):
        replace(ctx, provider_id="provider")
    with pytest.raises(DomainValidationError, match="attempt_id"):
        replace(ctx, attempt_id="")
    with pytest.raises(DomainValidationError, match="deadline"):
        replace(ctx, deadline=datetime(2026, 11, 6))
    with pytest.raises(DomainValidationError, match="trace_id"):
        replace(ctx, trace_id="")
    with pytest.raises(DomainValidationError, match="attempt_id"):
        ctx.next_attempt(" ")
    assert replace(ctx, trace_id="trace-123").trace_id == "trace-123"


def test_prepared_invocation_rejects_conflicting_binding() -> None:
    from dataclasses import replace

    from pyllmkit.domain.errors import DomainValidationError

    fake = FakeInferenceAdapter()
    _service(_catalog("d"), fake).invoke(_request())
    prepared = fake.calls[0]
    with pytest.raises(DomainValidationError, match="request"):
        replace(prepared, request="raw")
    with pytest.raises(DomainValidationError, match="resolution"):
        replace(prepared, resolution="raw")
    with pytest.raises(DomainValidationError, match="native_model_alias"):
        replace(prepared, native_model_alias=" ")
    with pytest.raises(DomainValidationError, match="context"):
        replace(prepared, context="raw")
    with pytest.raises(DomainValidationError, match="deployment binding mismatch"):
        replace(prepared, context=replace(
            prepared.context, deployment_id=DeploymentId("other")
        ))
    with pytest.raises(DomainValidationError, match="provider binding mismatch"):
        replace(prepared, context=replace(
            prepared.context, provider_id=ProviderId("other")
        ))
    with pytest.raises(DomainValidationError, match="parameter_assessment"):
        replace(prepared, parameter_assessment="raw")


def test_port_error_code_validation_and_sync_safe_failure() -> None:
    from pyllmkit.application.inference import InvocationPortError

    for code in ("bad code", "", "Bad", "missing-token!!", "x/y"):
        with pytest.raises(ValueError, match="invalid_safe_error_code"):
            InvocationPortError(code)
    failed = _service(
        _catalog("d"), FakeInferenceAdapter(failure_code="provider_timeout")
    ).invoke(_request())
    assert failed.run.failure is not None
    assert failed.run.failure.code == "provider_timeout"


def test_reject_invalid_factories_and_binding_map_at_composition() -> None:
    resolver = DeploymentResolver(
        _catalog("d").models, _catalog("d").deployments, _catalog("d").providers
    )
    with pytest.raises(TypeError, match="resolver"):
        InferenceService("invalid", FakeInferenceAdapter(), {})
    with pytest.raises(TypeError, match="model_alias_bindings"):
        InferenceService(resolver, FakeInferenceAdapter(), None)
    with pytest.raises(ValueError, match="invalid_explicit_model_binding"):
        InferenceService(resolver, FakeInferenceAdapter(), {"d": "native"})
    with pytest.raises(ValueError, match="invalid_explicit_model_binding"):
        InferenceService(resolver, FakeInferenceAdapter(), {DeploymentId("d"): " "})
    with pytest.raises(TypeError, match="options"):
        InferenceService(resolver, FakeInferenceAdapter(), {}, options="bad")
    with pytest.raises(TypeError, match="identity factories"):
        InferenceService(resolver, FakeInferenceAdapter(), {}, run_id_factory=None)
    with pytest.raises(TypeError, match="clock"):
        InferenceService(resolver, FakeInferenceAdapter(), {}, clock=None)


def test_invalid_ids_and_clock_fail_before_fake_invocation() -> None:
    c = _catalog("d")
    resolver = DeploymentResolver(c.models, c.deployments, c.providers)
    fake = FakeInferenceAdapter()
    base = {DeploymentId("d"): "native"}
    for extra, expected in (
        ({"run_id_factory": lambda: "wrong"}, "run_id_factory"),
        ({"attempt_id_factory": lambda: ""}, "attempt_id_factory"),
        ({"clock": lambda: datetime(2026, 11, 6)}, "clock"),
    ):
        service = InferenceService(resolver, fake, base, **extra)
        with pytest.raises((TypeError, ValueError), match=expected):
            service.invoke(_request())
    assert fake.calls == []


def test_empty_generation_config_is_not_silently_reinterpreted() -> None:
    c = _catalog("d")
    fake = FakeInferenceAdapter()
    request = _request(config=GenerationConfig())
    assert _service(c, fake).invoke(request).response is not None
    assert len(fake.calls) == 1


def test_unsupported_and_partially_supported_generation_fail_closed() -> None:
    c = _catalog("d")
    fake = FakeInferenceAdapter()
    request = _request(config=GenerationConfig(temperature=0.4))
    for level in (SupportLevel.UNSUPPORTED, SupportLevel.PARTIAL):
        snapshot = GenerationSupportSnapshot(request.target, (
            ParameterSupport("temperature", CapabilitySupport(
                level, notes="partial" if level is SupportLevel.PARTIAL else None
            )),
        ))
        code = (
            "unsupported_generation_parameter" if level is SupportLevel.UNSUPPORTED
            else "unknown_generation_parameter"
        )
        with pytest.raises(InvocationPreconditionError, match=code):
            _service(c, fake).invoke(request, snapshot)
    assert fake.calls == []


def test_snapshot_wrong_target_rejected_before_invocation() -> None:
    from pyllmkit.domain.errors import DomainValidationError

    c = _catalog("d")
    fake = FakeInferenceAdapter()
    request = _request(config=GenerationConfig(temperature=0.5))
    wrong = GenerationSupportSnapshot(DeploymentTarget(DeploymentId("d")))
    with pytest.raises(DomainValidationError, match="snapshot target"):
        _service(c, fake).invoke(request, wrong)
    assert fake.calls == []


def test_async_failure_cancel_and_unexpected_exception_are_sanitized() -> None:
    c = _catalog("d")
    resolver = DeploymentResolver(c.models, c.deployments, c.providers)
    binding = {DeploymentId("d"): "native"}
    for fake, state, code in (
        (AsyncFakeInferenceAdapter(failure_code="provider_timeout"), InferenceRunState.FAILED, "provider_timeout"),
        (AsyncFakeInferenceAdapter(cancelled=True), InferenceRunState.CANCELLED, None),
    ):
        result = asyncio.run(AsyncInferenceService(
            resolver, fake, binding, clock=lambda: NOW
        ).ainvoke(_request()))
        assert result.run.state is state
        assert result.run.failure is None if code is None else result.run.failure is not None
        if code is not None:
            assert result.run.failure is not None
            assert result.run.failure.code == code

    class ExplodingAsync:
        async def ainvoke(self, prepared):  # type: ignore[no-untyped-def]
            raise RuntimeError("api-key=SECRET-NOT-PUBLIC")

    guarded = asyncio.run(AsyncInferenceService(
        resolver, ExplodingAsync(), binding, clock=lambda: NOW,
    ).ainvoke(_request()))  # type: ignore[arg-type]
    assert guarded.run.failure is not None
    assert guarded.run.failure.code == "adapter_unexpected_error"
    assert "SECRET-NOT-PUBLIC" not in repr(guarded)


def test_async_adapter_protocol_mismatch_is_terminal_failed() -> None:
    c = _catalog("d")
    resolver = DeploymentResolver(c.models, c.deployments, c.providers)

    class WrongAsync:
        async def ainvoke(self, prepared):  # type: ignore[no-untyped-def]
            return InferenceResponse(InferenceRunId("wrong-run"), TextOutput("bad"))

    result = asyncio.run(AsyncInferenceService(
        resolver, WrongAsync(), {DeploymentId("d"): "native"},
        clock=lambda: NOW,
    ).ainvoke(_request()))  # type: ignore[arg-type]
    assert result.run.state is InferenceRunState.FAILED
    assert result.run.failure is not None
    assert result.run.failure.code == "adapter_protocol_error"


def test_p7_l71_local_deployment_without_provider_is_valid() -> None:
    c = InMemoryCatalog()
    c.models.register(Model(
        ModelId("m"), ModelIdentity(ModelFamily("family")),
        modalities=MODALITIES,
    ))
    c.deployments.register(Deployment(
        DeploymentId("local"), ModelId("m"), None,
        DeploymentStatus.AVAILABLE, modalities=MODALITIES, runtime="ollama",
    ))
    fake = FakeInferenceAdapter()
    result = _service(c, fake).invoke(_request())
    assert result.run.state is InferenceRunState.COMPLETED
    assert fake.calls[0].context.provider_id is None
