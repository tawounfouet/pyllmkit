"""Deterministic offline deployment resolution (P6 L6.5, ADR-045).

Never select the first entry or infer live provider availability.
"""

from dataclasses import dataclass

from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import DeploymentTarget, ModelTarget
from pyllmkit.domain.modalities import Modality
from pyllmkit.domain.registry import (
    CapabilityMatchMode,
    CapabilityResolver,
    EffectiveCapabilityReport,
    EffectiveLimits,
    LimitResolver,
)
from pyllmkit.domain.registry.selection import (
    AmbiguousDeploymentError,
    CandidateRejection,
    DeploymentNotFoundError,
    DeploymentRequirement,
    DeploymentResolutionReport,
    ModelNotFoundError,
    NoCompatibleDeploymentError,
)
from pyllmkit.domain.providers import InferenceProvider
from pyllmkit.protocols import DeploymentRegistryPort, ModelRegistryPort, ProviderCatalogPort


@dataclass(frozen=True, slots=True)
class DeploymentResolution:
    """Selected descriptive deployment and reproducible reason evidence."""

    deployment: Deployment
    capabilities: EffectiveCapabilityReport
    limits: EffectiveLimits
    report: DeploymentResolutionReport


class DeploymentResolver:
    """Strict read-only resolver over catalog ports and pure domain services."""

    __slots__ = ("_models", "_deployments", "_providers", "_capabilities", "_limits")

    def __init__(
        self,
        models: ModelRegistryPort,
        deployments: DeploymentRegistryPort,
        providers: ProviderCatalogPort,
    ) -> None:
        self._models = models
        self._deployments = deployments
        self._providers = providers
        self._capabilities = CapabilityResolver()
        self._limits = LimitResolver()

    @staticmethod
    def _modality_confirmed(
        item: Modality,
        direction: str,
        model: object,
        deployment: Deployment,
        provider: InferenceProvider | None,
    ) -> bool:
        from pyllmkit.domain.models import Model

        if not isinstance(model, Model):
            raise DomainValidationError("expected Model")
        layers = [model.modalities, deployment.modalities]
        if deployment.provider_id is not None:
            layers.append(provider.modalities if provider is not None else None)
        for modalities in layers:
            if modalities is None:
                return False
            match = (
                modalities.accepts_input(item) if direction == "input"
                else modalities.can_output(item)
            )
            if match is not True:
                return False
        return True

    def _assess(
        self, deployment: Deployment, requirement: DeploymentRequirement
    ) -> tuple[tuple[str, ...], EffectiveCapabilityReport, EffectiveLimits]:
        model = self._models.get(deployment.model_id)
        if model is None:
            raise ModelNotFoundError("Deployment references unknown ModelId")
        provider = (
            self._providers.get(deployment.provider_id)
            if deployment.provider_id is not None else None
        )
        capabilities = self._capabilities.resolve(
            model, deployment, provider, requirement.required_capabilities
        )
        limits = self._limits.resolve(model, deployment, provider)
        reasons: list[str] = []
        if requirement.require_available and deployment.status is not DeploymentStatus.AVAILABLE:
            reasons.append("STATUS_NOT_AVAILABLE")
        if requirement.provider_id is not None and deployment.provider_id != requirement.provider_id:
            reasons.append("PROVIDER_MISMATCH")
        if requirement.region is not None and deployment.region != requirement.region:
            reasons.append("REGION_MISMATCH")
        if requirement.runtime is not None and deployment.runtime != requirement.runtime:
            reasons.append("RUNTIME_MISMATCH")
        if deployment.provider_id is not None and provider is None:
            reasons.append("PROVIDER_METADATA_UNKNOWN")
        for capability_id in requirement.required_capabilities:
            item = capabilities.get(capability_id)
            if item is None:
                reasons.append("CAPABILITY_UNKNOWN")
            elif requirement.capability_mode is CapabilityMatchMode.NATIVE_ONLY:
                if not item.fully_native:
                    reasons.append("CAPABILITY_NOT_NATIVE")
            elif not item.confirmed_usable:
                reasons.append("CAPABILITY_NOT_CONFIRMED")
        for item in requirement.required_input_modalities:
            if not self._modality_confirmed(item, "input", model, deployment, provider):
                reasons.append("INPUT_MODALITY_NOT_CONFIRMED")
        for item in requirement.required_output_modalities:
            if not self._modality_confirmed(item, "output", model, deployment, provider):
                reasons.append("OUTPUT_MODALITY_NOT_CONFIRMED")
        if requirement.min_context_window is not None:
            context = limits.get("context_window")
            if context is None or context.value is None:
                reasons.append("CONTEXT_UNKNOWN")
            elif not context.confirmed:
                reasons.append("CONTEXT_PROVISIONAL")
            elif context.value < requirement.min_context_window:
                reasons.append("CONTEXT_TOO_SMALL")
        return tuple(sorted(set(reasons))), capabilities, limits

    def resolve(
        self,
        target: ModelTarget | DeploymentTarget,
        requirement: DeploymentRequirement | None = None,
    ) -> DeploymentResolution:
        if not isinstance(target, (ModelTarget, DeploymentTarget)):
            raise DomainValidationError("target must be ModelTarget or DeploymentTarget")
        if requirement is None:
            requirement = DeploymentRequirement()
        if not isinstance(requirement, DeploymentRequirement):
            raise DomainValidationError("requirement must be DeploymentRequirement")
        if isinstance(target, ModelTarget):
            if self._models.get(target.model_id) is None:
                raise ModelNotFoundError("ModelTarget references unknown ModelId")
            candidates = self._deployments.find(lambda dep: dep.model_id == target.model_id)
        else:
            exact = self._deployments.get(target.deployment_id)
            if exact is None:
                raise DeploymentNotFoundError("DeploymentTarget refers to missing DeploymentId")
            candidates = (exact,)
        candidates = tuple(sorted(candidates, key=lambda dep: dep.id.value))
        considered = tuple(dep.id for dep in candidates)
        eligible: list[Deployment] = []
        rejected: list[CandidateRejection] = []
        evidence: dict[str, tuple[EffectiveCapabilityReport, EffectiveLimits]] = {}
        for dep in candidates:
            reasons, capabilities, limits = self._assess(dep, requirement)
            if reasons:
                rejected.append(CandidateRejection(dep.id, reasons))
            else:
                eligible.append(dep)
                evidence[dep.id.value] = (capabilities, limits)
        eligible_ids = tuple(dep.id for dep in eligible)
        report = DeploymentResolutionReport(
            considered, eligible_ids, tuple(rejected),
            eligible_ids[0] if len(eligible_ids) == 1 else None,
        )
        if not eligible:
            raise NoCompatibleDeploymentError("No deployment satisfies requirements", report)
        if len(eligible) > 1:
            raise AmbiguousDeploymentError("Multiple deployments satisfy requirements", report)
        selected = eligible[0]
        capabilities, limits = evidence[selected.id.value]
        return DeploymentResolution(selected, capabilities, limits, report)
