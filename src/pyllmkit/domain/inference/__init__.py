"""Phase 3 L3.1 provider-free inference request domain (ADR-014/015/016/021)."""

from .compatibility import (
    GENERATION_PARAMETER_NAMES,
    CompatibilityReport,
    GenerationSupportSnapshot,
    ParameterAssessment,
    ParameterSupport,
    evaluate_request_support,
    validate_request_support,
)
from .config import GenerationConfig
from .request import InferenceRequest
from .targets import (
    DeploymentId,
    DeploymentTarget,
    EndpointId,
    EndpointTarget,
    InferenceTarget,
    ModelTarget,
)

__all__ = [
    "CompatibilityReport",
    "DeploymentId",
    "DeploymentTarget",
    "EndpointId",
    "EndpointTarget",
    "GENERATION_PARAMETER_NAMES",
    "GenerationConfig",
    "GenerationSupportSnapshot",
    "InferenceRequest",
    "InferenceTarget",
    "ModelTarget",
    "ParameterAssessment",
    "ParameterSupport",
    "evaluate_request_support",
    "validate_request_support",
]
