# P6-G5 - L6.5 Deployment Resolution candidate

- Date: 2026-11-05
- Status: DRAFT / NOT QUALIFIED
- Stack: PR #59 -> #60 -> #61 -> #62 -> #63 -> L6.5 branch
- Source version remains 0.1.0a2

## Candidate design
- ModelTarget and DeploymentTarget are the only supported descriptive targets; EndpointTarget is not implemented in P6.
- Typed strict conjunction of declared availability, provider, region, runtime, capability and directional modalities and confirmed context bounds.
- Actual multi-layer capability and limits are read from pure L6.4 resolvers, not declared DeploymentQuery matching alone.
- UNKNOWN/UNSUPPORTED do not qualify; EMULATED/PARTIAL require explicit usable-mode opt in.
- No hidden fallback, first-match or cost/latency scoring. 0 candidates -> NoCompatibleDeploymentError; >1 -> AmbiguousDeploymentError.
- Explicit DeploymentTarget may not redirect to another deployment.
- Report contains sorted considered and eligible DeploymentIds plus fixed rejection reason codes.
- AVAILABLE is a catalog claim, never a live endpoint probe; the resolver does not execute inference.

## Qualification pending
- [ ] AC-033..040 covered and strict mypy/Ruff/CI/coverage/wheel matrix passed.
- [ ] Prior PRs #59..63 reviewed and qualified on exact merged main SHAs.
- [ ] Review/merge L6.5, then exact-main CI and P6-G5 gate review.
- [ ] No tag, PyPI or 0.1.0b2 publication.
