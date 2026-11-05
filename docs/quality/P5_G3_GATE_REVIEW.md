# P5-G3 - ToolCall Delta - technical gate

- Date: 2026-11-05
- Verdict: GO technique avec réserves to start L5.4.
- PR: [#54](https://github.com/tawounfouet/pyllmkit/pull/54), merged.
- Qualified main SHA: [53a965ccf66e5249becf9b5c82e926b018911898](https://github.com/tawounfouet/pyllmkit/commit/53a965ccf66e5249becf9b5c82e926b018911898)
- CI push/main: [#42102029484](https://github.com/tawounfouet/pyllmkit/actions/runs/42102029484), completed/success; Python 3.11/3.12/3.13.
- Scope: ToolCallDelta raw fragments correlated by ToolCallId, interleaved per-call reassembly, per-call 1 MiB byte budget, explicit closed vs partial tool calls, tests P5-AC-017..024.
- No SDK, execution or fabricated ToolResult. Version remains 0.1.0a2.
- Outstanding: #22 main protection, #35 release, #36 future provider boundary. Publication NO-GO; no third-party approval claimed.
- G4 for sync/async remains to be qualified separately, as do G5, G6 and M5.
