# InferenceRun - un agregat a identite stable

> Statut : implemente et qualifie techniquement en P3-G3 (ADR-014/019).
> Implementation : `pyllmkit.domain.inference.run` et `failure`.

`InferenceRun` est une **Entity / Aggregate Root DDD**, non un Value Object. Une execution logique possede un `InferenceRunId` explicite et exactement une `InferenceRequest`. Un Run n'est pas un worker, un moteur de retry, un thread ou un ordonnanceur.

## Cycle de vie pur

```python
from datetime import UTC, datetime
from pyllmkit.domain import (
    Content, InferenceRequest, InferenceResponse, InferenceRun,
    InferenceRunId, InferenceRunState, Message, ModelId, ModelTarget,
    Role, TextContent, TextOutput,
)

request = InferenceRequest(
    ModelTarget(ModelId("model")),
    (Message(Role.USER, Content((TextContent("Bonjour"),))),),
)
at = datetime(2026, 11, 5, tzinfo=UTC)
created = InferenceRun(InferenceRunId("run-1"), request)
running = created.start(at)
finished = running.complete(
    InferenceResponse(created.run_id, TextOutput("reponse synthetique")), at
)
assert created.state is InferenceRunState.CREATED
assert finished.state is InferenceRunState.COMPLETED
assert created == finished  # Meme identite, snapshots differents.
```

## Six etats

- CREATED : aucune horloge ni resultat.
- RUNNING : `started_at` exige.
- STREAMING : `started_at` et `streaming_started_at` exiges, mais **aucun streaming reseau reel**.
- COMPLETED : `finished_at` et `response` du meme RunId obligatoires.
- FAILED : `finished_at` et `InferenceFailure(code)` obligatoires, aucune Response.
- CANCELLED : `finished_at`, raison facultative, aucune Response ni Failure.

Les seules transitions sont CREATED -> RUNNING, RUNNING -> STREAMING/COMPLETED/FAILED/CANCELLED et STREAMING -> COMPLETED/FAILED/CANCELLED. Tous les etats terminaux sont irreversibles. Chaque transition recoit son `datetime` timezone-aware, ne lit jamais l'horloge et retourne un **nouveau snapshot**.

L'egalite et le hash comparent **uniquement l'InferenceRunId**. Comparer `state` et les timestamps explicitement pour verifier les changements d'etat. Rejouer une requete signifie creer un nouveau RunId.

## Exclusion explicite

Les Domain Events catalogues ne sont pas publies automatiquement. Aucun provider, transport, cancellation distante ou persistance n'est implemente. Les six etats sont serialisables en Inference JSON v1 a l'aide de `run_to_dict/from_dict`, avec revalidation des invariants.

Voir [API Run](../api/inference-run.md), [ADR-019](../adr/ADR-019-inference-run-state-machine.md) et [PV G3](../quality/P3_G3_GATE_REVIEW.md).
