# PyLLMKit 0.3.0 - S9 Release Readiness Gate

> Date: 2026-11-06
> Status: **NO-GO FOR RELEASE**
> Integrated baseline: `main@9259c99c1ae3469c8abb639e1999fb1439563cc3`
> Source integration evidence: [12_S8_SOURCE_INTEGRATION_AND_MAIN_QUALIFICATION.md](12_S8_SOURCE_INTEGRATION_AND_MAIN_QUALIFICATION.md)
> This runbook does not initiate release operations.

## 1. What is already qualified

Eleven development PRs #82-#97 were integrated in dependency order
and `main` passed three Python CI jobs on the exact resulting commit.
The deterministic text-only contract covers six native provider
adapters (OpenAI, Anthropic, Google, xAI, Mistral and Ollama).
The source suite has 2,731 tests PASS per Python 3.11/3.12/3.13;
the provider conformance matrix has 752 PASS per Python, and the
separate S8 integrity checker has PASS for the same 752 cases.

These tests are **offline and synthetic**, do not spend provider
tokens and do not establish production readiness or safe external
network operation.

## 2. Pre-publication acceptance checklist

| Gate | Required evidence | Status |
|---|---|---|
| Source integration | Exact `main` SHA, green CI and matching artifacts | PASS |
| Compatibility | Six provider adapters, sync/async native text conformance | PASS offline |
| Public API | Documentation and no-HTTPX default-deny smoke | PASS offline |
| Peer review | Independent approvals for security and API behavior, not merely owner merge | **BLOCKED** |
| GitHub governance | Main ruleset / branch protection, 3 required CI checks, PR review policy and no force-push | **BLOCKED**, issue #22 |
| Provider boundary | DNS/peer-IP/TLS, SSRF/rebinding prevention, redirect/proxy controls, pinned destination policy | **BLOCKED**, issues #36/#81 |
| Live operation | Explicit scoped provider/model opt-in, per-run token/cost budget, rate budget, secret vault, bounded timeout | **BLOCKED**, issue #81 |
| Native sync streaming | Demonstrable hard-stop lifetime bound, otherwise keep fail-closed | **BLOCKED** for real sync streaming |
| Distribution | Reproducible wheel/sdist provenance, release signing/OIDC, policy approval and rollback | **BLOCKED**, issue #35 |
| Version policy | Approved target alpha vs stable semver and migration notice | NOT DECIDED |

Repository version is **`0.1.0a2`**; do not mistake the
`0.3.0` documentation milestone for an already released distribution.

## 3. Authorized paths and forbidden shortcuts

Permitted:
- develop/tests/docs on a normal PR after `main` protections
  become effective;
- run offline MockTransport and fake-adapter tests;
- request formal independent security, API and release reviews;
- prepare draft, non-published release metadata after approved policy.

Not authorized by this gate:
- any billable provider request or live canary;
- privileged DNS/peer-IP/TLS assumptions from MockTransport fixtures;
- publishing to TestPyPI/PyPI or pushing a `v0.3.0*` tag;
- silently bumping `pyproject.toml`, a GitHub Release or production rollout;
- bypassing future branch protections as a release shortcut.

## 4. Administrative follow-up (owner action required)

The connected GitHub integration has read/write repository content and
merge capabilities but does **not** have access to repository
administration endpoints for branch protection. GitHub shows
`main.protected=false` and an empty ruleset list; its detailed
`branches/main/protection` endpoint returned HTTP 403. Therefore the
rule must be configured by a repository administrator in GitHub:

`Repository > Settings > Rules > Rulesets` (or Branch protection rules),
target branch `main`, then require pull requests and all
`validate (3.11)`, `validate (3.12)`, `validate (3.13)` checks,
independent approvals, and prohibit deletion/force-push and unreviewed
bypasses. Independently verify the rules are **active and enforced**,
not merely described in a document.

An independent reviewer must also evaluate the already integrated
changes and any follow-on remediation. The owner-authorized historical
merges do **not** count as a formal independent review.

## 5. Decision

- Source integration: **GO, completed**.
- Offline contract: **GO, validated on exact SHA**.
- Release candidate, provider-live canary, production and PyPI:
  **NO-GO** until each blocked gate has verifiable evidence.

**No S9 publication operation is authorized or performed.**
