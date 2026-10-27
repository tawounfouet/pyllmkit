# PyLLMKit - Roadmap

> **Mission** : construire une ontologie exécutable, explicite, typée et provider-agnostic des primitives du domaine LLM et de leur cycle d'inférence.
>
> **Principe directeur** : *Domain First · Ports & Adapters · Capability-Driven · Explicit over Implicit*.

| Métadonnée | Valeur |
|---|---|
| Projet | PyLLMKit |
| Document | `ROADMAP.md` |
| Statut | **Proposition de planification**, à valider dans le dépôt |
| Date de référence | 2026-10-27 |
| Portée | Consolidation des spécifications, architecture, implémentation, qualification et releases |
| Sources vérifiées | `00_PYLLMKIT_*.md` à `09_PYLLMKIT_*.md` fournis dans la conversation |
| État du code | **Non vérifié** : aucun audit du repository, de la CI ou des tags de release effectué |
| Roadmap spécialisée | `22_PYLLMKIT_IMPLEMENTATION_ROADMAP.md` (document mentionné dans les spécifications ; existence et contenu non vérifiés) |

---

## 1. Vision et critères de réussite

PyLLMKit ne doit pas devenir un orchestrateur d'agents, un framework RAG complet, un moteur de workflows, un système de routing intelligent ou un proxy LLM enterprise. Il fournit les **primitives de domaine et les contrats** que de tels systèmes peuvent utiliser.

Les quatre capacités fonctionnelles définies dans `01_PYLLMKIT_REQUIREMENTS_ANALYSIS.md` servent de fil directeur :

1. **DESCRIBE** : décrire les modèles, artefacts, modalités, capabilities, limites et expositions.
2. **DISCOVER** : interroger des registries pour trouver des modèles et des deployments compatibles.
3. **INVOKE** : construire, valider et exécuter une inférence via des ports agnostiques.
4. **OBSERVE** : représenter réponses, événements de streaming, usage, erreurs, pricing et coûts.

**Réussite attendue** : le cœur fonctionne sans SDK provider ni réseau ; les adapters respectent ses contrats ; l'ajout d'un provider n'oblige pas à modifier les primitives existantes ; les différences non universelles restent explicites.

### 1.1 Principes non négociables

