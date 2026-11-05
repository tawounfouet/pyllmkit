"""L3.5: stable provider-free public API surface and package metadata."""

import importlib
import tomllib
from pathlib import Path

from pyllmkit import __version__ as runtime_version
from pyllmkit.domain import (
    INFERENCE_SCHEMA_VERSION,
    INTERACTION_SCHEMA_VERSION,
)
from pyllmkit.domain.models.serialization import SCHEMA_VERSION as MODEL_SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[2]

PUBLIC_INFERENCE_NAMES = (
    "ModelTarget", "DeploymentTarget", "EndpointTarget", "DeploymentId", "EndpointId",
    "InferenceTarget", "GenerationConfig", "InferenceRequest", "InferenceResponse",
    "InferenceRunId", "InferenceRun", "InferenceRunState", "InferenceFailure",
    "TextOutput", "InferenceOutput", "FinishReason", "FinishReasonCode", "Usage",
    "GenerationSupportSnapshot", "ParameterSupport", "ParameterAssessment",
    "CompatibilityReport", "evaluate_request_support", "validate_request_support",
    "INFERENCE_SCHEMA_VERSION", "request_to_dict", "request_from_dict",
    "response_to_dict", "response_from_dict", "run_to_dict", "run_from_dict",
)


def test_public_inference_symbols_identical_at_root_and_subpackage() -> None:
    root = importlib.import_module("pyllmkit.domain")
    module = importlib.import_module("pyllmkit.domain.inference")
    assert set(PUBLIC_INFERENCE_NAMES).issubset(set(root.__all__))
    assert set(PUBLIC_INFERENCE_NAMES).issubset(set(module.__all__))
    for name in PUBLIC_INFERENCE_NAMES:
        assert getattr(root, name) is getattr(module, name), name


def test_m1_m2_m3_schema_versions_are_independent_v1() -> None:
    assert (MODEL_SCHEMA_VERSION, INTERACTION_SCHEMA_VERSION, INFERENCE_SCHEMA_VERSION) == (
        1, 1, 1
    )


def test_package_is_explicitly_unpublished_a2_source_candidate() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    assert project["name"] == "pyllmkit"
    assert project["version"] == "0.1.0a2"
    assert runtime_version == "0.1.0a2"
    assert project["dependencies"] == []
    assert project["requires-python"] == ">=3.11"
    assert project["license"] == "MIT"
    assert (ROOT / "LICENSE").is_file()
    assert (ROOT / "src" / "pyllmkit" / "py.typed").is_file()


def test_phase3_does_not_add_accidental_provider_dependencies() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert not project["project"]["dependencies"]
    forbidden = {"openai", "anthropic", "httpx", "requests", "google-genai"}
    assert not (forbidden & set(project["project"]["dependencies"]))
