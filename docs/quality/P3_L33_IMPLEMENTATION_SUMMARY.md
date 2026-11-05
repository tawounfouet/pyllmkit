# PyLLMKit - P3 / L3.3 Implementation Summary

> Date : 2026-11-05
> Phase : 0.1.0a3 - Inference Primitives
> Lot : L3.3 - Inference Run Domain
> Statut : IMPLEMENTED ON FEATURE BRANCH / P3-G3 NOT YET QUALIFIED
> Architecture : ADR-014 et ADR-019 ACCEPTED, reemploi ADR-017/018
> Baseline : main `9ef8e521d84dc1a99139aca19a8cc0ea164032a7` (G2 GO technique)
> Metadata : 0.1.0a2, aucune publication ni tag

## 1. Livrables

| Objet / fichier | Contrat |
|---|---|
| `inference/failure.py` | `InferenceFailure(code)` est un VO code-only, snake_case valide, pas une exception native |
| `inference/run.py` | `InferenceRunState` (CREATED, RUNNING, STREAMING, COMPLETED, FAILED, CANCELLED), `InferenceRun` Aggregate Root |
| `InferenceRunId` | reutilise le VO d'identite introduit en L3.2, sans UUID auto-genere |
| `InferenceRequest` | reutilisee telle quelle; une request peut etre partagee par plusieurs runs |
| `InferenceResponse` | reutilisee; verification stricte `response.run_id == run.run_id` lors de `complete` |
| Public API | Reexport des symboles via `pyllmkit.domain.inference` et `pyllmkit.domain` |
| `tests/acceptance/test_p3_l33_inference_run.py` | P3-AC-014..020 et P3-AC-029 |
| `tests/unit/domain/inference/test_run_state_machine.py` | Table de transitions, temporalite, terminalite, egalite par identite |
| `tests/unit/domain/inference/test_run_invariants.py` | Validation du constructeur pour les six etats et refus de snapshots incoherents |
| `examples/10_define_inference_run.py` | Exemple offline pur, sans SDK |
| `docs/api/inference-run.md` | Documentation de l'API et du perimetre hors scope |
| CI | Python 3.11-3.13, ruff, mypy, pytest branche, exemple 10, wheel/sdist smoke |

## 2. Matrice d'acceptation

| ID | Cas | Preuve attendue |
|---|---|---|
| P3-AC-014 | Deux runs pour la meme Request | IDs distincts, request non mutee |
| P3-AC-015 | CREATED -> RUNNING -> COMPLETED | Response correlatee, finished_at |
| P3-AC-016 | RUNNING -> FAILED | Failure canonique, response absente |
| P3-AC-017 | RUNNING -> CANCELLED | Etat terminal et raison facultative |
| P3-AC-018 | COMPLETED -> RUNNING | Refus DomainValidationError |
| P3-AC-019 | Response avec autre RunId | Refus explicite sans mutation |
| P3-AC-020 | Rejouer la meme Request | Autre RunId, aucune mutation de la request |
| P3-AC-029 | Horloge controlee | Instants injectes et deterministes, sans now() |

## 3. Invariants retenus

1. `InferenceRun` est une **Entity**, tandis que `InferenceRequest`, `InferenceResponse` et `InferenceFailure` sont des **Value Objects**.
2. Les snapshots sont immuables, `__eq__` et `__hash__` comparent l'identite RunId; les etats se comparent explicitement.
3. Seules les transitions CREATED -> RUNNING; RUNNING -> STREAMING/COMPLETED/FAILED/CANCELLED; STREAMING -> COMPLETED/FAILED/CANCELLED sont possibles.
4. `STREAMING` est un **etat descriptif seulement**, non un flux realiste et non un `StreamEvent` executable.
5. `finished_at` existe dans tous les etats terminaux, avec `started_at` et `streaming_started_at` optionnel; chronologie aware monotone.
6. COMPLETED exige une Response du meme RunId et interdit Failure; FAILED exige un Failure et interdit Response; CANCELLED ne porte ni l'un ni l'autre.
7. `InferenceFailure.code` et `cancellation_reason_code` acceptent uniquement des codes non vides snake_case. Aucun message brut, stacktrace ou payload natif n'est stocke.
8. Les transitions sont **pures et deterministes** avec horloge injectee. Aucun reseau, executor, event bus, retry automatique, persistance ou provider.

## 4. Qualification et limites

La presente note ne declare **aucun G3 GO avant CI**. Le gate P3-G3 sera fonde sur la preuve du commit exact apres fusion, avec CI main validee, puis un PV distinct sur une branche documentaire.

Le contrat JSON v1 pour Request / Response / Run et son round-trip restent L3.4 (G4). Les evenements de domaine sont des specifications, non des objets emis par la machine a etats. L3.5 et M3 restent futurs. Les reserves existantes sur `main.protected=false` ([issue #22](https://github.com/tawounfouet/pyllmkit/issues/22)) et la dette M2 ([issue #20](https://github.com/tawounfouet/pyllmkit/issues/20)) ne sont pas levees par ce lot.

**Prochaine action : CI finale de PR, correction des anomalies, integration controlee, CI sur main, puis P3-G3 GO/NO-GO documente.**
