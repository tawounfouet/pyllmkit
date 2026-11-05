# Phase 3 - Traceabilite exigences, ADR, tests et preuves GitHub

> Date de reference : 2026-11-05
> Baseline avant L3.5 : `main@1155a534bb8acb1873a59723258013914ac8437c` (G4 archive, CI #42054732561 SUCCESS).
> Baseline PIR2 corrigee : `main@2ec317de98bd9d0897fe1e48801a9727e4f7ced6`, PR #31, CI #42057132634 SUCCESS.
> **Statut :** P3-G0..G4 GO technique avec reserves; L3.5/G5 et M3 en qualification, publication non autorisee.
> Sources : Phase 3 implementation plan, ADR-014..021 ACCEPTED et PV G0..G4.

## Sources et provenance

Les `P3-AC-001..030` sont les cas de recette propres au plan de Phase 3, et non des exigences originelles du corpus 00..09. Les exigences associees (INF, INT, MOD, SER, NFR) sont des references de la documentation fondatrice; aucun statut de test n'est invente pour un document qui n'est pas tracke dans GitHub.

## Matrice des trente cas P3-AC

| AC | Contrat et exigence | Decision | Test execution | Gate / PR | Statut |
|---|---|---|---|---|---|
| 001 | Request texte + ModelTarget, UC-008 | ADR-014/015 | `tests/acceptance/test_p3_l31_inference_request.py` | G1 / #23 | PASS G1 |
| 002 | Mixte texte/image ordonne, INT-003 | ADR-014/010 | meme fichier | G1 / #23 | PASS G1 |
| 003 | Target absente invalide, INF-007 | ADR-014/015 | meme fichier | G1 / #23 | PASS G1 |
| 004 | NaN/Inf temperature refuses, INF-003 | ADR-016 | meme fichier | G1 / #23 | PASS G1 |
| 005 | max_output_tokens None vs 0, INF-002 | ADR-016 | meme fichier | G1 / #23 | PASS G1 |
| 006 | Bool refuse comme entier, INF-003 | ADR-016 | meme fichier | G1 / #23 | PASS G1 |
| 007 | Parametre UNSUPPORTED refuse, INF support | ADR-021 A | meme fichier et `test_compatibility.py` | G1 / #23 | PASS G1 |
| 008 | Response + TextOutput, INF-008 | ADR-014/017 | `tests/acceptance/test_p3_l32_inference_response.py` | G2 / #25 | PASS G2 |
| 009 | FinishReason UNKNOWN native preservee | ADR-017 | meme fichier | G2 / #25 | PASS G2 |
| 010 | Usage totalement absente = None | ADR-018 | meme fichier | G2 / #25 | PASS G2 |
| 011 | Usage partielle, total non invente | ADR-018 | meme fichier | G2 / #25 | PASS G2 |
| 012 | Negatif/bool/float tokens refuses | ADR-018 | meme fichier | G2 / #25 | PASS G2 |
| 013 | Usage n'est pas Pricing/Cost | ADR-018 | meme fichier | G2 / #25 | PASS G2 |
| 014 | Deux runs de la meme Request | ADR-014/019 | `tests/acceptance/test_p3_l33_inference_run.py` | G3 / #27 | PASS G3 |
| 015 | CREATED -> RUNNING -> COMPLETED | ADR-019 | meme fichier | G3 / #27 | PASS G3 |
| 016 | FAILED sans Response et avec Failure | ADR-019 | meme fichier | G3 / #27 | PASS G3 |
| 017 | CANCELLED terminal et local | ADR-019 | meme fichier | G3 / #27 | PASS G3 |
| 018 | COMPLETED ne redemarre jamais | ADR-019 | meme fichier | G3 / #27 | PASS G3 |
| 019 | Response de mauvais RunId refusee | ADR-014/019 | meme fichier | G3 / #27 | PASS G3 |
| 020 | Rejouer Request sans mutation | ADR-019 | meme fichier | G3 / #27 | PASS G3 |
| 021 | Request/dict/JSON/Request | ADR-020 | `tests/acceptance/test_p3_l34_inference_json_v1.py` | G4 / #29 | PASS G4 |
| 022 | Response/dict/JSON/Response | ADR-020 | meme fichier | G4 / #29 | PASS G4 |
| 023 | Schema/version/cles inconnues refus | ADR-020 | meme fichier + `test_serialization_strict.py` | G4 / #29 | PASS G4 |
| 024 | Model/Interaction JSON v1 non casses | ADR-004/012/020 | meme fichier + `tests/serialization` | G4 / #29 | PASS G4 |
| 025 | Pas d'appels reseau/credentials | NFR-003/005 | `test_p3_l34_inference_json_v1.py` et examples | G4 / #29 | PASS G4 |
| 026 | Imports root/subpackage wheel/sdist | ADR-005/020 | CI `.github/workflows/ci.yml` + smoke | G4 / #29 | PASS G4 |
| 027 | Aucun secret URI dans les erreurs | ADR-011/020 | `test_p3_l34_inference_json_v1.py` | G4 / #29 | PASS G4 |
| 028 | ContentPart inconnu refuse | ADR-010/012 | meme fichier | G4 / #29 | PASS G4 |
| 029 | Horloge injectee, deterministe | ADR-019 | `test_p3_l33_inference_run.py` | G3 / #27 | PASS G3 |
| 030 | README/snippet P3 copiable | PIR2-02 / NFR-Docs | `tests/acceptance/test_p3_l35_readme_snippets.py` | **G5 / PR L3.5** | **PENDING final main CI** |

Pour les chemins courts `test_compatibility.py`, `test_serialization_strict.py`, consulter `tests/unit/domain/inference/`. Tous les tests de gates G1..G4 ont deja ete executes sur `main` qualifie; pour AC-030, la presence d'un fichier ne constitue pas une preuve PASS avant CI.

## Matrice G0-G5 et provenance CI

| Gate | PR de code / docs | SHA applicatif qualifiant sur main | CI main et resultat | Decision |
|---|---|---|---|---|
| P3-G0 | #19, #21 | `965311dbef527ad59222b7586f9c801bb713bead` | [#42029448967](https://github.com/tawounfouet/pyllmkit/actions/runs/42029448967) SUCCESS | GO avec reserves |
| P3-G1 | #23, #24 | `f1ef04b8ff1bb52a1ee17defa0ec8b20f84ac9d3` | [#42036557565](https://github.com/tawounfouet/pyllmkit/actions/runs/42036557565) SUCCESS | GO technique avec reserves |
| P3-G2 | #25, #26 | `783aa4381dc05a4b9bc431faab282f2bbe37d38d` | [#42039312011](https://github.com/tawounfouet/pyllmkit/actions/runs/42039312011) SUCCESS | GO technique avec reserves |
| P3-G3 | #27, #28 | `361791ff546612e10b407874c54014b1c0e1ce86` | [#42044787119](https://github.com/tawounfouet/pyllmkit/actions/runs/42044787119) SUCCESS | GO technique avec reserves |
| P3-G4 | #29, #30 | `d72b1ce82a4a34c62888ad48b50bcf07537f83d1` | [#42053906726](https://github.com/tawounfouet/pyllmkit/actions/runs/42053906726) SUCCESS | GO technique avec reserves |
| PIR2 correctifs | #31 | `2ec317de98bd9d0897fe1e48801a9727e4f7ced6` | [#42057132634](https://github.com/tawounfouet/pyllmkit/actions/runs/42057132634) SUCCESS (789 tests, 95 %) | #20 CLOSED |
| **P3-G5** | PR L3.5 et PV distinct | **PENDING** | **PENDING exact main CI** | **NON QUALIFIE** |
| **M3** | Revue et decision separee | **PENDING** | **PENDING** | **NON QUALIFIE** |

Les SHA ci-dessus sont les **SHAs applicatifs** de qualification. Les archives documentaires ont des SHAs differents, chacun avec sa propre CI mentionnee dans la PR d'archivage. Aucun chiffre de CI futur n'est pre-annonce.

## Verifications d'integration L3.5

- `tests/packaging/test_phase3_public_api.py` : 30 exports P3, version source, zero dependance fournisseur, schema v1 distinct.
- `tests/quality/test_phase3_documentation_integrity.py` : existence des artefacts contractuels, liens README et absence de commande de publication dans la CI.
- `tests/acceptance/test_p3_l35_readme_snippets.py` : syntaxe de tous les snippets README + execution du P3-AC-030.
- `tests/quality/test_readme_domain_example.py` : reprise de PIR2-02 en CI.
- `tests/serialization/test_interaction_mapping_contract.py` : PIR2-03, MappingProxyType top et nested.
- `examples/12_full_inference_walkthrough.py` : parcours offline Request -> Run -> Response -> JSON, sans fournisseur.
- CI : Python 3.11/3.12/3.13, Ruff, mypy strict, pytest avec couverture branches, wheel/sdist clean-install et exemples hors ligne.

## Risques et suivi

- **#20 PIR2-01/02/03 :** CLOSED suite a PR #31 et CI main sur SHA exact (pas une derogation).
- **#22 Protection main :** OPEN; `protected=false` lu dans la branche. Le connecteur ne dispose pas de droits admin pour installer/attester une ruleset.
- **Parser JSON texte :** duplicate keys non garanties par `json.loads` standard; la politique appartient au futur boundary d'application (ADR-020).
- **Release :** metadata `0.1.0a2`, aucune publication ni tag prevu par G5. Revue M3 et release sont deux decisions distinctes.

**Etat courant : P3-G5 et M3 non qualifies tant que les preuves de fusion et CI sur main ne sont pas archivees.**
