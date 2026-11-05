"""P3 fitness function: inference domain imports and dependency boundaries."""

import ast
from pathlib import Path

from pyllmkit.domain import (
    DeploymentId,
    GenerationConfig,
    InferenceRequest,
    ModelTarget,
    evaluate_request_support,
)
from pyllmkit.domain.inference import (
    DeploymentId as CanonicalDeploymentId,
)
from pyllmkit.domain.inference import (
    GenerationConfig as CanonicalGenerationConfig,
)
from pyllmkit.domain.inference import (
    InferenceRequest as CanonicalInferenceRequest,
)
from pyllmkit.domain.inference import (
    ModelTarget as CanonicalModelTarget,
)
from pyllmkit.domain.inference import (
    evaluate_request_support as canonical_evaluate_request_support,
)
from tests.architecture.guard import forbidden_imports

ROOT = Path(__file__).resolve().parents[2]
INFERENCE = ROOT / "src" / "pyllmkit" / "domain" / "inference"


def test_public_root_aliases_refer_to_canonical_inference_classes() -> None:
    assert DeploymentId is CanonicalDeploymentId
    assert GenerationConfig is CanonicalGenerationConfig
    assert InferenceRequest is CanonicalInferenceRequest
    assert ModelTarget is CanonicalModelTarget
    assert evaluate_request_support is canonical_evaluate_request_support


def test_inference_imports_are_provider_and_application_free() -> None:
    sources = tuple(INFERENCE.glob("*.py"))
    assert sources
    for source in sources:
        assert forbidden_imports(source) == []
        tree = ast.parse(source.read_text(encoding="utf-8"))
        assert tree is not None


def test_p3_l31_l32_l33_have_no_provider_or_io_runtime_modules() -> None:
    names = {path.name for path in INFERENCE.glob("*.py")}
    assert names == {
        "__init__.py", "targets.py", "config.py", "request.py", "compatibility.py",
        "identifiers.py", "output.py", "finish.py", "usage.py", "response.py",
        "failure.py", "run.py",
    }
