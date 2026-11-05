# Tooling JSON v1 et composition M3/P4 - L4.4

> Statut: implementation de branche, P4-G4 non qualifie. ADR-028/029 ACCEPTED.

## Usage

```python
from pyllmkit.domain.tooling.serialization import tool_to_dict, tool_from_dict
from pyllmkit.domain.tooling_inference import intent_to_dict, intent_from_dict

encoded_tool = tool_to_dict(tool)
restored_tool = tool_from_dict(encoded_tool)
encoded_intent = intent_to_dict(intent)
restored_intent = intent_from_dict(encoded_intent)
```

Les valeurs `tool` et `intent` sont des instances de domaine creees explicitement avant ces appels. Les fonctions retournent/prennent des objets JSON compatibles. Le transport, le formatage et le parsing JSON textuel appartiennent au consommateur.

Le namespace `domain.tooling_inference` contient les objets immuables `ToolingInferenceIntent`, `ToolCallOutput`, `ToolingInferenceObservation`, les rapports de support et les codecs composites. Les objets de base restent dans `domain.tooling` et `domain.structured_output`.

## Compatibilite

- Wrapper P4 distinct de `InferenceRequest`, `InferenceResponse`, `InferenceRun`.
- `request_to_dict` / `response_to_dict` M3 v1 strictement inchanges.
- Les informations de support NATIVE, EMULATED, PARTIAL, UNSUPPORTED et UNKNOWN restent distinctes. Les etats connus UNSUPPORTED sont refuses sans fallback.
- Aucun Inference JSON v2, aucune transformation `ToolCallOutput` en `TextOutput`.
- Aucun JSON text parsing dans le noyau.

Voir `docs/architecture/TOOLING_JSON_SCHEMA_V1.md`, `examples/16_tooling_json_round_trip.py` et les tests P4-AC-025..032.
