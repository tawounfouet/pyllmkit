# ADR-019 - InferenceRun : aggregate, etats et horloge

- Statut : **PROPOSED** (P3-BOOT, 2026-11-05).
- Sources : plan Phase 3 section 7, INF-013..021, INF-030..039, Domain Events 09.

## Contexte

Un run represente une execution logique identifiable, et non un executor Python, un client reseau ou une promesse que le fournisseur a ete invoque. Les transitions doivent etre reproductibles sans I/O.

## Decision proposee

1. **InferenceRunId** est un identifiant strict, non vide, fourni par l'appelant ou une factory explicite. Aucun UUID ni horodatage implicite dans le constructeur de Request.
2. **InferenceRun** est une Entity / Aggregate Root a identite stable. L'implementation P0 utilise des **snapshots immuables successifs**; chaque transition retourne un nouvel etat portant le meme run_id.
3. Equality et hash expriment l'identite du run, pas l'egalite de deux snapshots. Pour verifier les transitions, les tests comparent explicitement state, timestamps, response et failure.
4. Etats : CREATED, RUNNING, STREAMING, COMPLETED, FAILED, CANCELLED.
5. Transitions valides : CREATED -> RUNNING; RUNNING -> STREAMING/COMPLETED/FAILED/CANCELLED; STREAMING -> COMPLETED/FAILED/CANCELLED. Toutes les autres sont interdites.
6. **STREAMING** est un etat de domaine representable, sans mecanisme de streaming ni StreamEvent operationnel en a3. La transition pure begin_stream ne demarre aucun flux.
7. COMPLETED, FAILED et CANCELLED sont terminaux. COMPLETED requiert une response portant le meme RunId et aucune failure terminale. FAILED requiert un code d'echec de domaine et aucune response finale. CANCELLED ne declenche aucune interruption reseau.
8. Un run possede exactement une Request et **attempt >= 1** (entier exact, bool refuse). Une reexecution/retry cree un **autre RunId**; aucun retry automatique.
9. Les methodes de transition recoivent explicitement un **datetime timezone-aware**; pas de datetime.now implicite. started_at <= completed_at; horodatages de fin coherents et stables.
10. Les evenements InferenceStarted/Completed/Failed/Cancelled sont pour l'instant une semantique documentee. Pas de bus, outbox, scheduler, transport ou payload sensible dans les logs.
11. Identifiants provider et references de deployment/endpoint connus sont distincts de RunId et ne sont jamais inventes. Leur forme de stockage P0 doit etre minimaliste et explicite.

## Alternatives

- Entity mutable encapsulee : possible, mais snapshots preferes pour audit, tests et absence de mutations cachees.
- Run comme executor async : rejete (PyRuntimeKit et application ont d'autres responsabilites).
- Retries dans start/complete : rejetes, violeraient la separation intention/execution.

## Tests

- Table exhaustive des transitions permises/interdites et refus des reprises d'etats terminaux.
- Deux runs pour une request, identites distinctes; RunId mismatch refuse.
- Clock naive, inversion temporelle, attempt bool, failure avec response et terminalites refuses.
- Tests P3-AC-014..020, P3-AC-029.
