# PyLLMKit - M5 Streaming Qualified - Revue finale GO/NO-GO

> **Date : 2026-11-05.**
> **Décision : GO TECHNIQUE AVEC RÉSERVES**, exclusivement pour le **Streaming Domain hors réseau** de PyLLMKit.
> **Autorité :** demande explicite du propriétaire du projet de qualifier, valider et fusionner L5.6 puis la revue finale M5.
> **Baseline qualifiante indépendante sur main :** [`e733264cf914d1ada33dbd76df932102139533a4`](https://github.com/tawounfouet/pyllmkit/commit/e733264cf914d1ada33dbd76df932102139533a4).
> **CI exacte de la baseline :** [GitHub Actions #42104049873](https://github.com/tawounfouet/pyllmkit/actions/runs/42104049873), completed/success, Python 3.11, 3.12 et 3.13.
> **Version de la distribution déclarée :** `0.1.0a2`. **Objectif `0.1.0b1` non publié.**
> **Décision de release / tag / PyPI : NO-GO.**
> **Revue humaine indépendante GitHub : absente.** Ce rapport ne la remplace pas.

## 1. Objet de la décision

M5 qualifie le noyau agnostique de **description, validation, consommation et réduction de flux structurés LLM hors ligne**. Il valide les événements typés, la corrélation et l'ordre strict, la reconstruction déterministe des fragments texte et des appels d'outils descriptifs, les conventions sync/async, la gestion d'annulation/EOF/usage partiel et un codec Streaming JSON v1 indépendant.

Il ne qualifie pas l'exécution réelle d'un modèle, la connexion HTTP/SSE, la compatibilité d'un SDK, un gestionnaire d'outils, un runtime d'agent, l'authentification, les retries, un stockage durable, le débit en réseau, la sûreté universelle des données non fiables, ni une release publique.

## 2. Preuves observées sur le SHA exact

| Critère | Faits vérifiés | Conclusion |
|---|---|---|
| État de main | HEAD `e733264cf914d1ada33dbd76df932102139533a4` à l'audit de la baseline | PASS |
| L5.6 | PR #57 fusionnée le 2026-11-05 à 20:30 UTC | PASS |
| CI PR finale | #42103866176, SUCCESS au head ff0082c15422b9983580f3680c4a4bda6d5377c3 | PASS |
| CI push/main | #42104049873, SUCCESS au SHA exact `e733264cf914d1ada33dbd76df932102139533a4` | PASS |
| Python 3.11 | Job 127514075434 SUCCESS | PASS |
| Python 3.12 | Job 127514075211 SUCCESS | PASS |
| Python 3.13 | Job 127514075280 SUCCESS | PASS |
| Tests | **1048 passed / 0 failed**, chaque environnement Python ; suite cumulative M1-M5 | PASS |
| Couverture de branches du domaine | **96,08 %** (2707 statements, 75 misses, 1040 branches, 70 partial), seuil CI bloquant 95 % | PASS |
| Lint | Ruff PASS | PASS |
| Typage | mypy strict PASS sur 65 fichiers source | PASS |
| Exemples | 01..22 exécutés en checkout ; 18..22 exécutés également en clean wheel/sdist | PASS |
| Packaging | Build wheel + sdist, installations isolées, `py.typed`, pas de SDK provider obligatoire | PASS |
| Sérialisation | Streaming JSON v1 isolé, traces rejouées et cas hostiles, non-régression Model/Interaction/Inference/Tooling v1 | PASS |
| Recettes P5 | 48 identifiants AC-001..048 présents dans six fichiers d'acceptation, 48/48 uniques | PASS |
| Version/metadata | `pyproject.toml` en 0.1.0a2, `dependencies=[]`, Python >=3.11, MIT | PASS |
| Gouvernance GitHub | Branch `main` protected=false, rulesets=[], issue #22 OPEN | RÉSERVE |
| Revue indépendante | PR #57 : liste reviews vide | RÉSERVE |
| Release | Issue #35 OPEN, pas de publication autorisée | NO-GO release |

La couverture de **96,08 %** est la couverture globale du domaine, branches comprises, et non 96,08 % de toutes les configurations de runtime imaginables. Les 1048 tests sont **cumulatifs**, pas 1048 nouveaux tests P5.

## 3. Provenance des 7 gates

| Gate | Lot | PR | SHA main qualifiant | CI push/main | Décision |
|---|---|---|---|---|---|
| P5-G0 | Architecture | [#51](https://github.com/tawounfouet/pyllmkit/pull/51) | [`47538ce4`](https://github.com/tawounfouet/pyllmkit/commit/47538ce470e5158bcda6a4166da4a80ca380100c) | [#42100071595](https://github.com/tawounfouet/pyllmkit/actions/runs/42100071595) | GO avec réserves |
| P5-G1 | L5.1 Event Model | [#52](https://github.com/tawounfouet/pyllmkit/pull/52) | [`5157425c`](https://github.com/tawounfouet/pyllmkit/commit/5157425c0ebfefd30f00e0e8a91abb419eaa8c37) | [#42100651109](https://github.com/tawounfouet/pyllmkit/actions/runs/42100651109) | GO avec réserves |
| P5-G2 | L5.2 Ordering & Lifecycle | [#53](https://github.com/tawounfouet/pyllmkit/pull/53) | [`9039a1b2`](https://github.com/tawounfouet/pyllmkit/commit/9039a1b2ab981080170faff7cca339a2a799199d) | [#42101437194](https://github.com/tawounfouet/pyllmkit/actions/runs/42101437194) | GO avec réserves |
| P5-G3 | L5.3 ToolCall Delta | [#54](https://github.com/tawounfouet/pyllmkit/pull/54) | [`53a965cc`](https://github.com/tawounfouet/pyllmkit/commit/53a965ccf66e5249becf9b5c82e926b018911898) | [#42102029484](https://github.com/tawounfouet/pyllmkit/actions/runs/42102029484) | GO avec réserves |
| P5-G4 | L5.4 Sync/Async | [#55](https://github.com/tawounfouet/pyllmkit/pull/55) | [`63887110`](https://github.com/tawounfouet/pyllmkit/commit/6388711020cbd835fc812f87f200ca448e7eff7d) | [#42102577288](https://github.com/tawounfouet/pyllmkit/actions/runs/42102577288) | GO avec réserves |
| P5-G5 | L5.5 Streaming JSON v1 | [#56](https://github.com/tawounfouet/pyllmkit/pull/56) | [`6070ca4c`](https://github.com/tawounfouet/pyllmkit/commit/6070ca4c047123f973e113030db7b078e48ccb4b) | [#42103272574](https://github.com/tawounfouet/pyllmkit/actions/runs/42103272574) | GO avec réserves |
| P5-G6 | L5.6 Integration & Quality | [#57](https://github.com/tawounfouet/pyllmkit/pull/57) | [`e733264c`](https://github.com/tawounfouet/pyllmkit/commit/e733264cf914d1ada33dbd76df932102139533a4) | [#42104049873](https://github.com/tawounfouet/pyllmkit/actions/runs/42104049873) | GO avec réserves |

La qualification de P5-G6 repose sur [P5_G6_GATE_REVIEW.md](P5_G6_GATE_REVIEW.md), créé après vérification de la CI de main. La présente revue M5 est **postérieure et indépendante** de cette qualification ; son intégration documentaire en PR devra elle-même passer une CI sur le SHA d'archivage.

## 4. Revue contradictoire de 16 risques de NO-GO technique

Un constat "non constaté" signifie "non observé dans les sources et essais inspectés" et **n'est pas** une garantie universelle.

| # | Cause potentielle de refus | Preuve et analyse | Constat |
|---|---|---|---|
| 01 | Streaming supposé opérationnel avec un fournisseur | Le code et les tests qualifiés portent sur un domaine hors réseau et des fixtures en mémoire. Aucune intégration provider revendiquée. | NON CONSTATÉ dans le périmètre offline |
| 02 | Événement non typé, mutable ou dépourvu de corrélation | StreamEvent, InferenceRunId et validations de type, AC-001..008. | NON CONSTATÉ |
| 03 | Ordre non déterministe, trous ou doublons ignorés | Séquences strictement contiguës depuis 0, run_id exact, tests AC-009..013. | NON CONSTATÉ |
| 04 | Démarrage et transitions incohérents | ResponseStarted unique à 0, automates et refus post-terminal, AC-009/014. | NON CONSTATÉ |
| 05 | EOF ou annulation traité comme succès | INCOMPLETE distinct de COMPLETED, FAILED et CANCELLED, AC-014/015/027/028/043. | NON CONSTATÉ |
| 06 | Texte reconstitué avec pertes ou normalisation implicite | Fragments textuels conservés tels quels et reconstruits dans l'ordre, AC-003/010/016/041. | NON CONSTATÉ |
| 07 | Fragments d'outils mal corrélés ou entrelacés perdus | ToolCallId explicite, progression raw par appel et rejets d'orphelins, AC-017..024/042. | NON CONSTATÉ |
| 08 | Exécution d'outil ou ToolResult inventé par le reducer | ToolCall descriptifs avec ToolArguments raw et parsed absent ; aucun handler, AC-022/023. | NON CONSTATÉ |
| 09 | Usage manquant transformé en zéro ou déclaré final | Usage snapshot, is_final explicite, None distinct de 0, AC-029. | NON CONSTATÉ |
| 10 | Divergence sync/async ou ressources promises libérées à tort | Deux Protocols et parité de consommation, close/aclose explicites, AC-025/026/030/031/041. | NON CONSTATÉ |
| 11 | Streaming JSON mélange les anciens codecs | Enveloppe et schéma versionné indépendants, régressions M1-M4 AC-033..044. | NON CONSTATÉ |
| 12 | Payload, version ou statut terminal falsifié accepté par codec | Champs exacts, replay-validé, rejets d'incohérences, AC-035..039/043/046. | NON CONSTATÉ |
| 13 | Limites non bornées ou exposition triviale de contenu sensible | Budgets 100k événements/8 MiB texte/128 calls/1 MiB raw par call ; tests AC-024/046/047 et repr sans fragments. | NON CONSTATÉ dans les tests ; audit adversarial non exhaustif |
| 14 | CI ou packaging en échec sur main exact | CI #42104049873 SUCCESS, 3 Python, 1048 tests, couverture 96,08 %, Ruff, mypy, exemples 18..22 et wheel/sdist. | NON CONSTATÉ |
| 15 | 48 cas ou ADR manquants sans traçabilité | ADR-030..038 et 48 identifiants de tests présents, PHASE_5_TRACEABILITY.md et 7 gates qualifiés. | NON CONSTATÉ |
| 16 | Release ou approval humain présenté comme acquis sans preuve | Version 0.1.0a2 ; releases non autorisées ; main non protégée et aucune review GitHub PR #57 ; réserves conservées. | NON CONSTATÉ comme fausse revendication ; gouvernance reste incomplète |

**Conclusion de cette grille : aucune cause technique de NO-GO n'a été observée dans le périmètre offline réellement testé.** Les manques de gouvernance et de qualification provider limitent la portée du GO et interdisent de présenter le paquet comme prêt à être publié ou utilisé comme client LLM de production.

## 5. Architecture, patterns et principes de design retenus

| Principe | Évidence M5 | Conséquence |
|---|---|---|
| DDD / SoC | StreamEvent Value Object, InferenceStream Protocol, StreamState de réduction distinct de InferenceRun M3 | Pas de deuxième Aggregate Root d'exécution |
| DIP / Ports & Adapters | Ports sync/async sans SDK provider, dépendances vers les contrats du domaine uniquement | Future implémentation du provider explicite |
| Immutabilité | Dataclasses frozen et progression par fragments persistants | Reconstitution déterministe sans modification du state d'entrée |
| Contrats et invariants | Strict sequence, run correlation, terminalité et budgets | Rejet précoce des événements mal formés |
| API Python idiomatique | Iterator/AsyncIterator, Protocol, Enum, Type hints, mypy strict et tests négatifs | Expérience d'intégration cohérente |
| DRY/KISS/YAGNI | Même reducer sync/async, codec dédié, aucune couche d'agent ni scheduler implicite | Noyau minimal et testable |
| Event semantics | Observations de flux non durables, sans bus ni persistence automatique | Évite de confondre événements de transport, domaine et workflow |

## 6. Réserves explicites et critères avant publication

1. **Gouvernance de main, issue #22 :** `protected=false` et aucune ruleset imposée. Configurer les required checks, reviews et restrictions puis vérifier une enforcement effective ; une CI verte seule ne protège pas main.
2. **Revue humaine indépendante :** aucune review APPROVED sur la PR #57. Prévoir un examen tiers du code et de la sûreté avant distribution externe.
3. **Release, issue #35 :** version `0.1.0a2` inchangée. `0.1.0b1` n'est qu'une cible. Aucune autorisation de tag, build de release signé, TestPyPI ou PyPI.
4. **Frontière provider, issue #36 :** les adapters à venir doivent spécifier parsing JSON texte, SSE/HTTP, schémas natifs, secrets, erreurs, retries, quotas, limites, annulation et nettoyage des ressources.
5. **Données raw et sécurité :** les schémas JSON du domaine transportent volontairement les fragments raw. Les appelants doivent définir les politiques de logging, chiffrement, retention et contrôle d'accès ; `repr=False` n'est pas une mesure de sécurité end-to-end.
6. **Qualité supplémentaire :** la CI est hors réseau, les fixtures ne reproduisent pas tout fournisseur ni toute charge adversariale. Introduire property-based/fuzz tests et benchmarks de mémoire lors des premiers adapters.
7. **Contrats de ressources :** consommation anticipée et `close/aclose` restent sous responsabilité du propriétaire de l'itérateur ; pas de promesse de backpressure transport ou exactement-once distribué.

Ces réserves restent ouvertes et ne sont pas converties silencieusement en décisions de production.

## 7. Verdict et portée de l'autorisation

**M5 = GO TECHNIQUE AVEC RÉSERVES.** Les lots L5.1 à L5.6, les neuf ADR-030..038, les 48 recettes et les sept gates G0..G6 sont qualifiés pour la bibliothèque de domaine Streaming **hors réseau**. La suite admissible est l'étude explicite des prochains adapters et des mesures de gouvernance, sans supposer leur livraison.

**`0.1.0b1` = NO-GO pour publication dans cette opération.** Pas de changement de version, de tag, de release GitHub ou de publication PyPI. La décision de release doit être prise séparément par le propriétaire après les contrôles correspondants.

### Archivage

Ce rapport est établi après la qualification indépendante de `main@e733264cf914d1ada33dbd76df932102139533a4`. Il sera archivé via une PR documentaire dédiée, puis une CI sur le SHA de cette nouvelle fusion devra être vérifiée. Cette future CI ne doit pas être présentée comme déjà réussie au moment de la rédaction.

**Pythos - traçabilité d'exécution :** seuls les commits, PR, tests et contrôles effectivement vérifiés sont déclarés accomplis. Les recommandations et la revue assistée ne valent pas review GitHub tierce.
