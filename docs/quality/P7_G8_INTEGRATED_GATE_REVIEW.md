# P7-G8 - Integrated Phase 7 acceptance and merge evidence

> Date: 2026-11-06
> Scope: source integration of L7.1 to L7.7 into `main`.
> Decision: **GO to the next development milestone, NO-GO to live production or release**.
> Source merge baseline: `main@4633eba36cb04e818bb908cfe2ac9e48bf275b1e`.

## 1. Intent and scope

The repository owner explicitly requested qualification, validation, and ordered
merge of all open Phase 7 PRs. This report records what was actually checked,
what was not independently reviewed, and which governance gates remain open.
An owner-authorized integration is not equivalent to an independent approval
or a security audit. No live requests, credentials, provider billing, tags,
PyPI releases, or deployments were made during this integration.

## 2. Merge record

Every listed PR was checked as open, non-draft, mergeable and CI-qualified at
its frozen head SHA. Each was retargeted to `main` **in dependency order**
and merged using the GitHub merge-commit method with an expected-head-SHA
check. This retains the original commit ancestry rather than flattening
stacked changes.

| PR | Lot | Merge commit |
|---|---|---|
| [#70](https://github.com/tawounfouet/pyllmkit/pull/70) | L7.1 offline inference kernel | `e34dc26c5be72b3bc07cfda69b840e6efe30c2d0` |
| [#71](https://github.com/tawounfouet/pyllmkit/pull/71) | L7.2 secure adapter registry | `813f748feae7ef518de665b7b284d93c4c641ec1` |
| [#72](https://github.com/tawounfouet/pyllmkit/pull/72) | L7.3 Ollama | `6353fa50c224abcd6ab911c3bc04ef6cf274fd8c` |
| [#73](https://github.com/tawounfouet/pyllmkit/pull/73) | L7.4 OpenAI Responses | `6a6f75e0d1ac3efb39a7cfab999e041615c5ae0d` |
| [#74](https://github.com/tawounfouet/pyllmkit/pull/74) | L7.5 Anthropic | `fbe287cc94d78695078e4d84f17db9062b3416b6` |
| [#75](https://github.com/tawounfouet/pyllmkit/pull/75) | G5b Google Gemini | `048d35ca2aa7837f4338641fcad7a7e2378cf00f` |
| [#76](https://github.com/tawounfouet/pyllmkit/pull/76) | G5c xAI | `9ba7f373ea08196310fd55385377538ec88093d1` |
| [#77](https://github.com/tawounfouet/pyllmkit/pull/77) | G5d Mistral | `f883eac104d08494b7f00351dd3479b905844fe5` |
| [#78](https://github.com/tawounfouet/pyllmkit/pull/78) | L7.6 six-provider native streaming | `9be220c05babe4a222c7f25af881cf2f1e4da814` |
| [#79](https://github.com/tawounfouet/pyllmkit/pull/79) | L7.7 cancellation and deadline safety | `4633eba36cb04e818bb908cfe2ac9e48bf275b1e` |

The merged baseline `main@4633eba36` contained the full L7.7 head, and
the difference between the L7.7 branch and main was zero files. Search
reported zero remaining open PRs before the follow-up coverage-fix PR #80.

## 3. CI evidence and correction

All ten original PR heads had a completed `success` CI run. The integrated
main push run
[42210214065](https://github.com/tawounfouet/pyllmkit/actions/runs/42210214065)
reported `success` for `validate (3.11)`, `validate (3.12)`, and
`validate (3.13)`, with **1,890 general tests passed** on Python 3.12.

**Important discovered inconsistency:** the initial integrated main log
reported L7.6 coverage of **89.81% (3.11)** and **89.90% (3.12/3.13)**,
below the required 90%, even though its GitHub Actions step and overall
job were marked `success`. A green GitHub check alone was therefore
insufficient evidence of the coverage gate.

Follow-up [PR #80](https://github.com/tawounfouet/pyllmkit/pull/80)
extends the L7.6 coverage run with the L7.7 transport resilience tests
without reducing the threshold. Its qualification run
[42210586947](https://github.com/tawounfouet/pyllmkit/actions/runs/42210586947)
recorded the following on **each** of Python 3.11, 3.12 and 3.13:

- L7.6 native mapping/transport/application branch coverage: **90.87%**,
  satisfying its 90% threshold with **248 passing focused tests**.
- L7.7 cancellation module branch coverage: **100.00%**, satisfying
  its 95% threshold with **47 passing focused tests**.
- General offline suite: **1,890 passing tests**.
- All CI matrix jobs: `success`; lint, type checks, package build, wheel,
  source distribution and offline example steps were included.

The two focused runs overlap intentionally and their pass counts **must not
be added** to the general suite as independent tests.

## 4. Reviewed constraints and exceptions

- **No independent GitHub PR reviews:** PRs #70-#79 had zero reviews and zero
  inline review threads before merging. The repository owner authorized
  the integration, but no third-party `APPROVED` sign-off was recorded.
- **Main branch governance is absent:** GET `branches/main` reported
  `protected=false`; GET `rulesets` returned `[]`. The installed
  GitHub connector cannot write branch-protection rules. Issue
  [#22](https://github.com/tawounfouet/pyllmkit/issues/22) remains open.
- **Security boundary not certified:** no real provider calls, peer IP/TLS
  handshake attestations, DNS rebinding assessment or cloud-budget caps.
  Issue [#36](https://github.com/tawounfouet/pyllmkit/issues/36) remains open.
- **No release authorization:** versioning, distribution, tags, OIDC,
  artifact provenance and independent release approval remain in
  [#35](https://github.com/tawounfouet/pyllmkit/issues/35).
- **Sync streaming limitation:** real synchronous HTTPX streams are refused
  with `sync_stream_deadline_not_enforceable`. A monotonic check over
  received lines is not an enforceable deadline around an indefinite
  blocking socket operation.
- **Cancellation semantics:** cooperative session cancellation is local;
  it does not assert remote provider cancellation or billing cessation.
- **Retries/failover:** no automatic retry or fallback after partial
  streamed output; cloud live invocations are not production-qualified.

## 5. Gate decision and next milestone

| Decision boundary | Result |
|---|---|
| Source code integrated on `main` | GO |
| Offline CI and target coverage after PR #80 | GO on the recorded PR #80 SHA |
| Begin next engineering milestone | GO |
| Independent security certification | NOT DONE |
| Protected-main/reviewer enforcement | NO-GO |
| Production live provider execution | NO-GO |
| Tag, GitHub Release, TestPyPI or PyPI | NO-GO |

**Next proposed milestone: L7.8 - Operational Security & Release Readiness.**

Acceptance work should include effective GitHub ruleset enforcement,
human/independent review, connection-time DNS and peer verification,
real-network controlled tests with opt-in and budgets, externally
enforceable sync deadlines (or permanent documented sync-live restriction),
tracing without prompt/secret leakage, and an explicit provider/release
risk acceptance decision. These are **future work**, not evidence already
supplied by this integration.

PR #80 must itself pass the exact-head CI and be merged before declaring
the documented G8 source gate integrated. After that merge, the new main
commit needs an independent push-CI check at its exact SHA.
