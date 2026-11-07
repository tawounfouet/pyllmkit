"""Provider-independent P7 L7.1 invocation service and terminal Run lifecycle."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from pyllmkit.application.inference.contracts import (
    InferenceExecution,
    InvocationCancelledError,
    InvocationContext,
    InvocationOptions,
    InvocationPortError,
    InvocationPreconditionError,
    PreparedInvocation,
)
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.inference import (
    CompatibilityReport,
    DeploymentId,
    EndpointTarget,
    GenerationSupportSnapshot,
    InferenceFailure,
    InferenceRequest,
    InferenceResponse,
    InferenceRun,
    InferenceRunId,
    evaluate_request_support,
)
from pyllmkit.domain.modalities import Modality
from pyllmkit.domain.registry import DeploymentRequirement, NoCompatibleDeploymentError
from pyllmkit.protocols.inference import AsyncInferencePort, InferencePort


def _make_run_id() -> InferenceRunId:
    return InferenceRunId(uuid4().hex)


def _make_attempt_id() -> str:
    return uuid4().hex


def _utc_now() -> datetime:
    return datetime.now(UTC)


class _InvocationPipeline:
    """Shared sync/async preparation and terminality, without provider I/O."""

    __slots__ = ("_resolver", "_aliases", "_run_ids", "_attempt_ids", "_clock", "_options")

    def __init__(
        self,
        resolver: DeploymentResolver,
        model_alias_bindings: Mapping[DeploymentId, str],
        *,
        options: InvocationOptions | None = None,
        run_id_factory: Callable[[], InferenceRunId] = _make_run_id,
        attempt_id_factory: Callable[[], str] = _make_attempt_id,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if not isinstance(resolver, DeploymentResolver):
            raise TypeError("resolver must be DeploymentResolver")
        if not isinstance(model_alias_bindings, Mapping):
            raise TypeError("model_alias_bindings must be a mapping")
        bindings = dict(model_alias_bindings)
        if any(
            type(deployment_id) is not DeploymentId
            or type(alias) is not str
            or not alias.strip()
            for deployment_id, alias in bindings.items()
        ):
            raise ValueError("invalid_explicit_model_binding")
        if options is not None and type(options) is not InvocationOptions:
            raise TypeError("options must be InvocationOptions")
        if not callable(run_id_factory) or not callable(attempt_id_factory):
            raise TypeError("identity factories must be callable")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._resolver = resolver
        self._aliases = bindings
        self._run_ids = run_id_factory
        self._attempt_ids = attempt_id_factory
        self._clock = clock
        self._options = options or InvocationOptions()

    def _now(self) -> datetime:
        now = self._clock()
        if type(now) is not datetime or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("clock_must_return_aware_datetime")
        return now

    def prepare(
        self,
        request: InferenceRequest,
        support_snapshot: GenerationSupportSnapshot | None,
    ) -> tuple[PreparedInvocation, InferenceRun]:
        if type(request) is not InferenceRequest:
            raise TypeError("request must be InferenceRequest")
        target = request.target
        if isinstance(target, EndpointTarget):
            raise InvocationPreconditionError("target_not_routable")

        req_inputs = frozenset(
            part.modality for message in request.messages for part in message.content.parts
        )
        text = frozenset((Modality("text"),))
        try:
            resolution = self._resolver.resolve(
                target,
                DeploymentRequirement(
                    required_input_modalities=req_inputs,
                    required_output_modalities=text,
                ),
            )
        except NoCompatibleDeploymentError as exc:
            # Fallback for models whose native output modality is non-text (image, audio, video)
            resolved = False
            for fallback_mod in (Modality("image"), Modality("audio"), Modality("video")):
                try:
                    resolution = self._resolver.resolve(
                        target,
                        DeploymentRequirement(
                            required_input_modalities=req_inputs,
                            required_output_modalities=frozenset((fallback_mod,)),
                        ),
                    )
                    resolved = True
                    break
                except NoCompatibleDeploymentError:
                    continue
            if not resolved:
                if exc.report and any(
                    "INPUT_MODALITY_NOT_CONFIRMED" in r.reasons for r in exc.report.rejected
                ):
                    raise InvocationPreconditionError("unsupported_input_modality") from exc
                raise
        alias = self._aliases.get(resolution.deployment.id)
        if alias is None:
            raise InvocationPreconditionError("native_model_binding_missing")

        if support_snapshot is not None:
            assessment = evaluate_request_support(request, support_snapshot)
        else:
            assessment = CompatibilityReport(())
            if request.generation_config is not None:
                # A configuration with no explicitly supplied parameters is harmless.
                fields = (
                    "temperature", "top_p", "top_k", "max_output_tokens",
                    "seed", "stop_sequences", "presence_penalty",
                    "frequency_penalty",
                )
                if any(
                    getattr(request.generation_config, name) is not None
                    for name in fields
                ):
                    raise InvocationPreconditionError("generation_support_snapshot_missing")
        if assessment.unsupported_parameters:
            raise InvocationPreconditionError("unsupported_generation_parameter")
        if assessment.assessments and not assessment.is_confirmed_native:
            raise InvocationPreconditionError("unknown_generation_parameter")

        run_id = self._run_ids()
        attempt_id = self._attempt_ids()
        if type(run_id) is not InferenceRunId:
            raise TypeError("run_id_factory must return InferenceRunId")
        if type(attempt_id) is not str or not attempt_id.strip():
            raise TypeError("attempt_id_factory must return a nonblank string")
        started_at = self._now()
        context = InvocationContext(
            run_id, resolution.deployment.id, resolution.deployment.provider_id,
            attempt_id, started_at + timedelta(seconds=self._options.timeout_seconds),
        )
        prepared = PreparedInvocation(request, resolution, alias, context, assessment)
        running = InferenceRun(run_id, request).start(started_at)
        return prepared, running

    def success(self, run: InferenceRun, response: object) -> InferenceExecution:
        if type(response) is not InferenceResponse or response.run_id != run.run_id:
            return self.failed(run, "adapter_protocol_error")
        return InferenceExecution(run.complete(response, self._now()))

    def failed(self, run: InferenceRun, code: str) -> InferenceExecution:
        return InferenceExecution(run.fail(InferenceFailure(code), self._now()))

    def cancelled(self, run: InferenceRun) -> InferenceExecution:
        return InferenceExecution(run.cancel(self._now(), "user_cancelled"))


class InferenceService:
    """Resolve once, then invoke one explicit sync adapter without retries."""

    __slots__ = ("_pipeline", "_port")

    def __init__(
        self,
        resolver: DeploymentResolver,
        port: InferencePort,
        model_alias_bindings: Mapping[DeploymentId, str],
        *,
        options: InvocationOptions | None = None,
        run_id_factory: Callable[[], InferenceRunId] = _make_run_id,
        attempt_id_factory: Callable[[], str] = _make_attempt_id,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._pipeline = _InvocationPipeline(
            resolver, model_alias_bindings, options=options,
            run_id_factory=run_id_factory, attempt_id_factory=attempt_id_factory,
            clock=clock,
        )
        self._port = port

    def invoke(
        self,
        request: InferenceRequest,
        support_snapshot: GenerationSupportSnapshot | None = None,
    ) -> InferenceExecution:
        prepared, running = self._pipeline.prepare(request, support_snapshot)
        try:
            response = self._port.invoke(prepared)
        except InvocationCancelledError:
            return self._pipeline.cancelled(running)
        except InvocationPortError as error:
            return self._pipeline.failed(running, error.code)
        except Exception:
            # The provider exception could contain a URL, secret, or prompt.
            return self._pipeline.failed(running, "adapter_unexpected_error")
        return self._pipeline.success(running, response)


class AsyncInferenceService:
    """Same deterministic logic for an async adapter, without fake async I/O."""

    __slots__ = ("_pipeline", "_port")

    def __init__(
        self,
        resolver: DeploymentResolver,
        port: AsyncInferencePort,
        model_alias_bindings: Mapping[DeploymentId, str],
        *,
        options: InvocationOptions | None = None,
        run_id_factory: Callable[[], InferenceRunId] = _make_run_id,
        attempt_id_factory: Callable[[], str] = _make_attempt_id,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._pipeline = _InvocationPipeline(
            resolver, model_alias_bindings, options=options,
            run_id_factory=run_id_factory, attempt_id_factory=attempt_id_factory,
            clock=clock,
        )
        self._port = port

    async def ainvoke(
        self,
        request: InferenceRequest,
        support_snapshot: GenerationSupportSnapshot | None = None,
    ) -> InferenceExecution:
        prepared, running = self._pipeline.prepare(request, support_snapshot)
        try:
            response = await self._port.ainvoke(prepared)
        except InvocationCancelledError:
            return self._pipeline.cancelled(running)
        except InvocationPortError as error:
            return self._pipeline.failed(running, error.code)
        except Exception:
            return self._pipeline.failed(running, "adapter_unexpected_error")
        # External asyncio.Task cancellation propagates; no false remote cancel claim.
        return self._pipeline.success(running, response)
