# PyLLMKit - P3-G2 Response Ready - Proces-verbal de qualification

> **Date :** 2026-11-05
> **Phase / version cible :** P3 / `0.1.0a3 - Inference Primitives` (candidate source, non publiee)
> **Lot :** L3.2 - Inference Response Domain
> **Verdict : P3-G2 = GO TECHNIQUE AVEC RESERVES**
> **Perimetre :** objets domaine de reponse, sans invocation LLM ni machine a etats Run
> **PR d'implementation :** [#25](https://github.com/tawounfouet/pyllmkit/pull/25) - merge squash
> **SHA main qualifiant :** [`783aa4381dc05a4b9bc431faab282f2bbe37d38d`](https://github.com/tawounfouet/pyllmkit/commit/783aa4381dc05a4b9bc431faab282f2bbe37d38d)
> **CI push/main :** [GitHub Actions #42039312011](https://github.com/tawounfouet/pyllmkit/actions/runs/42039312011) - completed / **SUCCESS**
> **Publication :** NON AUTORISEE. La version du depot reste `0.1.0a2`.
> **Historique G1 :** [P3_G1_GATE_REVIEW.md](P3_G1_GATE_REVIEW.md), 432 tests et 93 % de couverture.

## 1. Objet et decision

Verifier que les objets **InferenceResponse, TextOutput, FinishReason, Usage** et leur identite de correlation sont implementees conformement aux ADR-014, ADR-017 et ADR-018 adoptees en P3-G0. Le gate G2 n'exige pas encore un provider ou un `InferenceRun` operationnel. La presence d'un objet Response ne prouve pas qu'un modele a ete invoque.

**Decision : GO technique avec reserves** pour passer a L3.3, sur preuve CI apres fusion et sur SHA exact de `main`. Les six tests d'acceptation P3-AC-008 a P3-AC-013 passent dans la suite complete.

## 2. Artefacts qualifies

| Contrat | Module / symbole | Comportement verifie |
|---|---|---|
| RunId de correlation | `inference/identifiers.py` / `InferenceRunId` | Identifiant opaque non vide, explicitement fourni, pas de UUID implicite |
| Output | `inference/output.py` / `TextOutput`, `InferenceOutput` alias de type | Unicode et chaine vide valides, type strict, kind text |
| FinishReason | `inference/finish.py` / `FinishReasonCode`, `FinishReason` | STOP, LENGTH, TOOL_CALL, CONTENT_FILTER, CANCELLED, ERROR, UNKNOWN; absence != UNKNOWN; raison native preservee |
| Usage | `inference/usage.py` / `Usage` | Cinq compteurs int exact >= 0 ou None, bool interdit, total jamais deduit |
| Reponse | `inference/response.py` / `InferenceResponse` | Value Object immuable, run_id et output obligatoires, raison et usage optionnels |
| Imports publics | `pyllmkit.domain.inference` et `pyllmkit.domain` | Compatibilite M1/M2/L3.1 conservee |
| API et exemple offline | `docs/api/inference-response.md`, `examples/09_define_inference_response.py` | Pas de SDK, pas de transport |
| Frontieres d'architecture | `tests/architecture/test_p3_l31_domain_boundaries.py` | Modules L3.1 + L3.2 connus et imports non providers |
| Packaging | `.github/workflows/ci.yml` | Wheel/sdist smoke API L3.2, matrix Python |

L'alias `InferenceOutput` est une famille conceptuelle exposee comme **TypeAlias = TextOutput** dans le P0. Il ne represente ni une nouvelle classe de base instanciable ni le support d'autres sorties.

## 3. Matrice d'acceptation P3-AC

| ID | Preuve d'acceptation sur le commit qualifie | Verdict |
|---|---|---|
| P3-AC-008 | `TextOutput` et `InferenceResponse` construits sans SDK | PASS |
| P3-AC-009 | `FinishReason.UNKNOWN` conserve son motif natif, sans STOP invente | PASS |
| P3-AC-010 | `usage=None` conserve si non reporte | PASS |
| P3-AC-011 | `Usage` partiel ne fabrique pas `total_tokens` | PASS |
| P3-AC-012 | Negatif, booleen ou float pour compteur -> `DomainValidationError` | PASS |
| P3-AC-013 | `Usage` sans Pricing ni Cost automatique | PASS |

Preuves : `tests/acceptance/test_p3_l32_inference_response.py`, `tests/unit/domain/inference/test_output_finish.py`, `test_usage.py`, `test_response.py`. L'ensemble est dans le workflow `pytest` de la CI.

**Ne pas comptabiliser 545 comme tests nouveaux L3.2 :** il s'agit du total M1 + M2 + L3.1 + L3.2. Baseline precedente G1 : 432 tests / 93 %.

## 4. Chaine de preuves CI

| Controle | Valeur |
|---|---|
| PR de code | [#25](https://github.com/tawounfouet/pyllmkit/pull/25) |
| Dernier SHA PR valide | `586f274e22c96348dee5a802cfa544abf89273b8` |
| CI PR | [#42039086705](https://github.com/tawounfouet/pyllmkit/actions/runs/42039086705), completed / SUCCESS, 3/3 jobs |
| SHA main apres squash | `783aa4381dc05a4b9bc431faab282f2bbe37d38d` |
| CI main | [#42039312011](https://github.com/tawounfouet/pyllmkit/actions/runs/42039312011), push / completed / SUCCESS |
| Python 3.11 | `validate (3.11)` - SUCCESS |
| Python 3.12 | `validate (3.12)` - SUCCESS |
| Python 3.13 | `validate (3.13)` - SUCCESS |
| Pytest Python 3.11 | **545 passed** |
| Couverture branche comprise | **94 %** : 1022 statements / 46 misses, 320 branches / 38 partials |
| Ruff | All checks passed |
| mypy | Success: no issues found in 36 source files |
| Exemples offline | 01 a 09 - SUCCESS |
| wheel + sdist et imports L3.2 en environnement propre | SUCCESS |

La CI qualifie le code exact de `main` a cette etape; elle ne prouve pas une absence absolue de vulnerability, d'I/O hors scope ou de toute regression future. La redaction du present PV sur une PR documentaire separee permet d'eviter les preuves circulaires.

## 5. Contrats semantiques et limites

1. Un `InferenceResponse` est un **Value Object**, pas un Run et ne possede aucun etat ou lifecycle.
2. Son `run_id` est fourni explicitement comme `InferenceRunId`; L3.3 devra verifier `response.run_id == run.id` lors de `complete()`.
3. `TextOutput("")` est valide; `TextOutput(None)` refuse. Le texte est masque du `repr` par defaut, sans pretendre une redaction universelle.
4. `finish_reason=None` signifie absence. `FinishReason(UNKNOWN, native)` represente un motif inconnu avec sa valeur source intacte; aucune transformation silencieuse en STOP.
5. `FinishReasonCode.TOOL_CALL` n'executera pas d'outil en a3.
6. `Usage` porte uniquement des compteurs observes. `None` ne signifie pas 0; `total_tokens` est preserve tel que fourni meme s'il differe de input+output.
7. Une source totalement muette sur les tokens produit `usage=None`. `Usage()` est un VO structurel valide sans mesure, mais ne doit pas etre presente comme une observation.
8. Aucun prix, cout, outil, streaming, JSON Inference v1, response native provider, model/deployment resolu ou invocation HTTP n'est implementee dans L3.2.
9. Les codecs Model JSON v1 et Interaction JSON v1 restent a leurs contrats precedents.

## 6. Reserves et gouvernance

- **R-01 main non protegee :** `main.protected=false` observe lors des qualifications recentes. Suivi [issue #22](https://github.com/tawounfouet/pyllmkit/issues/22). Une fusion volontaire avec SHA attendu et CI verte ne remplace pas des protections permanentes.
- **R-02 review externe :** aucune revue GitHub `APPROVED` independante n'est revendiquee ici.
- **R-03 dette M2 :** [issue #20](https://github.com/tawounfouet/pyllmkit/issues/20), PIR2-01/02/03 non resolues par L3.2.
- **R-04 code et sortie :** la CI couvre les objets du domaine mais aucune invocation de modele. Run et codecs seront testes dans les gates suivants.
- **R-05 publication :** la version actuelle dans `pyproject.toml` est `0.1.0a2`. Aucun `0.1.0a3` tag / release / PyPI autorise.

Ces reserves sont acceptees pour **G2 technique** et non pour une publication.

## 7. Tableau des gates et prochaine action

| Gate | Etat |
|---|---|
| P3-G0 - Architecture Ready | GO avec reserves (precedemment qualifie) |
| P3-G1 - Request Ready | GO technique avec reserves (precedemment qualifie) |
| **P3-G2 - Response Ready** | **GO technique avec reserves** |
| P3-G3 - Run Ready | NOT STARTED |
| P3-G4 - Inference JSON v1 Quality | NOT STARTED |
| P3-G5 - Integration & Packaging | NOT STARTED |
| M3 - Inference Foundations Qualified | NOT QUALIFIED |
| Publication 0.1.0a3 | NOT AUTHORIZED |

**Prochaine action autorisee :** L3.3 - Inference Run Domain, implementant `InferenceRun` Aggregate Root, machine a etats a six etats, timestamps explicitement injectes, `InferenceFailure`, transitions pures, reference a `InferenceResponse` et cas d'acceptation correspondants. Aucun moteur d'execution provider.

## 8. Regle d'archivage

Le verdict technique porte sur `main@783aa438...` et CI #42039312011. Le commit qui archivera ce document et les liens README/ROADMAP sera un **nouveau SHA**; il devra lui-meme passer la CI et les preuves doivent etre ajoutees en commentaire de la PR d'archivage. Aucun SHA futur n'est pre-qualifie.

---

**VERDICT : P3-G2 = GO TECHNIQUE AVEC RESERVES, L3.3 AUTORISE.**  
**M3, tag GitHub et publication PyPI restent non qualifies / non autorises.**
