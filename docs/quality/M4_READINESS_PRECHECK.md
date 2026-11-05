# PyLLMKit - M4 Readiness Precheck - Clôturé après revue finale

> **Date :** 2026-11-05.
> **Statut : TERMINÉ / M4 GO TECHNIQUE AVEC RÉSERVES pour le domaine hors ligne.**
> **Procès-verbal faisant autorité :** [M4_GATE_REVIEW.md](M4_GATE_REVIEW.md), revue indépendante des 14 causes de NO-GO.
> **SHA qualifiant :** [main@92874b2e97bcc130279e244bf1000c65a939d7e5](https://github.com/tawounfouet/pyllmkit/commit/92874b2e97bcc130279e244bf1000c65a939d7e5), [CI #42093041970](https://github.com/tawounfouet/pyllmkit/actions/runs/42093041970) SUCCESS.
> **Version déclarée :** 0.1.0a2. **Release NO-GO**, décision indépendante.

## 1. Synthèse de qualification

La séquence L4.1..L4.5 est intégrée à main, avec P4-G0..G5 techniquement qualifiés. L4.5 a été fusionné via [PR #48](https://github.com/tawounfouet/pyllmkit/pull/48), qualifié sur [main@aad2656c](https://github.com/tawounfouet/pyllmkit/commit/aad2656cbe1753dac709bb28b228ba22ecca44a2) et [CI #42092202193](https://github.com/tawounfouet/pyllmkit/actions/runs/42092202193). Le dossier P4-G5 et la couverture minimale obligatoire ont ensuite été intégrés via [PR #49](https://github.com/tawounfouet/pyllmkit/pull/49) puis qualifiés sur **main@92874b2e**, CI **#42093041970**.

La revue M4 est **une décision séparée**, réalisée après cette qualification. Elle constate 967 tests cumulatifs, 95,80 % de couverture de branches (96 % affichés), Python 3.11/3.12/3.13 3/3, Ruff PASS, mypy strict PASS, wheel/sdist et exemples offline 13..17 exécutés. Le nouveau seuil de couverture 95 % est effectivement bloquant en CI.

## 2. Matrice finale de readiness

| Contrôle | Condition de GO | Conclusion |
|---|---|---|
| Architecture | ADR-022..029 ACCEPTED par le propriétaire | PASS G0/M4 |
| Déclaration d'outils | Tool/ToolSchema/Choice, catalogue cohérent, sans handler | PASS G1/M4 |
| Appels et résultats | ToolCallId, raw/parsed, corrélation, duplicats rejetés | PASS G2/M4 |
| Sorties structurées | Formats, validation réelle, UNKNOWN/VALID/INVALID | PASS G3/M4 |
| Composition M3 | Wrapper P4 distinct, aucun ToolCallOutput converti en TextOutput | PASS G4/M4 |
| Sérialisation | Tooling JSON v1 strict, compatibilité Model/Interaction/Inference v1 | PASS G4/M4 |
| Acceptation | P4-AC-001..040 tracés et exécutés | PASS G5/M4 |
| Documentation | Architecture, concepts, API, README, exemples copiables | PASS G5/M4 |
| Offline | Exemples 13..17, aucun credential ni exécuteur requis | PASS G5/M4 |
| Packaging | Build wheel/sdist, installs propres, py.typed, MIT, 0.1.0a2 | PASS G5/M4 |
| CI qualité | 3/3 Python, 967 tests, 95,80 %, seuil >=95 bloquant | PASS M4 |
| Sécurité du domaine | Tests rejets schémas hostiles, pas de secret dans repr/erreurs testés | PASS périmètre qualifié |
| Gouvernance | SHAs exacts, owner, réserves #22/#35/#36 documentées | PASS traçabilité ; réserves ouvertes |
| Causes NO-GO | Les 14 familles examinées séparément dans le PV M4 | Aucune cause constatée dans ce périmètre |

## 3. Limites et réserves

- Main protected=false, rulesets=[], issue [#22](https://github.com/tawounfouet/pyllmkit/issues/22) OPEN : aucune enforcement de PR/CI/reviews revendiquée. Cette réserve bloque la publication.
- Absence d'approbation GitHub tierce : l'autorisation du propriétaire dans la conversation est réelle, mais n'est pas une review humaine indépendante.
- [#35](https://github.com/tawounfouet/pyllmkit/issues/35) release OPEN : ni tag, ni release, ni upload PyPI autorisé dans cette opération.
- [#36](https://github.com/tawounfouet/pyllmkit/issues/36) provider boundary OPEN : pas de parser textuel distant, transport, SSRF, contrôle des clés provider ou SDK.
- P4-JSON-1 n'implémente pas JSON Schema Draft 2020-12 au complet.
- Aucun audit sécurité exhaustif du futur runtime, aucun agent, aucune exécution d'outil, aucun streaming effectif qualifiés en M4.

## 4. Décision

**M4 est TECHNIQUEMENT QUALIFIÉ AVEC RÉSERVES**, pour les contrats de domaine agnostiques et hors ligne décrits dans le [PV final](M4_GATE_REVIEW.md). Le précheck est fermé. La diffusion et la Phase 5 sont des décisions futures et séparées.

L'archive documentaire M4 doit encore passer une CI sur son propre commit main avant d'être déclarée conservée dans la branche de référence.
