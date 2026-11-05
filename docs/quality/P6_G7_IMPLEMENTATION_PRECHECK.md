# P6-G7 - Integration & Quality: précheck de candidature

> **Précheck historique de candidature.** La qualification actuelle est consignée dans [`P6_G8_GATE_REVIEW.md`](P6_G8_GATE_REVIEW.md) et dans la revue finale [`M6_GATE_REVIEW.md`](M6_GATE_REVIEW.md). Les cases « pending » ci-dessous représentent l'état à la création du document, pas l'état actuel.


- Date : 2026-11-05
- Statut : CANDIDAT EN PR, PAS DE GO sur main.
- Dépendance : PR #59 (P6-G0) -> PR #60..#65 (L6.1..L6.6) -> L6.7.
- Version source : 0.1.0a2 ; cible 0.1.0b2 non autorisée à publication.

## Livrables L6.7

- Exemples hors ligne `examples/23_*.py` à `examples/28_*.py` pour domain, registry, search, capabilities, selection et offline merge.
- Test d'intégration P6-AC-049..056 couvrant ports, architecture, rétrocompatibilité, sécurité des erreurs, traçabilité et métadonnées de distribution.
- `docs/quality/PHASE_6_TRACEABILITY.md` : 56 identifiants AC-001..056 distincts observés dans sept fichiers de tests.
- `docs/api/registry-discovery.md` : contrats, exemples et limites réelles du noyau.
- CI étendue : exemples 23..28 depuis checkout, wheel et sdist sous Python 3.11/3.12/3.13.

## Conditions techniques à vérifier sur SHA exact

- [ ] Ruff, mypy strict et tests cumulatifs M1-M6 sans erreur.
- [ ] Couverture de branches globale `pyllmkit.domain` >= 95 % dans chaque job.
- [ ] Build wheel/sdist, clean installs et exemples 01..28.
- [ ] Conformité avec ADR-039..048, absence de dépendance provider dans le domaine.
- [ ] Vérification de l'absence de publication et d'augmentation de version.

## Conditions de qualification officielles non satisfaites

- [ ] Revue de conception et acceptation des ADR sur la PR #59.
- [ ] Fusion ordonnée des PR #59..#65 et validation CI push/main sur chaque SHA exact.
- [ ] Fusion de L6.7 et validation CI push/main de son propre SHA.
- [ ] Revue finale M6 distincte avec décision GO/NO-GO et réserves documentées.
- [ ] Protection GitHub main (#22), revue tierce indépendante et frontière provider (#36) à traiter ; publication (#35) reste NO-GO.

## Limites explicites

Le snapshot atomique InMemory et la vérification optimiste de révision sont prévus pour un processus en usage séquentiel ; aucune transaction multi-processus, sûreté multi-thread générale ou persistance n'est promise. La source statique attend des objets Python déjà typés ; aucun parseur de fichiers inconnus ni découverte réseau n'est livré. AVAILABLE est déclaratif et pas une mesure de santé. `repr=False` réduit la divulgation accidentelle mais n'est pas une mesure de sécurité end-to-end.

Ce précheck ne déclare aucun gate GO, ne constitue pas une revue GitHub tierce et n'autorise pas de release.
