# P7-G6 - Native streaming security and lifecycle precheck

## Scope and authority

- Phase: P7 / L7.6 - native streaming across Ollama, OpenAI Responses,
  Anthropic Messages, Google Gemini, xAI Responses and Mistral Chat.
- Pull request: https://github.com/tawounfouet/pyllmkit/pull/78
- Stacked base: `p7/l75d-mistral-chat-adapter` (PR #77).
- This is a technical precheck for independent review, not a production,
  cloud-invocation, merge or release authorization.
- Tests use injected HTTPX MockTransport. They do not attest runtime DNS,
  destination IP, TLS negotiation with a real provider or expenditure controls.

## Architectural invariants

1. Existing M5 `StreamEvent`, `StreamingPort.stream(request)`,
   `AsyncStreamingPort.astream(request)` and deterministic reducer stay stable.
2. One logical run has one `InferenceRunId`, with contiguous public event sequences.
3. A stream reaches `ResponseCompleted` only after the provider's native
   successful terminal condition, never after EOF or missing terminal markers.
4. Unrecognized events, tool calls, reasoning outputs, non-text payloads,
   native error bodies and protocol contradictions fail closed.
5. User-visible failures expose normalized reason codes only, not raw credentials
   or provider error responses.
6. The adapter is explicitly bound to an identified deployment and native model
   alias. No implicit provider discovery, fallback, retry or network at import.

## Security and lifecycle regression additions

The additional `test_p7_l76_security_lifecycle.py` suite exercises:

- OpenAI and xAI created/in-progress frames carrying hidden outputs, tools,
  storage changes, errors or model identity mismatches.
- Output item and content part lifecycle frames carrying non-text content,
  encrypted state, invalid indexes, and text inconsistent with deltas.
- OpenAI/xAI text deltas carrying unrepresentable metadata.
- Ollama native error frames and hidden message fields.
- Anthropic ping, text block and message stop events with unexpected fields.
- Gemini error frames that would otherwise coexist with a normal candidate.
- Mistral unrecognized reasoning fields in delta frames.
- All six provider streams truncated in the asynchronous transport.
- All six provider streams with additional frames after native termination,
  which must never produce a successful public terminal event.

The native decoder rejects these additional unsupported payloads explicitly.
The G6 coverage job must run both acceptance files and meet at least 80 percent
branch coverage of the streaming application, transport and mapper together.

## Qualification procedure

- [ ] CI succeeds on the final exact PR head SHA (push and pull_request workflows).
- [ ] Python 3.11, 3.12 and 3.13 pass offline tests.
- [ ] Ruff and mypy strict pass.
- [ ] Dedicated G6 branch coverage reaches >=80% with no omitted security tests.
- [ ] Wheel, sdist and installed-wheel smoke checks pass.
- [ ] Independent technical review attests provider wire mapping and M5 behavior.
- [ ] Independent security review assesses transport boundary and secret handling.
- [ ] All upstream G1-G5d gates are independently reviewed and merged in order.
- [ ] `main` branch protection, required checks and reviewer policies are enforced.

## Open risks and explicit NO-GO decisions

- Synchronous HTTPX timeouts are per phase; trickle streams can evade a hard
  wall-clock deadline. Strict sync cancellation or a bounded external execution
  policy is required before live/production authorization.
- Async streaming has an application wall-clock timeout but cancellation,
  resource closure and race behavior must remain under independent review.
- Cloud DNS resolution, connected peer IP, TLS runtime, and redirects require
  independent runtime evidence. MockTransport is not that evidence.
- No enforceable paid invocation budget or approved retention policy exists.
- Unknown native events, reasoning and tools are intentionally unsupported in
  the current strict text-only profile.
- Protected `main`, reviewer independence and release authority remain unresolved.
- Do not execute cloud or Ollama live smoke tests as part of this gate.
- Do not merge PR #78 or publish any package based on this precheck alone.

## Decision

**Status: IN REVIEW / NO-GO for merge, live invocation and release.**

Technical GO for requesting independent review requires green CI on the exact
head SHA. The gate owner must record the final CI run IDs, coverage figures,
reviewer identity and sign-off only after those facts are observed.
