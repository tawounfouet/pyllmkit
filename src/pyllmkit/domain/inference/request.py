"""Immutable chat inference intent, without conversation or provider resolution."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.interactions import Message

from .config import GenerationConfig
from .targets import DeploymentTarget, EndpointTarget, InferenceTarget, ModelTarget


@dataclass(frozen=True, slots=True)
class InferenceRequest:
    """L3.1 chat request: one typed target and 1..* ordered M2 messages.

    This Value Object is not an invocation, has no request ID and performs no I/O.
    """

    target: InferenceTarget
    messages: tuple[Message, ...]
    generation_config: GenerationConfig | None = None

    def __post_init__(self) -> None:
        if type(self.target) not in (ModelTarget, DeploymentTarget, EndpointTarget):
            raise DomainValidationError("InferenceRequest.target must be an InferenceTarget")
        if type(self.messages) is not tuple or not self.messages:
            raise DomainValidationError("InferenceRequest.messages must be a nonempty tuple")
        if any(type(message) is not Message for message in self.messages):
            raise DomainValidationError("InferenceRequest.messages must contain Message values")
        if self.generation_config is not None and type(self.generation_config) is not GenerationConfig:
            raise DomainValidationError(
                "InferenceRequest.generation_config must be GenerationConfig or None"
            )
