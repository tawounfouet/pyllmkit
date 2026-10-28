# Code dependency rules - PyLLMKit P1

These arrows represent **source-code imports**, not runtime calls.

```text
facade -> application -> protocols -> domain
adapters -> protocols
adapters -> domain
adapters -> provider SDK (optional; later releases)
```

- Domain may import standard-library and internal domain modules, but never SDKs, adapters, network clients, facade or application layers.
- Capability and modality packages must not depend on Model; Model may compose their types.
- Registry implementations are adapters, not domain primitives.
- The AST import guard catches known direct imports; it is not proof against dynamic imports.
- P1-BOOT is not an inference engine or a released alpha.