- `Model != Provider != Deployment != Endpoint` ; `Model != ModelArtifact`.
- `ModelDeveloper != InferenceProvider` ; `Registry != Runtime`.
- `Capability != Modality` ; `InferenceRequest != InferenceRun != InferenceResponse`.
- `Tool != ToolCall != ToolResult` ; `Usage != Pricing != Cost`.
- Capabilities explicites et nuancées (`UNSUPPORTED`, `EMULATED`, `PARTIAL`, `NATIVE`, `UNKNOWN` comme état d'information à préserver).
- Les `EffectiveCapabilities` et `EffectiveLimits` sont **dérivées** des différentes contraintes connues, jamais inventées ni sources de vérité autonomes.
- Les messages et sorties acceptent plusieurs `ContentPart` ; la multimodalité ne doit pas être une exception ajoutée après coup.
- Streaming modélisé par des `StreamEvent` typés, et non réduit à `Iterator[str]`.
- Les `DomainEvent`, `StreamEvent`, `TelemetryEvent` et `IntegrationEvent` ne sont pas interchangeables.
- Les données natives et options spécifiques aux providers restent accessibles via un *escape hatch* contrôlé.
- Aucun appel réseau, credential, SDK externe ou décision de routing dans `pyllmkit.domain`.
- Une déclaration de `Tool` ou un `ToolCall` ne signifie **pas** que le core exécute l'outil.

---

## 2. État de référence et conventions de suivi

### 2.1 Ce qui est vérifié

- Les documents fondateurs `00` à `09` ont été fournis ; ils sont au statut **Draft fondateur** et constituent le référentiel utilisé ici.
- Les quatre visuels ont été examinés ; l'audit a relevé des corrections architecturales et de représentation.
- Le document `02` propose une trajectoire de versions de `0.1.0a1` à `0.3.0`.
- Le document `03` prévoit trois incréments MVP : noyau + premier adapter, enrichissement multi-provider/serving, puis structured output, tool streaming, tokenization et coût.
- Le document `01` comporte les critères d'acceptation `AC-001` à `AC-018`.

### 2.2 Ce qui reste à vérifier

- L'existence et l'état des documents spécialisés `10` à `22` dans le dépôt.
- Le dépôt GitHub, le code Python, la suite de tests, la CI, le packaging, les releases et les tags réels.
- Le choix final des signatures d'API, du packaging des adapters et des dépendances externes.

> **Règle de reporting** : ne jamais assimiler « document rédigé » à « fonctionnalité implémentée », ni « jalon planifié » à « jalon livré ».

### 2.3 États de suivi

- **Proposé** : jalon à confirmer.
- **Prêt** : exigences, dépendances, tests et DoD validés.
- **En cours** : code ou documentation en cours de réalisation, preuves disponibles.
- **Qualifié** : critères d'acceptation satisfaits et tests enregistrés.
- **Publié** : tag/release et artefacts publiés, lorsque pertinents.
- **Non vérifié** : absence de preuve accessible ; **ne signifie pas non réalisé**.

---

## 3. Plan directeur

```text
P0  Architecture baseline & visual corrections
  |
P1  Documentation & contract freeze
  |
0.1.0a1  Model Domain Foundations
  |
0.1.0a2  Interaction Primitives
  |
0.1.0a3  Inference Primitives
  |
0.1.0a4  Tools & Structured Output
  |
0.1.0b1  Streaming Model
  |
0.1.0b2  Registry Foundations
  |
0.2.0a1  OpenAI Adapter
  |
0.2.0a2  Anthropic Adapter
  |
0.2.0a3  Ollama Adapter
  |
0.3.0    Multi-provider Contract Stabilization
  |
0.4.x+   Extensions graduelles selon preuves d'usage
  |
1.0.0    Stable public API (jalon conditionnel, non daté)
```

**Origine de la numérotation** : les versions jusqu'à `0.3.0` reprennent la trajectoire *indicative* du document `02` ; les extensions `0.4.x+` et les conditions de `1.0.0` sont des recommandations ajoutées dans ce document.

Les jalons sont **conditionnés à des preuves**, pas à des dates arbitraires.

---

## 4. P0 - Consolider l'architecture avant le code

**Objectif** : supprimer les ambiguïtés détectées dans les quatre visuels et aligner le référentiel sur les invariants des documents `02`, `03`, `06`, `07`, `08` et `09`.

| ID | Correction | Priorité | Preuve attendue |
|---|---|---|---|
| ARCH-001 | Corriger l'enchaînement erroné `Model -> ModelArtifact -> Deployment` : `Model` est relié séparément à `ModelArtifact*` et `Deployment*` ; `Deployment` expose `Endpoint*`. | P0 | ERD et visuel 3 corrigés |
| ARCH-002 | Définir explicitement la frontière du tool calling : PyLLMKit modélise appels et résultats ; l'exécution appartient à l'application / runtime externe. | P0 | Contrat et diagramme de séquence |
| ARCH-003 | Rendre visible `Application Services` entre façade et ports/domain dans la représentation technique. | P1 | Visuel 4 corrigé |
| ARCH-004 | Séparer dans les diagrammes **flux d'invocation** et **dépendances du code**. | P1 | Deux vues avec légendes |
| ARCH-005 | Afficher `InferenceRequest`, `InferenceRun`, `InferenceResponse` et leur lifecycle. | P1 | Diagramme de séquence + machine à états |
| ARCH-006 | Distinguer `Usage`, `Pricing`, `Cost` et faire apparaître la résolution des capabilities effectives. | P1 | Schémas domaine et résolution |
| ARCH-007 | Séparer visuellement développeurs de modèles, fournisseurs d'inférence, gateways, runtimes et protocoles. | P2 | Écosystème corrigé |
| ARCH-008 | Corriger les logos / doublons et harmoniser les noms dans le visuel 2. | P2 | Vue publique sans ambiguïté |
| ARCH-009 | Différencier `DomainEvent`, `StreamEvent`, `TelemetryEvent` et `IntegrationEvent`. | P2 | Légende et modèle événementiel |

### Diagrammes canoniques à maintenir

1. **Ecosystem Overview** : usages et écosystème, sans prétendre représenter les dépendances du code.
2. **Product Vision & Principles** : principes et responsabilités (référence `02`).
3. **System Architecture** : couches, façade, services, ports et adapters (référence `03`).
4. **Domain Ontology & ERD** : agrégats, relations, cardinalités (références `04` à `07`).
5. **Inference Lifecycle** : requête, résolution, run, streaming, réponse et événements (références `08` et `09`).
6. **Dependency & Ports Architecture** : graphe d'import Python et contrats (références `02` et `03`).

### Gate P0

- [ ] Chaque diagramme explicite **ce que signifient ses flèches**.
- [ ] Les invariants `INV-001` à `INV-010` sont vérifiables par lecture des représentations pertinentes.
- [ ] Les différences `Provider / ModelDeveloper / Runtime / Gateway / EndpointProtocol` sont expliquées.
- [ ] Aucun diagramme ne laisse entendre que le domaine importe un adapter ou exécute automatiquement un tool.

---

## 5. P1 - Finaliser le référentiel documentaire et les contrats

Le document `01` prévoit les approfondissements ci-dessous. Les fichiers non joints sont marqués **à vérifier** et non « inexistants ».

| Fichiers | Domaine | État dans cette revue |
|---|---|---|
| `00` - `03` | Besoin, exigences, principes, architecture | Fournis - draft fondateur |
| `04` - `07` | Objets, entities, relations, invariants | Fournis - draft fondateur |
| `08` - `09` | Commands/queries/use cases, events | Fournis - draft fondateur |
| `10_PYLLMKIT_CAPABILITY_MODEL.md` | Capability et résolution effective | À vérifier |
| `11_PYLLMKIT_MODALITY_AND_CONTENT_MODEL.md` | Multimodalité et content parts | À vérifier |
| `12_PYLLMKIT_INFERENCE_MODEL.md` | Requête, run, réponse, target | À vérifier |
| `13_PYLLMKIT_STREAMING_EVENT_MODEL.md` | Typologie et état du streaming | À vérifier |
| `14_PYLLMKIT_TOOL_CALLING_AND_STRUCTURED_OUTPUT_MODEL.md` | Tools et sorties structurées | À vérifier |
| `15_PYLLMKIT_PROVIDER_AND_DEPLOYMENT_MODEL.md` | Roles, deployments, endpoints | À vérifier |
| `16_PYLLMKIT_REGISTRY_AND_DISCOVERY_MODEL.md` | Catalogage, découverte, provenance | À vérifier |
| `17_PYLLMKIT_USAGE_PRICING_AND_COST_MODEL.md` | Mesures, tarifs versionnés, coûts | À vérifier |
| `18_PYLLMKIT_ERROR_MODEL.md` | Erreurs normalisées et erreurs natives | À vérifier |
| `19_PYLLMKIT_PORTS_PROTOCOLS_AND_ADAPTERS.md` | Contrats et translation provider | À vérifier |
| `20_PYLLMKIT_REPOSITORY_AND_PACKAGE_ARCHITECTURE.md` | Arborescence et dépendances | À vérifier |
| `21_PYLLMKIT_TESTING_AND_QUALIFICATION_STRATEGY.md` | Qualité et tests de contrats | À vérifier |
| `22_PYLLMKIT_IMPLEMENTATION_ROADMAP.md` | Plan détaillé des releases | À vérifier |

### Livrables de stabilisation

- [ ] Glossaire canonique (`Model`, `ModelArtifact`, `Deployment`, `Endpoint`, `Provider`, `Runtime`, `Client`).
- [ ] Tableau des agrégats vs entities vs value objects, avec IDs et invariants.
- [ ] Liste des ports publics et de leurs signatures sync/async/streaming.
- [ ] Politique d'extensions et de conservation des payloads natifs.
- [ ] Format de diagnostic de compatibilité : `SUPPORTED`, `PARTIAL`, `EMULATED`, `UNSUPPORTED`, `UNKNOWN` selon la sémantique finale validée.
- [ ] ADRs des choix ouverts : type des IDs, serialization, erreurs, modèles d'événements, stratégie de modules optionnels.
- [ ] Établissement d'une correspondance entre exigences, tests et jalons.

### Gate P1

**Go** lorsque les contrats nécessaires aux releases `0.1.0a1` à `0.1.0b2` sont suffisamment explicites pour développer et tester sans interprétations provider-specific.

---

## 6. Roadmap d'implémentation

> **Note de statut** : les livrables de cette section sont **planifiés** ; leur réalisation effective est **non vérifiée** dans cette revue.

### 0.1.0a1 - Model Domain Foundations

**But** : modéliser ce qu'est un modèle indépendamment de son fournisseur.

**Scope**

- `ModelId`, `ModelIdentity`, `ModelFamily`, `ModelVersion`, `ModelVariant`, `ModelRevision`.
- `Model`, `ModelArchitecture`, `ModelArtifact`, `ModelLimits`, `ProviderModelRef`.
- `Modality`, `ModalitySet`, `Capability`, `CapabilitySupport`, `CapabilityConstraint`, `CapabilitySet`.
- Value objects immuables, IDs typés, validations et sérialisation initiale.

**Tests et critères de sortie**

- [ ] Import `pyllmkit.domain` sans SDK provider, clé API ni accès réseau.
- [ ] Deux artefacts différents peuvent référencer un même `Model`.
- [ ] Plusieurs variantes de `ModelFamily` sont valides.
- [ ] Une information inconnue n'est pas convertie silencieusement en valeur inventée.
- [ ] Tests unitaires, invariants et serialization passent hors réseau.

**Critères liés** : `AC-001`, `AC-002`, `AC-004`, `AC-005`, `AC-018` (partiels).

### 0.1.0a2 - Interaction Primitives

**But** : représenter conversations et messages multimodaux sans format wire spécifique.

**Scope**

- `Role`, `Content`, `ContentPart`, `TextContent`, `ImageContent`.
- Emplacements extensibles pour `AudioContent`, `VideoContent`, `DocumentContent`.
- `Message`, `Conversation` (optionnelle), ordre explicite des messages et parts.

**Tests et critères de sortie**

- [ ] Construction d'un message texte avec rôle valide.
- [ ] Construction d'un message multimodal contenant plusieurs parties ordonnées.
- [ ] Réjection des messages structurellement invalides selon les invariants documentés.
- [ ] Aucun contenu du domaine n'est défini à partir d'un schéma SDK.

**Critères liés** : `AC-006`, `AC-007`.

### 0.1.0a3 - Inference Primitives

**But** : distinguer intention, exécution et résultat.

**Scope**

- `InferenceTarget` (`ModelTarget`, `DeploymentTarget`, `EndpointTarget`).
- `GenerationConfig`, `InferenceRequest`, `InferenceRun`, `InferenceResponse`.
- `InferenceOutput`, `FinishReason`, `Usage`.
- Machine à états `CREATED -> RUNNING -> [STREAMING] -> COMPLETED / FAILED / CANCELLED`.
- `Deployment` et `Endpoint` sous forme minimale si nécessaires aux cibles ; enrichissement et résolution multi-provider au jalon `0.3.0`.

**Tests et critères de sortie**

- [ ] Une même requête logique peut conduire à plusieurs runs distincts.
- [ ] Un run terminal ne revient jamais à l'état `RUNNING`.
- [ ] Cible, paramètres et réponse ne dépendent pas du wire format provider.
- [ ] Aucune capacité non vérifiée n'est annoncée comme native.

**Critères liés** : `AC-003`, `AC-008`, `AC-009` (certains validés complètement après intégration registry/serving).

### 0.1.0a4 - Tools & Structured Output

**But** : formaliser le tool calling et les formats de réponse.

**Scope**

- `Tool`, `ToolSchema`, `ToolChoice`, `ToolCall`, `ToolArguments`, `ToolResult`.
- `ResponseFormat`, formats texte, JSON et schéma.
- Validation des schémas, corrélation `ToolCallId`, conservation du résultat brut.
- Frontière explicite entre *déclaration / traduction* et *exécution effective de l'outil*.

**Tests et critères de sortie**

- [ ] Le résultat d'un tool référence un `ToolCall` connu dans le contexte pertinent.
- [ ] Un tool call invalide produit un diagnostic typé.
- [ ] Une sortie structurée incorrecte n'est pas présentée comme valide.
- [ ] Aucune exécution implicite de tool dans le Domain Core.

**Critères liés** : `AC-010`, `AC-011`.

### 0.1.0b1 - Streaming Model

**But** : fournir une sémantique événementielle du streaming.

**Scope**

- `InferenceStream`, `StreamEvent` typé.
- `ResponseStarted`, `ContentStarted`, `TextDelta`, `ReasoningDelta`, `ToolCallStarted`, `ToolArgumentDelta`, `ToolCallCompleted`, `UsageUpdated`, `ContentCompleted`, `ResponseCompleted`, `ResponseFailed` selon le périmètre des contrats stabilisés.
- Gestion explicite des états et de la terminaison ; distinction Domain Events / Stream Events.

**Tests et critères de sortie**

- [ ] Reconstitution déterministe d'une réponse à partir des événements supportés.
- [ ] Fragmentation arbitraire des deltas correctement gérée.
- [ ] Terminaison, échec et annulation testés.
- [ ] Pas de confusion entre événements progressifs et faits métier durables.

**Critères liés** : `AC-012`.

### 0.1.0b2 - Registry Foundations

**But** : décrire et découvrir des modèles sans exécuter leur inférence.

**Scope**

- `ModelRegistryPort`, `InMemoryRegistry`.
- `register`, `get`, `list`, `find` ; recherches par famille, modality et capability.
- Première définition de `ModelQuery` et métadonnées de provenance.
- Gestion explicite des collisions et conflits.

**Tests et critères de sortie**

- [ ] Inscription et récupération de plusieurs modèles d'une même famille.
- [ ] Recherche par capability et modality.
- [ ] Le registry n'effectue aucune invocation provider.
- [ ] Tests de contrats backend indépendants du stockage in-memory.

**Critères liés** : `AC-013`, `AC-014`.

### 0.2.0a1 - OpenAI Adapter

**But** : premier circuit end-to-end d'inférence réelle.

**Scope**

- `InferencePort` et `StreamingPort` stabilisés pour le premier adapter.
- Mapper request / messages / paramètres / outils vers le provider, puis normaliser réponses et streams.
- Gérer erreurs, `raw` native, `provider_options` et capabilities effectivement exposées.
- Configuration, secrets et transport strictement hors du domaine.

**Tests et critères de sortie**

- [ ] Contract tests sur transport simulé sans réseau en CI ordinaire.
- [ ] Intégration réelle opt-in, nécessitant credentials et environnement explicites.
- [ ] Réponse provider normalisée et réponse native accessible.
- [ ] Erreur provider traduite vers l'erreur PyLLMKit appropriée, erreur native conservée.
- [ ] Installation du core sans SDK OpenAI obligatoire.

**Critères liés** : `AC-015`, `AC-016`, `AC-017`, `AC-018`.

### 0.2.0a2 - Anthropic Adapter

**But** : éprouver l'abstraction avec un second provider aux conventions différentes.

**Scope**

- Translation rôles/messages, tools, réponses, fins d'inférence et streaming.
- Déclaration des limites et capabilities spécifiques.
- Tests comparatifs OpenAI / Anthropic, sans forcer un plus petit dénominateur commun.

**Tests et critères de sortie**

- [ ] Tous les tests de contrat communs passent pour les deux adapters.
- [ ] Les différences non représentables dans le contrat commun sont explicitement exposées ou rejetées.
- [ ] Aucune modification opportuniste du domaine simplement pour copier le SDK Anthropic.

### 0.2.0a3 - Ollama Adapter

**But** : qualifier un runtime local sans lui attribuer les propriétés d'un provider cloud.

**Scope**

- Adapter du runtime local et découverte/configuration locale selon capacité réelle.
- Différenciation explicite entre `Runtime`, `InferenceProvider`, `Deployment` et `Endpoint`.
- Capabilities et limites dépendant du modèle et du runtime, avec inconnus conservés.

**Tests et critères de sortie**

- [ ] Contrats communs vérifiés contre la troisième famille d'intégration.
- [ ] Fonctionnement local, sans imposer de clé API cloud.
- [ ] La description du runtime ne modifie pas l'identité du modèle logique.

### 0.3.0 - Multi-provider Contract Stabilization

**But** : qualifier l'abstraction sur trois implémentations hétérogènes et satisfaire l'ensemble des `AC-001` à `AC-018`.

**Scope**

- `CapabilityResolver`, `LimitResolver`, `CompatibilityEvaluator`.
- Modèle `Model / Deployment / Endpoint / Provider / Runtime` consolidé.
- `ModelResolver`, `DeploymentResolver`, `InferenceService` et façade simple.
- Contrats sync / async / streaming clairement définis.
- Régression multi-provider, taxonomie d'erreurs et documentation des divergences.

**Tests et critères de sortie**

- [ ] Matrice de compatibilité par adapter, capability et mode d'inférence publiée.
- [ ] Tous les `AC-001` à `AC-018` disposent de tests et de preuves.
- [ ] Aucun import interdit ni SDK obligatoire dans `domain`.
- [ ] Les interfaces partagées sont suffisamment stables pour des consommateurs externes.
- [ ] Au moins trois démonstrations pédagogiques : cloud A, cloud B, runtime local.

---

## 7. Extensions ultérieures - proposition, non engagée

Les documents `01` à `03` identifient plusieurs enrichissements. Leur affectation à des versions ultérieures ci-dessous est **une recommandation**, pas un engagement de release préexistant.

| Ordre indicatif | Extension | Conditions préalables |
|---|---|---|
| `0.4.x` | Registries composites, fichiers statiques, discovery, provenance et résolution des conflits | Contrats registry et identité de modèle stabilisés |
| `0.5.x` | TokenizerPort, budget de contexte, usage enrichi, tarifs versionnés et calcul des coûts | Sources de données explicites, inconnus et incertitudes traités |
| `0.6.x` | Multimodalité enrichie, structured output et tool streaming complets | Interopérabilité validée sur plusieurs providers |
| `0.7.x` | Plugins/adapters additionnels, façades pédagogiques et interfaces ergonomiques | Tests de contrats génériques, packaging optionnel |
| `0.8.x` | Observabilité avancée, documentation de performance, intégrations PyAgentsKit / PyRuntimeKit | Responsabilités inter-frameworks définies |
| `1.0.0` | API publique stable | Adoption, compatibilité, migration et politique SemVer qualifiées |

**Hors périmètre initial**, sauf ADR et justification nouvelle : agent loop autonome, exécution native des tools métier, moteur RAG complet, persistence obligatoire des conversations, fine-tuning, routing intelligent et proxy enterprise.

---

## 8. Matrice de traçabilité MVP

| Critère source | Démonstration attendue | Premier jalon cible |
|---|---|---|
| AC-001 | Créer un modèle sans SDK provider | `0.1.0a1` |
| AC-002 | Plusieurs variants d'une famille | `0.1.0a1` |
| AC-003 | Plusieurs deployments pour un modèle | `0.1.0a3` puis `0.3.0` |
| AC-004 | Décrire les modalities | `0.1.0a1` |
| AC-005 | Décrire les capabilities | `0.1.0a1` |
| AC-006 | Message texte agnostique | `0.1.0a2` |
| AC-007 | Message multimodal | `0.1.0a2` |
| AC-008 | Construire une `InferenceRequest` | `0.1.0a3` |
| AC-009 | Normaliser une `InferenceResponse` | `0.1.0a3` puis `0.2.0a1` |
| AC-010 | Exprimer un tool call | `0.1.0a4` |
| AC-011 | Exprimer une sortie structurée | `0.1.0a4` |
| AC-012 | Événements de streaming | `0.1.0b1` puis `0.2.0a1` |
| AC-013 | Plusieurs modèles dans un registry | `0.1.0b2` |
| AC-014 | Rechercher par capability | `0.1.0b2` |
| AC-015 | Brancher un provider adapter | `0.2.0a1` |
| AC-016 | Accéder à la réponse native | `0.2.0a1` |
| AC-017 | Normaliser une erreur provider | `0.2.0a1` |
| AC-018 | Tous les tests domain passent hors réseau | Transversal, clôture `0.3.0` |

**Lecture** : « premier jalon cible » n'équivaut pas à validation de l'AC. L'acceptation complète du MVP est un **gate transverse** à la stabilisation multi-provider.

---

## 9. Stratégie de tests et qualité

### 9.1 Pyramide de tests

1. **Domain unit tests** : identities, value objects, invariants, états, compatibilité, usage et sérialisation ; 100 % hors réseau.
2. **Property-based / edge cases** : contraintes, inconnus, limites, transitions invalides, ordre des content parts, tool deltas.
3. **Port contract tests** : une suite commune rejouée contre chaque adapter ou fake.
4. **Provider mapper tests** : payloads anonymisés et fixtures versionnées, sans secrets.
5. **Integration tests opt-in** : vrais endpoints avec budget, clés et configuration explicites.
6. **Architecture fitness tests** : dépendances et imports interdits, extras optionnels, surface API, import sans SDK.
7. **Packaging tests** : wheel/sdist installables en environnement vierge, documentation et exemples reproductibles.

### 9.2 Commandes envisagées (non garanties présentes dans le dépôt)

```bash
python -m pytest
python -m ruff check .
python -m mypy src/pyllmkit
python -m build
```

Le choix précis d'outillage sera décidé dans le bootstrap/CI ; ces commandes sont des **propositions**.

### 9.3 Definition of Done pour chaque jalon

- [ ] Fonctionnalité conforme aux spécifications applicables, avec décision documentée si divergence.
- [ ] API typée, docstrings, exemples pédagogiques et README à jour.
- [ ] Tests unitaires et contrats exécutés ; échecs corrigés.
- [ ] Invariants et interdictions d'import vérifiés automatiquement.
- [ ] Pas de fuite de clés, contenu sensible ou données brutes dans logs/events par défaut.
- [ ] Compatibilité arrière évaluée et release notes préparées.
- [ ] Preuve de qualification liée au commit, tag ou rapport de test.

---

## 10. Architecture du repository - cible indicative

La topologie ci-dessous s'appuie sur le document `03` ; elle reste **à valider** dans `20_PYLLMKIT_REPOSITORY_AND_PACKAGE_ARCHITECTURE.md`.

```text
src/pyllmkit/
├── __init__.py
├── domain/               # primitives, entities, VO, invariants
│   ├── models/
│   ├── capabilities/
│   ├── modalities/
│   ├── serving/
│   ├── interaction/
│   ├── tools/
│   ├── inference/
│   ├── streaming/
│   ├── tokenization/
│   ├── usage/
│   ├── pricing/
│   └── errors/
├── protocols/            # inference, streaming, registry, tokenizer...
├── application/          # resolution, validation, use cases
├── facade/               # public ergonomic API
├── providers/            # adapters optionnels et mappings
│   ├── openai/
│   ├── anthropic/
│   └── ollama/
├── registry/             # in-memory, static, composite
└── plugins/              # extensions éventuelles

tests/
├── unit/
├── contracts/
├── architecture/
├── integration/
└── fixtures/

docs/
├── concepts/
├── architecture/
├── providers/
├── guides/
├── examples/
├── adr/
└── reference/
```

**Règle de dépendance (imports)** :

```text
facade -> application -> protocols -> domain
adapters -> protocols + domain + optional provider SDK
registry implementations -> registry protocols + domain

domain -X-> adapters / external SDKs / network / secrets
```

Ce graphe exprime les **dépendances de code** ; le chemin réel d'une invocation peut être différent et impliquer le port injecté, son adapter et un SDK externe.

---

## 11. Risques, arbitrages et politiques

| Risque | Signal d'alerte | Politique de maîtrise |
|---|---|---|
| Provider leakage | Des objets du core copient un payload externe | Anti-Corruption Layer dans chaque adapter |
| Lowest common denominator | Les fonctionnalités avancées disparaissent de l'API | Core commun + capabilities + extensions spécifiques |
| Scope explosion | Agent loops, RAG ou routing avant stabilisation | Maintenir les non-objectifs et exiger une ADR |
| God Client | Façade avec toutes les responsabilités | Services spécialisés et ports petits |
| Metadata drift | Capabilities, tarifs ou disponibilités obsolètes | Provenance, dates de validité, unknown explicite |
| False cost precision | Coût calculé sans source tarifaire suffisante | `Cost` indisponible ou estimé avec statut explicite |
| Misleading diagrams | Une flèche signifie tantôt import, tantôt invocation | Légende, vues séparées, revue P0 |
| Excessive abstractions | Concepts sans sémantique ou invariant propre | Preuve par cas d'usage et plusieurs providers |
| CI dépendante du réseau | Tests instables ou secrets requis | Contrats simulés par défaut ; live tests opt-in |
| Couplage inter-Kits | PyLLMKit implémente des responsabilités agentiques | Séparer primitives LLM et orchestration externe |

### Décisions ouvertes à formaliser en ADR

- Typage public : `dataclass`, `Protocol`, validateurs dédiés, serializer indépendant.
- Sync/async : mêmes sémantiques, interfaces spécifiques ou séparation explicite.
- Identité canonique d'un modèle vs alias provider.
- Niveau de support des capabilities, valeur `UNKNOWN` et règles d'intersection.
- Gestion des erreurs : normalisation, cause native et propriétés `retryable`.
- Versioning des schémas d'événements et payloads exposés.
- Packaging optionnel des SDK (extras) et découverte des adapters.
- Politique des données de pricing : devise, version, date, estimation vs exactitude.

---

## 12. Plan de démarrage immédiat

**Ordre recommandé pour la prochaine session d'implémentation :**

1. **Inventaire réel** : vérifier repository, branche, fichiers `10` à `22`, tags, packaging et état des tests.
2. **Revue P0** : rectifier les vues `Model/Artifact/Deployment`, outils et flèches de dépendances.
3. **ADR minimale** : figer structure package, identifiants, valeur `UNKNOWN`, protocole d'inférence et critères de compatibilité.
4. **Bootstrap** : créer package installable, `pyproject.toml`, tests hors réseau, lint/type-check et architecture fitness tests.
5. **Première vertical slice** : `ModelId + ModelIdentity + Model + CapabilitySet + ModalitySet`, tests d'invariants.
6. **Valider `0.1.0a1`**, puis suivre les autres jalons sans multiplier les adapters prématurément.

### Checklist de pilotage

| Axe | Prochain point de contrôle | Statut de preuve |
|---|---|---|
| Spécifications `00-09` | Consolider les ambiguïtés / ADR | Fournies - drafts |
| Spécifications `10-22` | Inventorier les fichiers et leur état | Non vérifié |
| Visuels | Appliquer ARCH-001 et ARCH-002 | Corrections identifiées, non appliquées |
| Repository | Faire un état des lieux avant tout commit | Non vérifié |
| Premier milestone | Qualifier `0.1.0a1` | Non vérifié |
| Release stable | Passer tous les gates MVP et contrats | Non vérifié |

---

## 13. Sources et traçabilité documentaire

Cette roadmap est une **synthèse opérationnelle** des fichiers suivants, complétée par les corrections issues de l'audit comparatif des quatre visuels :

- `00_PYLLMKIT_EXPRESSION_DU_BESOIN.md` - besoin, périmètre et non-objectifs.
- `01_PYLLMKIT_REQUIREMENTS_ANALYSIS.md` - MVP-1 à MVP-7, providers de validation, `AC-001` à `AC-018`, séquence documentaire.
- `02_PYLLMKIT_PRODUCT_VISION_AND_ARCHITECTURE_PRINCIPLES.md` - principes architecturaux, dependency rule, trajectoire de releases indicative.
- `03_PYLLMKIT_SYSTEM_ARCHITECTURE.md` - couches, domaine, ports, adapters, topologie et phases MVP.
- `04_PYLLMKIT_DOMAIN_OBJECTS.md` - inventaire des objets et bounded contexts.
- `05_PYLLMKIT_ENTITIES_AND_VALUE_OBJECTS.md` - classifications DDD et frontières d'agrégats.
- `06_PYLLMKIT_DOMAIN_RELATIONSHIPS_AND_ERD.md` - relations, ownership et cardinalités.
- `07_PYLLMKIT_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md` - invariants structurants.
- `08_PYLLMKIT_COMMANDS_QUERIES_AND_USE_CASES.md` - commands, queries et services applicatifs.
- `09_PYLLMKIT_DOMAIN_EVENTS_CATALOG.md` - distinction des catégories d'événements.

**Gouvernance** : en cas de conflit entre cette roadmap et une spécification de domaine, créer une ADR et mettre à jour les documents concernés avant de modifier silencieusement le code.