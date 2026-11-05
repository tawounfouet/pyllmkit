"""Pure derived effective limits, with unknown and provisional evidence (ADR-044)."""

from dataclasses import dataclass
from dataclasses import fields as dataclass_fields

from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.models import Model, ModelLimits
from pyllmkit.domain.providers import InferenceProvider

from .capability_resolution import validate_serving_context


@dataclass(frozen=True, slots=True)
class LimitEvidence:
    """Known numeric upper bound or unknown at one applicable layer."""

    source: str
    value: int | None


@dataclass(frozen=True, slots=True)
class EffectiveLimit:
    """Conservative minimum of known bounds, never fabricated unknown=zero."""

    name: str
    value: int | None
    evidence: tuple[LimitEvidence, ...]

    @property
    def confirmed(self) -> bool:
        return self.value is not None and all(item.value is not None for item in self.evidence)

    @property
    def provisional(self) -> bool:
        return self.value is not None and not self.confirmed


@dataclass(frozen=True, slots=True)
class EffectiveLimits:
    """Derived ModelLimits projection plus field-level source traceability."""

    limits: ModelLimits
    fields: tuple[EffectiveLimit, ...]

    def get(self, name: str) -> EffectiveLimit | None:
        return next((item for item in self.fields if item.name == name), None)

    @property
    def unknown_fields(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.fields if item.value is None)

    @property
    def provisional_fields(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.fields if item.provisional)


class LimitResolver:
    """Conservative limit reducer for one correlated serving context."""

    def resolve(
        self,
        model: Model,
        deployment: Deployment,
        provider: InferenceProvider | None = None,
    ) -> EffectiveLimits:
        validate_serving_context(model, deployment, provider)
        layers: list[tuple[str, ModelLimits | None]] = [
            ("model", model.limits),
            ("deployment", deployment.limits),
        ]
        if deployment.provider_id is not None:
            layers.append(("provider", provider.limits if provider is not None else None))
        values: dict[str, int | None] = {}
        per_field: list[EffectiveLimit] = []
        for field_info in dataclass_fields(ModelLimits):
            name = field_info.name
            evidence = tuple(
                LimitEvidence(source, getattr(limits, name) if limits is not None else None)
                for source, limits in layers
            )
            known = tuple(item.value for item in evidence if item.value is not None)
            bound = min(known) if known else None
            values[name] = bound
            per_field.append(EffectiveLimit(name, bound, evidence))
        limits = ModelLimits(
            context_window=values["context_window"],
            max_input_tokens=values["max_input_tokens"],
            max_output_tokens=values["max_output_tokens"],
            max_images=values["max_images"],
            max_tool_calls=values["max_tool_calls"],
            max_tools=values["max_tools"],
        )
        return EffectiveLimits(limits, tuple(per_field))
