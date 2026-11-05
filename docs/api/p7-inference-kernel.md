# PyLLMKit - P7 L7.1 - Inference Kernel (offline)

- Date: 2026-11-06
- Status: IMPLEMENTATION IN PR - P7-G1 pending CI and review
- Baseline: P7-G0 main@0238c97b3d808f1c263de99e19e3858ecf58b02a
- No provider SDKs, live invocation, streaming implementation, API credentials, or release bump.

## Composition and ownership

`InferenceService` and `AsyncInferenceService` accept an M6 `DeploymentResolver`,
an explicit sync/async `InferencePort`, a deployment-id -> native-model-alias
mapping, and optionally injected clock/RunId/AttemptId factories.

`InferenceRequest` remains the immutable domain intent, without a RunId.
The service resolves an exact eligible deployment, checks TEXT input/output
availability conservatively, rejects non-text input and unsafe/unknown generation
parameters, then creates an `InvocationContext` and an `InferenceRun` before
invoking the port. `PreparedInvocation` stays in the application boundary.

A port must return an `InferenceResponse` with exactly the prepared RunId.
Success yields a COMPLETED Run. A safe `InvocationPortError` yields a FAILED Run
with a normalized `InferenceFailure`. A local `InvocationCancelledError`
yields a CANCELLED Run without claiming remote cancellation. An unexpected
adapter exception is sanitized to `adapter_unexpected_error`; the raw cause
is never included in the returned execution.

## Important limits

- L7.1 permits exactly one transport attempt. `InvocationContext.next_attempt()`
  checks the future retry correlation contract but DOES NOT perform retries.
- `EndpointTarget` fails `target_not_routable` until L7.2 introduces verified
  endpoint binding; its identifier is never treated as a URL.
- Missing model alias fails `native_model_binding_missing`; no heuristic
  model-name transformation is made.
- `GenerationSupportSnapshot` must correspond to the original request target.
  Explicitly set parameters must be confirmed NATIVE; UNKNOWN/UNSUPPORTED are
  refused before the fake is called.
- P6 deployment AVAILABLE remains descriptive, not proof that a model is online.
- The M5 `StreamingPort` / `AsyncStreamingPort` APIs are left unchanged.
  Stream binding and transport streaming are scheduled for L7.6.
- External `asyncio.Task` cancellation is not captured as a returned Run in
  this MVP; it propagates, without a false terminal/remote-cancel assertion.

## Example

```python
from pyllmkit.application.inference import InferenceService
from pyllmkit.adapters.inference import FakeInferenceAdapter

# catalog/resolver and InferenceRequest are existing M6/M3 objects.
fake = FakeInferenceAdapter("synthetic offline text")
service = InferenceService(
    resolver, fake, {deployment_id: "test-native-alias"}
)
execution = service.invoke(request)
assert execution.response is execution.run.response
```

Only fake-generated text is produced. A real Ollama model response requires
L7.3 and a separately authorized opt-in live test.
