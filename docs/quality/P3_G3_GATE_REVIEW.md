# PyLLMKit - P3-G3 Run Lifecycle Ready - Proces-verbal de qualification

> Date : 2026-11-05
> Phase cible : P3 / 0.1.0a3 - Inference Primitives (candidate source non publiee)
> Lot : L3.3 - Inference Run Domain
> **Verdict : P3-G3 = GO TECHNIQUE AVEC RESERVES**
> Qualifie : domaine pur, Aggregate Root et transitions immuables; **aucune invocation provider**
> PR de code : [#27](https://github.com/tawounfouet/pyllmkit/pull/27) (squash merge)
> **SHA exact de main qualifiant :** [`361791ff546612e10b407874c54014b1c0e1ce86`](https://github.com/tawounfouet/pyllmkit/commit/361791ff546612e10b407874c54014b1c0e1ce86)
> **CI push/main :** [Actions #42044787119](https://github.com/tawounfouet/pyllmkit/actions/runs/42044787119), `completed` / **SUCCESS**
> Publication : aucune; metadata pyproject.toml demeure `0.1.0a2`
> Autorite technique : decision de gate par analyse des preuves CI et des contrats ADR deja approuves; ne vaut pas APPROVED review tierce

## 1. Objet et portee

L3.3 introduit `InferenceRun` comme **Entity / Aggregate Root** a identite stable; `InferenceRequest` et `InferenceResponse` restent des **Value Objects**. La Phase 3 est provider-agnostic : aucun appel reseau, adaptateur, runtime, bus d'evenements, stockage ni systeme de streaming reel n'est compris dans ce GO.

Le gate G3 verifie la coherence avec les **ADR-014 et ADR-019 ACCEPTED**, les primitives G1/G2 deja integrees et les scenarios P3-AC-014..020 et P3-AC-029. Il n'atteste pas encore le JSON codec Inference v1, prevu pour L3.4.

## 2. Livrables integres

| Element | Fichier / contrat | Resultat |
|---|---|---|
| `InferenceRunState` | `domain/inference/run.py` | Six etats : CREATED, RUNNING, STREAMING, COMPLETED, FAILED, CANCELLED |
| `InferenceRun` | `domain/inference/run.py` | Snapshots immuables, une request, attempt exact >=1, egalite/hash par RunId |
| `InferenceFailure` | `domain/inference/failure.py` | VO code snake_case non vide; pas d'exception native ou stacktrace |
| ID et resultats | `InferenceRunId`, `InferenceResponse` de L3.2 | Correlation explicite, refus response d'un autre RunId |
| Horloge | `started_at`, `streaming_started_at`, `finished_at` | `datetime` timezone-aware injecte, dates coherentes |
| Transitions | `start`, `begin_stream`, `complete`, `fail`, `cancel` | Fonctions pures, nouveaux snapshots, etats terminaux irreversibles |
| Reexports | `pyllmkit.domain.inference` et `pyllmkit.domain` | API exposee sans rupture M1/M2/G1/G2 |
| Tests | acceptance/unit/architecture | Table de transitions, refus invalides et six snapshots reconstruisibles |
| Demo et documentation | `examples/10_define_inference_run.py`, `docs/api/inference-run.md` | Exemple offline; aucun provider appele |
| Packaging | Workflow CI Python 3.11/12/13 | Wheel et sdist smoke du nouvel API |

## 3. Matrice d'acceptation

| Cas | Contrat | Resultat |
|---|---|---|
| P3-AC-014 | Deux runs distincts d'une meme request | **PASS** |
| P3-AC-015 | CREATED -> RUNNING -> COMPLETED | **PASS** |
| P3-AC-016 | RUNNING -> FAILED, failure terminale sans response | **PASS** |
| P3-AC-017 | RUNNING -> CANCELLED, annulation terminale locale | **PASS** |
| P3-AC-018 | COMPLETED -> RUNNING interdite | **PASS** |
| P3-AC-019 | Response avec RunId different interdite | **PASS** |
| P3-AC-020 | Replay de Request sans mutation, nouveau RunId | **PASS** |
| P3-AC-029 | Horloge injectee et transitions deterministes | **PASS** |

Preuves : `tests/acceptance/test_p3_l33_inference_run.py`, `tests/unit/domain/inference/test_run_state_machine.py` et `test_run_invariants.py`. La suite verifie les six etats et toutes les transitions interdites dans la matrice, y compris les appels terminaux repetes.

## 4. CI de qualification sur le SHA exact de main

| Verification | Resultat constate |
|---|---|
| PR #27 final head | `aa75cc8209c7992ff3897b62aee05279b446b9cf` |
| PR CI | [#42044515067](https://github.com/tawounfouet/pyllmkit/actions/runs/42044515067) SUCCESS sur Python 3.11/12/13 |
| SHA main apres merge squash | `361791ff546612e10b407874c54014b1c0e1ce86` |
| CI push main | [#42044787119](https://github.com/tawounfouet/pyllmkit/actions/runs/42044787119), `completed`, `success` |
| `validate (3.11)` | SUCCESS |
| `validate (3.12)` | SUCCESS |
| `validate (3.13)` | SUCCESS |
| Pytest Python 3.11 | **679 passed**, 2.50 s |
| Coverage globale branche incluse | **94 %**, 1168 statements / 48 misses, 400 branches / 41 partials |
| Ruff | All checks passed |
| mypy | Success: no issues found in **38 source files** |
| Offline examples | 01..10, SUCCESS |
| Wheel/sdist clean environment | SUCCESS, nouveaux imports et transitions testes |

**Comparaison de la baseline :** P3-G2 = 545 tests et 94 %; P3-G3 = 679 tests et 94 %. Les **+134 tests** comptabilisent des cas unitaires et parametres dans la suite globale, pas 134 implementations nouvelles.

## 5. Invariants approuves et verifies

1. Un Run garde le meme RunId entre snapshots mais produit de nouvelles instances; comparer les changements d'etat explicitement car l'egalite Entity ne compare que l'identite.
2. `attempt` est un entier exact >=1, sans booleen; une repetition ou un retry donne un nouveau RunId, sans reexecution automatique.
3. Etats autorises : CREATED -> RUNNING, RUNNING -> STREAMING/COMPLETED/FAILED/CANCELLED, STREAMING -> COMPLETED/FAILED/CANCELLED. Tous les terminaux sont definitifs.
4. `STREAMING` represente une etiquette de cycle de vie; `begin_stream` **ne cree aucun flux**.
5. Les timestamps, fournis par l'appelant et timezone-aware, sont ordonnes. **Tous** les etats terminaux ont `finished_at`.
6. COMPLETED exige la Response du **meme RunId**, sans Failure. FAILED exige Failure code-only, sans Response. CANCELLED n'a ni Response ni Failure et peut avoir un code d'annulation.
7. Le constructeur rejette des snapshots incoherents, meme lors de `dataclasses.replace`; le futur decoder JSON v1 pourra s'appuyer sur ces invariants mais n'est pas encore code.
8. Aucun secret, prompt brut ou raw provider error n'entre dans `InferenceFailure`. La representation `repr` de l'Aggregate masque request, response, failure et cancellation_reason_code par defaut, sans promettre une redaction exhaustive en aval.
9. Les events InferenceStarted/Completed/Failed/Cancelled restent dans un **catalogue de domaine** et ne sont pas emis vers un event bus.

## 6. Reservations de qualification

- **R-01 gouvernance** : `main.protected=false` observe a l'integration; [issue #22](https://github.com/tawounfouet/pyllmkit/issues/22) encore ouverte. Le merge controle par SHA et la CI ne remplacent pas des protections de branche.
- **R-02 revue tierce** : aucune revue GitHub independante approuvante n'est revendiquee.
- **R-03 dette M2** : [issue #20](https://github.com/tawounfouet/pyllmkit/issues/20) ouverte, PIR2-01/02/03 traites separement.
- **R-04 limites fonctionnelles** : aucune execution de modele, cancellation reseau, streaming reel, retry, persistence, bus d'evenements ou reconciliation provider.
- **R-05 codec** : P3-AC-021..028, dont les round-trips JSON v1 et les tests de payloads inconnus, attendent L3.4. Aucun resultat codec P3 n'est declare passe par ce gate.
- **R-06 publication** : `pyproject.toml` conserve `0.1.0a2`; pas de release, tag ou PyPI.

Ces reserves sont compatibles avec **un GO technique du domaine L3.3**, pas avec un GO de publication de `0.1.0a3`.

## 7. Tableau des gates

| Gate | Etat |
|---|---|
| P3-G0 - Architecture Ready | GO avec reserves (precedent) |
| P3-G1 - Request Ready | GO technique avec reserves (precedent) |
| P3-G2 - Response Ready | GO technique avec reserves (precedent) |
| **P3-G3 - Run Lifecycle Ready** | **GO technique avec reserves** |
| P3-G4 - JSON Codec & Quality | NOT STARTED |
| P3-G5 - Integration & Packaging | NOT STARTED |
| M3 - Inference Foundations Qualified | NOT QUALIFIED |
| Release/PyPI 0.1.0a3 | NOT AUTHORIZED |

**Prochain chantier autorise : L3.4 - Inference JSON Codec & Quality**, en suivant ADR-020, avec schema JSON v1 independant, enveloppes Request/Response/Run, six snapshots reconstruisibles et negatives schemas stricts.

## 8. Archivage et non-circularite

Ce verdict porte sur `main@361791ff...` et CI #42044787119. Le present PV sera integre par une PR documentaire separee et produira un nouveau SHA `main` ; sa CI propre devra etre verifiee puis archivee en commentaire de cette PR pour eviter un document qui revendique par anticipation sa propre validation.

---

**VERDICT FINAL : P3-G3 = GO TECHNIQUE AVEC RESERVES. L3.4 EST AUTORISE A DEMARRER.** Aucun GO M3 ou publication.
