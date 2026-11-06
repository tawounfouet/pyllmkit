# PyLLMKit v0.3.0 - S4 History, Usage and Finish Semantics

> Date: 2026-11-06
> Status: **TECHNICAL SLICE QUALIFIED - S4-G4 INDEPENDENT REVIEW PENDING**
> Base: S4 generation contract PR #92
> Test baseline: `a56352d158f031baac68d4c013e23ca01ee53752`
> Issue: #86
> No external provider calls, deployments, releases, or package version change.

## Purpose

The `text_only_v1` contract guarantees **explicit native differences,
lossless representable values and a common observable failure policy**,
not an identical provider message wire format.

Prior S4 tests qualified each of eight generation settings for six native
encoders. This work qualifies three further dimensions with the real
provider encoders and HTTPX MockTransport adapters.

## Implemented executable scenarios

| Scenario ID | Providers | Test cases | Oracle |
|---|---:|---:|---|
| `test_supported_multiturn_text_history_is_lossless` | 6 | 6 | `SYSTEM, USER, ASSISTANT, USER` ordered; Unicode not lost |
| `test_history_role_restrictions_are_explicit_not_coerced` | 6 | 30 | Unsupported role orders fail, no merges or coercions |
| `test_native_response_usage_and_finish_semantics` | 6 x 2 modes | 60 | Usage zero vs None, completion reason, refusal and negative usage |
| **Total new S4 cases** | | **96** | Pure encoder and mock HTTP sync/async |

Provider-specific checks:
- **OpenAI/xAI Responses:** retain supported role order, including DEVELOPER.
  A completed response lifecycle is not a native STOP generation reason;
  preserve `FinishReasonCode.UNKNOWN`.
- **Anthropic/Gemini:** require leading optional SYSTEM, alternating
  USER/ASSISTANT and ending USER. Reject developer and unsupported order.
  STOP and max-token mappings remain native explicit.
- **Mistral:** permits its native representation of message histories but
  rejects non-leading SYSTEM or a history not ending in USER.
- **Ollama:** supports its native message history; does not silently
  synthesize a remote completion reason or missing usage.

The compatibility matrix is not a claim that all native providers
support arbitrary message histories. A provider's restriction is recorded
as a **supported refusal**, not a failing parity score.

## Normalization and missing data

For the same synthetic input-token-only usage fixture all six native
adapters must preserve `input_tokens=0`, `output_tokens=None`,
`total_tokens=None`, with cached/reasoning counts `None`.
A negative native token count must be rejected with a code-only
`provider_protocol_error` rather than sanitized into zero.

A vendor-specific unknown finish marker maps to
`FinishReasonCode.UNKNOWN`; a known max-token marker maps to
`LENGTH` where the vendor exposes it. OpenAI/xAI Responses status
`completed` does not prove STOP or LENGTH. Native tool-call/reasoning
states that cannot be represented, or a safety-filtered Gemini result,
fail closed.

## Evidence

- [GitHub Actions #42223866671](https://github.com/tawounfouet/pyllmkit/actions/runs/42223866671)
- Tested commit `a56352d158f031baac68d4c013e23ca01ee53752`
- All three Python 3.11, 3.12, 3.13 validation jobs: **SUCCESS**
- **2,602 general tests passed** on each Python version
- **638 conformance scenarios PASS** on each Python version
- Three nonempty conformance artifacts:
  `v030-conformance-3.11`, `v030-conformance-3.12`,
  `v030-conformance-3.13`
- Existing lint, strict type checks and wheel/sdist smoke passed.
- All fixtures are **synthetic** and the HTTPX transports are mock only.

## Gate status

- [x] Six native encoders tested with multi-turn history and Unicode
- [x] No silent coercion of unsupported role orders
- [x] Partial token counts and synthetic error states preserved
- [x] Known vs unknown FinishReason semantics qualified
- [x] Three-Python offline CI and evidence reporter qualified
- [ ] Independent code / native protocol review
- [ ] Real provider canaries authorized with egress and cost controls
- [ ] Full S4-G4 ratification and S8 integrated milestone qualification
- [ ] Main branch protection, release governance and hardening (#22/#35/#36/#81)

**Decision: engineering GO for further offline integration, not release GO.**
Next recommended work: S5 cancellation during active native streams,
provider transport resource closure and adversarial lifecycle cases.
