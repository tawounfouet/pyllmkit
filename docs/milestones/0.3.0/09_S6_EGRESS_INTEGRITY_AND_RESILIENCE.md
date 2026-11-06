# PyLLMKit v0.3.0 - S6 Egress Integrity & Resilience

> Date: 2026-11-06
> Status: **S6 ENGINEERING SLICE UNDER VALIDATION; FULL G6 SECURITY GATE PENDING**
> Base: S5 PR #94, `e805f59a90b057688a4859992471f2f6f7795209`
> Issues: #36 (live boundary), #81 (operational security), #22 (main protection), #35 (release).
> No actual provider network, secret-manager access, canary expense or release.

## Scope and threat boundary

The Phase 7 transport model supports exactly six native providers,
an explicit `allow_live` opt-in, official cloud endpoints or an
opted-in Ollama loopback IP literal, no HTTP proxy via environment,
no automatic redirects and no retry. A URL accepted by a transport
must remain canonical **at every invocation**, including if a frozen
configuration was tampered with after construction.

The gate must reject an unapproved destination **before**
`CredentialResolverPort.resolve()` and before HTTPX is called.
An invocation with an expired deadline must also stop before transport.
The tests use a synthetic secret and injected `httpx.MockTransport`.
This is not a DNS, peer-IP, certificate or network-adapter security proof.

## Red-to-green findings

Prior to S6 changes, a six-provider adversarial test matrix reproduced
**30 failures** against the inherited S5 implementation:

1. `cloud_post_async` accepted an arbitrary `url` argument, unlike
   `cloud_post_sync`, because it omitted `_validate_destination`.
   **20 cases** (5 cloud profiles x 4 invalid destinations) confirmed
   the asymmetric validation.
2. `OpenAIResponsesAdapter` / `AsyncOpenAIResponsesAdapter` validated
   the frozen `ProviderConnectionConfig` at construction only.
   Mutating `endpoint_url` after construction bypassed that initial
   validation. **2 cases**.
3. Ollama `_preflight` checked only parsed host and path. It did not
   verify the exact canonical scheme, netloc, credentials, query or
   fragment when a previously validated config was tampered with.
   **8 cases** (four variants x sync/async).

No tests contacted an external provider or leaked real credentials.
The assertion that these are security defects is based on observed
mock destination contact, not an externally exploited incident.

## Corrections

| Component | S6 fix | Runtime boundary |
|---|---|---|
| `cloud_http.cloud_post_async` | Call `_validate_destination` immediately after `validate_cloud_connection` and **before** payload/secret processing | Equal destination checks for sync/async |
| `openai_responses.*Adapter.invoke/ainvoke` | Re-run `_validate(config, credentials)` per invocation | Prevent post-construction endpoint mutation |
| `ollama._preflight` | Re-run `ProviderConnectionConfig._validate_local_endpoint()` and map unsafe configuration to `adapter_connection_invalid` | Enforce exact IPv4/IPv6 loopback URL syntax |
| `tools/v030_conformance_report.py` | Include S6 provider/mode/fixture/oracle matrix in CI | Safe machine-readable evidence |

The domain model, `InferencePort`/M5 protocols, error taxonomy,
generation semantics and retry count (`max_attempts=1`) are unchanged.
The canonical Ollama validation is strict by construction: explicit
`http://127.0.0.1:<port>/api/chat` or
`http://[::1]:<port>/api/chat`, without userinfo or URL suffixes.

## Offline S6 conformance matrix

| Scenario | Providers | Modes | Cases | Oracle |
|---|---|---|---:|---|
| Bad cloud destination (external, local, subdomain, userinfo) | 5 cloud | sync/async | 40 | Refusal **before** credential resolution and request |
| Valid exact cloud destination | 5 cloud | sync/async | 10 | One authorized mock request, one synthetic credential resolution |
| Mutated OpenAI config after construction | OpenAI | sync/async | 2 | `adapter_connection_invalid`, no mock request |
| Mutated noncanonical Ollama URL | Ollama | sync/async | 8 | `adapter_connection_invalid`, no mock request |
| Past-deadline invocation | 6 providers | sync/async | 12 | `provider_timeout`, no mock request |
| **Total new S6 cases** | | | **72** | Strict test oracle |
| **Expected combined S0-S6 cases** | | | **752** | Deterministic offline conformance |

All test case identifiers use safe parameter labels; synthetic URL
userinfo and query values are not embedded in the uploaded evidence
`case_id`. No raw JUnit failure stack trace is uploaded.

Files:
- `tests/conformance/test_v030_s6_egress_integrity.py`
- `tools/v030_conformance_report.py`

## Qualification checklist

- [x] Reproduced 30 real pre-fix violations via synthetic HTTPX transport.
- [x] Implemented matching sync/async destination validation.
- [x] Added OpenAI per-invocation config revalidation.
- [x] Added Ollama canonical loopback endpoint revalidation.
- [x] Added expired-deadline fast refusal across six providers.
- [x] Added S6 assertions to the conformance evidence gate.
- [ ] Exact final PR SHA: Python 3.11, 3.12, 3.13 CI green.
- [ ] 752 PASS scenarios with three nonempty JSON/MD artifacts.
- [ ] Independent technical/security code review and G6 decision.
- [ ] Explicit policies for production DNS resolution / peer-IP
  verification, TLS identities, redirect/proxy bypass and SSRF
  under real transport stack (#36, #81).
- [ ] Verify sync real HTTP streaming hard-stop policy before deployment.
- [ ] Protect `main` and obtain release governance authorization
  before any version tagging or publication (#22, #35).

## Gate decision

**GO** for review of this bounded offline hardening slice once exact
CI evidence is attached, **NO-GO** for declaring S6/G6 closed,
provider-live security certified, or authorizing `0.3.0` release.
