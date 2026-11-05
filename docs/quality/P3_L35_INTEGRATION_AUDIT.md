# PyLLMKit - L3.5 Integration & Packaging - Audit transversal pre-G5

**POST-INTEGRATION (2026-11-05): P3-G5 GO TECHNIQUE AVEC RESERVES.** [PR #32](https://github.com/tawounfouet/pyllmkit/pull/32) fusionnee sur [main 49cf26e](https://github.com/tawounfouet/pyllmkit/commit/49cf26e830819675a1c4cad9dfd2860fc977f0b6), [CI main #42059417894 SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42059417894) : 798 tests et 95 % de couverture, trois versions Python vertes. Voir [P3_G5_GATE_REVIEW.md](P3_G5_GATE_REVIEW.md). Le texte PENDING ci-dessous est la photographie de l'audit **pre-gate**, non le verdict actuel. M3 reste a qualifier.


> Date : 2026-11-05
> Perimetre : M1 Model, M2 Interaction, P3 Request/Response/Run/Codec v1.
> Etat : **AUDIT CANDIDAT**, ne vaut **pas** verdict GO P3-G5 avant CI sur SHA final de `main`.
> Baseline de depart : `main@1155a534bb8acb1873a59723258013914ac8437c` (G4 archive).
> Baseline baseline-debt corrigee : PR #31 / `main@2ec317de98bd9d0897fe1e48801a9727e4f7ced6`; [CI #42057132634](https://github.com/tawounfouet/pyllmkit/actions/runs/42057132634) SUCCESS, 789 tests / 95 % (Python 3.11).
> Gate G5 et M3 : PENDING a la redaction; publication non autorisee.

## 1. Methode et sources

Cet audit compare les contrats du [plan de Phase 3](../03_PYLLMKIT_PHASE_3_IMPLEMENTATION_PLAN.md), ADR-014..021, PV G0-G4, `pyproject.toml`, les codes `src/pyllmkit/domain`, les 12 exemples offline et `.github/workflows/ci.yml`. Les faits externes de publication ou de protection GitHub ne sont pas supposes si le connecteur ne les prouve pas.

## 2. Check-list du backlog L3.5

| ID | Livrable concret | Preuve/artefact | Pre-G5 |
|---|---|---|---|
| P3-L35-T01 | API publique root/subpackage figee et testee | `docs/api/inference.md`; `tests/packaging/test_phase3_public_api.py` | Implementee, CI a qualifier |
| P3-L35-T02 | Trois concepts et deux documents d'architecture | `docs/concepts/inference-*.md`, `PHASE_3_INFERENCE_CONTRACTS.md`, `INFERENCE_JSON_SCHEMA_V1.md` | Redigee, a relire |
| P3-L35-T03 | Exemple offline M1-M3 dans la matrice CI | `examples/12_full_inference_walkthrough.py`, workflow Python 3.11/12/13 | Implementee, CI a qualifier |
| P3-L35-T04 | Wheel et sdist propres, imports et usage complet | `Wheel clean environment smoke`, `Sdist clean environment smoke`, exemple 12 | Implementee, CI a qualifier |
| P3-L35-T05 | README snippets copiables, PIR2-02 corrige | PR #31, `test_readme_domain_example.py`, `test_p3_l35_readme_snippets.py` | Corrigee, AC-030 CI a qualifier |
| P3-L35-T06 | ADR historiques M2 reels, PIR2-01 corrige | PR #31, notes ADR-010..013, PV M2 | Corrigee, CI #42057132634 SUCCESS |
| P3-L35-T07 | PIR2-03 Mapping M2 aligne, tests | PR #31 et `test_interaction_mapping_contract.py` | Corrigee, CI #42057132634 SUCCESS |
| P3-L35-T08 | Version, licence, dependencies, changelog | `pyproject.toml`, `LICENSE`, `CHANGELOG.md`, test metadata | Source candidate a2, no release |
| P3-L35-T09 | Preuve CI exacte SHA main integre | A remplir apres PR d'implementation | PENDING |
| P3-L35-T10 | Audit G5, risques et precheck M3 | Ce document, `PHASE_3_TRACEABILITY.md`, PV G5 futur | PENDING gate |

Ne jamais convertir un resultat de test sur une branche PR en preuve de CI du SHA integre.

## 3. Reconciliation M1-M3

- M1 : pas de changement schema Model v1, objets `ModelId` et `Capability` conserves; tests M1 inclus dans la suite complete.
- M2 : Interaction JSON v1 et Message `Role/Content` conserves, ordre et multimodalite descriptive. PIR2-01/02/03 ont ete traites dans une PR separee. `MappingProxyType` est maintenant supporte dans le decodeur Interaction comme l'annonce `Mapping[str,object]`.
- L3.1 : la Request est une intention, Config optional et stricte, Target typee, support effectif sans fournisseur.
- L3.2 : Response est un VO; Usage/FinishReason ne doivent pas inventer des observations.
- L3.3 : Run est un aggregate DDD avec snapshots immuables et horloges injectees; streaming est un etat conceptuel.
- L3.4 : trois enveloppes Inference JSON v1 avec versions propres, cles obligatoires et revalidation de Run au decode.
- L3.5 : aucun nouveau runtime provider ni outil operationnel, pas de migration de schemas.

## 4. Evidences attendues G5

Le controle minimal exige **Ruff, mypy strict, pytest full + branch coverage, tests des 30 P3-AC, scripts offline, wheel/sdist clean-install** sur Python 3.11/3.12/3.13. Le PV G5 doit rapporter les chiffres **du job et du SHA exact**, incluant les erreurs/couverture et non une projection de resultats.

La validation de `pyproject.toml`, `LICENSE`, `py.typed` et l'absence de dependencies runtime provider fait partie des tests. L'API de domaine est testee via ses aliases root et subpackage. Il faut verifier qu'aucune commande de publication n'existe dans le workflow CI ordinaire.

## 5. Risques et arbitrages

| Risque | Constat | Impact | Traitement G5 |
|---|---|---|---|
| G5-R01, main unprotected | API GitHub `main.protected=false` | Fusion/push non controles par ruleset | **Issue #22 OPEN**, owners repository, requerra droits admin et politique avant release |
| G5-R02, parser JSON text | `json.loads` ne refuse pas par defaut les cles dupliquees | Dropping avant codec | Defere au boundary applicatif futur; l'API domaine n'accepte que mappings JSON-compatible |
| G5-R03, revue independante | Pas de GitHub APPROVED review tierce revendiquee | Absence de separation de responsabilites | Reserve avant release, pas revendiquee comme acquise |
| G5-R04, release candidate | `pyproject.toml` vaut `0.1.0a2` | Nom de source ≠ version future M3 | Bump a3 distinct, uniquement apres strategie de release approuvee |
| G5-R05, provider runtime | Aucun adapter/HTTP/streaming reel M3 | Pas de generation a distance | **Hors scope** explicite, non un test manquant |

Les risques R01/R03 ne sont **pas** qualifies comme corriges. Un GO technique G5, s'il est prononce, doit rester **avec reserves**, distinct d'un GO de publication et d'une preuve de security compliance.

## 6. Prochaine transition

1. Completer code/tests/docs et verifier CI sur la PR d'implementation.
2. Fusionner uniquement par squash + SHA attendu, puis controler la CI du nouveau SHA de `main`.
3. Archiver `P3_G5_GATE_REVIEW.md` avec preuves reels et nouvelle CI de l'archive.
4. Preparer une **revue M3 independante** (GO/NO-GO, risques explicites), sans declencher un tag, une GitHub Release ou un upload PyPI.

**VERDICT DE CET AUDIT PRE-G5 : IMPLEMENTATION CANDIDATE - GO/NO-GO G5 PENDING.**
