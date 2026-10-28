# L1.2 - Capabilities and Modalities

**Implementation:** Phase 1 / L1.2. **Decision ADR-006:** PROPOSED.

## Ubiquitous language

- **Capability** describes *what* a model is able to do, e.g. `vision` or `tool_calling`.
- **Modality** describes *what type of content* it consumes or emits, e.g. `image` or `text`.
- `CapabilityId` and `Modality` are extensible value objects; neither is an exhaustive enum.
- `SupportLevel` is a small enum with `UNSUPPORTED`, `EMULATED`, `PARTIAL`, `NATIVE`. **Unknown is represented by `None`**, not by `NATIVE` or `UNSUPPORTED`.
- `CapabilitySupport` carries a level, optional constraints and notes; partial support requires a constraint or explanatory note.
- `CapabilitySet` is an immutable collection. Missing entries indicate unknown support. `supports()` only returns true when available support is explicitly declared.
- `ModalitySet` maintains *separate* `input_modalities` and `output_modalities`. `None` means unspecified, `frozenset()` means explicitly empty; lookups return `bool | None`.

## Example: modality != capability

```python
from pyllmkit.domain.capabilities import Capability, CapabilityId, CapabilitySet, CapabilitySupport, SupportLevel
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity

model = Model(
    id=ModelId("example/vision"),
    identity=ModelIdentity(family=ModelFamily("example")),
    capabilities=CapabilitySet((
        Capability(CapabilityId("vision"), CapabilitySupport(SupportLevel.NATIVE)),
    )),
    modalities=ModalitySet(
        input_modalities=frozenset({Modality("text"), Modality("image")}),
        output_modalities=frozenset({Modality("text")}),
    ),
)
assert model.supports(CapabilityId("vision"))
assert model.modalities.accepts_input(Modality("image")) is True
assert model.modalities.can_output(Modality("image")) is False
assert model.supports(CapabilityId("tool_calling")) is False  # UNKNOWN, not unsupported
assert model.capabilities.support_of(CapabilityId("tool_calling")).level is None
```

## Collection algebra vs effective capability negotiation

The `union` and `intersection` operations on `CapabilitySet` are defined on compatible declarations. **Conflicting declarations raise `DomainValidationError`.** This prevents accidental inference of provider-/deployment-effective support. A dedicated `CapabilityResolver` will later interpret restrictive rules such as `UNSUPPORTED` dominance, constraints merging, partial support, and emulation provenance across Model / Deployment / Provider / Endpoint.

Do not mistake `CapabilitySet.intersection` for an effective capability resolver. A `CapabilitySet` only represents what is declared, with potentially missing knowledge.

## JSON compatibility

The L1.1 `schema_version=1` Model codec gains optional `capabilities` (array) and `modalities` (object). Older schema-v1 model snapshots *without these fields* still decode to an empty capability catalog and unknown directional modalities, respectively. Unknown schema keys continue to fail fast. Roundtrips preserve explicit unknown support and known directional sets.

## Architecture

`capabilities` and `modalities` depend only on the domain error module, not on `Model`, providers or HTTP. `Model` composes both as immutable value objects. No transport, effective serving resolution, registry or agent orchestration in L1.2.
