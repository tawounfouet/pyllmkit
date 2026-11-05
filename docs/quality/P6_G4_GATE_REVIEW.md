# PyLLMKit P6-G4 - Gate Review - L6.4 Effective Capability & Limits

- Date : 2026-11-05
- Gate : P6-G4
- PR intégrée : [#63](https://github.com/tawounfouet/pyllmkit/pull/63)
- SHA de qualification exact sur `main` : [`3bdfd84df9c414e755d6dd939eca0a15b99d769d`](https://github.com/tawounfouet/pyllmkit/commit/3bdfd84df9c414e755d6dd939eca0a15b99d769d)
- CI post-merge de `main` : [GitHub Actions #42123414949](https://github.com/tawounfouet/pyllmkit/actions/runs/42123414949) - **completed / success**
- Précondition : P6-G3: main@9f3edaab

## Périmètre livré et contrôlé

CapabilityResolver, contraintes conservatrices et LimitResolver avec preuves par couche.

## Preuves et invariants

- UNSUPPORTED veto, UNKNOWN séparé de NOT_APPLICABLE prouvé
- PARTIAL/EMULATED disjoints avec trace source et refus des conflits
- Bornes numériques restrictives; None non inventé en zéro

- Couverture des recettes : P6-AC-025..032.
- Matrice CI vérifiée : `validate (3.11)`, `validate (3.12)`, `validate (3.13)` = **3/3 SUCCESS** sur le SHA qualifiant.
- Logs Python 3.11 : **1137 tests cumulatifs passés**, couverture du domaine avec branches **96.50 %**, seuil requis 95 %.
- Statut de merge : PR #63 **MERGED** sur main.

## Gouvernance et portée du verdict

**Verdict : GO TECHNIQUE AVEC RÉSERVES**, pour le périmètre P6 hors réseau. Il est fondé sur l'autorisation explicite du propriétaire donnée le 2026-11-05, une revue technique assistée et la CI push/main au SHA indiqué. Ce verdict ne prétend **pas** à une approbation par un reviewer GitHub indépendant ; aucune review indépendante n'est enregistrée sur la PR de ce gate. `main` a été vérifiée sans protection effective (`protected=false`, règles `[]`). Les issues #22 (protection), #35 (release) et #36 (frontière providers) restent à instruire. **Release, tag, GitHub Release et publication PyPI : NO-GO.** Le code reste en version `0.1.0a2`, la cible `0.1.0b2` n'est pas distribuée.

La CI de ce gate ne prouve pas la sûreté d'un fournisseur LLM réel, d'une transaction distribuée, d'un déploiement productif, ni une revue externe humaine. Les procès-verbaux de gate sont des preuves de jalons de code; le bilan M6 doit encore être traité séparément.
