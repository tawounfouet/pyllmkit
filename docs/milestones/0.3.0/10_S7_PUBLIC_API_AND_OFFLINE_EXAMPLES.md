# PyLLMKit 0.3.0 - S7 Public API & Offline Examples

> Date: 2026-11-06
> Status: **S7 DOCUMENTATION / DEMONSTRATION SLICE; G7 PENDING INDEPENDENT REVIEW**
> Base: S6 [PR #95](https://github.com/tawounfouet/pyllmkit/pull/95)
> No migration of the published version `0.1.0a2`, no live provider access.

## Purpose

Users need a truthful distinction between the **implemented six-provider
interfaces**, the **offline conformance guarantee** and the **still
unqualified production network boundary**. S7 preserves the existing
public interfaces and adds an executable demonstration of default-deny
behavior that runs even from an installed wheel **without HTTPX**.

## Deliverables

| Source | Purpose |
|---|---|
| `docs/api/v030-multi-provider-contract.md` | Public import surface, six native profiles, compatibility and safety limits |
| `examples/41_v030_six_provider_default_deny.py` | All six cloud/local providers, sync and async, `allow_live=False` |
| `.github/workflows/ci.yml` | Run example 41 as source plus clean wheel without HTTPX |

The example explicitly uses `CredentialRef` and
`EnvCredentialResolver(..., environ={})` and never requests or loads
real credentials. It intentionally passes an arbitrary placeholder as
the request parameter to check **authorization precedes invocation
preparation**, and is described as a *guard diagnostic*, not an
inference tutorial. Actual offline inference composition remains in
`examples/29` and `38`; native HTTP mock examples in `31,33..37`.

## Public guarantees documented

- Sync/async prepared inference ports and M5 streaming contract
  remain separate, no rename or added parameter.
- NATIVE capabilities are strict, no silent mapping of unsupported
  fields, roles or multimodal/tool output to text.
- `Usage` partial observations remain partial; lifecycle completed
  does not prove generation STOP; local cancellation never implies
  remote billing or provider cancellation.
- One attempt, no fallback, no redirects/proxy inference, explicit
  opt-in, fixed cloud destinations or strict Ollama loopback IP URLs.
- All vendor-live DNS/peer-IP/TLS security and release governance
  questions stay open (#22, #35, #36, #81).

## Acceptance checks

- [x] Public API guide points to existing documented import surfaces,
  examples and restrictions instead of inventing a new Facade.
- [x] Source smoke example asserts 12 denial codes and zero real
  credential resolution / socket connections.
- [x] CI invokes the example using both repository sources and the
  installed wheel environment with no optional dependency.
- [ ] CI exact HEAD successful on Python 3.11, 3.12, 3.13.
- [ ] Public guide and example code independently reviewed.
- [ ] S7-G7 decision recorded with explicit release prohibition.

## Release boundary

This tranche adds docs and a smoke example, **not a 0.3.0 release**.
No package version change, merge to `main`, GitHub Release, tag,
TestPyPI/PyPI publication or billable provider request is authorized.
