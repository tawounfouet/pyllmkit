# ADR-007 - Phase 1 licensing and release governance

- **Status:** ACCEPTED for Phase 1 as a project implementation decision (2026-10-28).
- **Authorization:** Project owner's instruction to complete the M1 milestone; no separate legal opinion or person-signed approval is asserted.
- **Decision:** Use **MIT** for the open-source PyLLMKit repository; ship the unchanged standard MIT grant/disclaimer in `LICENSE`, and declare SPDX `MIT` in project metadata.
- **Reasoning:** A compact, permissive license compatible with provider-agnostic Python libraries and common downstream commercial/OSS uses. Compared to Apache-2.0, MIT does not have the same explicit patent grant/termination terms; this is a documented trade-off, not a legal finding.
- **Copyright:** `PyLLMKit contributors`, 2026, pending any contributor/ownership refinements before third-party distribution.
- **Boundary:** License selection **does not authorize** a PyPI upload, Git tag or GitHub release.
- **Release gate:** Only a reviewed, CI-green integrated `main` SHA may receive a formal M1 GO. Artifacts remain unpublished unless a separate publication action is explicitly authorized.
- **Follow-up:** Recheck source ownership, contributors and any inbound-license obligations before publishing.
