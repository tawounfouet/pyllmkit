# Tool Definition - Déclarer des outils sans les exécuter

`ToolSchema` décrit les arguments attendus et applique le profil fermé `P4-JSON-1`. `Tool` combine nom, description et schéma. Aucune fonction Python exécutable, handler, secret, credential ou connexion réseau n'est embarqué.

```python
from pyllmkit.domain.tooling import (
    Tool, ToolSchema, ToolChoice, ToolChoiceKind,
    validate_tool_set, validate_tool_choice,
)

weather = Tool("get_weather", "Descriptive only", ToolSchema({
    "type": "object",
    "properties": {"city": {"type": "string"}},
    "required": ["city"],
    "additionalProperties": False,
}))
tools = validate_tool_set((weather,))
choice = ToolChoice.specific("get_weather")
validate_tool_choice(choice, tools)
assert choice.kind is ToolChoiceKind.SPECIFIC_TOOL
```

AUTO permet une sélection, NONE la désactive, REQUIRED demande un outil (catalogue non vide), SPECIFIC_TOOL référence un nom existant. Ces choix sont des **intentions**, pas des décisions du provider ou des autorisations d'exécuter.

Le schéma est gelé en profondeur; `schema.value` rend une nouvelle copie. Les mots-clés inconnus et les références distantes sont rejetés. Voir [Tooling API](../api/tooling.md), ADR-022/024/026 et [exemple 13](../../examples/13_define_tools.py).
