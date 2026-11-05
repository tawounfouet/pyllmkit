# PyLLMKit - Phase 2 Architecture Decision Register

**Date:** 2026-11-05
**Status:** ADR-008 to ADR-013 **ACCEPTED for Phase 2 design**, G0 GO.
**Authority:** Direct review and acceptance by the repository project owner during the PyLLMKit conversation. No independently submitted GitHub APPROVED review claimed.
**Qualified SHA:** [`93e9467e2bef819201507aa2c4f06fdf4a4b04da`](https://github.com/tawounfouet/pyllmkit/commit/93e9467e2bef819201507aa2c4f06fdf4a4b04da)
**CI:** https://github.com/tawounfouet/pyllmkit/actions/runs/42005569202
**PR:** https://github.com/tawounfouet/pyllmkit/pull/8

| ADR | Status | Follow-up |
|---|---|---|
| ADR-008 Role Taxonomy | ACCEPTED | L2.1: implement canonical Role and negative tests |
| ADR-009 Message and Conversation | ACCEPTED | L2.1: immutable Message; Conversation remains deferred |
| ADR-010 Content Polymorphism | ACCEPTED | L2.2: ContentPart, TextContent, nonempty ordered Content |
| ADR-011 Media Source Safety | ACCEPTED | L2.3: passive MediaSourceRef and ImageContent |
| ADR-012 Interaction JSON Codec | ACCEPTED | L2.4: strict independent versioned codec |
| ADR-013 Multimodal Extensions | ACCEPTED | M2 text/image; future ADRs for other content types |

**Not decided by G0:** any provider adapters, model invocations, ToolCall and ToolResult, streaming, publishing packages, or declaring M2 GO. Implementation acceptance tests remain pending.

**Evidence:** See `docs/quality/P2_BOOT_GATE_REVIEW.md` and original ADR files.
