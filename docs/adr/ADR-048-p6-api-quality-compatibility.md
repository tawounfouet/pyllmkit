# ADR-048 - Public contracts, quality, budgets and release boundaries

- Date: 2026-11-05
- Status: PROPOSED (P6-G0 review; not yet qualified)
- Phase: P6 Registry & Discovery / M6
- Baseline: main@19cc1c9e1d5598711890ddc3e14f1da94c79ce70
- References: 06_PYLLMKIT_PHASE_6_REGISTRY_AND_DISCOVERY_IMPLEMENTATION_PLAN.md; domain design 00-09; existing M1-M5 contracts.

## Decision
Public P6 APIs must be typed, additive and importable without provider SDK dependencies. Existing M1-M5 objects, codecs and semver stay unchanged. Add `Registry JSON v1` **only if** replay/fixtures in L6.6 require it, as a distinct versioned codec with strict validation, bounded input size and canonical output; never alter `models`, `interactions`, `inference`, `tooling` or `streaming` v1 formats.

Set prototype memory expectations for 10/1,000/10,000 records; document timings rather than promise production throughput. Limit untrusted static data and nested metadata before allocation; reject unsafe paths, executable payloads and unbounded conflict reports. No credentials or raw user/provider secrets may appear in repr/errors. All P6 public inputs receive strict type validation. Return immutable snapshots, stable sorting and errors with only canonical IDs.

Qualification: 56 P6-AC cases across seven gates; unit, contract, negative, architecture and regression tests; Ruff; mypy strict; Python 3.11/3.12/3.13; >=95% branch-inclusive coverage across package; wheel and sdist build; examples 23..28; CI on the **exact merged main SHA for each gate**. Gate result is independent from publishing. `0.1.0b2` is a target; current `0.1.0a2` remains unchanged. No tag/PyPI/release without explicit authority.

## Verification
P6-AC-049..056, reproducible local and CI evidence, regression tests for all preexisting serialization. Track issues #22 (main protection), #35 (release), #36 (provider boundary).
