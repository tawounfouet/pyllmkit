# ADR-040 - Provider and Deployment domain identity

- Date: 2026-11-05
- Status: ACCEPTED for P6 offline technical architecture by owner-delegated authorization, 2026-11-05 (independent GitHub review absent)
- Phase: P6 Registry & Discovery / M6
- Baseline: main@19cc1c9e1d5598711890ddc3e14f1da94c79ce70
- References: 06_PYLLMKIT_PHASE_6_REGISTRY_AND_DISCOVERY_IMPLEMENTATION_PLAN.md; domain design 00-09; existing M1-M5 contracts.

## Decision
Create frozen slotted `ProviderId(value: str)` with nonblank, unmodified opaque value; no case folding or hidden alias conversion. `InferenceProvider` is a **descriptive entity snapshot**, identified by `ProviderId`, with nonempty display name and optional declared capabilities/modalities/limits. It contains no executable adapter, credentials, or client.

Create frozen slotted `Deployment` identified by the **existing** `domain.inference.targets.DeploymentId` and referencing exactly one existing `domain.models.ModelId`. Its `provider_id: ProviderId | None` may be None for local/self-hosted deployment. Optional runtime, region, capability overrides, modality overrides and limits remain explicitly unknown if absent. Avoid adding a physical `Endpoint` in P6.

`DeploymentStatus` has exactly `UNKNOWN`, `AVAILABLE`, `UNAVAILABLE`, `DEPRECATED` (descriptive declarations, **not live health**). Default is UNKNOWN. Explicit `with_status(...)` returns a new snapshot, rejects type errors and prohibits unapproved transitions from DEPRECATED to AVAILABLE. A known AVAILABLE is evidence of catalog declaration only.

Do **not** change `Model`, `ModelId`, `DeploymentId`, `ProviderModelRef.provider_id: str`, `ModelTarget`, `DeploymentTarget` or their codecs. Conversion `ProviderId(alias.provider_id)` must be explicit at an application boundary. A provider is neither a model developer nor a gateway nor a runtime.

## Alternatives
Rejected: treating a provider-specific model name as `ModelId`, using strings for deployment reference, requiring providers for local runtimes, adding SDK-specific properties to the entity.

## Verification
P6-AC-001..008: invalid ID/type rejection, identity continuity, shared model across deployments, local provider absent, UNKNOWN default, explicit status transition, deep immutable snapshots, M1/M3 regression.
