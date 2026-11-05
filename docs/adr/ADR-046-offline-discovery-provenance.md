# ADR-046 - Offline discovery, provenance and freshness

- Date: 2026-11-05
- Status: PROPOSED (P6-G0 review; not yet qualified)
- Phase: P6 Registry & Discovery / M6
- Baseline: main@19cc1c9e1d5598711890ddc3e14f1da94c79ce70
- References: 06_PYLLMKIT_PHASE_6_REGISTRY_AND_DISCOVERY_IMPLEMENTATION_PLAN.md; domain design 00-09; existing M1-M5 contracts.

## Decision
`DiscoverySourcePort` yields `DiscoveryResult` containing independently typed providers, models and deployments, warnings, source and `observed_at`. The MVP source is a deterministic in-memory fixture or explicitly permitted local static data file; no SDK, HTTP, scraping or polling. Discovery returns **uncommitted candidates** and does not write registries.

`MetadataSource` identifies type, stable reference and optional authority label. `observed_at` is timezone-aware UTC and explicitly supplied or validated against an **injected clock**; never call `datetime.now()` inside the pure domain. Naive timestamps and values beyond an explicitly configured clock-skew allowance are rejected. Freshness is descriptive metadata and not proof of truth or automatic precedence. Retain source and observation data without storing credentials or raw secret payloads.

P6 uses record-level provenance by default. Per-field `MetadataValue[T]` is deferred unless a concrete L6.6 conflict requires it. Snapshots are deterministic, with stable canonical IDs and reproducible order; importing model aliases never invents logical ModelIds. `RegistryRefreshed` remains an optional domain event concept, not a requirement for a bus.

## Verification
P6-AC-041..044/048: offline operation, explicit timestamps, rejected naive/future timestamps, provenance in preview, repeated fixtures and no hidden mutation.
