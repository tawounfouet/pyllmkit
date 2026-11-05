"""Provider-free inference domain: requests, responses and pure run lifecycle."""

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
from .failure import InferenceFailure
from .finish import FinishReason, FinishReasonCode
from .identifiers import InferenceRunId
from .output import InferenceOutput, TextOutput
from .request import InferenceRequest
from .response import InferenceResponse
from .run import InferenceRun, InferenceRunState
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
    "InferenceFailure",
    "InferenceRun",
    "InferenceRunState",
    "InferenceRunId",
    "TextOutput",
    "Usage",
    "ModelTarget",
    "ParameterAssessment",
    "ParameterSupport",
    "evaluate_request_support",
    "validate_request_support",
]
