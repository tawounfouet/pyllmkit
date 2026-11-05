"""L3.1 offline example: typed inference request and support diagnostics."""

from pyllmkit.domain import (
    CapabilitySupport,
    Content,
    GenerationConfig,
    GenerationSupportSnapshot,
    InferenceRequest,
    Message,
    ModelId,
    ModelTarget,
    ParameterSupport,
    Role,
    SupportLevel,
    TextContent,
    validate_request_support,
)

request = InferenceRequest(
    target=ModelTarget(ModelId("example/llm")),
    messages=(Message(Role.USER, Content((TextContent("Bonjour !"),))),),
    generation_config=GenerationConfig(temperature=0.0, max_output_tokens=128),
)
snapshot = GenerationSupportSnapshot(
    target=request.target,
    parameters=(
        ParameterSupport("temperature", CapabilitySupport(SupportLevel.NATIVE)),
        ParameterSupport("max_output_tokens", CapabilitySupport(SupportLevel.NATIVE)),
    ),
)
report = validate_request_support(request, snapshot)

assert report.is_confirmed_native
assert report.is_compatible is True
assert request.messages[0].content.parts[0] == TextContent("Bonjour !")
print("L3.1 offline request constructed and explicitly assessed; no model was invoked.")
