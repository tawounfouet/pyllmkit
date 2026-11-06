# PyLLMKit - Multi-provider API and contract profile (target 0.3.0)

> Status: **DRAFT S7, NOT A PUBLISHED 0.3.0 API**
> Package on GitHub `main` and the S0-S7 branches: `0.1.0a2` in `pyproject.toml`.
> Target milestone: `0.3.0`, `text_only_v1` conformance.
> Supported Python: 3.11, 3.12, 3.13 (CI). No live provider approval.

## 1. Installation and safe first run

From a local clone:

```shell
python -m pip install -e .
python examples/38_six_provider_offline_registry.py
python examples/41_v030_six_provider_default_deny.py
```

The first example uses explicit registry bindings and **FakeInferenceAdapter**.
The second instantiates actual native sync/async adapters with their
default `allow_live=False` and verifies each rejects before resolving
credentials or importing optional HTTPX. Neither is a paid LLM request.

Network adapters require `httpx` when actually invoked:

```shell
python -m pip install -e '.[providers]'
```

The `providers` extra is optional and does not authorize network I/O
or fetch provider credentials. The current core package has **no mandatory
runtime dependencies**. Actual live requests are **not covered by the
target 0.3.0 offline qualification** and require separately approved
egress policy, TLS/peer-IP controls and cost budget.

## 2. Public composition surfaces (S0 signature freeze)

- `pyllmkit.application.inference.InferenceService.invoke(request, support_snapshot=None)`
- `AsyncInferenceService.ainvoke(request, support_snapshot=None)`
- `StreamingInferenceService.open_stream(request, support_snapshot=None)`
- `AsyncStreamingInferenceService.open_astream(request, support_snapshot=None)`
- `InferencePort.invoke(prepared)` and `AsyncInferencePort.ainvoke(prepared)`
- `PreparedStreamingPort.stream_prepared(prepared)` and
  `AsyncPreparedStreamingPort.astream_prepared(prepared)`
- `InvocationPortError(code)`, `InvocationPreconditionError(code)`,
  `InvocationOptions(max_attempts=1)`, `InferenceExecution`

`InferenceRequest` is immutable provider-agnostic intent. Deployment
resolution selects one explicitly registered endpoint and an explicit
native model alias; the application computes a RunId and attempt ID.
`PreparedInvocation` is an application boundary, **not** a direct
transport destination or a provider-issued model name.

M5 `stream(request)` and `astream(request)` are distinct from the
P7 native prepared-stream ports. Do not replace one with the other.

## 3. Six native adapters

| Provider | Sync class | Async class | Config | Native protocol |
|---|---|---|---|---|
| OpenAI | `OpenAIResponsesAdapter` | `AsyncOpenAIResponsesAdapter` | `ProviderConnectionConfig.openai(ref)` | Responses |
| Anthropic | `AnthropicMessagesAdapter` | `AsyncAnthropicMessagesAdapter` | `ProviderConnectionConfig.anthropic(ref)` | Messages |
| Google | `GoogleGeminiAdapter` | `AsyncGoogleGeminiAdapter` | `ProviderConnectionConfig.google(ref)` | Gemini generateContent |
| xAI | `XAIResponsesAdapter` | `AsyncXAIResponsesAdapter` | `ProviderConnectionConfig.xai(ref)` | Responses |
| Mistral | `MistralChatAdapter` | `AsyncMistralChatAdapter` | `ProviderConnectionConfig.mistral(ref)` | Chat Completions |
| Ollama | `OllamaAdapter` | `AsyncOllamaAdapter` | `ProviderConnectionConfig.ollama_local()` | `/api/chat` |

For native text streaming, `NativeProviderStreamingAdapter` implements
both prepared-stream ports. Five cloud providers use SSE; Ollama
uses JSONL/NDJSON. It is not six separate public streaming classes.

The provider classes, registry and security configuration are exported
by `pyllmkit.adapters.inference`; domain types and services live in
their own packages. Do not import private `_*mapping` codecs as a stable
public SDK.

