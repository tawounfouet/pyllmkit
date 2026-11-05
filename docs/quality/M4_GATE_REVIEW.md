# PyLLMKit - M4 Tooling & Structured Output Qualified - Revue finale GO/NO-GO

> **Date de la décision : 2026-11-05.**
> **Verdict final : GO TECHNIQUE AVEC RÉSERVES, limité au domaine Tooling & Structured Output HORS LIGNE.**
> **Autorité :** propriétaire du projet, demande explicite de finaliser L4.5 et M4, de mener la revue finale et d'intégrer tous les artefacts dans main.
> **SHA qualifiant indépendant de main :** [92874b2e97bcc130279e244bf1000c65a939d7e5](https://github.com/tawounfouet/pyllmkit/commit/92874b2e97bcc130279e244bf1000c65a939d7e5).
> **CI push/main qualifiante du même SHA :** [GitHub Actions #42093041970](https://github.com/tawounfouet/pyllmkit/actions/runs/42093041970) completed/success, Python 3.11/3.12/3.13.
> **Version déclarée :** 0.1.0a2 (source non reversionnée dans cette opération).
> **Décision de release, tag et publication PyPI : NO-GO - AUCUNE AUTORISATION.**
> **Niveau d'assurance :** qualification de contrats de domaine Python hors réseau ; aucune certification sécurité, production, SLA ni preuve d'exécution avec un provider.
> **Revue GitHub humaine indépendante :** ABSENTE ; approbation du propriétaire dans la conversation, sans lui substituer un APPROVED review tiers.

## 1. Périmètre final M4

L'objectif M4 consiste à représenter et valider hors ligne des déclarations d'outils et leurs schémas, des demandes de ToolCall, des ToolResult corrélés, et des formats/sorties structurées avec statuts de validation exacts. Le codec Tooling JSON v1 doit effectuer des round-trips non destructifs dans un espace de schéma distinct. Les API et JSON v1 de M1/M2/M3 restent inchangés. Aucun SDK fournisseur, client LLM, outil exécutable, transport, retry/repair, agent ou streaming effectif n'est livré.

Le verdict couvre les six gates P4-G0..G5, la matrice P4-AC-001..040, les **huit** ADR-022..029 acceptées, les modules livrés, les tests, la documentation, le packaging et leurs preuves CI sur le commit intégré. Les résultats synthétiques de l'exemple 17 ne sont pas des appels LLM réels.

## 2. Qualification technique vérifiée indépendamment

| Dimension | Observation factuelle sur le SHA qualifiant | Verdict |
|---|---|---|
| SHA de main exact | 92874b2e97bcc130279e244bf1000c65a939d7e5 | PASS |
| CI push/main correspondante | [#42093041970](https://github.com/tawounfouet/pyllmkit/actions/runs/42093041970), completed/success | PASS |
| Matrice Python | 3.11 SUCCESS, 3.12 SUCCESS, 3.13 SUCCESS | 3/3 PASS |
| Tests Python 3.11 | **967 passed**, 0 échec ; suite cumulative M1/M2/M3/M4 | PASS |
| Couverture globale branches comprises | **95,80 %** calculés, **96 %** affichés ; 2254 statements, 67 misses, 866 branches, 62 partial | PASS |
| Seuil de couverture effectif | CI utilise --cov-fail-under=95, journal : Required test coverage of 95% reached | PASS |
| Ruff | All checks passed | PASS |
| mypy strict | Success: no issues found in 58 source files | PASS |
| Parcours offline | exemples 01..17 exécutés depuis le checkout ; exemple 17 également depuis wheel et sdist | PASS |
| Packaging | python -m build ; installations propres wheel et sdist avec imports et exemples | PASS |
| Metadata | pyproject.toml version 0.1.0a2, aucune dépendance runtime, Python >=3.11, MIT, py.typed | PASS |
| Contrats Model/Interaction/Inference | codecs v1, test de régression et fitness M3 toujours verts | PASS |
| Recettes P4 | P4-AC-001..040 traçées dans [PHASE_4_TRACEABILITY.md](PHASE_4_TRACEABILITY.md) et exécutées dans la CI | PASS |
| Gouvernance de main | GitHub API protected=false et rulesets=[], issue #22 toujours OPEN | RÉSERVE |
| Revue indépendante GitHub | aucune review APPROVED sur PR #48 / #49 constatée ; owner a explicitement autorisé les fusions | RÉSERVE |
| Distribution | issue #35 OPEN, aucune permission de release ; GitHub Releases renvoyait une liste vide lors de la revue | NO-GO release |

Les **967 tests sont ceux de la suite cumulative**, non 967 tests spécifiques M4. L'évaluation de la qualité au-delà du périmètre exécuté requiert de nouveaux tests/audits et n'est pas extrapolée de cette CI. Le SHA de la future PR qui archive ce PV aura sa propre CI, vérifiée séparément.

## 3. Chaîne de provenance par gate

| Gate / lot | PR implémentation, archivage | SHA applicatif qualifiant de main | CI push/main vérifiée | Décision |
|---|---|---|---|---|
| P4-G0 Architecture | #38, #39 | b66e94e3bcfec9b84fc77fd5e2860612f55827eb | [#42079191595](https://github.com/tawounfouet/pyllmkit/actions/runs/42079191595) | GO avec réserves |
| P4-G1 L4.1 Tool Domain | #40, #41 | 764809cedf4f79866757e14ed92fc9427cc87d56 | [#42082114438](https://github.com/tawounfouet/pyllmkit/actions/runs/42082114438) | GO avec réserves |
| P4-G2 L4.2 Tool Calling | #42, #43 | a7991d9fc6648b280744e7ca461d79c7c2544b60 | [#42084636736](https://github.com/tawounfouet/pyllmkit/actions/runs/42084636736) | GO avec réserves |
| P4-G3 L4.3 Structured Output | #44, #45 | f187fe5278980a84e578a1a3d65ed21d2a117e78 | [#42087094649](https://github.com/tawounfouet/pyllmkit/actions/runs/42087094649) | GO avec réserves |
| P4-G4 L4.4 Composition/Codec | #46, #47 | ab0257a0a9a08f2320b580340ba84c92609bbfc0 | [#42089506022](https://github.com/tawounfouet/pyllmkit/actions/runs/42089506022) | GO avec réserves |
| P4-G5 L4.5 Integration/Quality | #48, #49 | aad2656cbe1753dac709bb28b228ba22ecca44a2 | [#42092202193](https://github.com/tawounfouet/pyllmkit/actions/runs/42092202193) | GO avec réserves |
| G5 archive + seuil bloquant | #49 | **92874b2e97bcc130279e244bf1000c65a939d7e5** | **[#42093041970](https://github.com/tawounfouet/pyllmkit/actions/runs/42093041970)** | BASELINE M4 QUALIFIÉE |

Cette chaîne de preuve a été confrontée aux exécutions GitHub Actions et non déduite uniquement des statuts mentionnés dans les anciens PV.

## 4. Revue indépendante des quatorze causes obligatoires de NO-GO M4

La grille suit exactement les **14 familles** de refus du plan [Phase 4, section 16.1](../04_PYLLMKIT_PHASE_4_IMPLEMENTATION_PLAN.md). « Non constaté » signifie **dans les sources et tests inspectés**, jamais une garantie d'absence universelle.

| # | Critère NO-GO obligatoire | Examen et éléments probants | Constat |
|---|---|---|---|
| **01** | Tool/Call/Result exécute code, réseau ou secrets cachés | API descriptives sans handler/executor ; tests architecture L4.1-L4.4, P4-AC-033/034, aucune dépendance runtime provider | **NON CONSTATÉ** |
| **02** | Identité ToolCallId absente ou ambiguë | ToolCallId explicite, opaque, non vide, identité ToolCall par ID et non par arguments ; P4-AC-009/010 | **NON CONSTATÉ** |
| **03** | Résultat orphelin ou deux résultats finaux acceptés | attach_tool_result, validation de contexte local, refus IDs inconnus et résultats dupliqués ; P4-AC-014/015 et négatifs | **NON CONSTATÉ** |
| **04** | Raw confondu avec parsed ou valeur invalide marquée VALID | ToolArguments.has_parsed, distinction ABSENT/null, validate_tool_call ; StructuredOutput.validation et tests P4-AC-012/013/018/022 | **NON CONSTATÉ** |
| **05** | Support schéma inconnu ou capability UNKNOWN promu à VALID/NATIVE | Statuts UNKNOWN/VALID/INVALID probants, support NATIVE déclaré et distinct de PARTIAL/EMULATED, unsupported refusé ; P4-AC-021/023/026/027 | **NON CONSTATÉ** |
| **06** | Schéma mutable malgré Value Object immutable | gel JSON profond avec copies défensives, tests de mutation alias avant et après construction ; P4-AC-004 et tests L4.2/L4.3 | **NON CONSTATÉ** |
| **07** | P4 casse ou tronque JSON v1 historiques | Tooling JSON v1 autonome, request_to_dict/from_dict et response_to_dict/from_dict M3 v1 inchangés, tests P4-AC-029/032 et M1-M3 | **NON CONSTATÉ** |
| **08** | ToolCallOutput converti silencieusement en TextOutput | composition ADR-028 option B, classes distinctes, pas de nouvel Output dans InferenceResponse, P4-AC-028 et guards d'architecture | **NON CONSTATÉ** |
| **09** | SDK provider, executor ou credentials obligatoires pour les tests | dependencies=[], environnements de CI sans clés provider, exemples offline et clean installs ; P4-AC-033/034/035/037 | **NON CONSTATÉ** |
| **10** | Revendication JSON Schema supérieure au profil validé | limites P4-JSON-1 déclarées, keywords inconnus et $ref refusés, pas de promesse Draft 2020-12 ; tests P4-AC-002/019/038 | **NON CONSTATÉ** |
| **11** | Secret ou raw exposé dans repr/erreur/log de non-divulgation | attributs sensibles en repr=False, codes d'erreur non fondés sur payload, tests P4-AC-016/024/039 et 038/039 codecs | **NON CONSTATÉ** |
| **12** | CI, Python, coverage, wheel/sdist ou exemple en échec | CI push/main #42093041970 sur SHA exact, 967 tests, 95,80 % >=95%, matrix 3/3, Ruff/mypy, builds/17 exemples | **NON CONSTATÉ** |
| **13** | PR confondue avec CI main, ADR ou gate sans preuve | 8 ADR acceptées par l'owner, 6 PV G0..G5, SHAs et CI de push distincts, G5 archivée, revue M4 séparée | **NON CONSTATÉ** |
| **14** | Documentation promet agent exécutant, streaming, provider ou release non livrée | architecture P4, README, concepts et exemple 17 explicitement offline ; version source 0.1.0a2 et publication NO-GO | **NON CONSTATÉ** |

**Conclusion : aucune cause obligatoire bloquante n'a été constatée dans le périmètre M4 inspecté et testé.** Le constat est lié aux preuves ci-dessus. Les limites du périmètre et les réserves sont conservées comme risques explicites, non déclarées résolues.

## 5. Qualité de l'architecture et conventions Software Design & Learning

| Principe | Décision vérifiable | Conséquence |
|---|---|---|
| Domain-Driven Design | Tool et ToolSchema = descriptions/VO ; ToolCall = Entity par identité ; ToolResult = observation | Contrats explicites, sans agrégat exécuteur inventé |
| SOLID, SoC, DIP | Contextes tooling, structured_output et tooling_inference séparés de l'inference M3 et des futurs providers | Domaine dépend des abstractions internes, aucune I/O provider |
| Immutable Value Objects | dataclass frozen/slots, gel JSON et copie défensive | Protection contre les mutations externes des charges complexes |
| CQRS/EDA | Pas d'Event Bus / Command Handler exécutant introduit prématurément | YAGNI maintenu, futurs événements d'exécution hors M4 |
| Anti-Corruption Layer future | Tooling JSON v1 indépendant d'Inference JSON v1 ; aucun fallback ou downgrade | Les futurs adapters pourront traduire explicitement, avec une ADR si nécessaire |
| DRY/KISS | Validateurs purs réutilisés, formats discriminés et erreurs métier bornées | Tests hors réseau reproductibles et complexité localisée |
| Python idiomatique | Typage strict mypy, enums et dataclasses, tuples/copies défensives, tests négatifs | Contrats alpha lisibles et contrôlés sur Python 3.11-3.13 |

L'immutabilité et la preuve de validation sont **des contrats internes du domaine**. Elles ne sont pas un mécanisme de signature cryptographique ou une protection contre un programme Python qui contournerait intentionnellement des API privées.

## 6. Réserves et risques acceptés par le propriétaire pour le seul GO technique

| Risque | Situation vérifiée | Disposition |
|---|---|---|
| **M4-R01 Protection de main** | GitHub branch protected=false, rulesets=[], issue [#22](https://github.com/tawounfouet/pyllmkit/issues/22) OPEN | Blocage release ; activer rulesets, required checks/reviews et vérifier l'enforcement |
| **M4-R02 Revue humaine indépendante** | Aucun APPROVED review tiers sur PR #48/#49 ; revue technique assistée et décision du propriétaire | Revue tierce souhaitable avant publication ; ne pas la présenter comme effectuée |
| **M4-R03 Release/versionnement** | pyproject.toml reste 0.1.0a2, issue [#35](https://github.com/tawounfouet/pyllmkit/issues/35) OPEN, GitHub Releases aucun résultat | Aucun bump/tag/GitHub Release/TestPyPI/PyPI ; décision explicite future |
| **M4-R04 Frontière providers** | issue [#36](https://github.com/tawounfouet/pyllmkit/issues/36) OPEN | Pas de parser provider JSON textuel, secrets, SSRF, retry ou idempotence livré |
| **M4-R05 Limitations JSON Schema** | Sous-ensemble P4-JSON-1 explicitement borné ; pas de conformité Draft 2020-12 complète | Adapters futurs doivent annoncer leurs capacités, refuser l'incompatible |
| **M4-R06 Limites des tests et logs** | Couverture mesurée 95,80 %, pas 100 %, guards statiques non exhaustifs | Réaliser des audits ciblés et fuzz/property tests avant clients I/O externes |
| **M4-R07 Sérialisation des contenus bruts** | Les fonctions *to_dict* conservent volontairement raw comme données ; redaction repr/exception ne chiffre pas ni ne masque le wire explicite | Consommateurs responsables des logs, chiffrement, ACL et politique de conservation |

Ces risques sont **non bloquants pour la qualification du domaine hors ligne seulement**. Ils constituent des limites bloquantes ou prérequis pour les étapes ultérieures selon leur périmètre. Aucune dérogation autorisant une publication n'est sous-entendue.

## 7. Décision finale et suite admissible

**DÉCISION M4 : GO TECHNIQUE AVEC RÉSERVES.**

- P4-G0..P4-G5 : **tous GO techniques avec réserves**.
- M4 Tooling & Structured Output Qualified : **GO technique**, sans moteur de génération, executor ni provider.
- L4.1..L4.5, 40 cas d'acceptation et docs correspondantes sont intégrés à main et qualifiés sur CI de main.
- Publication/versionnement : **NO-GO** tant que gouvernance et issue release ne sont pas résolues et sans autorisation expresse.
- Suite permise : **conception Phase 5 Streaming** et remédiation des réserves, chacune sur une nouvelle décision et avec ses propres gates. Aucun code Phase 5 livré par ce rapport.

### Archivage de la revue finale

Le présent PV est produit **après** la qualification indépendante du SHA 92874b2. Il doit être intégré à main via une PR documentaire explicite et la CI push/main de l'archive doit être vérifiée à son tour. Cette dernière sera enregistrée dans la PR et la réponse finale ; elle n'est **pas inventée ici** avant son exécution.

**Pythos :** recommandation et revue technique ne constituent pas une exécution provider ni une approbation tiers. Seules les modifications, CI, merges et checks effectivement observés sont attestés.
