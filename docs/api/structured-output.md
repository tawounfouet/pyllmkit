# Structured Output - P4 L4.3

> Statut : implementation en branche, gate P4-G3 non encore qualifie. Sources ADR-024, 025, 026, 027.

## Contrats

Les Value Objects sont \`TextResponseFormat\`, \`JsonResponseFormat\` et \`SchemaResponseFormat\`. Le \`strict\` de JSON/schema est optionnel, conserve \`None\` distinct de \`False\` et ne garantit pas de support provider.

\`StructuredOutput\` contient un format, une chaine \`raw\` eventuelle et une valeur \`parsed\` eventuelle, gelee en profondeur. Le parsed absent est different de JSON null explicite. La construction ne revendique aucune validation.

\`validate_structured_output(output)\` retourne un nouveau snapshot immuable dont \`validation.status\` vaut \`UNKNOWN\`, \`VALID\` ou \`INVALID\`. Les diagnostics de non-conformite sont des codes fixes, sans payload. Pour le format texte, l'existence de raw suffit, y compris une chaine vide; pour JSON et JSON Schema, une valeur parsed explicite est requise, **sans parsing implicite du raw**. Schema exige en plus une validation effective des contraintes P4-JSON-1.

\`evaluate_response_support\` accepte seulement un \`CapabilitySupport\` explicite fourni par le caller. NATIVE est prouve uniquement par une declaration NATIVE; EMULATED, PARTIAL et UNKNOWN restent non confirms. UNSUPPORTED connu est rejete par \`validate_response_support\`.

## Exemple offline

```python
from pyllmkit.domain.structured_output import (
    SchemaResponseFormat, StructuredOutput, validate_structured_output,
)
from pyllmkit.domain.tooling import ToolSchema, ValidationStatus

fmt = SchemaResponseFormat(ToolSchema({
    "type": "object", "properties": {"name": {"type": "string"}},
    "required": ["name"], "additionalProperties": False,
}), strict=True)
out = validate_structured_output(
    StructuredOutput(fmt, raw='{"name":"Paris"}', parsed={"name": "Paris"})
)
assert out.validation.status is ValidationStatus.VALID
```

## Limites

P4-JSON-1 est un sous-ensemble ferme de JSON Schema, pas un moteur complet Draft 2020-12. Aucune transformation d'un `UNKNOWN` en `VALID`, aucun JSON text parser, pas de repair, retries, invocation provider, streaming ou execution d'outil. Les codecs Tooling JSON v1 et la composition avec M3 restent L4.4. Les API M3 et schemas JSON v1 existants restent inchanges.
