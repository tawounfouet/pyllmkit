# ADR-008 - Role taxonomy and provider neutrality

- **Status:** PROPOSED FOR REVIEW (P2-BOOT, 2026-11-05). Not yet accepted or merged.
- **Context:** Interaction uses semantic roles. Providers differ in supported roles and some APIs omit a developer or tool role.
- **Sources:** specifications 03, 05, 07 (INT-004, INT-006, INT-007); Phase 2 plan section 5; ADR-005/006.

## Decision
1. Define a canonical `Role` string-valued enumeration with exactly `system`, `developer`, `user`, `assistant`, `tool` and symbolic public members `SYSTEM`, `DEVELOPER`, `USER`, `ASSISTANT`, `TOOL`. Values are lower-case stable domain strings.
2. `Message.role` requires a `Role` instance. The domain rejects unknown values; it does not coerce bare strings, silently fall back to `USER`, or translate between roles.
3. Extensible non-standard roles require a distinct future typed extension contract, not open-ended strings masquerading as canonical `Role`. Capture original provider roles at adapters when such an extension is deliberately introduced.
4. `TOOL` is a semantic speaker role only. It does not introduce `ToolCall`, `ToolResult`, correlation, or tool execution in a2.
5. Adapter mappings may translate or reject a role, but any lossy emulation requires an explicit policy and must not happen in the domain.

## Alternatives
- Unrestricted `str`: easy to extend, but invalid/ambiguous roles silently enter the core. Rejected.
- One open `Role(value)` object: extensible but complicates validation and the canonical guarantee for a2. Deferred.
- SDK-native role enums: rejected due to provider coupling.

## Consequences
- Stable simple contract for AC-006/007; SDK independence.
- Non-standard provider roles cannot be represented as ordinary canonical Message roles in a2; this is an explicit limitation, not silent data loss.
- Roles do not imply provider capabilities or supported endpoints.

## Acceptance Tests
- All five canonical roles construct valid messages.
- Arbitrary role strings, unknown role names and implicit casts are rejected with `DomainValidationError`.
- Role `TOOL` is representable without importing or invoking tools.
- Architecture guard checks no provider SDK in Interaction.

## Follow-ups
- L2.1: implement/test canonical `Role`; document adapter mapping policy in a later provider phase.
- Revisit custom roles only with a concrete cross-provider use case.
