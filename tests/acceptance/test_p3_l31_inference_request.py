"""P3-AC-001..007: L3.1 typed inference request acceptance, offline."""

from typing import cast

import pytest

from pyllmkit.domain import (
    CapabilitySupport,
    Content,
    DomainValidationError,
    GenerationConfig,
    GenerationSupportSnapshot,
    ImageContent,
    InferenceRequest,
    MediaSourceRef,
    Message,
    ModelId,
    ModelTarget,
    ParameterSupport,
    Role,
    SupportLevel,
    TextContent,
    validate_request_support,
)


def test_p3_ac001_create_model_request_with_text_message() -> None:
    request = InferenceRequest(
        ModelTarget(ModelId("my-model")),
        (Message(Role.USER, Content((TextContent("Bonjour"),))),),
    )
    assert request.target.kind == "model"
    assert request.messages[0].content.parts[0] == TextContent("Bonjour")


def test_p3_ac002_preserve_mixed_content_and_order_without_vision_claim() -> None:
    content = Content((
        TextContent("What is in this image?"),
        ImageContent(MediaSourceRef("asset", "asset-123")),
        TextContent("Be precise."),
    ))
    message = Message(Role.USER, content)
    request = InferenceRequest(ModelTarget(ModelId("unresolved-model")), (message,))
    assert request.messages[0] is message
    assert request.messages[0].content.parts is content.parts
    assert tuple(part.kind for part in content.parts) == ("text", "image", "text")
    # No effective capabilities are inferred by the request constructor.
    assert not hasattr(request, "effective_vision_support")


def test_p3_ac003_missing_target_rejected() -> None:
    message = Message(Role.USER, Content((TextContent("test"),)))
    with pytest.raises(DomainValidationError, match="target"):
        InferenceRequest(cast(ModelTarget, None), (message,))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_p3_ac004_non_finite_temperature_rejected(bad: float) -> None:
    with pytest.raises(DomainValidationError, match="temperature"):
        GenerationConfig(temperature=bad)


def test_p3_ac005_none_vs_zero_max_output_tokens() -> None:
    assert GenerationConfig().max_output_tokens is None
    with pytest.raises(DomainValidationError, match="max_output_tokens"):
        GenerationConfig(max_output_tokens=0)


@pytest.mark.parametrize("field", ["top_k", "max_output_tokens", "seed"])
def test_p3_ac006_bool_rejected_for_integer_parameters(field: str) -> None:
    with pytest.raises(DomainValidationError, match=field):
        GenerationConfig(**{field: True})  # type: ignore[arg-type]


def test_p3_ac007_explicit_unsupported_parameter_rejected_without_fallback() -> None:
    request = InferenceRequest(
        ModelTarget(ModelId("my-model")),
        (Message(Role.USER, Content((TextContent("hello"),))),),
        GenerationConfig(top_p=0.9),
    )
    snapshot = GenerationSupportSnapshot(
        request.target,
        (ParameterSupport("top_p", CapabilitySupport(SupportLevel.UNSUPPORTED)),),
    )
    with pytest.raises(DomainValidationError, match="unsupported generation parameter: top_p"):
        validate_request_support(request, snapshot)
    assert request.generation_config == GenerationConfig(top_p=0.9)
