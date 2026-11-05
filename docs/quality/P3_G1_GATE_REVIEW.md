# PyLLMKit - P3-G1 Request Ready - Proces-verbal de qualification

> Date: 2026-11-05
> Version cible: 0.1.0a3 - Inference Primitives (source candidate, non publiee)
> Lot: L3.1 - Inference Request Domain
> Verdict: **P3-G1 = GO TECHNIQUE AVEC RESERVES**
> Portee: Request/Target/GenerationConfig/compatibilite offline, pas d'inference provider
> Integration: [PR #23](https://github.com/tawounfouet/pyllmkit/pull/23) fusionnee par squash
> Main qualifiant: [f1ef04b8ff1bb52a1ee17defa0ec8b20f84ac9d3](https://github.com/tawounfouet/pyllmkit/commit/f1ef04b8ff1bb52a1ee17defa0ec8b20f84ac9d3)
> CI main: [GitHub Actions #42036557565](https://github.com/tawounfouet/pyllmkit/actions/runs/42036557565) - push, completed, **success**
> Release: NOT AUTHORIZED, aucune publication PyPI, aucun tag ou release a3

## 1. Objet et decision

P3-G1 qualifie le lot L3.1 implemente sur main, dans le perimetre ADR-014, ADR-015, ADR-016 et ADR-021 option A adoptes lors de P3-G0. L'acceptation technique est une preuve de logiciel et de domaine; elle n'implique ni l'existence d'InferenceRun/InferenceResponse ni une connexion a un modele.

**Decision technique:** les sept cas P3-AC-001 a P3-AC-007 disposent de tests d'acceptation et passent avec l'ensemble de la suite existante sur le SHA main qualifie. Le gate G1 est GO pour poursuivre vers L3.2, avec risques explicites de gouvernance et dette technique suivis.

## 2. Composants integres

| Composant | Preuve | Limite |
|---|---|---|
| ModelTarget / DeploymentTarget / EndpointTarget | domain/inference/targets.py | Identifiants passifs, pas de resolver |
| DeploymentId / EndpointId | Identifiants opaques, immuables et distincts | Ne sont ni URLs a contacter ni provider credentials |
| GenerationConfig | domain/inference/config.py, bornes strictes | Aucun default fournisseur, None preserve |
| InferenceRequest | domain/inference/request.py, 1..* Message | Value Object sans ID, pas d'execution |
| GenerationSupportSnapshot | domain/inference/compatibility.py | Snapshot fourni et cible exacte |
| CompatibilityReport + validation | evaluate_request_support / validate_request_support | UNKNOWN reste inconnu, UNSUPPORTED explicitement rejete |
| Imports publics | domain.inference et domain | M1/M2 conserves |
| Exemple offline | examples/08_define_inference_request.py | Aucun appel LLM |
| Documentation | docs/api/inference-request.md | API L3.1, pas de Run ou JSON Inference v1 |

## 3. Matrice d'acceptation

| Scenario | Resultat | Fichier de preuve |
|---|---|---|
| P3-AC-001 - Request ModelTarget + texte | PASS | tests/acceptance/test_p3_l31_inference_request.py |
| P3-AC-002 - Texte/image sans changement d'ordre | PASS | idem |
| P3-AC-003 - Target absente refusee | PASS | idem |
| P3-AC-004 - Temperature NaN/Infinity refusee | PASS | idem |
| P3-AC-005 - max_output_tokens None != 0 | PASS | idem |
| P3-AC-006 - True refuse pour entier | PASS | idem |
| P3-AC-007 - Parametre UNSUPPORTED selon snapshot explicite | PASS | idem et tests/unit/domain/inference/test_compatibility.py |

Les assertions P3-AC-001..007 ont ete executees dans la suite CI et non seulement mentionnees en documentation. Les autres cas P3-AC-008..030 attendent leurs lots futurs.

## 4. Evidence CI exacte

| Controle | Resultat verifie |
|---|---|
| SHA integre sur main | f1ef04b8ff1bb52a1ee17defa0ec8b20f84ac9d3 |
| Actions push main | #42036557565 - completed/success |
| validate (Python 3.11) | SUCCESS |
| validate (Python 3.12) | SUCCESS |
| validate (Python 3.13) | SUCCESS |
| Pytest Python 3.11 | **432 passed**, 1.04 s |
| Couverture combinee branche incluse | **93 %**, total 939 statements / 46 misses, 300 branches / 38 partials |
| Ruff et mypy | SUCCESS; mypy: no issues found in 31 source files |
| Exemples offline | SUCCESS, including example 08 |
| Wheel et sdist, smoke tests propres | SUCCESS, y compris imports L3.1 |

Le compteur 432 tests inclut M1, M2 et L3.1; il ne represente pas 432 nouveaux tests de Phase 3. La baseline M2 precedente etait 342 tests / 91 % de couverture. Le workflow n'est pas une preuve exhaustive de securite ni d'absence absolue d'I/O hors de son cadre.

## 5. Invariants confirmes

1. Un Target ne resout ni provider, ni Deployment, ni Endpoint; ses IDs conservent leur type.
2. GenerationConfig impose float exact fini et int exact hors bool. temperature=0.0 valide, temperature=0 entier rejete, stop_sequences=() distinct de None.
3. Request est un Value Object immuable, contient 1..* Message M2 ordonnes et n'acquiert aucun ID implicite.
4. L'evaluateur est une fonction pure sur snapshot effectif fourni par l'appelant pour la cible exacte. Il ne deduit pas de support a partir du seul nom de modele.
5. UNSUPPORTED provoque un refus explicite; UNKNOWN, PARTIAL, EMULATED et l'absence de parametres evalues n'equivalent jamais a une confirmation NATIVE.
6. La requete contenant ImageContent ne prouve pas une capacite VISION effective.
7. Aucun client fournisseur, HTTP, tool execution, Run, Response, Inference JSON v1, streaming reel ou changement du codec M1/M2.

## 6. Reservations et limites

**R-01 - main non protegee :** API de branche renvoie protected=false. Voir [issue #22](https://github.com/tawounfouet/pyllmkit/issues/22). La politique GitHub de protection/review reste a configurer avant publication.

**R-02 - revue externe :** pas de revue GitHub APPROVED independante revendiquee pour PR #23; l'execution technique et l'autorisation utilisateur ne sont pas un audit tiers.

**R-03 - dette de baseline M2 :** [issue #20](https://github.com/tawounfouet/pyllmkit/issues/20) toujours ouverte, correctifs separes et non revendiques.

**R-04 - version et perimetre :** pyproject.toml reste en version 0.1.0a2. P3-G1 n'autorise ni bump a3, ni tag, ni Github Release, ni PyPI. Phase 3 M3 reste PENDING.

## 7. Gates et suite

| Jalons | Etat apres G1 |
|---|---|
| P3-G0 | GO architecture avec reserves, deja archive |
| P3-G1 - Request Ready | **GO technique avec reserves** |
| P3-G2 - Response Ready | NOT STARTED |
| P3-G3 - Run Ready | NOT STARTED |
| P3-G4 - Codec / Quality | NOT STARTED |
| P3-G5 - Integration & Packaging | NOT STARTED |
| M3 - Inference Foundations Qualified | NOT QUALIFIED |
| Publication 0.1.0a3 | NOT AUTHORIZED |

**Suite autorisee:** ouvrir L3.2 - Inference Response Domain (TextOutput, FinishReason, Usage, InferenceResponse), sans fournisseur ni service d'execution.

## 8. Archivage et non circularite des SHA

Le GO technique porte sur le commit main f1ef04b8... apres PR #23 et sur CI #42036557565. La presente archive est une PR documentaire distincte. Son nouveau commit main devra lui-meme passer les controles CI; ajouter les preuves de post-archivage dans un commentaire de la PR pour eviter une chaine infinie d'auto-reference.

**Verdict final : P3-G1 = GO TECHNIQUE AVEC RESERVES. L3.2 peut demarrer. M3 et toute publication restent distincts et non autorises.**
