# PyLLMKit - M4 Readiness Precheck

> Date de préparation : 2026-11-05.
> **Statut : PRECHECK PENDING, M4 NO-GO de qualification finale.**
> Cette checklist ne remplace ni P4-G5 (integration & quality) ni le futur `M4_GATE_REVIEW.md`.
> Release : NO-GO, autorisation séparée.

## 1. Qualification disponible

P4-G0..G4 sont documentés, techniquement qualifiés avec réserves sur leurs SHAs respectifs. La dernière preuve de code intégrée est [main@ab0257a0](https://github.com/tawounfouet/pyllmkit/commit/ab0257a0a9a08f2320b580340ba84c92609bbfc0), [CI #42089506022](https://github.com/tawounfouet/pyllmkit/actions/runs/42089506022) SUCCESS, 954 tests cumulatifs et 96 % de couverture de branches sur Python 3.11, matrix 3/3, Ruff/mypy strict PASS.

L4.5 et P4-G5 sont encore à qualifier sur un nouveau commit `main`. **Ne pas convertir la CI de branche ou la préparation documentaire en M4 GO.**

## 2. Critères M4 à réexaminer après G5

| Contrôle | Condition de qualification | État présent |
|---|---|---|
| Architecture | ADR-022..029 ACCEPTED, aucune exécution d'outil dans le domain | PASS G0..G4 |
| Domaine | Tools, calls, results, sorties, identité et immutabilité | PASS G1..G3 |
| Codecs | Tooling JSON v1 séparé, non-régression Model/Interaction/Inference v1 | PASS G4 |
| Support capabilities | UNKNOWN/EMULATED/PARTIAL ne deviennent pas NATIVE | PASS G4 |
| Acceptation | P4-AC-001..040 tracés et exécutés sur SHA main qualifiant | PENDING G5 |
| Docs | Architecture, concepts, API, README, snippets réellement exécutables | PENDING G5 |
| Exemples | 13..17 hors ligne, sans credentials | PENDING G5 |
| Packaging | `py.typed`, license, metadata, wheel/sdist isolés, pas de provider SDK | PENDING G5 |
| Matrice CI | Python 3.11/3.12/3.13, Ruff, mypy strict, pytest, >=95% de couverture cible | PENDING G5 |
| Sécurité | Pas de secret en erreur/repr, valeurs dangereuses rejetées | PENDING G5 |
| Gouvernance | Sha exact, review et réserves #22/#35/#36 documentées | PENDING G5 |

## 3. Critères de NO-GO transversaux

- P4 qui exécute un handler ou invoque un provider depuis le domaine.
- IDs de `ToolCall` perdus, résultat orphelin accepté, `raw` confondu avec `parsed`.
- Schéma ou capacité UNKNOWN présenté comme validé ou NATIVE.
- Codec v1 historique modifié ou silent downgrade de P4 vers `TextOutput`.
- Documentation ne correspondant pas aux APIs effectivement livrées, snippets faux.
- Tests/CI incomplets ou couverture sans décision de dérogation.
- Provenance de CI non liée au SHA intégré dans `main`.
- Publication, tag, bump ou release déclenché sans décision spécifique.

## 4. Réserves de gouvernance

- [#22](https://github.com/tawounfouet/pyllmkit/issues/22) : protection `main` non enforced, signalée par l'API GitHub `protected=false`.
- [#35](https://github.com/tawounfouet/pyllmkit/issues/35) : politique de version/release ouverte.
- [#36](https://github.com/tawounfouet/pyllmkit/issues/36) : boundary providers futur hors M4.
- Aucune revue indépendante GitHub APPROVED constatée pour les gates précédents.

## 5. Décision attendue

Après P4-G5, produire une revue séparée `M4_GATE_REVIEW.md` avec verdict GO / NO-GO, preuves exactes sur `main`, réserves et décision de release explicitement distincte. Ne rien publier automatiquement.
