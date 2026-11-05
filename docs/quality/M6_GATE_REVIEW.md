# PyLLMKit - M6 Registry & Discovery - Revue finale GO/NO-GO

> Date : 2026-11-05.
>
> **Décision : GO TECHNIQUE AVEC RÉSERVES** pour le noyau de registre, recherche, résolution de capacités et découverte **hors réseau**.
>
> Autorité de livraison : autorisation explicite du propriétaire dans la conversation du 2026-11-05 de qualifier, valider et fusionner de bout en bout. Revue technique assistée, **pas une review GitHub tierce indépendante**.
>
> **Baseline finale du code :** [main@6c58b052](https://github.com/tawounfouet/pyllmkit/commit/6c58b0523edbbba009cd1b437db9d6f82dcba7a3) - [CI #42123870931](https://github.com/tawounfouet/pyllmkit/actions/runs/42123870931) completed/success.
>
> **Baseline d'archivage des 8 gates :** [main@670ccab9](https://github.com/tawounfouet/pyllmkit/commit/670ccab98f253be70198d3916adfc55ddb22c64f) - [CI #42124522939](https://github.com/tawounfouet/pyllmkit/actions/runs/42124522939) completed/success.
>
> **Release `0.1.0b2` : NO-GO.** Version déclarée du package : `0.1.0a2`, inchangée. Aucun tag, GitHub Release ni PyPI publish.

## 1. Objet et portée du GO

M6 achève le domaine **Registry & Discovery** de PyLLMKit : descriptions `Model` / `InferenceProvider` / `Deployment`, registres canoniques, recherches typées, résolution restrictive de capacités et limites effectives, sélection déterministe d'un deployment, découverte statique offline, prévisualisation et fusion atomique d'un snapshot InMemory.

Le nom historique « Phase 6 Provider Adapters » est remplacé, dans la roadmap de P6, par Registry & Discovery suivant ADR-039. **Les Provider Adapters exécutables, HTTP, SDKs, secrets, retries, healthchecks et routage d'inférence ne sont pas implémentés en M6.** Ils relèvent de l'architecture du prochain milestone P7.

Le GO n'affirme ni que PyLLMKit est un client LLM opérationnel en réseau, ni qu'une source de métadonnées est réellement à jour, ni que la transaction InMemory est sûre dans un système distribué.

## 2. Constat exact sur le dernier SHA de code

| Contrôle | Résultat vérifié | Décision |
|---|---|---|
| Fusion des lots | PR #59 à #66 : toutes **MERGED** dans l'ordre | PASS |
| Baseline de code | `6c58b0523edbbba009cd1b437db9d6f82dcba7a3` sur main | PASS |
| CI push/main du code | #42123870931, `completed/success` sur SHA identique | PASS |
| Exécution des tests | **1 189 tests cumulatifs réussis**, Python 3.11 | PASS |
| Couverture domaine avec branches | **96,61 %**, seuil CI bloquant >=95 % | PASS |
| Matrice Python | `validate (3.11)`, `validate (3.12)`, `validate (3.13)` : 3/3 SUCCESS | PASS |
| Lint & typage | Ruff et mypy strict passés dans les jobs CI | PASS |
| Exemples | 01 à 28 depuis checkout ; 23 à 28 dans wheel et sdist installées isolément | PASS |
| Distributions | Wheel et sdist construites et testées en CI | PASS |
| Architecture | Contrôle des imports P6 et absence de SDK provider obligatoire | PASS dans la portée testée |
| Non-régression | Tests cumulatifs M1-M5 et codecs historiques inclus | PASS dans la portée CI |
| Traçabilité P6 | 56 identifiants AC-001..056 présents dans les tests de lots et cartographiés | PASS |
| Archivage des gates | PR #67 intégrée, `main@670ccab9`, CI #42124522939 3/3 SUCCESS | PASS |
| ADR | ADR-039..048 marquées ACCEPTED sous autorisation explicite du propriétaire | PASS décision de conception |
| Protection main | `protected=false`, liste rulesets vide | RÉSERVE |
| Review GitHub indépendante | Aucune review APPROVED tierce sur les PR #59..#66 lors de l'audit | RÉSERVE |
| Version / release | `0.1.0a2`, projet non publié dans cette opération | NO-GO release |

Les statistiques sont extraites du journal d'un job Python 3.11 sur le SHA de code qualifiant, non d'une extrapolation à partir des fichiers de tests. Les trois versions Python ont des jobs verts. Les revendications de qualité restent bornées à la CI et ne remplacent pas un audit de sécurité externe.

## 3. Chaîne exacte de qualification G0 à G7

| Gate | Périmètre | PR | SHA main | CI push/main | Tests | Couverture |
|---|---|---|---|---|---:|---:|
| P6-G0 | Architecture ADR-039..048 | #59 | `d1e7841a` | #42122809277 | 1048 | 96,08 % |
| P6-G1 | Provider & Deployment | #60 | `a1e2f0ca` | #42122966414 | 1081 | 96,21 % |
| P6-G2 | Registry Ports & InMemory | #61 | `614af324` | #42123116242 | 1094 | 96,22 % |
| P6-G3 | Queries & Catalog Search | #62 | `9f3edaab` | #42123260072 | 1106 | 96,35 % |
| P6-G4 | Effective Capability & Limits | #63 | `3bdfd84d` | #42123414949 | 1137 | 96,50 % |
| P6-G5 | Deployment Resolution | #64 | `5f0b8ad5` | #42123564296 | 1154 | 96,56 % |
| P6-G6 | Offline Discovery & Merge | #65 | `1b92a784` | #42123710290 | 1180 | 96,57 % |
| P6-G7 | Integration & Quality | #66 | `6c58b052` | #42123870931 | 1189 | 96,61 % |

**8/8 gates ont un GO TECHNIQUE AVEC RÉSERVES**, avec une preuve main différente à chaque étape. Dossiers officiels : `docs/quality/P6_G0_GATE_REVIEW.md` à `P6_G7_GATE_REVIEW.md`. Le présent procès-verbal est **postérieur** aux huit décisions de gate et à l'archivage des preuves, donc ne les remplace pas.

## 4. Revue contradictoire des risques de NO-GO

Un résultat « non constaté » est borné au code et aux essais réellement vérifiés, et n'est pas une garantie générale.

| # | Cause de NO-GO potentielle | Contrôle et constat | Verdict |
|---|---|---|---|
| 01 | P6 confond Registry et SDK de Provider | ADR-039 et frontière claire entre catalogue descriptif et AdapterRegistry exécutable | Non constaté |
| 02 | Type d'identifiant perdu ou provider alias confondu avec ModelId | ModelId/DeploymentId existants réutilisés, ProviderId typé, AC-001..008 | Non constaté |
| 03 | Provider local absent traité comme fournisseur inconnu | NOT_APPLICABLE explicite pour deployment sans ProviderId | Non constaté |
| 04 | Duplication de ModelId écrasant des métadonnées | Contrôle du snapshot complet, refus des collisions AC-013/045 | Non constaté |
| 05 | Delete cascade orphelinant un deployment | Contrôles de dépendance et suppression interdite AC-014 | Non constaté |
| 06 | Query strict satisfaisant une capacité UNKNOWN | Filtrage fail-closed, mode NATIVE_ONLY/USABLE explicite AC-017..024 | Non constaté |
| 07 | UNSUPPORTED ignoré au profit de déclarations positives | Veto explicite AC-027 | Non constaté |
| 08 | PARTIAL et EMULATED réduits par un classement naïf | Preuves et indicateur d'émulation préservés AC-028 | Non constaté |
| 09 | Limites manquantes fabriquées à 0 ou illimitées | None, borne min connue et statut provisoire AC-031 | Non constaté |
| 10 | Contrainte incohérente acceptée arbitrairement | Conflits de type, exactitude, plage inversée et politique inconnue rejetés AC-032 | Non constaté |
| 11 | Plusieurs deployments éligibles sélectionnés selon l'ordre d'insertion | AmbiguousDeploymentError avec IDs triés AC-035/040 | Non constaté |
| 12 | AVAILABLE interprété comme endpoint live | Contrat explicitement déclaratif ; pas de healthcheck | Non constaté dans P6 |
| 13 | Découverte extérieure effectuant HTTP ou SDK caché | Source statique déterministe et horloge injectée AC-041..044 | Non constaté |
| 14 | Fusion partielle après conflit ou référence absente | Prévisualisation, refus du batch et snapshot atomique AC-045/046 | Non constaté en usage séquentiel |
| 15 | Prévisualisation pouvant être réutilisée avec contenu changé mais IDs identiques | Correctif L6.6 : digest SHA-256 sur champs complets, test négatif AC-047 | Non constaté après correctif |
| 16 | Réexécution identique générant nouvelle écriture ou provenance inventée | Replay no-op et révision inchangée AC-047/054 | Non constaté |
| 17 | M1-M5 cassés par la nouvelle API/CI | Tests cumulatifs, exemple 01..28 et clean builds sur SHA G7 | Non constaté dans la CI |
| 18 | Gate présenté comme GO sans preuve exacte de main | Huit SHA et CI distinctes + archive validée sur main | Non constaté |
| 19 | Garantie de concurrence ou de stockage exagérée | Atomicité **in-process séquentielle** uniquement, sans locks ni transaction distribuée | Limite explicite |
| 20 | Release ou approbation humaine déclarée à tort | Pas de release ni review tierce revendiquée ; main non protégée | Réserve de gouvernance |

**Décision d'audit :** aucune cause technique de refus n'est observée dans le périmètre offline testé. Les réserves sont réelles, documentées et ne doivent pas être masquées par une couverture élevée.

## 5. Principes d'architecture vérifiés

- **DDD et Aggregate Identity** : `Model`, `InferenceProvider`, `Deployment` ont identité canonique ; les Value Objects d'identité et de contraintes préservent leurs invariants.
- **DIP / Ports & Adapters** : les Protocols `ModelRegistryPort`, `ProviderCatalogPort`, `DeploymentRegistryPort`, `DiscoverySourcePort`, `AtomicCatalogPort` isolent le domaine des implémentations InMemory.
- **CQRS / séparation lecture-écriture** : requêtes et résolveurs de capacités ne modifient pas le catalogue ; merge explicite et opéré après preview.
- **Immutabilité** : snapshots de domaine et rapports dérivés sont figés, résultats de query triés et retournés en tuples.
- **Deterministic Selection** : pas de scoring, randomisation, fallback ni « premier trouvé » silencieux ; les ambiguïtés sont des erreurs.
- **Fail-closed et provenance** : UNKNOWN n'est pas un succès, les conflits sont visibles, les dates UTC sont validées via horloge injectée.
- **Optimistic Concurrency** : révision CAS et snapshot publié en une seule substitution en mémoire, uniquement pour le contexte séquentiel documenté.
- **SOLID/SoC/YAGNI** : aucun mélange avec SDK, transport, authentification, rate limiters ou orchestration d'agents du jalon suivant.

## 6. Réserves et limites à conserver

1. **#22 - Protection de main :** `protected=false` et rulesets vides dans le dernier audit. Les outils actuellement disponibles n'offrent pas d'action d'administration pour activer cette protection. Cela doit être traité depuis une identité disposant de droits d'administration GitHub, avec required checks et reviews. La CI réussie seule n'apporte aucune enforcement.
2. **Review tierce indépendante :** les PR M6 ont été livrées selon autorisation du propriétaire, sans review GitHub indépendante. Une nouvelle revue humaine sera nécessaire avant une qualification de distribution externe.
3. **#35 - Release :** publication PyPI, version `0.1.0b2`, tag et GitHub Release demeurent hors de cette autorisation. Pas de release implicite par GO technique.
4. **#36 - Provider boundary :** avant P7 exécutable, formaliser les contrats de parsing provider, représentation d'erreurs, secrets, retries, quotas, annulation, streaming réseau, observabilité et compatibilité.
5. **Concurrence et durabilité :** le CAS InMemory est conçu pour des appels séquentiels au sein d'un processus. Rien ne prouve un comportement transactionnel thread-safe, multi-processus ou distribué ; pas de stockage durable fourni.
6. **Entrées non fiables :** `StaticDiscoverySource` attend des objets typés, non un parseur de fichiers arbitraires. Aucun engagement contre les attaques provenant de données non fiables avant une étape d'adapter sécurisé.
7. **Observabilité et santé réelle :** `AVAILABLE` est une déclaration, non une télémétrie de transport. Les résolveurs ne peuvent pas démontrer qu'un modèle répond.
8. **Confidentialité :** `repr=False` et diagnostics sans raw ne suffisent pas à une politique complète de sécurité et de logs. Les futurs adapters P7 devront établir le modèle de menace.

## 7. Verdict formel et milestone suivant

**M6 = GO TECHNIQUE AVEC RÉSERVES** pour **Registry & Discovery hors réseau**. Les 7 lots L6.1..L6.7, les 10 ADR-039..048, les 56 AC, les huit gates G0..G7 et leur archivage sont fusionnés et qualifiés sur main. Aucune nouvelle implémentation P6 n'est nécessaire pour ouvrir la **préparation de P7 Provider Adapters**.

**P7-G0 Architecture = prochain chantier autorisé à commencer** : contrats d'adapters et menace provider, puis sélection d'une première intégration limitée. Le code P7 exécutable devra faire l'objet de gates distincts. Voir `docs/roadmap/P7_PROVIDER_ADAPTERS_ENTRY_CRITERIA.md`.

**Publication `0.1.0b2` = NO-GO**. Le présent GO ne permet pas une release. Aucune approbation humaine tierce ni protection main n'est prétendue acquise.

### Archivage de la revue

La présente revue finale est postérieure à la qualification de main@6c58b052 et à l'archivage main@670ccab9. Elle est soumise dans une PR documentaire dédiée ; le SHA de cette fusion et sa propre CI push/main devront être vérifiés avant d'affirmer que le dossier final M6 est lui-même archivé avec succès.
