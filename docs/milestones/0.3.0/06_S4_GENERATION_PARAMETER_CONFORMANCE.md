# PyLLMKit 0.3.0 - S4 Generation Compatibility and No-Silent-Drop

> Date : 2026-11-06
> Status : **S4-G4 technical implementation in progress, independent review pending**
> Source dependency : S3 [PR #91](https://github.com/tawounfouet/pyllmkit/pull/91)
> Scope : six native request encoders; no live HTTP or billing.
> Ticket : [#86](https://github.com/tawounfouet/pyllmkit/issues/86)

## Goal

The multi-provider contract promises that every explicitly provided generation
option is either encoded faithfully under a known native field **and**
validated against a trusted NATIVE capability assessment, or refused
explicitly. A directly constructed `PreparedInvocation` is public and
must not become a bypass around the service's `GenerationSupportSnapshot`
validation.

The profile is a **local software encoding promise**, not a claim that
every remote model currently accepts the parameter. No default,
emulation, coercion or silent truncation of `stop_sequences`.

## Code-level native parameter inventory (reviewed at S4 baseline)

| Canonical parameter | OpenAI | Anthropic | Gemini | xAI | Mistral | Ollama |
|---|---|---|---|---|---|---|
| temperature | temperature | temperature | temperature | temperature | temperature | temperature |
| top_p | top_p | top_p | topP | top_p | top_p | top_p |
| top_k | REJECT | top_k | topK | REJECT | top_k | top_k |
| max_output_tokens | max_output_tokens | max_tokens | maxOutputTokens | max_output_tokens | max_tokens | num_predict |
| seed | REJECT | REJECT | seed | REJECT | random_seed | seed |
| stop_sequences | REJECT | stop_sequences | stopSequences | REJECT | stop | stop |
| presence_penalty | REJECT | REJECT | presencePenalty | REJECT | presence_penalty | REJECT |
| frequency_penalty | REJECT | REJECT | frequencyPenalty | REJECT | frequency_penalty | REJECT |

A non-`REJECT` cell means that the **encoder** has an explicit mapping.
It does not mean a remote deployment has advertised NATIVE support.
Even a mapped field requires `SupportLevel.NATIVE` for the exact target.

## Divergences reproduced and corrected

Initial S4 cross-provider acceptance revealed 30 bypass cases:
OpenAI and Ollama encoded `temperature`, `top_p` or
`max_output_tokens` even when the supplied `PreparedInvocation`
declared UNKNOWN/UNSUPPORTED/PARTIAL/EMULATED or omitted the assessment.
The application pipeline already rejected these states but direct encoder
entrypoints did not.

The two encoders now revalidate `parameter_assessment` before adding
native fields; an insufficient level results in
`InvocationPortError("unknown_generation_parameter")`. They continue
to reject inherently non-representable fields with
`unsupported_generation_parameter`.

This is an adapter-boundary correction only, preserving all public
Protocol signatures and M5 event semantics.

## Cross-provider acceptance cases

| Scenario group | Dimensions | Expected tests |
|---|---|---:|
| Native mapping vs explicit provider refusal | 8 canonical parameters x 6 providers | 48 |
| Non-NATIVE direct port denial | 3 core parameters x 4 non-NATIVE states x 6 providers | 72 |
| Missing assessment direct port denial | 3 core parameters x 6 providers | 18 |
| Application preflight deny before any fake adapter calls | 4 support levels x 6 providers | 24 |
| **Total S4** | | **162** |

The four support states are UNKNOWN (None), UNSUPPORTED, PARTIAL and
EMULATED. A zero-contact application preflight may return
`unsupported_generation_parameter` for explicit UNSUPPORTED, and
`unknown_generation_parameter` for all other non-NATIVE conditions.

New test module: `tests/conformance/test_v030_s4_generation_parity.py`.
The CI conformance reporter requires all **162** cases in addition to
the existing 380 cases, yielding **542** contract scenarios per Python
version once qualified.

## Gate S4-G4

- [x] Independent test parametrization across all six native encoders.
- [x] Red cases observed before fix in OpenAI/Ollama.
- [x] Provider adapter validations tightened without changing domain.
- [ ] Exact-head CI Python 3.11/3.12/3.13 and 542-case report PASS.
- [ ] Human/independent technical review of provider native parameter claims.
- [ ] Tests of entire multi-turn role histories, usage and finish reasons.
- [ ] No version bump, no live provider execution, no release, no merge.

**Decision: S4 partial, NO-GO for milestone closure/release until outstanding
gates are satisfied.** Operational security and governance remain tracked
in #22, #35, #36 and #81.
