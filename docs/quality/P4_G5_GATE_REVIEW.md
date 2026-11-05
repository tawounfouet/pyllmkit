# PyLLMKit - P4-G5 Integration & Quality Ready - Procès-verbal de qualification

> **Date :** 2026-11-05.
> **Verdict : GO TECHNIQUE AVEC RÉSERVES**, phase P4-G5 qualifiée.
> **Autorité :** propriétaire du dépôt, instruction explicite de finaliser L4.5, qualifier M4 et intégrer les artefacts sur main.
> **SHA applicatif qualifiant sur main :** [aad2656cbe1753dac709bb28b228ba22ecca44a2](https://github.com/tawounfouet/pyllmkit/commit/aad2656cbe1753dac709bb28b228ba22ecca44a2).
> **CI push/main correspondante :** [GitHub Actions #42092202193](https://github.com/tawounfouet/pyllmkit/actions/runs/42092202193), `completed/success`.
> **Version source :** `0.1.0a2` ; **publication : NO-GO / non autorisée**.
> **Portée :** validation technique du domaine hors ligne, ni production ni exécution de tools/agents ou d'adapters fournisseurs.

## 1. Conditions examinées et preuves exactes

| Contrôle | Constat / référence | Verdict |
|---|---|---|
| P4-G0 Architecture | ADR-022..029 ACCEPTED ; [PV G0](P4_G0_GATE_REVIEW.md) | PASS |
| P4-G1 Tool Declaration | [PV G1](P4_G1_GATE_REVIEW.md) | PASS |
| P4-G2 Tool Call Ready | [PV G2](P4_G2_GATE_REVIEW.md) | PASS |
| P4-G3 Structured Output | [PV G3](P4_G3_GATE_REVIEW.md) | PASS |
| P4-G4 Composition/Codec | [PV G4](P4_G4_GATE_REVIEW.md) | PASS |
| L4.5 PR | [#48](https://github.com/tawounfouet/pyllmkit/pull/48) squash-merged avec head attendu `bd6375fb88634a7674d0f357c3c104176690bdab` | PASS |
| CI PR | [#42091493580](https://github.com/tawounfouet/pyllmkit/actions/runs/42091493580) `completed/success` | PASS |
| CI push/branche | [#42091487084](https://github.com/tawounfouet/pyllmkit/actions/runs/42091487084) `completed/success` | PASS |
| SHA de main après merge | `aad2656cbe1753dac709bb28b228ba22ecca44a2` | PASS |
| CI push/main du SHA exact | [#42092202193](https://github.com/tawounfouet/pyllmkit/actions/runs/42092202193) `completed/success` | PASS |
| Python 3.11 | job `127472873735` SUCCESS | PASS |
| Python 3.12 | job `127472873875` SUCCESS | PASS |
| Python 3.13 | job `127472873251` SUCCESS | PASS |
| Tests Python 3.11 | **967 passed, 0 failed** : suite cumulative M1-M4 | PASS |
| Couverture globale branches incluses | **96 %** : 2 254 statements, 67 misses, 866 branches, 62 partial | PASS |
| Lint | Ruff `All checks passed!` | PASS |
| Typage | mypy strict : `Success: no issues found in 58 source files` | PASS |
| Exemples offline | 01..17 en source ; 13..17 en clean wheel/sdist, example 17 exercé | PASS |
| Build | `python -m build`, wheel et sdist puis installations isolées | PASS |
| Package | `py.typed`, LICENSE MIT, `dependencies=[]`, version `0.1.0a2` | PASS |
| M1-M3 | modèles, Interaction JSON v1 et Inference JSON v1 toujours couverts et non modifiés | PASS |
| Release | aucune autorisation de tag / publication | NO-GO release, décision distincte |

Les **967 tests** sont le total **cumulatif** du dépôt, et non 967 tests L4.5 ni 967 tests P4 isolés. La couverture de 96 % s'applique au domaine instrumenté, sur Python 3.11. Les installations wheel/sdist ont été démontrées par les étapes de la même CI.

## 2. Traçabilité des quarante recettes P4

La matrice [PHASE_4_TRACEABILITY.md](PHASE_4_TRACEABILITY.md) référence P4-AC-001..040, leur ADR, exigences, fichiers de tests, PR et gates :

- **001..008 / G1 :** définitions Tool, ToolSchema, ToolChoice, unicité, immutabilité et validation.
- **009..016 / G2 :** identité ToolCallId, raw/parsed, validation locale et corrélation sans résultat orphelin ou dupliqué.
- **017..024 / G3 :** formats de réponse, JSON/schema, preuve VALID/INVALID/UNKNOWN, capacité déclarée et redaction.
- **025..032 / G4 :** composition séparée de M3, Tooling JSON v1, round-trip, compatibilité Model/Interaction/Inference v1.
- **033..040 / G5 :** absence de SDK/exécution, credentials non requis, exemple 17, snippet README exécutable, packaging, schémas hostiles, secret en repr/erreurs et traçabilité complète.
- **038/039 :** déjà couverts à G4 et revérifiés dans les tests G5.

Tous les tests applicables ont été exécutés avec succès dans la suite cumulative du SHA qualifiant. La traçabilité ne doit pas être confondue avec une attestation de sécurité de production.

## 3. Revue d'intégration et frontières non franchies

- Les modules `domain.tooling`, `domain.structured_output` et `domain.tooling_inference` restent des contrats **purs** ; les outils sont déclarés, jamais exécutés.
- `ToolCallOutput` n'est pas inventé comme `TextOutput`, `ToolResult` n'est jamais créé par le domaine.
- Tooling JSON v1 possède sa propre enveloppe strictement typée et versionnée ; aucune extension implicite ni conversion à perte des JSON v1 M1/M2/M3.
- Validation P4-JSON-1 **limitée**, hors réseau, sans promesse de JSON Schema Draft 2020-12 complet, sans parser de JSON textuel hostile intégré.
- `raw` distinct de `parsed`, `ABSENT` distinct de JSON null et `UNKNOWN` distinct de `VALID`.
- La réponse du README et les résultats de l'exemple 17 sont **illustratifs**, sans modèle ni provider réellement appelé.
- Documentation architecture et concepts, contrat API, README, ROADMAP, CHANGELOG et M4 precheck sont présents dans le dépôt.

**Amélioration de l'archivage G5 :** le workflow de CI ajoute le garde `--cov-fail-under=95` afin que le seuil de couverture devienne **bloquant** pour les commits futurs. Cette modification est postérieure au SHA applicatif ci-dessus; sa CI devra être revérifiée sur le SHA d'archivage. Elle n'est pas faussement attribuée au commit `aad2656c`.

## 4. Gouvernance et réserves

| Réserve | Constat vérifié | Conséquence |
|---|---|---|
| #22 Protection main | GitHub API `protected=false`, `/rulesets=[]`, issue [#22](https://github.com/tawounfouet/pyllmkit/issues/22) OPEN | Pas de protection obligatoire attestée, bloquant pour publication |
| Revue humaine | 0 GitHub review `APPROVED` soumise sur PR #48 | Accord du propriétaire explicite en conversation, pas de revue indépendante inventée |
| #35 Release | issue [#35](https://github.com/tawounfouet/pyllmkit/issues/35) OPEN | NO-GO publication, pas de bump/tag |
| #36 Provider boundary | issue [#36](https://github.com/tawounfouet/pyllmkit/issues/36) OPEN | Hors périmètre M4, aucun adapter HTTP/SDK |
| Parsing JSON texte | détection des doublons, limites et sécurité d'un JSON de provider non fournie dans le noyau | A traiter à la future frontière application |
| Couverture et audit | 96 % n'est pas 100 %, les guards ne prouvent pas une absence universelle de vulnérabilités | GO limité au domaine hors ligne qualifié |

Ces réserves ne sont pas masquées, ne constituent pas un GO de publication et restent ouvertes jusqu'à des preuves distinctes.

## 5. Verdict P4-G5

**P4-G5 = GO TECHNIQUE AVEC RÉSERVES** : L4.5 est intégré et qualifié, avec 40 recettes tracées et CI de `main` verte. Cette décision **autorise la revue indépendante M4 GO/NO-GO**, non sa conclusion automatique.

**M4 et release demeurent des décisions distinctes.** Le présent PV est archivé après qualification. Contrôler et mentionner séparément la CI de son commit d'archivage dans la PR.
