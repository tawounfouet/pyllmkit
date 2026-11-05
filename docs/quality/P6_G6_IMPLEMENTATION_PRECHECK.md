# P6-G6 - L6.6 Offline Discovery & Merge implementation precheck

- Date: 2026-11-05
- Status: CANDIDATE / NOT YET QUALIFIED
- Stack: PR #59 -> #60 -> #61 -> #62 -> #63 -> #64 -> L6.6
- Version remains `0.1.0a2`; `0.1.0b2` is an unapproved target.

## Scope
- Typed `DiscoverySourcePort` and deterministic `StaticDiscoverySource`, no SDK/HTTP/automatic registration.
- Frozen `DiscoveryResult`, `MetadataSource`, source provenance, explicit UTC observation time.
- Injected-clock validation with opt-in future skew; naive, non-UTC and unsupported source rejected.
- Bounded candidate batches (10,000 per kind), duplicate ID rejection and limited warning counts.
- `CatalogMergeService.preview` is a read-only, deterministic dry-run; adds, identical replays, changed fields, existing/import provenance and missing references explicitly represented.
- `CatalogMergeService.apply` requires a matching preview and a matching catalog revision, validates dependencies, rejects the **entire batch** when conflicts/references are invalid.
- InMemory ports now publish copy-on-write root snapshots; coordinated `commit_snapshot` switches one shared root pointer after full validation.
- Only `FAIL_ON_CONFLICT` is implemented. No precedence based on timestamps or source order.
- Replays are no-ops. Catalog deletes drop provenance; old M1-M5 APIs remain additive.
- P6-AC-041..048 are covered by acceptance tests, negative cases and architectural checks.

## Important limitations
- Atomicity is one **in-process** catalog snapshot swap with optimistic revision checks; cross-process, distributed and concurrency transaction guarantees are **not** claimed.
- Catalog import is metadata only. No physical endpoint discovery, healthchecks, execution, provider adapters, HTTP or API keys.
- No untrusted file parser in L6.6 MVP. Static source is already typed fixture data; local-file parsing is deferred pending a bounded, versioned codec ADR.

## Qualification outstanding
- [ ] Ruff, mypy strict, tests with >=95% branch coverage, wheel/sdist and Python 3.11/3.12/3.13 CI on this head.
- [ ] Exact-main qualification of all predecessor gates #59..#64 and owner design review.
- [ ] L6.6 review, merge and exact-main CI; P6-G6 formal gate record.
- [ ] No tag, release, package publish or version bump.
