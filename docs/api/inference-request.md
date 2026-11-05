# PyLLMKit - Inference Request Domain API (L3.1)

**Status:** Implementation candidate on L3.1 feature branch, **G1 not yet qualified**. Architecture ADR-014/015/016/021 approved at P3-G0. Package metadata still 0.1.0a2 (unpublished) until a3 qualification.

## Scope and boundaries

This code represents the **intent** to run inference, not an inference invocation.

- `ModelTarget(ModelId)`, `DeploymentTarget(DeploymentId)`, `EndpointTarget(EndpointId)` are three immutable typed references. No discovery, URL fetch, registry or credential validation.
- `InferenceRequest` is an immutable Value Object, with a target, a nonempty ordered tuple of Phase 2 `Message` values, and an optional `GenerationConfig`.
- `GenerationConfig` has 8 optional parameters, all defaulting to `None`. Exact finite `float` for decimal fields (`temperature=0.0` valid; integer `0` invalid), exact `int` excluding `bool` for integer fields.
- `stop_sequences` is a tuple of nonempty strings; an explicitly empty tuple is valid and distinct from `None`; order and repeats preserved.
- A successful request constructor does **not** imply that the target is available, or that the target supports images, tools, a parameter or an output type.

## Constructing a request

```python
from pyllmkit.domain import (
    Content, GenerationConfig, InferenceRequest, Message,
    ModelId, ModelTarget, Role, TextContent,
)

request = InferenceRequest(
    target=ModelTarget(ModelId("example/llm")),
    messages=(Message(Role.USER, Content((TextContent("Bonjour"),))),),
    generation_config=GenerationConfig(temperature=0.0, max_output_tokens=128),
)
assert request.target.kind == "model"
```

## Optional compatibility check (ADR-021 option A, AC-007)

Only a **caller-supplied, target-specific snapshot** is inspected. The current implementation does not fetch model capabilities or resolve deployments/endpoints. Missing declarations are **UNKNOWN**, never implicitly NATIVE. EMULATED/PARTIAL are not treated as confirmed native.

```python
from pyllmkit.domain import (
    CapabilitySupport, GenerationSupportSnapshot,
    ParameterSupport, SupportLevel, validate_request_support,
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
```

An explicit `SupportLevel.UNSUPPORTED` declaration triggers `DomainValidationError` naming the rejected **allowlisted parameter only**. A report containing unknown, partial, emulated or **no assessed parameters** has `is_compatible is None`, not True. `is_compatible` is **parameter compatibility** only, never endpoint availability or safe execution.

## Design evidence

| Criterion | Contract |
|---|---|
| P3-AC-001 | ModelTarget + text Message |
| P3-AC-002 | Text/image parts remain ordered and unchanged |
| P3-AC-003 | Missing/incorrect target rejected |
| P3-AC-004 | NaN/Infinity rejected |
| P3-AC-005 | None vs zero treated distinctly |
| P3-AC-006 | Bool rejected for int fields |
| P3-AC-007 | Explicit UNSUPPORTED rejected using provided snapshot |

These tests are **proposed execution evidence** until PR CI and integrated main CI are verified. No a3 JSON codec is implemented in L3.1 (ADR-020 belongs to L3.4). No Run, Response, streaming, tool execution, provider SDK or transport is included here.
