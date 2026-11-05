# PyLLMKit - Registre de decisions d'architecture Phase 3

**Gate decision archived (2026-11-05): P3-G0 GO architecture avec reserves.** ADR-014..021 ACCEPTED by owner and merged in [PR #19](https://github.com/tawounfouet/pyllmkit/pull/19); main SHA [`965311db`](https://github.com/tawounfouet/pyllmkit/commit/965311dbef527ad59222b7586f9c801bb713bead), [CI SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42029448967). See [P3_G0_GATE_REVIEW.md](P3_G0_GATE_REVIEW.md). Existing PENDING language below documents the historical pre-qualification gate checklist, not current status.


> Date : 2026-11-05
> Version visee : 0.1.0a3 - Inference Primitives
> Statut global : **ADR-014..021 ACCEPTED by owner - G0 integration CI PENDING**
> Autorite decisionnelle : approbation explicite du proprietaire le 2026-11-05 (voir P3_G0_OWNER_ARCHITECTURE_APPROVAL.md).
> Baseline : M2 main acd6dfb76d73c260ccca523cf904be44ec249288, CI finale M2 #42016493260 SUCCESS (selon le PIR M2).
> Publication : non autorisee. Aucun package a3 ni adaptateur fournisseur n'est livre par ce registre.

## 1. Registre

| ADR | Sujet | Choix initial a arbitrer | Statut | Dependance |
|---|---|---|---|---|
| [ADR-014](../adr/ADR-014-inference-request-run-response-boundaries.md) | Request / Run / Response | VO / Aggregate / VO, request chat 1..* messages | ACCEPTED | Fondations M1/M2 |
| [ADR-015](../adr/ADR-015-inference-target-model-deployment-endpoint.md) | Cibles | Model / Deployment / Endpoint discriminants, references opaques | ACCEPTED | ADR-014 |
| [ADR-016](../adr/ADR-016-generation-config-validation-and-support.md) | Config | None, types float exact a arbitrer | ACCEPTED | ADR-015 |
| [ADR-017](../adr/ADR-017-text-output-and-finish-reason.md) | Output / fin | TextOutput, valeur vide valide, raison native preservee | ACCEPTED | ADR-014 |
| [ADR-018](../adr/ADR-018-usage-metrics-and-missing-values.md) | Usage | Compteurs optionnels, aucune valeur inventee | ACCEPTED | ADR-017 |
| [ADR-019](../adr/ADR-019-inference-run-state-machine.md) | Run lifecycle | Snapshots, Failure, finished_at et six etats | ACCEPTED | ADR-014/017 |
| [ADR-020](../adr/ADR-020-inference-json-v1-codec.md) | JSON v1 | Enveloppes canoniques Request/Response/Run et six etats | ACCEPTED | ADR-014..019 |
| [ADR-021](../adr/ADR-021-inference-port-and-effective-compatibility.md) | Ports / compatibilite | Port differe; arbitrer evaluator et AC-007 | ACCEPTED | ADR-015/016 |

**Attention :** ACCEPTED designe l'adoption des contrats de conception par le proprietaire, **pas** une implementation Python, une revue GitHub tierce, la qualification CI sur main, ou une publication.

## 2. Arbitrages du proprietaire - tranches le 2026-11-05

1. Confirmer les trois classes de cible versus ModelTarget seul.
2. Valider la restriction des messages 1..* au chat a3, sans modifier la relation conceptuelle 0..*.
3. Choisir la strategie de Run snapshots immuables versus Entity mutable encapsulee, et confirmer identite/egalite.
4. Confirmer les conventions strictes GenerationConfig, notamment float exact, bornes et max_output_tokens.
5. Confirmer la distinction finish_reason absent (None) vs inconnu (UNKNOWN).
6. Confirmer Usage.total_tokens observe et non calcule silencieusement.
7. Approuver schema Inference JSON v1, presence des champs nullable et snapshot Run.
8. Decider ADR-021 : evaluator pur sur snapshot (option A recommandee) ou report explicite d'AC-007 (option B). Port executable reporte.
9. Fixer InferenceFailure, timestamps terminaux finished_at et egalite par RunId.
10. Arbitre sur le choix strict float exact dans GenerationConfig.

## 3. Tracabilite des exigences

- Request : FR-016..018, INF-001..012, INT-001..003, P3-AC-001..007.
- Response / Usage : FR-019/021/030, INF-022..029, USG-001..006, P3-AC-008..013.
- Run : FR-020, INF-013..021/030..039, P3-AC-014..020/029.
- Codec / securite : SER-001..006, ADR-012, P3-AC-021..028/030.
- Protection M1/M2 : aucune modification de Model JSON v1 / Interaction JSON v1 sans ADR separee.

## 4. Registre des decisions effectives

| Date | Objet | Autorite | Decision | Preuve |
|---|---|---|---|---|
| 2026-11-05 | Ouverture des propositions P3-BOOT | Dossier documentaire | Preparation uniquement, pas de decision d'adoption | Cette branche |
| 2026-11-05 | Revue contradictoire ADR-014..021 | Analyse technique | Revisions et recommandations, **pas une adoption** | [P3-G0 review](P3_G0_ARCHITECTURE_REVIEW.md) |
| 2026-11-05 | Dette PIR2-01..03 | Suivi technique | [Issue #20](https://github.com/tawounfouet/pyllmkit/issues/20) ouverte, dette non resolue | [Issue #20](https://github.com/tawounfouet/pyllmkit/issues/20) |
| 2026-11-05 | Adoption ADR-014..021 et decisions D-01..D-10 | Proprietaire du projet | ACCEPTED, ADR-021 option A (AC-007 requise), float strict | [Decision owner](P3_G0_OWNER_ARCHITECTURE_APPROVAL.md) |

L'adoption explicite a ete accordee par le proprietaire lors de la conversation PyLLMKit du 2026-11-05. Voir [decision owner](P3_G0_OWNER_ARCHITECTURE_APPROVAL.md). **Aucune review GitHub tierce ou approbation independante n'est revendiquee.**

## 5. Qualification de P3-G0

G0 sera eligible a une revue GO uniquement lorsque :
- les ADR-014..020 auront ete explicitement arbitrees et ADR-021 decidee ou reportee ;
- les contrats publics auront ete actualises apres arbitrage ;
- le perimetre des lots et la matrice P3-AC auront ete approuves ;
- les contradictions PIR2-01..03 auront ete levees ou isolees avec risque accepte (suivi initial : issue #20, encore ouverte) ;
- les changements documentaires auront ete integres dans main et la CI de **ce SHA exact** aura ete verifiee.

**Decision de conception : ACCEPTED.** Jusqu'a integration, CI du SHA exact sur main et PV : **P3-G0 QUALIFICATION PENDING; M3 PENDING**.
