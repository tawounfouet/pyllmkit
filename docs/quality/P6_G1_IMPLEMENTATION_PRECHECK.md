# P6-G1 - L6.1 Provider & Deployment Domain - candidate precheck

- Status: IMPLEMENTATION CANDIDATE / NOT QUALIFIED GO
- Baseline: stacked onto P6-G0 architecture commit `62e2bceddbdedae3fa27a26d4828fcc9cdb497b4`
- Dependency: P6-G0 design approval + merge + successful exact-main CI

## Scope delivered on draft branch
- ProviderId typed ID, opaque validation, no normalization.
- InferenceProvider metadata entity, optional declarations, no client/SDK/keys.
- Deployment reused ModelId/DeploymentId, optional ProviderId for local runtime.
- DeploymentStatus UNKNOWN/AVAILABLE/UNAVAILABLE/DEPRECATED and explicit immutable transitions.
- Acceptance tests for P6-AC-001..008 including invalid types and M1/M3 regression.

## Not yet proven / not attempted
- [ ] CI passing on this draft PR's exact SHA on Python 3.11, 3.12, 3.13.
- [ ] Review and merge after the P6-G0 prerequisite is qualified.
- [ ] P6-G1 post-merge push/main success and formal gate decision.

## Explicit boundaries
No registries, query services, discovery, provider adapter, live availability, credentials, SDK integration, network calls or version change are included in this lot. `0.1.0b2` remains a target, not a release.
