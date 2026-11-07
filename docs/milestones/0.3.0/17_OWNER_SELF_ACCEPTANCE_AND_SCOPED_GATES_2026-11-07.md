# PyLLMKit v0.3.0 - Décision du mainteneur unique et gates à périmètre limité

> Date de décision : 2026-11-07  
> Autorité de décision : propriétaire, développeur et mainteneur unique de PyLLMKit  
> Nature : **acceptation du propriétaire (self-approval)**, sans revue tierce  
> Baseline technique qualifiée : `main@125b2e67d55954e949c9a836f7ceed8f7adaac2b`  
> CI : [#42322797692](https://github.com/tawounfouet/pyllmkit/actions/runs/42322797692), 3/3 jobs Python SUCCESS  
> Décision de release G9 : **non prise dans ce document**

## 1. Instruction du propriétaire

Le propriétaire a déclaré explicitement dans la conversation du projet le 2026-11-07 : **« je suis le seul dev et mainteneur et je valide donc tout la preuve j'ai tout testé en local »**.

Interprétation appliquée au dépôt : le propriétaire **accepte personnellement** la conception, les contrats et la qualification technique **dans le périmètre documenté**, et renonce à l'obligation de revue humaine distincte de lui-même pour PyLLMKit. La décision est rapportée dans le présent dossier ; elle ne constitue **ni une approbation GitHub d'un autre reviewer ni une signature cryptographique**.

L'issue [#105](https://github.com/tawounfouet/pyllmkit/issues/105) est fermée en `not_planned` (revue tierce non exigée), et non en `completed`. Le propriétaire avait également écarté l'obligation de protéger `main` dans [#22](https://github.com/tawounfouet/pyllmkit/issues/22), également `not_planned`.

## 2. Provenance des preuves

| Objet | Type de preuve | Vérification obtenue |
|---|---|---|
| Tests locaux « tout testé » | **Attestation du propriétaire** | Déclaration reçue, sans rapport, commande, environnement, résultats détaillés ou SHA local joints. Les tests locaux ne sont pas contre-vérifiés ici. |
| CI de `main` au SHA exact | **Preuve GitHub vérifiée** | [Run #42322797692](https://github.com/tawounfouet/pyllmkit/actions/runs/42322797692) : succès des jobs `validate (3.11)`, `validate (3.12)`, `validate (3.13)`. |
| Socle six providers text-only hors ligne | **Tests hermétiques** | 2 825 tests pytest et 752 cas de conformance PASS par version Python lors de la qualification du code, 27 familles avec minima identiques dans le reporter et le validateur S8. |
| Conformité réseau réel | **Non établie** | Les mocks et la CI ne vérifient pas le pair IP connecté, DNS/TLS, SSRF/rebinding ou budgets fournisseurs en environnement hostile. |
| Revue externe indépendante | **Non réalisée** | Exception acceptée par le propriétaire, sans prétendre à une indépendance. |

Les rapports [15](15_CONTRACT_CONFORMANCE_AND_INDEPENDENT_REVIEW_DOSSIER_2026-11-07.md) et [16](16_COMPATIBILITY_AND_MIGRATION_PROPOSAL_2026-11-07.md) restent les dossiers techniques initiaux et sont **historiques** : leur statut « pending independent review » est remplacé **pour la politique de revue** par cette décision explicite, pas par une preuve de revue tierce.

## 3. Ratification de contrat par le propriétaire

Le propriétaire ratifie pour la **baseline de développement text-only offline** :

1. Les huit décisions d'[ADR-059](../../adr/ADR-059-multi-provider-conformance-boundary.md) : frontières Protocols/adapters, périmètre texte strict, support explicite des capabilities, erreurs code-only, identité/cycle de vie, parité canonique sync/async, provenance des scénarios et gates indépendants.
2. Le profil `text_only_v1` de [01_MULTI_PROVIDER_CONTRACT_V1.md](01_MULTI_PROVIDER_CONTRACT_V1.md), avec les refus explicites pour rôles, contenus ou paramètres non représentables.
3. La logique de compatibilité et les limitations de migration décrites dans [16](16_COMPATIBILITY_AND_MIGRATION_PROPOSAL_2026-11-07.md), comme **guide de développement** à préciser avant une distribution stable.
4. La politique de maintenance *mainteneur unique* : pas de ruleset obligatoire ni de reviewer tiers, mais conservation de preuves CI exact-SHA et de la décision de publication.

**Ce qui n'est pas ratifié :** fonctionnement universel de tous les modèles du catalogue, sécurité live, parité multimodale, facturation fournisseur réelle, réussite de scénarios qui n'ont pas été testés, ou publication de version stable.

## 4. Registre des gates après l'acceptation du propriétaire

| Gate | Décision du propriétaire | Preuve qualifiée / réserve non levée |
|---|---|---|
| **G0** | **OWNER ACCEPTED - OFFLINE** | ADR-059 approuvé comme décision de conception text-only. |
| **G1** | **OWNER ACCEPTED - OFFLINE** | `text_only_v1` approuvé comme contrat normatif de la baseline. |
| **G2** | **OWNER ACCEPTED WITH EXCEPTIONS - OFFLINE** | 752 PASS sur 27 familles ; registre exhaustif des scénarios *non exécutés*, N/A/UNSUPPORTED/BLOCKED encore à compléter. |
| **G3** | **OWNER ACCEPTED WITH EXCEPTIONS - OFFLINE** | Normalisation d'erreurs/redaction en mocks ; revue transversale logs, traces et chaînes d'exceptions non démontrée. |
| **G4** | **OWNER ACCEPTED WITH EXCEPTIONS - OFFLINE** | Paramètres/roles/usage/finish testés ; traçabilité exhaustive alias, RunId/attemptId et préconditions P0 non établie. |
| **G5** | **OWNER ACCEPTED WITH EXCEPTIONS - OFFLINE** | Lifecycle sur transports simulés ; synchronisation stream live sans hard deadline reste **fail-closed**. |
| **G6** | **OWNER ACCEPTED - PREFLIGHT OFFLINE ONLY** | Test egress hermétique validé ; **NO-GO live/production** pour DNS/peer IP/TLS, SSRF, budgets et canaris non qualifiés. |
| **G7** | **OWNER ACCEPTED WITH EXCEPTIONS - DEV DOCS** | Guide compatibilité/migration rédigé ; comparaison ABI/API et preuve de migration de consommateurs à formaliser avant distribution stable. |
| **G8** | **OWNER ACCEPTED WITH EXCEPTIONS - OFFLINE** | CI vérifiée sur SHA exact, 3/3 environnements ; absence de revue tierce acceptée par owner, pas de gate global « live ». |
| **G9** | **PENDING RELEASE DECISION** | Version candidate/stable, changelog, artefacts, provenance, cible de distribution et autorisation explicite restent distincts. |

Le mot « accepté » ici est un **arbitrage de risque et de périmètre du propriétaire**. Il ne convertit pas une absence de test ou de preuve en statut technique « PASS ». Les exceptions doivent rester visibles dans l'issue de release [#103](https://github.com/tawounfouet/pyllmkit/issues/103).

## 5. Politique de publication et suites

- Tout nouveau tag doit viser un **SHA exact de `main` ayant passé la CI après le changement de version**.
- Une version stable `0.3.0` ne doit promettre que le sous-ensemble de fonctionnalités explicitement qualifié et documenté, avec ses restrictions claires.
- Les demandes de réseau réel / dépenses API sont **séparées** des tests hermétiques ; aucune campagne live n'est déclenchée ici.
- Avant `v0.3.0` : décider du bump SemVer, compléter les notes de migration et vérifier les wheel/sdist produites au SHA versionné.
- Tag Git, GitHub Release et publication PyPI sont **des opérations distinctes** ; l'attestation de validation locale ne vaut pas, à elle seule, une instruction d'exécution de chacun de ces canaux.

## 6. Traçabilité

- Owner exception governance : [#22](https://github.com/tawounfouet/pyllmkit/issues/22) clôturée `not_planned`.
- Owner exception third-party review : [#105](https://github.com/tawounfouet/pyllmkit/issues/105) clôturée `not_planned`.
- Suivi de release : [#103](https://github.com/tawounfouet/pyllmkit/issues/103) reste ouvert.
- Dossier original S0-S9 : [14](14_S0_S9_FUNCTIONAL_CLOSURE_AUDIT_2026-11-06.md) demeure historique.
