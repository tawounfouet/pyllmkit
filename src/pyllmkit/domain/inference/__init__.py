"""Provider-free inference domain: L3.1 requests and L3.2 responses."""

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
from .finish import FinishReason, FinishReasonCode
from .identifiers import InferenceRunId
from .output import InferenceOutput, TextOutput
from .request import InferenceRequest
from .response import InferenceResponse
from .targets import (
    DeploymentId,
    DeploymentTarget,
    EndpointId,
    EndpointTarget,
    InferenceTarget,
    ModelTarget,
)
from .usage import Usage

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
    "FinishReason",
    "FinishReasonCode",
    "InferenceOutput",
    "InferenceResponse",
    "InferenceRunId",
    "TextOutput",
    "Usage",
    "ModelTarget",
    "ParameterAssessment",
    "ParameterSupport",
    "evaluate_request_support",
    "validate_request_support",
]
