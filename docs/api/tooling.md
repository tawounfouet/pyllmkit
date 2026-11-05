# Tooling Domain API - Phase 4, lot L4.1

> Etat : code de branche d'implementation L4.1, non qualifie P4-G1 avant CI main.
> ADR : [022](../adr/ADR-022-tool-definition-and-execution-boundary.md), [024](../adr/ADR-024-json-schema-profile-and-validation.md), [025](../adr/ADR-025-immutable-json-raw-parsed-and-validation.md), [026](../adr/ADR-026-tool-choice-and-capability-semantics.md).

## Concepts

- **ToolSchema** : specification structurelle d'arguments au profil **P4-JSON-1**; copie profonde, valeur immutable et restitution defensive.
- **Tool** : nom ASCII 1 a 64 caracteres, description optionnelle, ToolSchema. C'est une description, **pas une fonction executable**.
- **ToolChoice** : AUTO, NONE, REQUIRED ou SPECIFIC_TOOL(name). Choix d'intention sans inference de support provider.
- **validate_tool_set** : controle local de la collection tuple, objets et unicite de noms (sensibles a la casse).
- **validate_tool_choice** : controle que REQUIRED a des outils et SPECIFIC_TOOL designe un outil declare.

## Exemple Python hors reseau

```python
from pyllmkit.domain.tooling import (
    Tool, ToolSchema, ToolChoice, ToolChoiceKind,
    validate_tool_set, validate_tool_choice,
)

schema = ToolSchema({
    "type": "object",
    "properties": {"city": {"type": "string"}},
    "required": ["city"],
    "additionalProperties": False,
})
tools = validate_tool_set((Tool("get_weather", "Weather lookup", schema),))
validate_tool_choice(ToolChoice.specific("get_weather"), tools)
validate_tool_choice(ToolChoice(ToolChoiceKind.NONE), tools)
```

## Profil JSON Schema P4-JSON-1 (non exhaustif)

Mots-cles autorises : type, properties, required, additionalProperties, items, enum, const, minItems, maxItems, minLength, maxLength, minimum, maximum, title, description. Ce n'est **pas** une implementation complete de JSON Schema Draft 2020-12.

- Les mots-cles inconnus, $ref, $defs, oneOf et les references distantes sont refuses.
- Profondeur maximale : 32; noeuds JSON maximum : 10 000; taille canonique maximale : 1 MiB.
- Les schema peuvent avoir des properties et des items imbriques. Une chaine JSON Schema est fournie comme objet Python dict.
- Le **profil local** ne pretend ni imposer les capacites d'un provider ni effectuer la validation des valeurs d'arguments (cette derniere est en L4.2/L4.3).
- Le dictionnaire transmis peut etre modifie sans changer le ToolSchema. L'attribut `value` restitue une **copie** et non un pointeur vers le stockage interne.
- Aucune dependance provider, cle API, fonction Python arbitraire ou reseau n'est necessaire.

## Limites et suite

Les primitives L4.1 ne representent pas encore ToolCall, ToolArguments, ToolResult ou StructuredOutput. Elles ne produisent pas de ToolResult et n'executent rien. La qualification du lot requiert P4-G1 apres tests, revue, CI et verification sur main.
