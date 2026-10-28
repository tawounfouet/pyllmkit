# M1 - Domain Foundations Qualified - Procès-verbal de qualification

**Décision M1 : GO - FONDATIONS QUALIFIÉES**
**Date de décision technique : 2026-10-28**
**Portée : Phase 1 - P1-BOOT, L1.1 Model Domain, L1.2 Capabilities & Modalities, L1.3 Quality & Testing**
**Version candidate : `0.1.0a1` (PEP 440 alpha ; NON PUBLIÉE)**
**SHA source qualifié sur `main` : `4aaf4c91e97ff7dfc3d0f2c6164c3cd88fe2923a`**
**CI principale : [GitHub Actions #40638326259](https://github.com/tawounfouet/pyllmkit/actions/runs/40638326259) - SUCCESS**
**Validation : audit et décision technique effectués sous instruction explicite du propriétaire de terminer M1 ; aucune signature humaine indépendante ni autorisation de publication n'est prétendue.**

Le présent document enregistre un **GO du jalon de réalisation M1**, non une publication du package. La validation est fondée sur un commit exact de `main` ayant passé les mêmes contrôles après fusion des PR, et sur les décisions d'architecture enregistrées. Le commit documentaire qui archive cette décision fera lui aussi l'objet de la CI ; il ne change pas les primitives.

## Gates internes

| Gate | Éléments de preuve | Décision |
|---|---|---|
| G0 - Architecture Ready | ADR-001 à ADR-007 ACCEPTED, API publique racine et sous-packages, schéma v1 gelé, licence MIT | **PASS** |
| G1 - Model Domain Ready | PR #2 fusionnée, entités Model/ModelArtifact et VO, tests négatifs/identités | **PASS** |
| G2 - Capability & Modality Ready | PR #3 fusionnée, niveaux de support, UNKNOWN, entrées/sorties, tests | **PASS** |
| G3 - Quality Ready | PR #4 fusionnée, tests hors réseau, garde-fous, mypy/Ruff, exemples, wheel/sdist | **PASS** |
| **M1 - Domain Foundations Qualified** | **G0 + G1 + G2 + G3 ; exact-SHA main CI** | **GO** |

## Résultats observés sur le commit source intégré

| Contrôle | Résultat |
|---|---|
| Python 3.11 | SUCCESS |
| Python 3.12 | SUCCESS |
| Python 3.13 | SUCCESS |
| Tests pytest | **137 passed, 0 failed** |
| Couverture avec branches | **89 % combiné** (aucun seuil contractuel imposé) |
| Ruff | PASS |
| mypy strict | PASS, 17 fichiers source |
| Tests négatifs d'invariants | PASS |
| AC-001 / 002 / 004 / 005 / 018(P1) | PASS selon traçabilité |
| TEST-MOD02 IMAGE != VISION | PASS |
| Tests offline (scope fixture) | PASS ; pas de sandbox réseau exhaustive |
| Exemplaires Python | PASS, 3 exemples |
| Wheel | BUILD + clean install PASS |
| Sdist | BUILD + clean install PASS |
| Dépendance SDK obligatoire | Aucune |
| Architecture | Import guard + tests négatifs PASS |

**Trace CI :** `https://github.com/tawounfouet/pyllmkit/actions/runs/40638326259`
**Commit qualifié :** `4aaf4c91e97ff7dfc3d0f2c6164c3cd88fe2923a`

## Décisions formalisées

- `ADR-001` à `ADR-006` sont ACCEPTED pour la portée de l'alpha, avec limitations et réserves inscrites dans les ADR individuelles.
- `ADR-007` choisit MIT comme licence de projet pour la première alpha, sous réserve d'un contrôle de titularité et contributions avant distribution publique.
- `pyllmkit.domain` est un contrat d'import public en plus des sous-packages.
- Les champs du writer JSON `schema_version=1` sont figés ; les anciens snapshots de développement sont lisibles par le lecteur actuel, pas nécessairement l'inverse ; migration pour futures ruptures.

## Intégration des lots

- [x] [PR #1](https://github.com/tawounfouet/pyllmkit/pull/1) - P1-BOOT - merged
- [x] [PR #2](https://github.com/tawounfouet/pyllmkit/pull/2) - L1.1 - merged
- [x] [PR #3](https://github.com/tawounfouet/pyllmkit/pull/3) - L1.2 - merged
- [x] [PR #4](https://github.com/tawounfouet/pyllmkit/pull/4) - L1.3 - merged
- [x] [PR #5](https://github.com/tawounfouet/pyllmkit/pull/5) - M1 audit - merged
- [x] [PR #6](https://github.com/tawounfouet/pyllmkit/pull/6) - G0 décisions - merged
- [x] La CI a été exécutée sur le `main` résultant, pas uniquement sur les feature branches.

## Réserves NON bloquantes pour M1

- Le pourcentage de couverture n'a pas fait l'objet d'un seuil de gouvernance. 89 % est une mesure observée, pas un seuil garanti.
- Aucun provider, Deployment, Endpoint, Registry, InferenceRun, streaming ou tool execution n'est validé par M1.
- Les garde-fous AST et pytest sont ciblés ; ils ne remplacent pas un audit de sécurité ou un sandbox OS.
- La titularité des contributions et les obligations de distribution feront l'objet d'une vérification distincte **avant publication**.
- Le travail sur les schémas d'illustration P0 reste un chantier documentaire distinct, sans incidence sur les invariants du code qualifié.

## Suite

**M1 : GO. Phase 1 : TECHNIQUEMENT TERMINÉE.**
**Publication `v0.1.0a1` : NON AUTORISÉE PAR CETTE DÉCISION, NON EFFECTUÉE.**
Prochaine étape projet : décider séparément de la publication alpha, puis démarrer `0.1.0a2 - Interaction Primitives` selon `ROADMAP.md`.

La CI du commit documentaire archivant ce procès-verbal doit encore passer après fusion de la PR d'archive ; l'état final sera vérifié et communiqué séparément.
