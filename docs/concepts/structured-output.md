# Structured Output - Format demandé et conformité observée

Le format demandé est représenté par `TextResponseFormat`, `JsonResponseFormat` ou `SchemaResponseFormat`. Pour JSON et Schema, `strict=None` n'est pas identique à `strict=False`. `strict=True` ne démontre pas un support natif de provider.

```python
from pyllmkit.domain.structured_output import (
    SchemaResponseFormat, StructuredOutput, validate_structured_output,
)
from pyllmkit.domain.tooling import ToolSchema, ValidationStatus

fmt = SchemaResponseFormat(ToolSchema({
    "type": "object", "required": ["ok"],
    "properties": {"ok": {"type": "boolean"}},
}), strict=True)
observed = StructuredOutput(fmt, raw='{"ok":true}', parsed={"ok": True})
validated = validate_structured_output(observed)
assert validated.validation.status is ValidationStatus.VALID
```

VALID est le résultat d'une vérification réelle; INVALID indique une valeur non conforme; UNKNOWN indique une preuve insuffisante, notamment si `parsed` est absent. La charge `raw` n'est jamais parsée automatiquement par le domaine. Les capacités NATIVE/EMULATED/PARTIAL/UNSUPPORTED/UNKNOWN sont évaluées indépendamment des statuts de validation.

Voir [Structured Output API](../api/structured-output.md), ADR-027, [exemple 15](../../examples/15_validate_structured_output.py) et [architecture P4](../architecture/PHASE_4_TOOLING_AND_STRUCTURED_OUTPUT_CONTRACTS.md).
