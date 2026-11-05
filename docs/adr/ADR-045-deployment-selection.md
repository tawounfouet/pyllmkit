# ADR-045 - Deployment resolution is descriptive and unambiguous

- Date: 2026-11-05
- Status: PROPOSED (P6-G0 review; not yet qualified)
- Phase: P6 Registry & Discovery / M6
- Baseline: main@19cc1c9e1d5598711890ddc3e14f1da94c79ce70
- References: 06_PYLLMKIT_PHASE_6_REGISTRY_AND_DISCOVERY_IMPLEMENTATION_PLAN.md; domain design 00-09; existing M1-M5 contracts.

## Decision
The `DeploymentResolver` is an application query reading registry ports and calling pure effective-capability services. It accepts existing `ModelTarget` or `DeploymentTarget`, plus explicit requirements (provider/region/status/modalities/capabilities). It never alters a target's ID and never contacts an endpoint.

For a ModelTarget: require the logical model, find referential deployments, filter explicit criteria, require declared availability where caller requests routability, evaluate capability evidence strictly and create an immutable `ResolutionReport` (candidate IDs, rejected IDs + reasons, selected ID, evidence). Return the **only** eligible candidate. Zero produces a typed no-compatible/not-found failure; more than one produces `AmbiguousDeploymentError` with safe IDs only. No implicit "first", random, price, latency, policy scoring or fallback. Explicit provider/region filters are hard constraints rather than arbitrary ranking.

For DeploymentTarget: require that exact deployment, evaluate requirements and refuse known incompatibilities/unknown availability; never transparently redirect to another ID. AVAILABLE means "catalog-declared", not a live ping. Selection never promises that the provider is online.

## Verification
P6-AC-033..040; no candidate, multiple, provider preference, unknown capability, incompatible status, exact-target preservation, and no side effects or network imports.
