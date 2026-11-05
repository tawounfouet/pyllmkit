"""Provider-free restrictive effective-capability resolution (ADR-043)."""

from dataclasses import dataclass, field
from enum import StrEnum

from pyllmkit.domain.capabilities import (
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    SupportLevel,
)
from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.models import Model, ModelId
from pyllmkit.domain.providers import InferenceProvider, ProviderId

from .constraints import ConstraintReport, merge_constraints


class ResolutionReason(StrEnum):
    """Explain how an effective level was derived, never merely inferred."""

    NATIVE = "native"
    PARTIAL = "partial"
    EMULATED = "emulated"
    PARTIAL_EMULATED = "partial_emulated"
    UNSUPPORTED_VETO = "unsupported_veto"
    UNKNOWN = "unknown"
    CONSTRAINT_CONFLICT = "constraint_conflict"


@dataclass(frozen=True, slots=True)
class CapabilityEvidence:
    """Declaration by an applicable layer, or explicit non-applicability."""

    source: str
    applicable: bool
    support: CapabilitySupport | None = field(repr=False)

    @property
    def level(self) -> SupportLevel | None:
        return None if self.support is None else self.support.level

    @property
    def state(self) -> str:
        if not self.applicable:
            return "NOT_APPLICABLE"
        return "UNKNOWN" if self.level is None else self.level.value.upper()


@dataclass(frozen=True, slots=True)
class EffectiveCapability:
    """Derived support of one capability, never a persisted declaration."""

    id: CapabilityId
    level: SupportLevel | None
    reason: ResolutionReason
    emulated: bool
    constraints: ConstraintReport = field(repr=False)
    evidence: tuple[CapabilityEvidence, ...] = field(repr=False)

    @property
    def confirmed_usable(self) -> bool:
        return self.level in (SupportLevel.NATIVE, SupportLevel.PARTIAL, SupportLevel.EMULATED)

    @property
    def fully_native(self) -> bool:
        return self.level is SupportLevel.NATIVE


@dataclass(frozen=True, slots=True)
class EffectiveCapabilitySet:
    """Read-only, canonically ordered derived capability collection."""

    items: tuple[EffectiveCapability, ...]

    def get(self, capability_id: CapabilityId) -> EffectiveCapability | None:
        if not isinstance(capability_id, CapabilityId):
            raise DomainValidationError("expected CapabilityId")
        return next((cap for cap in self.items if cap.id == capability_id), None)

    def supports(self, capability_id: CapabilityId) -> bool:
        item = self.get(capability_id)
        return item is not None and item.confirmed_usable


@dataclass(frozen=True, slots=True)
class EffectiveCapabilityReport:
    """Contextual model/deployment/provider evidence for all selected capabilities."""

    model_id: ModelId
    deployment_id: DeploymentId
    provider_id: ProviderId | None
    capabilities: EffectiveCapabilitySet

    def get(self, capability_id: CapabilityId) -> EffectiveCapability | None:
        return self.capabilities.get(capability_id)


def validate_serving_context(
    model: Model,
    deployment: Deployment,
    provider: InferenceProvider | None,
) -> None:
    """Reject miscorrelated snapshots; missing provider metadata stays UNKNOWN."""
    if not isinstance(model, Model):
        raise DomainValidationError("expected Model")
    if not isinstance(deployment, Deployment):
        raise DomainValidationError("expected Deployment")
    if provider is not None and not isinstance(provider, InferenceProvider):
        raise DomainValidationError("provider must be InferenceProvider or None")
    if deployment.model_id != model.id:
        raise DomainValidationError("Deployment references a different ModelId")
    if deployment.provider_id is None and provider is not None:
        raise DomainValidationError("local Deployment does not reference a ProviderId")
    if provider is not None and provider.id != deployment.provider_id:
        raise DomainValidationError("ProviderId does not match Deployment")


def _declared(
    source: str,
    capabilities: CapabilitySet | None,
    capability_id: CapabilityId,
) -> CapabilityEvidence:
    support = capabilities.support_of(capability_id) if capabilities is not None else CapabilitySupport()
    return CapabilityEvidence(source, True, support)


def _resolve_one(
    capability_id: CapabilityId,
    model: Model,
    deployment: Deployment,
    provider: InferenceProvider | None,
) -> EffectiveCapability:
    evidence = (
        _declared("model", model.capabilities, capability_id),
        _declared("deployment", deployment.capabilities, capability_id),
        _declared("provider", provider.capabilities if provider is not None else None, capability_id)
        if deployment.provider_id is not None
        else CapabilityEvidence("provider", False, None),
    )
    known_levels = tuple(item.level for item in evidence if item.applicable)
    constraint_layers = tuple(
        (item.source, item.support)
        for item in evidence
        if item.applicable and item.support is not None
    )
    constraints = merge_constraints(constraint_layers)
    emulated = SupportLevel.EMULATED in known_levels
    if SupportLevel.UNSUPPORTED in known_levels:
        level, reason = SupportLevel.UNSUPPORTED, ResolutionReason.UNSUPPORTED_VETO
    elif not known_levels or None in known_levels:
        level, reason = None, ResolutionReason.UNKNOWN
    elif not constraints.qualified:
        level, reason = None, ResolutionReason.CONSTRAINT_CONFLICT
    elif SupportLevel.PARTIAL in known_levels:
        level = SupportLevel.PARTIAL
        reason = ResolutionReason.PARTIAL_EMULATED if emulated else ResolutionReason.PARTIAL
    elif emulated:
        level, reason = SupportLevel.EMULATED, ResolutionReason.EMULATED
    else:
        level, reason = SupportLevel.NATIVE, ResolutionReason.NATIVE
    return EffectiveCapability(capability_id, level, reason, emulated, constraints, evidence)


class CapabilityResolver:
    """Pure conservative resolver; not CapabilitySet.intersection() from M1."""

    def resolve(
        self,
        model: Model,
        deployment: Deployment,
        provider: InferenceProvider | None = None,
        capability_ids: tuple[CapabilityId, ...] | None = None,
    ) -> EffectiveCapabilityReport:
        validate_serving_context(model, deployment, provider)
        if capability_ids is not None:
            if not isinstance(capability_ids, tuple) or any(
                not isinstance(cap, CapabilityId) for cap in capability_ids
            ):
                raise DomainValidationError("capability_ids must be tuple[CapabilityId, ...]")
            if len(set(capability_ids)) != len(capability_ids):
                raise DomainValidationError("duplicate capability_ids")
            ids = tuple(sorted(capability_ids, key=lambda x: x.value))
        else:
            sources: tuple[CapabilitySet | None, ...] = (model.capabilities, deployment.capabilities)
            if provider is not None:
                sources += (provider.capabilities,)
            ids = tuple(sorted(
                {item.id for source in sources if source is not None for item in source},
                key=lambda x: x.value,
            ))
        results = tuple(_resolve_one(item, model, deployment, provider) for item in ids)
        return EffectiveCapabilityReport(
            model.id, deployment.id, deployment.provider_id, EffectiveCapabilitySet(results)
        )