## 4. Contract compatibility, not feature coercion

The `text_only_v1` profile requires exactly one `TextContent` per
message. Provider support for `SYSTEM`, `DEVELOPER` and
alternating role histories is **not uniform**:

- OpenAI and xAI serialize `DEVELOPER` natively.
- Anthropic/Gemini require restricted alternation; SYSTEM handling is
  leading-only. Unsupported histories fail explicitly.
- Mistral permits leading SYSTEM and requires final USER.
- Ollama supports its native ordered text roles but refuses DEVELOPER.

The eight canonical `GenerationConfig` fields are
`temperature`, `top_p`, `top_k`, `max_output_tokens`,
`seed`, `stop_sequences`, `presence_penalty` and
`frequency_penalty`. A parameter must be encodable **and**
have `SupportLevel.NATIVE` on the exact target to be forwarded.
UNKNOWN, UNSUPPORTED, PARTIAL and EMULATED are not silently
treated as native. The native field inventory is in
[the S4 gate document](../milestones/0.3.0/06_S4_GENERATION_PARAMETER_CONFORMANCE.md).

Unsupported modalities, tool-calls, structured output, private
reasoning or provider-native states not represented in the text profile
must be refused, not flattened or discarded.

## 5. Canonical outputs and errors

- Response `run_id` must equal the prepared invocation RunId.
- `Usage(input_tokens=0)` is different from `None`. Missing output,
  total, cache or reasoning counts remain absent and are never inferred.
- `FinishReasonCode.UNKNOWN` is legitimate. Responses
  `status=completed` is a lifecycle state, not proof of STOP.
- Provider HTTP failures map to **safe code-only errors**, not exception
  messages containing native payloads, prompts, API secrets or headers.
- Native JSON rejects duplicated keys and nonstandard NaN/Infinity;
  unexpected structured output fails closed.
- Streaming emits ordered M5 events, with exactly one terminal event,
  and cancellation is local. Remote billing cessation is **not** promised.

## 6. Operational security boundary

Construction is offline and defaults to `allow_live=False`. The
application must not treat `allow_live=True` alone as a production
authorization. Available protections include fixed configured
destinations, strict per-invocation validation, size/time limits, exact
Ollama loopback URLs, `trust_env=False`, no redirects and one attempt.

**Still unqualified:** production DNS rebinding, the resolved peer IP,
end-to-end TLS identity, provider-live budgets, remote hard deadlines,
independent reviewer approval, branch protection and release gates
(issues #22, #35, #36, #81).

In particular, real **sync** HTTPX streaming is intentionally refused
with `sync_stream_deadline_not_enforceable` until a preemptive total
deadline can be demonstrated. Offline `httpx.MockTransport` cannot
establish remote SSRF/TLS safety.

## 7. Executable examples and evidence

| Example | Purpose | Network |
|---|---|---|
| `examples/29_offline_inference_kernel.py` | Inference service with fake port | None |
| `examples/31_ollama_mock_transport.py` | Ollama native mock | None |
| `examples/33_openai_responses_mock.py` through `37_mistral_chat_mock.py` | Provider-native injected fixtures | None |
| `examples/38_six_provider_offline_registry.py` | Six explicit registry bindings, fake responses | None |
| `examples/39_native_streaming_contracts.py` | Native stream contracts | Synthetic |
| `examples/40_stream_resilience_offline.py` | Cooperative cancellation | None |
| `examples/41_v030_six_provider_default_deny.py` | 12 public default-deny guards, no HTTPX | None |

Conformance evidence is generated by
`tools/v030_conformance_report.py` in CI. Reports are JSON/Markdown
per Python version with exact SHA, scenario, provider, mode, status
and synthetic fixture provenance. **PASS is proof of offline tests
only**, not qualification against remote vendor APIs.

The `0.3.0` version bump, tag, GitHub Release or PyPI publication
remains forbidden until the independent integrated S8 and S9 gates.
