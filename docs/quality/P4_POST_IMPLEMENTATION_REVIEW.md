# PyLLMKit - Phase 4 : bilan post-implémentation, revue M4 et trajectoire

> Date de référence : 2026-11-05.
> **Bilan : L4.1..L4.5 intégrés, P4-G0..G5 GO techniques avec réserves, M4 GO TECHNIQUE AVEC RÉSERVES.**
> **Preuve finale M4 :** [main@92874b2e97bcc130279e244bf1000c65a939d7e5](https://github.com/tawounfouet/pyllmkit/commit/92874b2e97bcc130279e244bf1000c65a939d7e5), [CI #42093041970](https://github.com/tawounfouet/pyllmkit/actions/runs/42093041970) SUCCESS.
> **Version source : 0.1.0a2.** Aucun changement de version ni release autorisé.
> **Procès-verbal final :** [M4_GATE_REVIEW.md](M4_GATE_REVIEW.md), audit indépendant des 14 NO-GO obligatoires.

## 1. Résumé exécutif

La Phase 4 de PyLLMKit fournit désormais une **couche de contrats Python de Tooling & Structured Output, agnostique des fournisseurs et entièrement hors ligne**. Elle permet de décrire une définition d'outil avec son schéma, de construire des demandes d'appel et des résultats corrélés, de représenter une sortie structurée, de valider les charges JSON selon un profil explicite, de préserver les états d'incertitude et de sérialiser ces éléments dans Tooling JSON v1. Elle **n'exécute aucun outil**.

Les choix architecturaux les plus protecteurs sont les suivants : identité explicite ToolCallId, Tool non exécutable, gel profond JSON, raw/parsed/ABSENT distincts, preuves de validation UNKNOWN/VALID/INVALID, politique de capability fidèle, et wrappers P4 indépendants de M3. La compatibilité de Model/Interaction/Inference JSON v1 est conservée.

La qualification finale est **technique et limitée au domaine**, pas à l'interopérabilité réelle d'un provider, à la production, à la sécurité d'un executor ou à la publication.

## 2. Inventaire incrémental des livrables

| Lot | Livrable principal | Tests et démonstrations | Preuve main |
|---|---|---|---|
| L4.1 Tool Domain | Tool, ToolSchema, ToolChoice, P4-JSON-1 | P4-AC-001..008, exemple 13 | [G1](P4_G1_GATE_REVIEW.md) |
| L4.2 Tool Calling | ToolCallId, ToolArguments, ToolCall, ToolResult, validation, corrélation | P4-AC-009..016, exemple 14 | [G2](P4_G2_GATE_REVIEW.md) |
| L4.3 Structured Output | Text/JSON/Schema formats, StructuredOutput, statuts et support explicite | P4-AC-017..024, exemple 15 | [G3](P4_G3_GATE_REVIEW.md) |
| L4.4 Composition & Codec | ToolingInferenceIntent/Observation, ToolCallOutput, Tooling JSON v1 | P4-AC-025..032, exemple 16 | [G4](P4_G4_GATE_REVIEW.md) |
| L4.5 Integration & Quality | README, architecture, concepts, tests docs/packaging, traçabilité 40 AC | P4-AC-033..040, exemple 17, CI installée wheel/sdist | [G5](P4_G5_GATE_REVIEW.md) |

Les huit ADR-022..029 ont été approuvées par le propriétaire en G0 et adoptées avant le code. Les gates sont traçables à leurs PRs, commits main et CI de push dans [PHASE_4_TRACEABILITY.md](PHASE_4_TRACEABILITY.md).

## 3. Mesures de progression

| Étape | Tests de la suite cumulative | Couverture globale arrondie |
|---|---:|---:|
| M3 initial, avant P4 | 802 | 95 % |
| P4-G1 | 846 | 95 % |
| P4-G2 | 884 | 95 % |
| P4-G3 | 903 | 95 % |
| P4-G4 | 954 | 96 % |
| P4-G5 | 967 | 96 % |
| M4, SHA final vérifié avant archivage | **967** | **95,80 %** calculés |

La différence de tests reflète la croissance de la suite globale, **pas un nombre de tests attribuables exclusivement à chaque lot**. En clôture G5, le seuil `--cov-fail-under=95` est devenu **bloquant** dans la CI ; la baseline M4 le franchit.

## 4. Architecture et design patterns appliqués

**DDD et types de domaine.** Tool et ToolSchema décrivent, ToolCall est une Entity identifiée par ToolCallId, ToolResult une observation, et les formats sont des Value Objects. La validation est pure et la corrélation n'exécute pas de commande.

**SOLID/SoC/DIP.** Le domaine P4 est divisé en trois espaces : tooling, structured_output, tooling_inference. Aucune dépendance transitive vers un SDK ou une couche HTTP n'est nécessaire. L'Anti-Corruption Layer reste une option pour les futurs providers, et non une implémentation invisible dans les Value Objects.

**KISS/YAGNI.** Pas de runtime, scheduler, parser JSON texte réseau, registry, retry/repair ou streaming créé prématurément. Les décisions ADR-028 et ADR-029 ont évité de faire passer ToolCallOutput pour TextOutput et de réviser silencieusement Inference JSON v1.

**Python idiomatique.** Typage mypy strict, dataclasses frozen/slots et sérialisation vers dictionnaires de données. Le profil JSON Schema est délibérément limité à P4-JSON-1, sans réclamer la conformité complète à Draft 2020-12.

## 5. Risques techniques et gouvernance

| Famille | Situation | Traitement futur |
|---|---|---|
| Protection main | [#22](https://github.com/tawounfouet/pyllmkit/issues/22) OPEN, protected=false et rulesets=[] | Activer/enforcer required checks, PR/reviews avant release |
| Revue indépendante | Pas d'APPROVED GitHub tiers sur PR #48/#49 | Relecture humaine indépendante avant publication |
| Release et version | [#35](https://github.com/tawounfouet/pyllmkit/issues/35) OPEN, 0.1.0a2 source, publication interdite | Décision version/tag/distribution explicite |
| Provider boundary | [#36](https://github.com/tawounfouet/pyllmkit/issues/36) OPEN | Parser strict, secrets, SSRF, rate limits, retry/idempotence, négociation capabilities |
| Raw sensible | Champs raw explicitement sérialisables, non masqués sur le wire | Logs, ACL et politique de données au niveau de l'application |
| Validation | Sous-ensemble P4-JSON-1, couverture 95,80 %, pas de full Draft | Tests de propriété/fuzz, stratégies provider et profils déclarés |
| Exécution réelle | Aucun handler d'outil, agent ou streaming effectif | Phases ultérieures avec threat model et revues distinctes |

Aucune de ces réserves n'autorise automatiquement une publication. Le GO M4 est volontairement **technique et borné au domaine hors ligne**.

## 6. Prochaine trajectoire recommandée

La suite logique du point de vue du plan est **Phase 5 - Streaming**, à instruire dans une nouvelle phase de conception : identité des deltas, ordre et réassemblage des fragments, backpressure, cancellation et durabilité, puis nouvelles décisions d'architecture. Ce bilan **n'autorise aucune implémentation P5 sans son propre cadrage**.

En parallèle, traiter les issues #22, #35 et #36 pour construire une trajectoire de livraison de package et de futurs adapters réaliste. Il faut distinguer les progrès d'architecture et de qualité technique des capacités opérationnelles ou commerciales effectivement disponibles.

## 7. Conclusion et décision

Le dossier [M4_GATE_REVIEW.md](M4_GATE_REVIEW.md) évalue **14 causes de NO-GO** et prononce **M4 GO TECHNIQUE AVEC RÉSERVES** sur main@92874b2e et sa CI. La documentation de clôture elle-même est soumise à une PR et à une CI d'archivage distinctes avant d'être conservée dans main.

**État de diffusion : NO-GO**, sans version bump, tag ni publication PyPI. Les preuves historiques sont préservées et les limitations restent explicitement ouvertes.
