"""ADR-021 option A: explicit support snapshots, no provider fallback."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import (
    CapabilitySupport,
    Content,
    DomainValidationError,
    Message,
    ModelId,
    Role,
    SupportLevel,
    TextContent,
)
from pyllmkit.domain.inference import (
    CompatibilityReport,
    DeploymentId,
    DeploymentTarget,
    GenerationConfig,
    GenerationSupportSnapshot,
    InferenceRequest,
    ModelTarget,
    ParameterAssessment,
    ParameterSupport,
    evaluate_request_support,
    validate_request_support,
)


def _request(config: GenerationConfig | None = None) -> InferenceRequest:
    return InferenceRequest(
        ModelTarget(ModelId("model1")),
        (Message(Role.USER, Content((TextContent("hello"),))),),
        config,
    )


def test_explicit_unsupported_parameter_is_reported_and_rejected_ac007() -> None:
    request = _request(GenerationConfig(top_p=0.7, temperature=0.0))
    snapshot = GenerationSupportSnapshot(
        request.target,
        (
            ParameterSupport("top_p", CapabilitySupport(SupportLevel.UNSUPPORTED)),
            ParameterSupport("temperature", CapabilitySupport(SupportLevel.NATIVE)),
        ),
    )
    report = evaluate_request_support(request, snapshot)
    assert report.unsupported_parameters == ("top_p",)
    assert report.unknown_parameters == ()
    assert report.is_compatible is False
    with pytest.raises(DomainValidationError, match="unsupported generation parameter: top_p"):
        validate_request_support(request, snapshot)
    assert request.generation_config == GenerationConfig(top_p=0.7, temperature=0.0)


def test_unknown_is_never_assumed_to_be_native_or_supported() -> None:
    request = _request(GenerationConfig(top_p=0.2, temperature=0.0))
    snapshot = GenerationSupportSnapshot(
        request.target,
        (ParameterSupport("top_p", CapabilitySupport(SupportLevel.NATIVE)),),
    )
    report = validate_request_support(request, snapshot)
    assert report.unknown_parameters == ("temperature",)
    assert report.is_confirmed_native is False
    assert report.is_compatible is None
    assert tuple(item.name for item in report.assessments) == ("temperature", "top_p")


def test_all_native_parameters_are_confirmed_only_on_explicit_snapshot() -> None:
    request = _request(GenerationConfig(top_k=1, stop_sequences=()))
    snap = GenerationSupportSnapshot(
        request.target,
        (
            ParameterSupport("top_k", CapabilitySupport(SupportLevel.NATIVE)),
            ParameterSupport("stop_sequences", CapabilitySupport(SupportLevel.NATIVE)),
        ),
    )
    report = validate_request_support(request, snap)
    assert report.is_confirmed_native is True
    assert report.is_compatible is True
    assert report.unsupported_parameters == ()


@pytest.mark.parametrize("level", [SupportLevel.PARTIAL, SupportLevel.EMULATED])
def test_partial_and_emulated_require_explicit_policy(level: SupportLevel) -> None:
    request = _request(GenerationConfig(temperature=0.0))
    support = CapabilitySupport(level, notes="requires policy")
    snapshot = GenerationSupportSnapshot(
        request.target, (ParameterSupport("temperature", support),)
    )
    report = validate_request_support(request, snapshot)
    assert report.is_compatible is None
    assert report.is_confirmed_native is False


def test_no_generation_config_does_not_invent_a_parameter() -> None:
    request = _request()
    report = evaluate_request_support(request, GenerationSupportSnapshot(request.target))
    assert report.assessments == ()
    assert report.is_confirmed_native is False  # no positive support evidence
    assert report.is_compatible is None  # NOT_EVALUATED, never implicit NATIVE


def test_request_and_snapshot_targets_must_match_exactly() -> None:
    request = _request(GenerationConfig(top_k=2))
    different = GenerationSupportSnapshot(ModelTarget(ModelId("other")))
    with pytest.raises(DomainValidationError, match="target"):
        validate_request_support(request, different)
    wrong_kind = GenerationSupportSnapshot(DeploymentTarget(DeploymentId("model1")))
    with pytest.raises(DomainValidationError, match="target"):
        evaluate_request_support(request, wrong_kind)


@pytest.mark.parametrize("bad", ["unknown", "", "api_key", "native_temperature", 1])
def test_snapshot_accepts_only_allowlisted_parameter_names(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="unknown"):
        ParameterSupport(cast(str, bad), CapabilitySupport(SupportLevel.NATIVE))


def test_duplicate_support_items_are_rejected() -> None:
    item = ParameterSupport("top_k", CapabilitySupport(SupportLevel.NATIVE))
    with pytest.raises(DomainValidationError, match="duplicate"):
        GenerationSupportSnapshot(_request().target, (item, item))


def test_invalid_snapshot_content_or_type_rejected() -> None:
    with pytest.raises(DomainValidationError):
        GenerationSupportSnapshot(cast(ModelTarget, "model"))
    with pytest.raises(DomainValidationError):
        GenerationSupportSnapshot(_request().target, cast(tuple[ParameterSupport, ...], [1]))
    with pytest.raises(DomainValidationError):
        ParameterSupport("top_k", cast(CapabilitySupport, SupportLevel.NATIVE))
    with pytest.raises(DomainValidationError):
        evaluate_request_support(cast(InferenceRequest, None), GenerationSupportSnapshot(_request().target))
    with pytest.raises(DomainValidationError):
        evaluate_request_support(_request(), cast(GenerationSupportSnapshot, None))


def test_report_and_assessment_require_strict_types() -> None:
    with pytest.raises(DomainValidationError, match="assessed parameter"):
        ParameterAssessment("not_a_parameter", SupportLevel.NATIVE)
    with pytest.raises(DomainValidationError, match="assessment level"):
        ParameterAssessment("top_p", cast(SupportLevel, "native"))
    with pytest.raises(DomainValidationError, match="tuple"):
        CompatibilityReport(cast(tuple[ParameterAssessment, ...], []))
    good = ParameterAssessment("top_p", SupportLevel.NATIVE)
    with pytest.raises(DomainValidationError, match="duplicate"):
        CompatibilityReport((good, good))


def test_snapshot_is_immutable() -> None:
    snap = GenerationSupportSnapshot(_request().target)
    with pytest.raises(FrozenInstanceError):
        snap.parameters = ()  # type: ignore[misc]
