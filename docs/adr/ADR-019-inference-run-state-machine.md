# ADR-019 - InferenceRun : Aggregate Root, machine a etats et horloge
> **Decision owner P3-G0 (2026-11-05)** : `ACCEPTED`, sous autorite du proprietaire dans la conversation du projet. Cette autorisation concerne les contrats et leur integration, **pas** une GitHub review externe ni la publication d'un package. 
> **Arbitrage retenu :** Immutable run snapshots with identity equality RunId, explicit timezone-aware clock, finished_at for all terminal states, minimal InferenceFailure and optional cancellation code, six states.


- **Statut : ACCEPTED** - adoption explicite par le proprietaire pour P3-G0 le 2026-11-05. Contrat de conception adopte, implementation Python non commencee.
- **Decisionnaire :** proprietaire du projet.
- **Sources :** Phase 3 sections 4 et 7; specification 07 INF-013..021, INF-030..039; catalogue 09; ADR-014/017/020.
- **Portee :** domaine pur. Aucun appel provider ou streaming operationnel.

## Probleme

Une execution concrete possede identite, etat, horloge, reponse ou echec. Elle est distincte de l'intention InferenceRequest. Les etats terminaux doivent etre serialisables sans construire d'informations imaginaires.

## Decision proposee

1. **InferenceRun** est une **Entity / Aggregate Root** identifiee par un InferenceRunId fort fourni explicitement. La request reste un **Value Object** sans UUID implicite.
2. Les transitions produisent des **snapshots immuables** du meme RunId. Aucune mutation de l'ancien snapshot, aucune persistance ou transaction imposee.
3. **Egalite par identite** : deux snapshots d'un meme run sont egaux au sens Entity, meme si leurs etats different. Hash par RunId. Pour prouver une transition, comparer explicitement state, dates, response, failure, et non les deux snapshots avec l'operateur d'egalite. Une methode same_identity_as est envisageable.
4. Un run contient exactement **une** Request; attempt est un entier **exact >= 1**, sans bool; un retry ou replay cree **un autre RunId**, sans execution automatique.
5. Etats : CREATED, RUNNING, STREAMING, COMPLETED, FAILED, CANCELLED. Transitions : CREATED -> RUNNING; RUNNING -> STREAMING/COMPLETED/FAILED/CANCELLED; STREAMING -> COMPLETED/FAILED/CANCELLED; terminal -> rien.
6. **STREAMING** est un etat descriptif et la transition begin_stream(at) est pure; ni StreamEvent, ni flux de donnees ni systeme reseau reel en a3.
7. **InferenceFailure** est un Value Object minimal propose pour a3 : code non vide et normalise. Aucun payload natif d'exception, stacktrace ou texte de prompt. Les erreurs de validation/transition utilisent DomainValidationError ou un sous-type decide en G0, distinct du failure metier.
8. **cancellation_reason_code: str | None** est facultatif, non sensible et uniquement autorise en CANCELLED. Ce champ n'implique aucune interruption reelle d'un provider.
9. **Horloge explicite** : start(at), begin_stream(at), complete(response, at), fail(failure, at), cancel(at, cancellation_reason_code=None). at est un datetime **timezone-aware** injecte; aucune horloge/UUID implicite.
10. Champs temporels : started_at, streaming_started_at, **finished_at** (tous nullable selon etat). finished_at decrit toute sortie terminale, y compris FAILED et CANCELLED, contrairement a completed_at qui pourrait etre mal interprete.
11. Le schema de snapshots obeit a la table ci-dessous. Invariants : started_at <= streaming_started_at <= finished_at lorsque les dates sont presentes; les dates absentes restent null.
12. COMPLETED exige une response et un RunId concordant, sans failure. FAILED exige un InferenceFailure, sans response. CANCELLED n'a ni response ni failure. Tous les etats terminaux sont irreversibles.
13. La request.target n'est pas la preuve d'un DeploymentId/EndpointId resolu. Tout identifiant de provider reel reste absent tant qu'il n'est pas observe; extension explicite plus tard.
14. Les events du catalogue 09 restent **conceptuels** en a3 : aucun bus, outbox, emission ou ordonnanceur. Un complete purement metier n'affirme pas une invocation provider.

## Tableau d'invariants

| State | started_at | streaming_started_at | finished_at | response | failure | cancellation_reason_code |
|---|---|---|---|---|---|---|
| CREATED | null | null | null | null | null | null |
| RUNNING | date | null | null | null | null | null |
| STREAMING | date | date | null | null | null | null |
| COMPLETED | date | date/null | date | required | null | null |
| FAILED | date | date/null | date | null | required | null |
| CANCELLED | date | date/null | date | null | null | code/null |

## Alternatives et compromis

- Entity mutable encapsulee : DDD possible, mais les snapshots facilitent les tests offline et evitent une mutation cachee.
- Egalite structurelle des snapshots : utile pour les tests, mais diverge de l'identite Entity; les assertions sur state sont requises.
- completed_at uniquement : refuse, ambigu pour FAILED et CANCELLED.
- Exceptions native provider : refusees, secrets et couplage.
- Retry dans Run : refuse.
- Streaming reel : differe au jalon beta.

## Validation G0 puis G3

- Revoir explicitement **finished_at**, **InferenceFailure**, **cancellation_reason_code** et egalite identity-based.
- Tester toutes transitions autorisees et interdites, terminalite, horloge aware et ordre chronologique, attempt exact, RunId mismatch, absence de secrets.
- Round-trip et rejet JSON pour **les six etats** selon ADR-020.
- Scenarios P3-AC-014..020, P3-AC-029, regression M1/M2.

**Statut : ACCEPTED pour la conception P3.** L'API Python n'est pas encore implementee; la qualification G0 exige toujours l'integration et la CI.
