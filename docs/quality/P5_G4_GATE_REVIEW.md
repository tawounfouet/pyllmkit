# P5-G4 - Sync/Async Streaming - technical gate

- Date: 2026-11-05
- Verdict: GO technique avec réserves, authorizes L5.5 only.
- PR: [#55](https://github.com/tawounfouet/pyllmkit/pull/55), merged.
- Main SHA qualified: [6388711020cbd835fc812f87f200ca448e7eff7d](https://github.com/tawounfouet/pyllmkit/commit/6388711020cbd835fc812f87f200ca448e7eff7d).
- CI push/main: [#42102577288](https://github.com/tawounfouet/pyllmkit/actions/runs/42102577288), completed/success; Python 3.11/3.12/3.13.
- Scope: P5-AC-025..032, two independent protocols sync/async, deterministic parity, partial EOF, explicit cancellation, resource ownership and usage snapshots.
- Initial branch CI flagged import order, resolved by two commits culminating in 8e5b4b06; final PR and main CI passed.
- No provider transport, no network, no tool execution, no version bump. Version still 0.1.0a2.
- Publication NO-GO; outstanding #22/#35/#36. G5, G6 and M5 unqualified at this point.
