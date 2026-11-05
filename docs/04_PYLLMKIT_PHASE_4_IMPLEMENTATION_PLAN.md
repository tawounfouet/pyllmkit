# PyLLMKit - Plan d'implémentation de la Phase 4

> **État d'implémentation réel au 2026-11-05 :** L4.1 à L4.5 sont intégrés. P4-G0 à P4-G5 ont un GO technique avec réserves; voir [PV G5](quality/P4_G5_GATE_REVIEW.md), [main@aad2656c](https://github.com/tawounfouet/pyllmkit/commit/aad2656cbe1753dac709bb28b228ba22ecca44a2), [CI #42092202193](https://github.com/tawounfouet/pyllmkit/actions/runs/42092202193). **M4 reste une revue finale séparée**. Les passages ci-dessous sont le plan historique de référence, non le statut temps réel du dépôt. Version source `0.1.0a2`, sans publication.

## P4 - Tooling & Structured Output / M4 - Tooling & Structured Output Qualified

> **Statut : PLAN ET ADR-022..029 APPROUVÉS PAR LE PROPRIÉTAIRE EN P4-G0. QUALIFICATION DU GATE SUR CI MAIN À CONSIGNER SÉPARÉMENT. AUCUN CODE P4 IMPLÉMENTÉ PAR CE DOCUMENT.**
>
> **Date de référence :** 5 novembre 2026.
>
> **Baseline GitHub vérifiée :** [`main@3d5ffc811c33ae6dabf392b2c7d24f7ec2a27dc6`](https://github.com/tawounfouet/pyllmkit/commit/3d5ffc811c33ae6dabf392b2c7d24f7ec2a27dc6).
>
> **Qualification M3 :** [`M3_GATE_REVIEW.md`](quality/M3_GATE_REVIEW.md), **GO technique avec réserves pour le domaine d'inférence hors ligne**, [CI #42070067345](https://github.com/tawounfouet/pyllmkit/actions/runs/42070067345) SUCCESS sur Python 3.11, 3.12 et 3.13, **802 tests et 95 % de couverture globale** sur Python 3.11.
>
> **État du package :** `pyproject.toml` déclare **`0.1.0a2`**. La version **`0.1.0a3` n'est pas publiée**. Le label **`0.1.0a4` est une cible indicative du plan directeur**, pas un numéro de version approuvé ni une autorisation de publication.
>
> **Réserves ouvertes :** [#22 - protection de main](https://github.com/tawounfouet/pyllmkit/issues/22), [#35 - stratégie de release](https://github.com/tawounfouet/pyllmkit/issues/35), [#36 - frontière des futurs providers](https://github.com/tawounfouet/pyllmkit/issues/36).
>
> **Autorité de décision :** propriétaire du projet. L'adoption des huit ADR par le propriétaire est documentée dans [P4_G0_OWNER_ARCHITECTURE_APPROVAL.md](quality/P4_G0_OWNER_ARCHITECTURE_APPROVAL.md). Les critères d'acceptation et gates restent à vérifier par des preuves GitHub.

---

## 0. Résumé exécutif

La Phase 4 construit les **primitives de domaine qui décrivent une sélection d'outils, une demande d'appel, un résultat corrélé et un format de sortie structurée**, sans exécuter les outils, sans invoquer un fournisseur LLM et sans présumer qu'un fournisseur sait produire du JSON conforme.

La finalité M4 n'est **pas** de livrer un agent autonome ou un moteur d'exécution : elle consiste à permettre à un consommateur Python de définir des outils et des schémas, construire des `ToolCall` et `ToolResult`, valider explicitement leurs relations et des sorties structurées, et sérialiser ces valeurs avec des contrats versionnés, tout cela **hors réseau** et en préservant M1, M2 et M3.

La décision la plus risquée est **l'extension de l'Inference Domain qualifié à M3**. Aujourd'hui :

- `InferenceRequest` contient `target`, `messages` et `generation_config`. Il ne possède **ni `tools`, ni `tool_choice`, ni `response_format`**.
- `InferenceResponse.output` accepte uniquement `TextOutput`; `InferenceOutput` est un alias de ce type, pas une union extensible déjà disponible.
- **Inference JSON v1 est strict** : ajouter des champs aux enveloppes ou de nouveaux variants sans changer le contrat serait une rupture.
- Le `GenerationSupportSnapshot` M3 couvre les **paramètres de génération**, pas automatiquement `TOOL_CALLING` ni `STRUCTURED_OUTPUT`.
- Les messages M2 et leur codec Interaction JSON v1 ne contiennent pas implicitement des `ToolCallContent` et `ToolResultContent`.

**Conclusion de conception :** P4-G0 doit choisir comment composer les primitives P4 avec les types M3 et comment introduire les nouveaux formats, **sans compatibilité fictive ni perte silencieuse de données**. Le plan recommande de traiter ces questions avant toute PR de code public.

### 0.1. Découpage proposé

| Étape | Objet | Livrable principal | Qualification |
|---|---|---|---|
| **P4-BOOT** | ADR et contrat d'extension | Décisions sur identité, JSON Schema, v2, Request/Response | **P4-G0 - Architecture Ready** |
| **L4.1** | Tool Definition & Choice | `Tool`, `ToolSchema`, `ToolChoice`, validations de catalogues locaux | **P4-G1 - Tool Declaration Ready** |
| **L4.2** | Tool Calls & Results | `ToolCallId`, `ToolArguments`, `ToolCall`, `ToolResult`, corrélation | **P4-G2 - Tool Call Ready** |
| **L4.3** | Structured Output | `ResponseFormat`, `StructuredOutput`, validation déclarative | **P4-G3 - Structured Output Ready** |
| **L4.4** | Composition & Serialization | Intégration optionnelle Request/Response et **schéma versionné distinct** | **P4-G4 - Integration Contract & Codec Ready** |
| **L4.5** | Qualité et packaging | 40 recettes P4, exemples offline, docs, wheel/sdist, traçabilité | **P4-G5 - Integration & Quality Ready** |
| **M4** | Qualification transversale | `M4_GATE_REVIEW.md` motivé, séparé de la publication | **M4 - GO/NO-GO** |

Ce découpage est une **proposition d'organisation**. La Phase 4 Tooling vient du document fondateur `00`, mais les lots, identifiants P4-AC, gates et critères M4 sont **créés par ce plan**, non préexistants dans les documents `00` à `09`.

---

## 1. Sources, provenance et hiérarchie

### 1.1. Corpus fondateur fourni par le propriétaire

| Document | Parties mobilisées | Exigences retenues |
|---|---|---|
| `00_PYLLMKIT_EXPRESSION_DU_BESOIN.md` | `19 Tool Calling`, `20 Structured Output`, `37 Phase 4` | `Tool`, `ToolSchema`, `ToolChoice`, `ToolCall`, `ToolArguments`, `ToolResult`; formats texte/JSON/schéma |
| `01_PYLLMKIT_REQUIREMENTS_ANALYSIS.md` | `UC-011`, `UC-012`, `FR-025` à `FR-028`, `NFR-001` à `NFR-010` | Types provider-agnostic, sorties structurées, typage, déterminisme, sérialisation et testabilité |
| `02_PYLLMKIT_PRODUCT_VISION_AND_ARCHITECTURE_PRINCIPLES.md` | `Domain First`, `Explicit over Implicit`, `Ports Before Clients`, `Unknown Must Remain Unknown` | Aucun transport/SDK dans le domaine, pas de provider leakage, pas de God Client |
| `03_PYLLMKIT_SYSTEM_ARCHITECTURE.md` | Couches, frontières et roadmap MVP | Contrats purs, adapters externes et packaging modulaire |
| `04_PYLLMKIT_DOMAIN_OBJECTS.md` | ``51-59` et ``73-74` | Catalogue des objets, `StructuredOutput` et `ToolCallOutput` |
| `05_PYLLMKIT_ENTITIES_AND_VALUE_OBJECTS.md` | ``58-65`, ``79-80` | `Tool`, `ToolSchema`, `ToolArguments`, `ToolResult` comme Value Objects; `ToolCall` comme Entity |
| `06_PYLLMKIT_DOMAIN_RELATIONSHIPS_AND_ERD.md` | ``33-38`, ``42-43`, ``53-56` | Cardinalités Request -> Tools/Format/Choice et Call -> Result; MVP 0..1 résultat |
| `07_PYLLMKIT_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md` | `TOOL-001` à `TOOL-021`, `INF-009/010` | Outil non exécutable, ID et corrélation, schéma valide, support explicite, raw distinct de parsed |
| `08_PYLLMKIT_COMMANDS_QUERIES_AND_USE_CASES.md` | `DefineTool`, `ValidateToolSet`, `ValidateToolCall`, `AttachToolResult`, `ValidateStructuredOutput` | Fonctions et opérations à réaliser sans transport |
| `09_PYLLMKIT_DOMAIN_EVENTS_CATALOG.md` | `ToolCallObserved` et `ToolResultAttached` | Événements **conceptuels**, pas de bus effectif ni de publication automatique |

Ces fichiers sont des **spécifications de conception**, pas des preuves de code P4 existant. Les signatures et stratégies de validation qui suivent ne sont pas automatiquement décidées par le corpus : leurs arbitrages sont indiqués comme **P4-G0 requis**.

### 1.2. Sources GitHub actuellement qualifiées

- [`M3_GATE_REVIEW.md`](quality/M3_GATE_REVIEW.md) : M3 GO technique avec réserves, 11 critères de NO-GO inspectés.
- [`P3_G5_GATE_REVIEW.md`](quality/P3_G5_GATE_REVIEW.md) et [`PHASE_3_TRACEABILITY.md`](quality/PHASE_3_TRACEABILITY.md) : 30 recettes P3 et chaîne de preuve.
- [`03_PYLLMKIT_PHASE_3_IMPLEMENTATION_PLAN.md`](03_PYLLMKIT_PHASE_3_IMPLEMENTATION_PLAN.md) : modèle de gates, PRs contrôlées, baseline et code de qualité.
- [`INFERENCE_JSON_SCHEMA_V1.md`](architecture/INFERENCE_JSON_SCHEMA_V1.md) : format strict à protéger.
- [`FUTURE_PROVIDER_BOUNDARY_CONTRACT.md`](architecture/FUTURE_PROVIDER_BOUNDARY_CONTRACT.md) : tâches de parsing texte, secrets, retries, SSRF et HTTP **réservées aux intégrations futures**.
- [`PYKIT_DELIVERY_AND_LEARNING_LOOP.md`](governance/PYKIT_DELIVERY_AND_LEARNING_LOOP.md) : besoin -> invariants -> ADR -> code -> tests négatifs -> CI PR -> CI main -> PV.
- [Issues #22](https://github.com/tawounfouet/pyllmkit/issues/22), [#35](https://github.com/tawounfouet/pyllmkit/issues/35) et [#36](https://github.com/tawounfouet/pyllmkit/issues/36) : gouvernance, release et frontière provider non résolues.

**Règle d'arbitrage :** le code M3 et les ADR acceptées ont autorité sur les contrats **déjà livrés**; le corpus `00` à `09` définit l'intention fonctionnelle **future**. En cas de conflit, décider dans une nouvelle ADR et écrire les migrations/tests avant de modifier une API.

---

## 2. Définition du périmètre M4

### 2.1. MUST de M4

1. Définir des outils et leurs schémas de paramètres de façon provider-agnostic et immuable.
2. Exprimer une stratégie de sélection `AUTO`, `NONE`, `REQUIRED` ou `SpecificTool(name)` sans décision de routing.
3. Donner une identité explicite à chaque `ToolCall` et préserver les arguments bruts vs parsés.
4. Corréler un `ToolResult` à **un appel existant** dans le contexte de validation fourni; représenter le succès et l'échec.
5. Valider les noms d'outils uniques dans une request ou un ensemble local et empêcher une référence inconnue.
6. Décrire les formats `TextResponseFormat`, `JsonResponseFormat` et `SchemaResponseFormat`, avec validation et statut explicites.
7. Signaler la non-conformité d'une sortie structurée et conserver l'absence/UNKNOWN au lieu de fabriquer une validation.
8. Conserver les versions M1/M2/Inference JSON v1 et introduire toute évolution P4 avec **une politique de compatibilité explicite**.
9. Publier une **API Python de domaine hors ligne**, avec sérialisation déterministe, tests négatifs et exemples copiables.
10. Garder le nombre de dépendances runtime du domaine minimal et l'installation depuis wheel/sdist possible sans SDK fournisseur.

### 2.2. SHOULD conditionnels, à décider en G0

- Représentation immuable d'un sous-ensemble JSON Schema documenté, avec stratégie explicite de validation sémantique.
- Un `ToolCallOutput` ou une `StructuredOutput` associé à une réponse **sans falsifier** le type `TextOutput` existant.
- Vérification déterministe d'une chaîne de résultats associée à un ensemble d'appels, sans persistance ni pub/sub.
- Un validateur de schémas optionnel **si** les garanties et dépendances sont approuvées.
- Une facade d'usage offline très mince uniquement si les primitives sont difficiles à composer sans elle.

### 2.3. Hors scope explicite

- **Exécuter une fonction Python**, un shell, un script, un outil externe, un conteneur ou un plugin à la suite d'un `ToolCall`.
- Agents autonomes, autorisation d'accès aux outils, policy engine, retries d'exécution, orchestration, planification, workflows, approbations utilisateur et sandbox.
- SDK OpenAI/Anthropic/Google/Ollama, transport réseau, credentials, egress et JSON texte HTTP.
- Assemblage streaming de `ToolCallDelta`, streaming des arguments, reconstruction de fragments : **Phase 5**.
- Tool registry distant, résolution dynamique de services, auto-discovery, requêtes au provider : phases ultérieures.
- Déclenchement de `ToolCallObserved` / `ToolResultAttached` sur un bus effectif.
- Validation de conformité JSON Schema **complète** si seul un profil partiel a été décidé.
- Publication d'un package, bump de version, tag Git ou PyPI comme effet secondaire de M4.
- Modification silencieuse de `Inference JSON v1`, `Interaction JSON v1` ou `Model JSON v1`.

### 2.4. Définition de succès M4

Un développeur doit pouvoir, **sans clé API et sans exécution d'outil**, créer deux définitions d'outils, choisir une politique, générer deux appels corrélables, constater qu'un résultat est valide ou en échec, valider une sortie JSON au regard d'un schéma approuvé, effectuer un round-trip de valeurs P4 dans un codec versionné, et exécuter les exemples depuis des installations wheel/sdist isolées.

Un M4 GO signifie **Tooling & Structured Output Domain Qualified**, **pas un agent capable d'appeler des outils réels**.

---

## 3. Architecture cible et frontières

### 3.1. Bounded context P4

```text
                              Consumer Python (offline)
                                       |
                         constructions / validations pures
                                       |
                  +--------------------+--------------------+
                  |                                         |
          Tooling Domain                              Structured Output
                  |                                         |
       Tool, ToolSchema                          TextResponseFormat
       ToolChoice                                JsonResponseFormat
       ToolArguments                             SchemaResponseFormat
       ToolCallId + ToolCall                      StructuredOutput
       ToolResult                                ValidationResult
                  |                                         |
                  +--------------------+--------------------+
                                       |
                    Composition optionnelle avec M3
                   InferenceRequest / InferenceResponse
                                       |
                     P4 Codec versionné, séparé de v1
                                       |
                        M1 / M2 / M3 sans régression

      EXCLUS : Python function executor / shell / HTTP / provider SDK
                 streaming réel / agent orchestration / secrets
```

### 3.2. Modèle DDD visé

| Type | Classification attendue | Invariant principal |
|---|---|---|
| `Tool` | Value Object par défaut (source `05`) | Définition de capacité, pas un exécuteur |
| `ToolSchema` | Value Object | Copie/gel profond ou représentation réellement immutable |
| `ToolChoice` | Value Object / union discriminée | AUTO, NONE, REQUIRED ou nom spécifique non vide |
| `ToolCallId` | Value Object d'identité | Non vide, type exact, pas de génération cachée |
| `ToolArguments` | Value Object | Raw, parsed et état de validation ne sont pas interchangeables |
| `ToolCall` | Entity (`ToolCallId`) | Deux appels identiques en valeur gardent des identités distinctes |
| `ToolResult` | Value Object | Référence exactement le `ToolCallId`, statut d'échec explicite |
| `ResponseFormat` | Union de Value Objects | Variants connus et discriminés, pas un booléen "json" ambigu |
| `StructuredOutput` | Value Object | Payload, format, résultat de validation et raw éventuel distincts |
| `ToolCallOutput` | Option de sortie métier | Ne devient pas automatiquement un variant M3 JSON v1 |
| `ToolSet` | Option de composition | Collection immutable, noms uniques, pas un runtime registry |

**Choix à confirmer :** si un `ToolCall` existe indépendamment d'une `InferenceResponse`, son identité est suffisante pour la comparaison, mais la corrélation à un `InferenceRunId` ne doit pas être inventée automatiquement. Une liaison explicite pourra être une valeur composite décidée à G0.

### 3.3. Exemple de relations

```text
InferenceRequest
  +-- target: InferenceTarget                         [M3 existant]
  +-- messages: tuple[Message, ...]                   [M2 existant]
  +-- generation_config?: GenerationConfig            [M3 existant]
  +-- tools?: tuple[Tool, ...]                         [P4 proposé]
  +-- tool_choice?: ToolChoice                         [P4 proposé]
  +-- response_format?: ResponseFormat                 [P4 proposé]

Tool ----1----> ToolSchema
ToolSet ----0..*----> Tool
ToolCall ----1----> ToolCallId
ToolCall ----1----> ToolArguments
ToolCall --tool_name--> ToolSet                        [validation contextuelle]
ToolResult --call_id--> ToolCall                       [0..1 result / call pour M4]

InferenceResponse
  +-- output: TextOutput                               [M3 existant]
  +-- ToolCallOutput / StructuredOutput?                [extension soumise a ADR]
```

Le `?` exprime une **question de design**, pas un champ déjà implémenté. La cardinalité 0..1 de `ToolResult` par `ToolCall` suit le MVP du document `06`; les résultats partiels multiples attendront une ADR propre à Streaming.

---

## 4. P4-BOOT : registre des ADR à arbitrer avant code

La numérotation **ADR-022 à ADR-029 est proposée**, car le dépôt dispose aujourd'hui d'ADR-001 à ADR-021. Il faut vérifier les collisions au moment de la création. **Les huit ADR-022 à ADR-029 sont ACCEPTED par décision du propriétaire le 5 novembre 2026; voir le registre P4-G0.**

| ADR candidate | Question à trancher en G0 | Options à comparer | Décision attendue |
|---|---|---|---|
| **ADR-022** | Frontière `Tool` / `ToolCall` / exécuteur | VOs/Entity purs vs commandes exécutables | Contrat descriptif, no executor |
| **ADR-023** | Identité et corrélation `ToolCallId` | ID opaque vs source provider; result 0..1 vs 0..* | Typage, unicité et contexte explicite |
| **ADR-024** | `ToolSchema` et profil JSON Schema | Profil local minimal vs Draft standard complet + dependency optionnelle | Dialecte, `$ref`, limites, validateur, garantie réelle |
| **ADR-025** | Raw / parsed / validation et JSON immuable | Défensive-copy + freeze vs AST JSON immuable | Pas de mutation indirecte, aucun parser implicite |
| **ADR-026** | `ToolChoice` et capabilities | Union typée vs enum + name; NATIVE/EMULATED/UNKNOWN | Stratégie et support sans invention |
| **ADR-027** | `ResponseFormat` / `StructuredOutput` | Variants, statut de conformité, raw, strictness | Représentation et états d'échec |
| **ADR-028** | Composition P4 avec M3 | Étendre Request/Response + version v2 **ou** wrapper P4 explicite | Compatibilité API et migration vérifiables |
| **ADR-029** | Sérialisation P4 et compatibilité | Enveloppe Tooling JSON v1 indépendante + éventuel Inference JSON v2 | V1 intouchables, unknown fields refusés |

### 4.1. Arbitrage critique : Request/Response et JSON v1

**Option A : extension explicite des Value Objects M3.** Ajouter des champs optionnels `tools`, `tool_choice` et `response_format` à `InferenceRequest`, et des variants de sortie à `InferenceResponse` si retenus. Nécessite le contrat de migration des constructeurs, tests sur `eq/hash/representations`, et **Inference JSON v2** pour tout nouveau champ ou kind. Le codec v1 doit **rejeter explicitement** toute valeur P4 non représentable, et non la tronquer.

**Option B : composition séparée.** Garder les classes M3 intactes et introduire un wrapper de domaine `ToolingInferenceIntent` / `StructuredInferenceIntent` qui assemble la demande M3 et ses options. Avantage : API M3 inchangée; coût : composition plus complexe et second contrat public.

**Recommandation de travail :** évaluer d'abord **l'option B pour le lot initial** afin d'éviter la modification opportuniste d'un contrat M3 qualifié, puis adopter A seulement si les cas d'acceptation justifient le coût d'une v2 et que les tests de migration sont écrits. C'est une **recommandation**, pas une ADR adoptée.

**Interdits dans les deux options :**

- Ne jamais ajouter des clés `tools`, `tool_choice` ou `response_format` à une enveloppe Inference JSON v1 existante.
- Ne jamais accepter une nouvelle valeur puis l'omettre silencieusement dans `request_to_dict`, `response_to_dict` ou `run_to_dict`.
- Ne jamais décoder une sortie `ToolCallOutput` en `TextOutput` fictif.
- Ne jamais convertir un `UNKNOWN` de support en `NATIVE` ou supposer une compatibilité provider.
- Ne jamais introduire de `ToolCallContent` ou `ToolResultContent` dans Interaction JSON v1 sans contrat versionné et tests de non-régression.

### 4.2. Arbitrage JSON Schema et sécurité

Le corpus exige un schéma **valide**, mais ne décide ni du **dialecte** ni d'une bibliothèque de validation. En G0, décider :

1. Le dialecte revendiqué, par exemple JSON Schema Draft 2020-12, ou bien un **profil explicitement partiel**.
2. Si le `ToolSchema` embarque un JSON-compatible immutable, un schéma typé ou un AST interne.
3. Les mots-clés autorisés, les `$ref` locaux et le refus des références réseau; interdire le chargement distant implicite.
4. Les types Python exacts, les nombres non finis et les limites de taille, profondeur et récursion.
5. La validation structurelle du schéma **distincte** de la validation d'instances et de la sortie.
6. L'usage éventuel d'un validateur tiers : dépendance facultative ou développement de profil limité, sans promesse de conformité complète.
7. La présence ou non d'une politique de conversion `raw_json -> parsed` dans le domaine; la politique de **texte JSON externe** reste au futur boundary applicatif (`issue #36`).

**NO-GO G0 :** toute proposition qui annonce "support complet JSON Schema" sans validateur défini et tests correspondants.

### 4.3. Conditions de sortie P4-G0

- ADR-022..029 acceptées ou remplacées par des décisions équivalentes **consignées** par le propriétaire.
- Signatures publiques et règle d'égalité/immutabilité définies pour chaque objet.
- Scope du schéma, règles de sécurité et migration M3 approuvés.
- Catalogues d'erreurs et d'événements P4 définis, sans promesse d'émission runtime.
- Matrice d'acceptation P4-AC-001..040 examinée et mise en cohérence avec les ADR.
- Revue des éventuelles tensions avec la gouvernance GitHub et le release runbook.
- PR documentaire G0 avec CI sur son SHA, merge contrôlé et CI de `main`, puis `P4_G0_GATE_REVIEW.md`.
- **Aucune PR L4.1 de code public avant P4-G0.**

---

## 5. L4.1 - Tool Definition, ToolSchema & ToolChoice

### 5.1. Objectif

Déclarer des outils, leurs paramètres et une politique de sélection **sans fournir d'implémentation exécutable**.

### 5.2. Contrats candidats

```python
# PSEUDO-SIGNATURES P4 : sujettes aux ADR de G0, PAS du code livre.
@dataclass(frozen=True, slots=True)
class ToolSchema:
    # JSON Schema profile agreed in ADR-024, immutable at every level
    ...

@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    description: str | None
    schema: ToolSchema

class ToolChoice:
    # Typed variants: Auto, None, Required, SpecificTool(name)
    ...
```

### 5.3. Invariants du lot

- Nom `Tool.name` non vide, stable dans un `ToolSet`; politique de caractères/casse explicite, pas d'hypothèse sur le provider final.
- Schéma structurellement valide selon **le profil accepté**, sans chargement réseau ni mutation indirecte de dictionnaires Python.
- Deux `Tool` de même nom au sein d'une même request doivent provoquer un rejet; deux noms différents peuvent partager un schéma.
- `ToolChoice.SPECIFIC_TOOL` doit référencer un `Tool` disponible; `REQUIRED` avec liste vide est incohérent.
- `NONE` avec une tool declaration non vide n'autorise **aucune** invocation automatique. La présence d'outils ne prouve pas le support `TOOL_CALLING`.
- Les limites de nombre/taille des outils ne sont **pas inventées** comme universelles : les quotas applicables restent ceux de l'application et du provider, éventuellement connus par snapshot.

### 5.4. Backlog L4.1

| Tâche | Livraison | Test minimal |
|---|---|---|
| P4-L41-T01 | `ToolSchema` immuable, valideur structurel du profil | Objet mutable original n'altère pas le VO |
| P4-L41-T02 | `Tool` typé et représentation sécurisée | Nom vide, typage invalide refusés |
| P4-L41-T03 | `ToolChoice` discriminé | AUTO/NONE/REQUIRED/SPECIFIC cohérents |
| P4-L41-T04 | `validate_tool_set` et `validate_tool_choice` | Unicité, tool spécifique absent |
| P4-L41-T05 | API publique `pyllmkit.domain.tooling` (selon ADR) | Imports et types exacts |
| P4-L41-T06 | `examples/13_define_tools.py` | Sans provider ni exécution |
| P4-L41-T07 | Docs d'API et tests d'architecture | Domaine sans dépendance au runtime |

**P4-G1 - Tool Declaration Ready :** contrats immuables, validation des noms/schémas/choix, tests négatifs et CI sur `main`, sans fonction d'exécution d'outil.

---

## 6. L4.2 - ToolCall, ToolArguments & ToolResult

### 6.1. Objectif

Représenter une **demande d'appel** corrélée à un outil déclaré et un **résultat observé**, sans appeler cet outil.

### 6.2. Contrats candidats

```python
# PSEUDO-SIGNATURES P4 : modèle d'intention seulement.
@dataclass(frozen=True, slots=True)
class ToolCallId:
    value: str

@dataclass(frozen=True, slots=True)
class ToolArguments:
    raw: str | None = None
    # parsed: JSON value representation immuable, optionnelle
    # validation_status: UNKNOWN / VALID / INVALID (à décider)
    ...

@dataclass(frozen=True, slots=True, eq=False)
class ToolCall:
    call_id: ToolCallId
    tool_name: str
    arguments: ToolArguments

@dataclass(frozen=True, slots=True)
class ToolResult:
    call_id: ToolCallId
    value: object  # type réel à figer dans ADR; jamais objet arbitraire non-JSON
    is_error: bool
```

### 6.3. Invariants du lot

- `ToolCallId` explicite, unique dans le contexte de validation, non généré silencieusement avec UUID.
- L'égalité d'un `ToolCall` Entity dépend de son ID, pas des arguments; deux appels de paramètres identiques restent deux appels.
- `ToolCall.tool_name` référence un outil présent dans l'ensemble fourni au validateur. Une déclaration absente n'est pas ignorée.
- `ToolArguments.raw` et la valeur parsed sont **des informations différentes**; ne pas inférer `parsed` valide à partir du simple fait qu'une chaîne soit non vide.
- Si le parsing/validation des arguments échoue, conserver un résultat explicite d'échec sans faire passer la valeur comme conforme.
- Le payload du résultat est immutable/JSON-compatible selon l'ADR, et ne peut pas contenir du code exécutable implicite.
- `ToolResult.call_id` correspond à un appel existant. Une correspondance `tool_name` seule n'est jamais suffisante.
- Pour M4 : **au plus un résultat final par appel** dans un contexte déterministe; répétition/contradiction refusée. Les deltas partiels restent P5.
- `is_error=True` doit pouvoir représenter l'échec; le texte détaillé d'une erreur provider n'entre pas en clair dans les messages d'exception.
- `ToolCall` décrit une requête du modèle et **ne déclenche pas** un exécuteur.

### 6.4. Backlog L4.2

| Tâche | Livraison | Test minimal |
|---|---|---|
| P4-L42-T01 | `ToolCallId` et identité `ToolCall` | Collision, égalité, IDs invalides |
| P4-L42-T02 | `ToolArguments` raw/parsed/état | Échec parsing, non-finite, copie défensive |
| P4-L42-T03 | `ToolResult` corrélé, `is_error` exact | Mauvais ID, bool incorrect, secret non divulgué |
| P4-L42-T04 | `validate_tool_call` | Tool absent, schéma arguments non conforme |
| P4-L42-T05 | `attach_tool_result` **pure** (résultat/contexte immuable) | Doublon rejeté, ordre respecté |
| P4-L42-T06 | `examples/14_define_tool_call_and_result.py` | Cycle simulé sans exécuteur |
| P4-L42-T07 | Suite de cas positifs et négatifs | Références, cardinalité, identité |

**P4-G2 - Tool Call Ready :** tous les appels/résultats représentables et corrélables, erreurs contrôlées, aucun effet de bord.

---

## 7. L4.3 - ResponseFormat & StructuredOutput

### 7.1. Objectif

Exprimer **ce qu'une réponse devrait respecter** et **ce qui a réellement été validé**. Une demande de sortie structurée n'est pas une garantie qu'un modèle ou qu'un provider l'a satisfaite.

### 7.2. Variants proposés

| Type | Sémantique | Garantie |
|---|---|---|
| `TextResponseFormat` | Réponse textuelle libre | Aucune promesse de JSON |
| `JsonResponseFormat` | JSON attendu | Une valeur structurée conforme uniquement après parsing/validation |
| `SchemaResponseFormat` | JSON conforme au `ToolSchema` ou à un schéma de sortie dédié | Strictness explicite, profil documenté, validation réelle |
| `StructuredOutput` | Résultat brut, valeur parsée éventuelle, statut de conformité | Invalid/unknown ne peut pas devenir VALID |
| `StructuredValidationResult` | Rapport immuable | Diagnostics bornés et sécurisés, aucune fuite de payload sensible |

### 7.3. Règles

- `response_format` absent signifie **non spécifié**, jamais `JsonResponseFormat` par défaut.
- `TextResponseFormat` ne revendique aucune capability de structured output.
- `JsonResponseFormat` peut être déclaré `NATIVE`, `EMULATED` ou `UNKNOWN` **si** le caller fournit une information fiable; aucune promotion automatique.
- Un `SchemaResponseFormat` ne peut pas contenir un schéma invalide selon le profil G0.
- `strict=True/False/None` a une sémantique documentée; `None` ne vaut pas `False`.
- Validation du schéma, parsing JSON et validation du résultat sont trois opérations distinctes, avec des erreurs séparées.
- Un `StructuredOutput` invalide a un statut explicite et ne doit pas être sérialisé comme validé.
- Les valeurs raw peuvent contenir des secrets; `repr`, exceptions et logs de test ne les recopient pas.
- La politique des `$ref`, la complexité du schéma et le risque de déni de service sont traités avant une implémentation de validation avancée.
- Aucune exécution LLM, aucun "repair" de sortie automatique et aucun fallback de provider en M4.

### 7.4. Backlog L4.3

| Tâche | Livraison | Test minimal |
|---|---|---|
| P4-L43-T01 | Trois Value Objects ResponseFormat | Variants et strictness exacts |
| P4-L43-T02 | `StructuredOutput` et état de validation | Invalid et UNKNOWN préservés |
| P4-L43-T03 | Validateur de schéma selon ADR-024 | Schéma structurellement invalide rejeté |
| P4-L43-T04 | Validateur de valeur selon format | Type faux, required manquant, extra refusé si profil |
| P4-L43-T05 | Évaluation de support STRUCTURED_OUTPUT | NATIVE, EMULATED, UNKNOWN, UNSUPPORTED distincts |
| P4-L43-T06 | `examples/15_validate_structured_output.py` | Valeur valide et invalide sans provider |
| P4-L43-T07 | Docs de limites et de garanties | Pas de conformité complète inventée |

**P4-G3 - Structured Output Ready :** validité structurelle et statut de conformité prouvés, erreurs contrôlées, garanties calibrées sur le profil approuvé.

---

## 8. L4.4 - Composition avec M3, codecs et compatibilité

### 8.1. Objectif

Rendre les primitives P4 utilisables ensemble avec M3 sans casser un contrat public v1. **Cette étape ne peut commencer que si ADR-028 et ADR-029 sont ACCEPTED.**

### 8.2. Résultats attendus

1. Une manière *officielle* de joindre `Tool`, `ToolChoice` et `ResponseFormat` à une intention d'inférence.
2. Une manière *officielle* de représenter un `ToolCallOutput` et un `StructuredOutput` sans tromper sur `TextOutput`.
3. Une politique explicite de compatibilité tool calling/structured output à partir de **capabilities déclarées**, pas du snapshot M3 destiné aux paramètres de génération.
4. Un **codec Tooling JSON v1 indépendant**, ou une autre forme approuvée par G0, pour les primitives P4.
5. Une évolution **Inference JSON v2** *seulement si* les nouvelles valeurs doivent s'intégrer dans les enveloppes Request/Response/Run.
6. Des règles de migration des anciennes valeurs, de rejet d'un variant non représentable et de refus des clés inconnues.

### 8.3. Politique normative proposée

| Format | État | Politique de compatibilité |
|---|---|---|
| Model JSON v1 | M1 qualifié | Inchangé, tests M1 PASS |
| Interaction JSON v1 | M2 qualifié | Inchangé; aucun ToolCallContent nouveau en v1 |
| Inference JSON v1 | M3 qualifié | Inchangé; une valeur P4 non représentable **échoue** au lieu d'être tronquée |
| Tooling JSON v1 | P4 candidat | Nouveau namespace, version et object_type distincts, clés exactes |
| Inference JSON v2 | Conditionnel à ADR-028/029 | Nouveau contrat/codec sans modifier le v1, migration explicite |

L'implémentation choisie doit pouvoir effectuer une transformation ou un round-trip sur les valeurs représentables **sans inventer de champs, de finish reason, de tool call ou de résultat**. Un `ToolCallOutput` ne signifie pas qu'un outil est exécuté; `FinishReasonCode.TOOL_CALL` ne signifie pas qu'un `ToolResult` existe.

### 8.4. Risques à tester

- Retours silencieux à TextOutput, perte de `raw`/`parsed`, perte d'ID.
- JSON dupliqué, listes mal typées, clés inconnues, versions inconnues.
- Objets Python dict/list mutables ayant corrompu une représentation frozen.
- Cohérence `ToolChoice.SPECIFIC_TOOL` avec le tuple d'outils.
- Inference JSON v1 qui accepte par mégarde des clés v2.
- Inference JSON v2 qui "downgrade" une valeur P4 en v1 avec perte de sens.
- Imports cycliques entre `domain.inference`, `domain.tooling`, `domain.structured_output`.

### 8.5. Backlog L4.4

| Tâche | Livraison | Preuve |
|---|---|---|
| P4-L44-T01 | Contrat de composition approuvé | Test M3 + P4 avec 0, 1 et plusieurs tools |
| P4-L44-T02 | Support explicite TOOL_CALLING/STRUCTURED_OUTPUT | UNKNOWN ne devient pas supporté |
| P4-L44-T03 | Codec Tooling JSON v1 | Round-trip, types exacts, versions inconnues |
| P4-L44-T04 | Éventuel Inference JSON v2 | P3 v1 inchangé + tests de migration |
| P4-L44-T05 | Guard d'architecture contre adapter leakage | Aucun SDK, réseau, exécuteur, secret |
| P4-L44-T06 | `examples/16_tooling_json_round_trip.py` | Cycle offline, aucune mutation |
| P4-L44-T07 | Documentation de transition et API | Contrat de compatibilité public |

**P4-G4 - Integration Contract & Codec Ready :** composition explicite approuvée, round-trip sans perte, M1-M3 intacts et CI de non-régression.

---

## 9. L4.5 - Intégration, documentation, qualité et packaging

### 9.1. Livrables

- `docs/architecture/PHASE_4_TOOLING_AND_STRUCTURED_OUTPUT_CONTRACTS.md`
- `docs/architecture/TOOLING_JSON_SCHEMA_V1.md` et, si décidé, `INFERENCE_JSON_SCHEMA_V2.md`
- `docs/concepts/tool-definition.md`, `tool-call.md`, `structured-output.md`
- `docs/api/tooling.md`, `docs/api/structured-output.md` et mise à jour conditionnelle de `docs/api/inference.md`
- `docs/quality/PHASE_4_TRACEABILITY.md` et `docs/quality/P4_L4x_IMPLEMENTATION_SUMMARY.md`
- `docs/quality/P4_G0_GATE_REVIEW.md` à `P4_G5_GATE_REVIEW.md`
- `docs/quality/M4_READINESS_PRECHECK.md` et, après revue indépendante, `M4_GATE_REVIEW.md`
- Exemples `13` à `17` et README copiable.
- Wheel/sdist clean installs et smoke des imports depuis des environnements isolés.
- ROADMAP/CHANGELOG alignés avec le statut **réel** des livrables, jamais avec des gates imaginés.

### 9.2. Backlog L4.5

| Tâche | Livrable | Gate |
|---|---|---|
| P4-L45-T01 | Revue transversale des exports et choix de nommage | G5 |
| P4-L45-T02 | Documentation d'architecture, concepts, API et schémas | G5 |
| P4-L45-T03 | Traçabilité P4-AC-001..040 aux sources, ADR et tests | G5 |
| P4-L45-T04 | `examples/17_full_tooling_walkthrough.py`, pure/offline | G5 |
| P4-L45-T05 | Tests de snippets README et API | G5 |
| P4-L45-T06 | Wheel/sdist, `py.typed`, metadata/licence, aucun provider SDK | G5 |
| P4-L45-T07 | Audit final des NO-GO et risque de release | Précheck M4 |
| P4-L45-T08 | PR documentaire et preuve exacte sur `main` | G5 |

**P4-G5 - Integration & Quality Ready :** aucune recette P4 bloquante en échec, docs et examples copiables, CI avec matrix verte et packaging vérifié sur commit intégré.

---

## 10. Catalogue des cas d'acceptation P4 (proposition)

Ces identifiants **P4-AC-001..040 sont nouveaux**. Le document `01` définit UC/FR, le document `07` définit les invariants TOOL; les numéros P4-AC ci-dessous servent au pilotage de l'implémentation et doivent être confirmés en G0.

| ID | Scénario | Source principale | Critère de succès |
|---|---|---|---|
| **P4-AC-001** | Définir un `Tool` valide et immutable | FR-025, TOOL-001/003 | Description stable, zéro effet de bord |
| P4-AC-002 | Refuser un nom vide, non-str ou invalide selon profil | TOOL-001 | DomainValidationError explicite |
| P4-AC-003 | Refuser un `ToolSchema` structurellement invalide | TOOL-002 | Erreur contrôlée, pas d'exécution |
| P4-AC-004 | Modifier le dictionnaire Python initial du schéma | NFR-006 | `ToolSchema` ne change pas |
| P4-AC-005 | Deux tools avec même nom dans `ToolSet` | ValidateToolSet | Doublon rejeté |
| P4-AC-006 | `ToolChoice` AUTO/NONE/REQUIRED | UC-011 | Choix distincts et stables |
| P4-AC-007 | `SpecificTool(name)` inexistant | TOOL-005 | Rejet contextuel |
| P4-AC-008 | Choix REQUIRED mais ensemble d'outils vide | TOOL-001/005 | Rejet, aucun fallback |
| **P4-AC-009** | Deux ToolCalls identiques en arguments, IDs différents | TOOL-004, `05` | Deux entités distinctes |
| P4-AC-010 | `ToolCallId` manquant ou vide | TOOL-004 | Rejet |
| P4-AC-011 | Appel un outil absent du contexte fourni | TOOL-005 | Rejet, pas de drop |
| P4-AC-012 | Conserver raw et parsed distincts | TOOL-008 | Aucun parsing inventé |
| P4-AC-013 | Arguments invalides face au schéma | ValidateToolCall | Diagnostic invalide, sans exécution |
| P4-AC-014 | Attacher un résultat au mauvais `call_id` | TOOL-006 | Rejet explicite |
| P4-AC-015 | Attacher deux résultats finaux au même appel | `06` MVP 0..1 | Doublon final rejeté |
| P4-AC-016 | `ToolResult` de type échec | TOOL-009 | `is_error=True` conservé, sans fuite |
| **P4-AC-017** | `TextResponseFormat` | TOOL-011/015 | Aucun JSON imposé |
| P4-AC-018 | `JsonResponseFormat` | TOOL-016 | Exigence JSON distincte de validation effective |
| P4-AC-019 | `SchemaResponseFormat` sans schéma valide | TOOL-012 | Rejet |
| P4-AC-020 | `strict=None` vs `False` | TOOL-017 | Absence distincte de non-strict |
| P4-AC-021 | Valider une sortie structurée conforme | ValidateStructuredOutput | Statut VALID démontré par validateur |
| P4-AC-022 | Rejeter/signaliser sortie JSON invalide | TOOL-014/020 | Statut INVALID, jamais VALID |
| P4-AC-023 | UNKNOWN / EMULATED / NATIVE de support | TOOL-013 | Pas de promotion en NATIVE |
| P4-AC-024 | Conserver output brut sans l'exposer en erreur | TOOL-021 | Repr/erreurs sans fuite sensible |
| **P4-AC-025** | Composer M3 Request + ToolSet et choix | `06` relations | Composition sans mutation M3 |
| P4-AC-026 | Request avec tools, capability UNSUPPORTED | INF-009 | Rejet de support connu |
| P4-AC-027 | Request avec SchemaFormat, support UNKNOWN | INF-010 | UNKNOWN explicite |
| P4-AC-028 | ToolCallOutput sans résultat exécuté | INV-010 | Pas de résultat inventé |
| P4-AC-029 | Outillage non représentable dans Inference JSON v1 | ADR-020/028/029 | Échec, **pas** de drop |
| P4-AC-030 | Round-trip Tooling JSON v1 | NFR-008 | Identités, raw/parsed et ordre conservés |
| P4-AC-031 | Version ou variant JSON inconnu | NFR-008/010 | Rejet, pas d'extension silencieuse |
| P4-AC-032 | Test régressions Model/Interaction/Inference v1 | M1/M2/M3 | Anciennes suites PASS |
| **P4-AC-033** | Le core n'importe pas d'executor / réseau / SDK | Domain First, TOOL-003 | Fitness tests PASS |
| P4-AC-034 | Appeler les validateurs sans credentials | NFR-003/005 | Suite offline PASS |
| P4-AC-035 | Boucle Python autonome : tool -> call -> result | UC-011/012 | Exemple exécutable sans provider |
| P4-AC-036 | Exemples et snippets README copiables | NFR qualité | Test d'exécution PASS |
| P4-AC-037 | Imports et wheel/sdist isolés | NFR-001/004 | Python 3.11/3.12/3.13 PASS |
| P4-AC-038 | JSON malveillant, schéma profond, réf distante | ADR-024, qualité | Refus/limite selon profil approuvé |
| P4-AC-039 | Métadonnées secrets ou valeurs sensibles dans erreur | NFR sécurité | Aucune donnée source divulguée |
| P4-AC-040 | Relecture des 40 recettes et gates G0..G5 | Convention PyKit | Traceabilité complète, preuves `main` |

### 10.1. Jeu de tests négatifs indispensable

- Identifiants non-str, vides, collisions et booléens utilisés comme types entiers.
- Tool schema mutable réutilisé après construction, clés non-str, profondeur excessive, cycle dans un dict Python.
- Schéma JSON avec `$ref` distant interdit, type non reconnu, combinaison de mots-clés hors profil.
- Arguments raw non valides, parsed absent, parsed invalide déclaré VALID, NaN/Infinity et deep nesting.
- `ToolChoice` SPECIFIC sans outil disponible, REQUIRED sans tool, doublons de noms.
- Call inconnu, result orphelin, mauvais `call_id`, plusieurs résultats finaux pour un call.
- Erreur d'outil sérialisée sans statut `is_error` ou divulguant un secret.
- `strict=None` converti en `False`, sortie non valide déclarée conforme.
- `TOOL_CALLING=UNKNOWN` ou `STRUCTURED_OUTPUT=UNKNOWN` converti en NATIVE.
- Inference JSON v1 qui accepte par erreur une extension P4, ou sérialiseur qui supprime des champs P4.
- Anciennes classes M3 dont l'égalité, le `repr`, les defaults ou l'immutabilité changent involontairement.

---

## 11. Matrice de traçabilité exigences -> lots -> preuves

| Référence fondatrice | Invariant / capacité | Lots concernés | Preuves cibles |
|---|---|---|---|
| UC-011 / FR-025 | Définition Tool | L4.1 | AC-001..008 |
| UC-011 / FR-026 | ToolCall, identité et arguments | L4.2 | AC-009..013 |
| UC-011 / FR-027 | ToolResult, erreur et corrélation | L4.2 | AC-014..016 |
| UC-012 / FR-028 | ResponseFormat/StructuredOutput | L4.3 | AC-017..024 |
| TOOL-001..003 | Nom/schéma valides, pas d'exécution | L4.1 | AC-001..005, 033 |
| TOOL-004..010 | CallId, tool disponible, résultats et raw/parsed | L4.2 | AC-009..016 |
| TOOL-011..017 | Formats, validité, support natif/émulé | L4.3 | AC-017..024 |
| TOOL-018..021 | Correlation dans context, validation et raw | L4.2/L4.3 | AC-014..016, 022, 024 |
| INF-009/010 | Support explicite et pas de fallback | L4.4 | AC-025..027 |
| `09` ToolCallObserved/ToolResultAttached | Événements de domaine conceptuels | L4.4 | Aucune publication runtime |
| M1/M2/M3 v1 | Backward compatibility | L4.4/L4.5 | AC-029..032 |
| NFR-001..010 | Python, typage, offline, serialization | L4.5 | AC-033..040 |

**Traçabilité obligatoire à l'implémentation :** chaque AC doit correspondre à un test nommé, à un numéro de PR et à la preuve CI du **SHA de `main`** qui l'a qualifié. La seule présence du test n'est pas une preuve d'exécution.

---

## 12. Stratégie de qualité et CI

### 12.1. Tests unitaires

- Invariants exacts des Value Objects : type exact, nullabilité, immutabilité profonde et `repr` redacted.
- Identité `ToolCall`, corrélation du `ToolResult`, unicité et cardinalité dans contexte.
- Validation structurale des schémas vs validation d'une valeur.
- Support/compatibility sans provider, transitions de statut de validation explicites.
- Codec round-trips et rejets de versions inconnues.

### 12.2. Tests d'acceptation

Créer `tests/acceptance/test_p4_l41_tools.py`, `test_p4_l42_tool_calls.py`, `test_p4_l43_structured_output.py`, `test_p4_l44_contracts_and_codecs.py` et `test_p4_l45_integration.py`, avec 40 cas P4-AC traçables.

### 12.3. Architecture fitness

- `domain` ne doit importer ni `openai`, ni `anthropic`, ni `httpx`, ni un executor Python arbitraire.
- Les imports P4 -> M1/M2/M3 autorisés sont explicitement tracés; éviter les cycles.
- Aucun appel réseau, accès fichiers ou requête de secret dans les validateurs de domaine.
- Les adapters futurs restent hors domaine et soumis à [#36](https://github.com/tawounfouet/pyllmkit/issues/36).
- Les codecs v1 antérieurs restent importables et leurs formats inchangés.

### 12.4. Matrice CI cible

| Contrôle | Politique |
|---|---|
| Python | 3.11, 3.12, 3.13 |
| Ruff | `ruff check .`, PASS |
| mypy | `mypy src/pyllmkit` strict, PASS |
| pytest | Toute la suite M1/M2/M3/M4, 0 test bloquant rouge |
| Coverage | Branch coverage, cible **au moins le niveau qualifié M3 de 95 %** ou décision documentée avant gate |
| Offline | Aucune clé provider requise, aucun réseau dans tests de domaine |
| Examples | Exemples existants 01..12 + nouveaux 13..17 |
| Build | Wheel et sdist, sans publier |
| Clean installs | Imports et walkthrough P4 depuis wheel et sdist |
| Docs/README | Snippets compilés/exécutés, chemins réels, versions cohérentes |
| Security | Aucun raw prompt / token / tool result dans exceptions et logs, pas de fonctions dangereuses exécutées |
| Dependencies | Toute dépendance supplémentaire est approuvée en ADR et conditionnée au périmètre concerné |

Une CI de PR verte **n'est pas** un gate GO. Le gate nécessite aussi la **CI du commit intégré à `main`**. Ne pas revendiquer une protection de branche effective tant que [#22](https://github.com/tawounfouet/pyllmkit/issues/22) reste ouvert.

---

## 13. Structure de code candidate

```text
src/pyllmkit/
  domain/
    tooling/                         # L4.1, L4.2
      __init__.py
      identifiers.py                  # ToolCallId
      definitions.py                  # Tool, ToolSchema
      choice.py                       # ToolChoice
      arguments.py                    # ToolArguments
      calls.py                        # ToolCall, ToolResult
      validation.py                   # ToolSet, ValidateToolCall, AttachToolResult
      serialization.py                # Tooling JSON v1 si ADR-029
    structured_output/               # L4.3
      __init__.py
      formats.py                      # Text/Json/SchemaResponseFormat
      result.py                       # StructuredOutput
      validation.py                   # structured output validation
    inference/                       # M3 existant, modifié SEULEMENT selon ADR-028
      request.py
      response.py
      serialization.py               # Codec Inference JSON v1 à préserver
      serialization_v2.py            # Option, seulement si ADR-029
tests/
  unit/domain/tooling/
  unit/domain/structured_output/
  acceptance/test_p4_*.py
  architecture/
  packaging/
examples/
  13_define_tools.py
  14_define_tool_call_and_result.py
  15_validate_structured_output.py
  16_tooling_json_round_trip.py
  17_full_tooling_walkthrough.py
docs/
  adr/ADR-022-*.md ... ADR-029-*.md
  architecture/PHASE_4_*.md
  api/tooling.md
  api/structured-output.md
  concepts/
  quality/P4_G0_GATE_REVIEW.md ... P4_G5_GATE_REVIEW.md
  quality/M4_GATE_REVIEW.md
```

**Important :** cette arborescence est une proposition de design, **pas** un inventaire de code existant. P4-G0 pourra retenir des modules plus petits si les invariants n'exigent pas autant de fichiers. Privilégier KISS/YAGNI et le nombre minimal de contrats.

---

## 14. Pipeline de PR, gates et preuves GitHub

### 14.1. Séquence autorisée

1. **PR P4-BOOT** : registre de décisions, ADR proposées et plan revu. Approbation explicite du propriétaire, puis CI PR et CI `main`.
2. **PR L4.1** : déclarations `Tool`/`ToolSchema`/`ToolChoice`, tests et exemple; **G1 seulement après CI `main`**.
3. **PR L4.2** : `ToolCall`/`ToolArguments`/`ToolResult`, corrélation et cas d'erreur; **G2**.
4. **PR L4.3** : `ResponseFormat`/`StructuredOutput`, validation de schémas; **G3**.
5. **PR L4.4** : composition et codecs versionnés, tests M1-M4; **G4**.
6. **PR L4.5** : docs, README, exemples, packaging, traceability, audit; **G5**.
7. **Revue M4 séparée** : vérification transversale NO-GO, risques et preuve sur le dernier SHA qualifié.
8. **Toute release ultérieure** : autorisation distincte, [#22](https://github.com/tawounfouet/pyllmkit/issues/22) résolue et [#35](https://github.com/tawounfouet/pyllmkit/issues/35) qualifiée.

### 14.2. Convention par gate

- Capturer `base_sha`, `head_sha`, PR URL, CI de head, statuts des trois jobs Python.
- Fusionner en squash en vérifiant le `expected_head_sha` et les règles GitHub effectivement en vigueur.
- Capturer le **nouveau SHA de `main`** et sa propre CI `push`.
- Inspecter tests réussis, coverage, lint, mypy, exemples et smoke wheel/sdist sur ce SHA.
- Produire un `P4_Gx_GATE_REVIEW.md` dans une **PR documentaire distincte**.
- Vérifier ensuite la CI du SHA d'archivage et ajouter cette preuve à la PR.
- N'inscrire `GO` qu'après validation; ne pas confondre ancien P4-G0 et nouveau P4-G5.

### 14.3. Gouvernance en parallèle

Le [runbook de protection GitHub](governance/MAIN_BRANCH_PROTECTION_RUNBOOK.md) et l'[issue #22](https://github.com/tawounfouet/pyllmkit/issues/22) restent prioritaires. La disponibilité des droits GitHub App ne suffit pas à prouver l'enforcement. Il est possible de **préparer** la conception P4 pendant ce chantier, mais **ne pas autoriser de release** en l'absence de preuves de protection et de revue.

---

## 15. Registre de risques P4

| Risque | Signal | Prévention / gate |
|---|---|---|
| **R-P4-01 : execution creep** | `ToolCall` contient un callback exécutable ou appelle Python | TOOL-003, tests d'architecture dès G1 |
| **R-P4-02 : JSON v1 cassé** | Ajout de clés inconnues aux codecs M2/M3 | ADR-028/029, tests de régression G4 |
| **R-P4-03 : pseudo-conformité JSON Schema** | Validateur partiel revendique Draft complet | ADR-024, tests de schéma G0/G3 |
| **R-P4-04 : mutabilité cachée** | Dataclass frozen avec dict/list externe mutable | Deep freeze et tests G1/G2/G3 |
| **R-P4-05 : confusion raw/parsed** | Des arguments invalides déclarés valides | TOOL-008 et AC-012/013 |
| **R-P4-06 : résultat orphelin** | `ToolResult` sans `ToolCallId` reconnu | TOOL-006, tests G2 |
| **R-P4-07 : validation par supposition** | UNKNOWN -> NATIVE ou un JSON non vérifié -> VALID | Tests G3/G4 |
| **R-P4-08 : divulgation** | Schema, args, raw ou result copiés dans exception/repr | Tests de redaction G2/G3/G4 |
| **R-P4-09 : streaming prématuré** | `ToolCallDelta`/reassembly introduits en P4 | Reporter à P5, ne pas rendre Run mutable |
| **R-P4-10 : dépendances provider** | SDK ajouté au package core | CI offline et optionnalité G5 |
| **R-P4-11 : gouvernance** | `main` toujours non protégée, review absente | #22 demeure ouverte, release NO-GO |
| **R-P4-12 : release drift** | Version a4 ou a3 bump sans artefacts approuvés | [Runbook release](governance/RELEASE_0_1_0a3_POLICY_AND_RUNBOOK.md), #35 |

---

## 16. Gates P4 et M4 : matrice GO/NO-GO

| Gate | Conditions GO | NO-GO type |
|---|---|---|
| **P4-G0 - Architecture Ready** | ADR décidées, profil schema, ID, extension M3/v2, compatibilité approuvés | Codec v1 modifié sans version; validateur JSON non défini |
| **P4-G1 - Tool Declaration Ready** | Tool/ToolSchema/Choice immuables, uniqueness, tests negatifs, CI main | Tool exécutable; mutable schema; choix incohérent |
| **P4-G2 - Tool Call Ready** | ToolCallId, ToolArguments, ToolResult et corrélation validés | Résultat orphelin, échec caché, raw/parsed confondus |
| **P4-G3 - Structured Output Ready** | Formats typés et validation conforme au profil, états VALID/INVALID/UNKNOWN | Non-conformité marquée VALID ou support inventé |
| **P4-G4 - Integration Contract & Codec Ready** | Composition M3 explicite, versionnement non destructif, M1-M3 green | Champs P4 silencieusement supprimés; Inference JSON v1 rompu |
| **P4-G5 - Integration & Quality Ready** | 40 AC tracés, docs, examples, CI main, wheel/sdist | Documentation trompeuse, tests ou builds rouges |
| **M4 - Tooling & Structured Output Qualified** | Tous les gates GO, revue des risques, décision motivée sur SHA exact | Au moins une cause de NO-GO bloquante ou preuve absente |

### 16.1. NO-GO M4 obligatoires

M4 est **NO-GO** si l'un de ces cas est constaté :

1. Un objet `Tool`, `ToolCall` ou `ToolResult` exécute du code, du réseau ou accède à un secret caché.
2. L'identité `ToolCallId` manque, est ambigüe ou peut être remplacée par une seule égalité de noms/arguments.
3. Un résultat orphelin est accepté comme corrélé ou deux résultats finaux contradictoires sont considérés valides sans ADR.
4. Raw et parsed sont confondus, ou un argument/une sortie non conforme reçoit le statut VALID.
5. Une sortie structurée, un schéma ou une capability inconnue est convertie en succès/NATIVE sans preuve.
6. Un schéma mutable corrompt une Value Object prétendument immutable.
7. Une extension P4 casse ou tronque silencieusement Model/Interaction/Inference JSON v1.
8. Un variant `ToolCallOutput` est silencieusement converti en `TextOutput`.
9. Une dépendance provider, un executor ou des credentials sont requis pour exécuter les tests du domaine.
10. La prétendue prise en charge JSON Schema dépasse le profil réellement validé.
11. Un secret, une URL sensible ou un raw payload est exposé dans des erreurs/repr/logs lors des tests de non-divulgation.
12. Un test d'acceptation bloquant, Ruff, mypy, une version Python supportée, wheel/sdist ou exemple offline échoue sur le SHA qualifiant.
13. Une preuve de PR est présentée comme CI de `main`, ou les ADR/gates sont revendiqués sans adoption réelle.
14. Une documentation annonce un agent exécuteur, du streaming réel, un appel provider, ou une publication non effectuée.

### 16.2. Procès-verbal M4 à créer après exécution

```markdown
# M4 - Tooling & Structured Output Qualified - GO/NO-GO
- Date et responsable de décision :
- SHA exact de main et URL de commit :
- Version déclarée / version publiée :
- ADR-022..029 : ACCEPTED / REVISED / OPEN (sans supposition)
- P4-G0 / G1 / G2 / G3 / G4 / G5 : GO / NO-GO
- CI main exact, Python 3.11/3.12/3.13 :
- Tests PASS/FAIL, couverture globale et branches :
- Tool / ToolSchema / ToolChoice :
- ToolCallId / ToolArguments / ToolCall / ToolResult :
- ResponseFormat / StructuredOutput :
- Correlation / invariants / statut de validation :
- Composition M3 / schema Tooling JSON v1 / eventuel Inference JSON v2 :
- Regression Model v1 / Interaction v1 / Inference v1 :
- Domaine sans execution / reseau / SDK :
- Wheel, sdist, exemples offline et README :
- NO-GO obligatoires, chacun etaye :
- Risques/waivers / autorite d'acceptation :
- Decision technique M4 : GO / NO-GO :
- Decision version et release : SEPAREE / NON AUTORISEE :
- CI de l'archive apres merge (attestation PR) :
```

La revue M4 doit être **distincte du PV P4-G5**, comme la revue M3 l'était de G5. Elle n'implique aucune autorisation de publication.

---

## 17. Release, versionnement et gouvernance

La roadmap historique positionne la Phase 4 autour de **`0.1.0a4`**. Or le dépôt **déclare actuellement `0.1.0a2`** et la Phase 3 `0.1.0a3` n'a jamais été publiée. Un planning technique M4 peut progresser **sans** avancer la version du package.

Règles :

1. P4 peut débuter **en conception** après adoption de ce plan et d'ADR G0. Le GO technique M3 existe déjà.
2. **Aucun bump `0.1.0a4` automatique**, et aucune création de tag, GitHub Release, TestPyPI ou PyPI par ce plan.
3. Le passage `0.1.0a2 -> 0.1.0a3` demeure traité séparément par [#35](https://github.com/tawounfouet/pyllmkit/issues/35), après règlement des conditions de gouvernance de [#22](https://github.com/tawounfouet/pyllmkit/issues/22).
4. Le jalon `0.1.0a4` sera revu selon l'historique réel des versions publiées et l'API approuvée au moment de M4.
5. Le provider boundary [#36](https://github.com/tawounfouet/pyllmkit/issues/36) est indépendant de P4 : l'intégration réelle devra se conformer au runbook d'adapters, pas modifier un Value Object silencieusement.

---

## 18. Apprentissage, conception et DoD de chaque lot

Pour chaque L4.x, le rapport d'implémentation devra rendre explicite :

- **DDD :** pourquoi l'objet est Entity ou Value Object, quelle identité et quels invariants.
- **SOLID / SoC / DIP :** frontière de dépendance, ports futurs vs domaine effectivement livré.
- **GoF / patterns :** uniquement ceux qui apportent une sémantique vérifiable (Strategy pour validation si nécessaire, Specification pour règles, Anti-Corruption Layer future).
- **DRY / KISS / YAGNI :** préserver les API et éviter l'introduction prématurée d'un Executor, Runtime, Registry ou Client.
- **Python idiomatique :** `dataclass(frozen=True, slots=True)` là où pertinent, `StrEnum`/unions discriminées, types exacts, erreurs explicites et fonctions pures.
- **Validation :** tests positifs, tests négatifs, propriétés immuables, absence d'I/O et benchmark de complexité seulement si une limite est définie.
- **Documentation :** exemple hors ligne copiable, docstrings de contrat, ADR référencée, diagramme sans confusion entre données, imports et exécution.
- **Preuve :** CI PR, CI `main` SHA exact, PV de gate, puis contrôle de la CI d'archivage.

La convention [`PYKIT_DELIVERY_AND_LEARNING_LOOP.md`](governance/PYKIT_DELIVERY_AND_LEARNING_LOOP.md) est obligatoire comme méthode de suivi, mais ne remplace pas les invariants propres à P4.

---

## 19. Ordonnancement et dépendances

```text
M3 (GO technique, avec reserves)
              |
              v
     P4-BOOT / ADR-022..029
              |
              v
       P4-G0 Architecture
              |
              v
     L4.1 Tool Declaration   ---> P4-G1
              |
              v
     L4.2 Call and Result    ---> P4-G2
              |
              v
     L4.3 Structured Output  ---> P4-G3
              |
              v
     L4.4 Contracts & Codec  ---> P4-G4
              |
              v
     L4.5 Integration        ---> P4-G5
              |
              v
     M4 independent GO/NO-GO
              |
              +--> NO-GO -> remediation + new evidence
              |
              +--> GO technique -> Phase 5 Streaming planning
                                      (release requires separate approval)

Parallel, NON bloquant pour le design P4 :
   #22 main governance / #35 release / #36 future provider boundary

Bloquant pour toute publication :
   #22 effective protection + explicit release authorization
```

### Ordre conseillé de la prochaine session

1. Faire examiner et accepter **ce plan** (ou amender ses limites).
2. Rédiger les ADR P4 proposées avec alternatives et cas d'usage, **sans les marquer ACCEPTED par défaut**.
3. Trancher **ADR-028/029** et **ADR-024** avant de figer les signatures.
4. Préparer la matrice P4-G0 et son procès-verbal technique.
5. Commencer **L4.1 seulement après GO P4-G0**, puis itérer par lots et gates.

---

## 20. Checklist finale d'approbation du plan

- [ ] Le propriétaire approuve le périmètre et les exclusions de la Phase 4.
- [ ] Les 40 P4-AC sont validés ou révisés dans la matrice officielle.
- [ ] Les noms des ADR candidates et la politique de JSON Schema sont approuvés en P4-G0.
- [ ] L'extension ou la composition avec M3 est tranchée en ADR-028.
- [ ] Le contrat Tooling JSON v1 et un éventuel Inference JSON v2 sont tranchés en ADR-029.
- [ ] L'immutabilité profonde et le format des arguments/résultats sont définis.
- [ ] La distinction "déclaration de Tool" vs "exécution de Tool" est maintenue dans toutes les API.
- [ ] La compatibilité M1/M2/M3 est définie comme critère bloquant G4/M4.
- [ ] Les moyens de CI Python 3.11-3.13 et les tests wheel/sdist restent disponibles.
- [ ] La gouvernance [#22](https://github.com/tawounfouet/pyllmkit/issues/22) est suivie et ne donne lieu à aucune fausse attestation.
- [ ] Le processus release [#35](https://github.com/tawounfouet/pyllmkit/issues/35) reste distinct.
- [ ] Aucun code P4, changement de version ni publication n'est pris pour acquis avant preuve.

---

## 21. Statut et décision proposée

**Statut de ce fichier : PLAN P4/M4 PROPOSÉ, SOUMIS À REVUE.**

Le plan ne prononce **ni P4-G0 GO, ni M4 GO**, et ne qualifie pas un provider, un exécuteur d'outils ou une release. Il donne des objectifs testables, un chemin de réalisation et une grille explicite de refus.

**Prochain chantier documentaire recommandé : P4-BOOT - ADR-022..029 et P4-G0 Architecture Ready.**

**Prochain chantier de code, uniquement après le gate G0 : L4.1 - Tool Definition & Choice.**
