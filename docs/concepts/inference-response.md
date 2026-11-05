# InferenceResponse - un resultat de domaine sans execution

> Statut : implementee et qualifiee techniquement en P3-G2 (ADR-014/017/018).
> Implementation : `pyllmkit.domain.inference.response`, `output`, `finish`, `usage`.

`InferenceResponse` est un **Value Object** immuable relie par `InferenceRunId` a une execution logique. Le simple fait de la construire ne signifie pas qu'une invocation fournisseur a eu lieu.

```python
from pyllmkit.domain import (
    FinishReason, FinishReasonCode, InferenceResponse,
    InferenceRunId, TextOutput, Usage,
)

response = InferenceResponse(
    run_id=InferenceRunId("run-offline"),
    output=TextOutput("Bonjour !"),
    finish_reason=FinishReason(FinishReasonCode.UNKNOWN, "native_reason"),
    usage=Usage(input_tokens=0),
)
assert response.usage is not None and response.usage.total_tokens is None
```

## Contrats

- `TextOutput(text: str)` conserve le texte exact, meme une chaine vide. Le variant `InferenceOutput` est un alias conceptuel pour TextOutput dans la version actuelle.
- `FinishReasonCode` comporte STOP, LENGTH, TOOL_CALL, CONTENT_FILTER, CANCELLED, ERROR et UNKNOWN. `finish_reason=None` ne signifie pas `UNKNOWN`, et un UNKNOWN ne devient jamais STOP. `TOOL_CALL` ne declenche aucun outil.
- `Usage` contient cinq compteurs eventuellement absents : input, output, total, reasoning et cached_input. Les entiers negatifs et booleens sont refuses. `None` n'est pas zero et aucun total n'est recalcule.
- Aucun prix, cout, token factice, payload natif ou metadata provider n'est ajoute a la reponse.

La coherence `response.run_id == run.run_id` est imposee par `InferenceRun.complete()`, non par le constructeur de la reponse. La serialisation est dans `response_to_dict/from_dict` (JSON v1).

Voir [API Response](../api/inference-response.md), [schema JSON](../architecture/INFERENCE_JSON_SCHEMA_V1.md) et [PV G2](../quality/P3_G2_GATE_REVIEW.md).
