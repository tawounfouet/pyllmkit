# ADR-039 - Registry & Discovery boundary and sequence

- Date: 2026-11-05
- Status: ACCEPTED for P6 offline technical architecture by owner-delegated authorization, 2026-11-05 (independent GitHub review absent)
- Phase: P6 Registry & Discovery / M6
- Baseline: main@19cc1c9e1d5598711890ddc3e14f1da94c79ce70
- References: 06_PYLLMKIT_PHASE_6_REGISTRY_AND_DISCOVERY_IMPLEMENTATION_PLAN.md; domain design 00-09; existing M1-M5 contracts.

## Context
The original expression of need called "Provider Adapters" Phase 6, while requirements call Registry MVP-6. M6 now explicitly targets Registry & Discovery and `0.1.0b2` is an indicative, not released, version.

## Decision
Adopt **P6 = Registry & Discovery**, postponing executable Provider Adapters to P7 or later. Separate: (a) model/provider/deployment **descriptions** in domain; (b) registry ports and in-memory adapters; (c) pure capability and limit resolvers; (d) application lookup/selection and offline merge. `ProviderCatalog` stores descriptive metadata. Future `AdapterRegistry` stores runtime factories: it is NOT part of P6.

Keep the core offline with no network, SDK, API key, plugin loading, endpoint probing, LLM invocation, agent orchestration, cost/latency routing or background polling. Discovery produces **candidates**, never hidden registration. No domain event bus is required; domain events remain conceptual facts.

## Consequences
Use a separate `domain.registry` bounded context with dependencies on stable M1-M5 value objects. New code may import the domain; the domain must never import infrastructure. The older Phase 6 naming discrepancy must be noted in future roadmaps rather than silently rewritten.

## Verification
Architecture import-fitness tests and P6-AC-002/011/048/049/052. Review for SDK/transport imports and mutation of M1-M5 codecs. Release remains NO-GO until independent governance.
