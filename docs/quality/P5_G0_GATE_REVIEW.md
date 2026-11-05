# P5-G0 Architecture Gate Review - GO technique avec réserves

- Date de vérification : 2026-11-05
- Référentiel : tawounfouet/pyllmkit
- PR d'architecture : [#51](https://github.com/tawounfouet/pyllmkit/pull/51)
- SHA main qualifié : [47538ce470e5158bcda6a4166da4a80ca380100c](https://github.com/tawounfouet/pyllmkit/commit/47538ce470e5158bcda6a4166da4a80ca380100c)
- CI push/main : [#42100071595](https://github.com/tawounfouet/pyllmkit/actions/runs/42100071595), completed / success
- Python : jobs validate (3.11), validate (3.12), validate (3.13) tous success.
- Décision : P5-G0 GO TECHNIQUE AVEC RÉSERVES, uniquement pour commencer L5.1; aucun code P5 qualifié à G0.
- Publication : NO-GO, cible 0.1.0b1 indicative et version actuelle 0.1.0a2.

## Contrats adoptés

ADR-030..038 : streaming non-agrégat, événements typés, séquences contiguës à partir de 0, run correlation, transitions et cancellation terminale distincte, ToolCallDelta canonique, reducer pur, sync/async séparé, codec Streaming JSON v1 indépendant, usage partiel et budgets explicites.

## Réserves

- Issue #22 : protection main non effective à M4; aucune enforcement inférée par une CI verte.
- Issue #35 : release et publication non autorisées.
- Issue #36 : frontière providers en attente; aucun adapter ne peut être présenté comme fourni par M5.
- Aucune revue GitHub tierce indépendante démontrée; approbation technique portée par la demande d'implémentation du propriétaire.

## Portée des preuves

La CI #42100071595 valide la baseline documentaire G0, pas une implémentation P5. Les lots P5-G1..G6 nécessitent leurs propres PR et CI sur le SHA main qualifiant.
