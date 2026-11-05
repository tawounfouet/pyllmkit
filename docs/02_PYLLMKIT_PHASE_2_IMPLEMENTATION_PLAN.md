# 02_PYLLMKIT_PHASE_2_IMPLEMENTATION_PLAN

> **PHASE 2 - Primitives d'interaction LLM**  
> Incrément produit : **`0.1.0a2 - Interaction Primitives`**  
> Lots proposés : **L2.1 Message Domain**, **L2.2 Content Domain**, **L2.3 Multimodal Content**, **L2.4 Quality & Testing**  
> Jalon : **M2 - Interaction Foundations Qualified**  
> Livrable : **candidat alpha `v0.1.0a2`**, distinct de sa publication.

| Métadonnée | Valeur |
|---|---|
| Projet | **PyLLMKit** |
| Document | Plan d'implémentation - Phase 2 |
| Référence | `02_PYLLMKIT_PHASE_2_IMPLEMENTATION_PLAN.md` |
| Date de rédaction | **2026-11-05** |
| Statut | **Plan d'exécution proposé - Phase 2 non implémentée à la date de référence** |
| Baseline Git vérifiée | [`main` / `d7f06072d246819fb976c6a456949995ae33562d`](https://github.com/tawounfouet/pyllmkit/commit/d7f06072d246819fb976c6a456949995ae33562d) |
| Prérequis | M1 = **GO** - Phase 1 qualifiée, 137 tests, 89 % de couverture combinée, Python 3.11/3.12/3.13 |
| Version inscrite dans `pyproject.toml` au départ | `0.1.0a1` - **alpha candidate non publiée** |
| Version de développement visée | `0.1.0a2` (PEP 440) ; un tag Git éventuel serait `v0.1.0a2` |
| Cadre technique | Python >= 3.11 ; DDD ; Domain First ; Ports & Adapters ; Provider-Agnostic |
| Références fondatrices | `00` à `09`, `ROADMAP.md`, plan Phase 1 et bilan post-implémentation |
| Validation requise | CI, invariants, ADR, qualité et procès-verbal **M2 GO/NO-GO** |

> **Traçabilité de statut.** Les résultats de M1 sont des faits du dépôt et de ses CI ; les tâches L2.x, classes cibles, nouvelles ADR, séquence de PR et métriques de M2 sont des **propositions à réaliser**, non des fonctionnalités déjà livrées. La roadmap utilise bien le jalon de version `0.1.0a2`, mais ne définit pas officiellement un « P2 » ni les quatre lots L2.x. Ce document propose ces conventions pour conserver le même pilotage que la Phase 1.

---

## 1. Objet et résultat attendu

### 1.1. Pourquoi une Phase 2 ?

La Phase 1 sait représenter un **Model**, son identité, ses **Capabilities** et ses **Modalities**. Elle ne représente pas encore l'**interaction** qu'un appelant souhaiterait adresser à ce modèle.

La Phase 2 doit rendre exprimables, dans des objets Python indépendants des fournisseurs :

1. **Qui s'exprime ?** : un `Role` explicite associé à un `Message`.
2. **Que transmet-il ?** : un `Content` composé de `ContentPart` typées.
3. **Dans quel ordre ?** : séquence de messages et de parties préservée.
4. **Sous quelle forme ?** : texte et image qualifiés, avec points d'extension pour audio, vidéo et documents.
5. **Selon quelles règles ?** : validation structurelle sans conversion, exécution ni mapping provider implicites.

À l'issue de M2, l'API suivante doit être **réalisable**, sous réserve du contrat public fixé par les ADR. Il s'agit ici d'un **exemple de design cible**, et non de code déjà disponible :

```python
# API cible illustrative - à figer par ADR avant implémentation
from pyllmkit.domain.interactions import Content, Message, Role, TextContent

message = Message(
    role=Role.USER,
    content=Content(parts=(TextContent(text="Bonjour PyLLMKit"),)),
)
assert message.content.parts[0].text == "Bonjour PyLLMKit"
```

Pour un message multimodal, on doit aussi pouvoir construire un `Content` dans lequel les parties texte et image se succèdent **sans réordonnancement ni conversion implicite**.

### 1.2. Positionnement dans la roadmap

```text
Phase 1 - Domain Foundations
  └── M1 : GO  [intégré dans main, CI qualifiée]
       └── v0.1.0a1 : candidate alpha NON publiée

Phase 2 - Interaction Primitives  [ce document]
  ├── P2-BOOT  : contrat, audit, ADR, CI
  ├── L2.1     : Role, Message, Conversation optionnelle
  ├── L2.2     : Content, ContentPart, TextContent
  ├── L2.3     : ImageContent, sources de média, extensions
  ├── L2.4     : tests, contrat JSON, exemples, packaging
  └── M2       : Interaction Foundations Qualified
       └── v0.1.0a2 : candidate alpha ; publication séparée

0.1.0a3 : Inference Primitives         [après M2]
0.1.0a4 : Tools & Structured Output    [après M2]
0.1.0b1 : Streaming Model              [après M2]
0.1.0b2 : Registry Foundations         [après M2]
0.2.x   : Provider Adapters            [après M2]
```

**Convention :** `Phase`, `Lot`, `Jalon` et `Release` sont quatre objets de pilotage différents. **M2 GO ne signifie pas `v0.1.0a2` publiée.**

### 1.3. Objectifs mesurables de M2

- `AC-006` : construire, valider et représenter un message texte provider-agnostic.
- `AC-007` : construire, valider et représenter un message multimodal avec **plusieurs parties ordonnées**.
- Préserver les invariants de domaine `INT-001` à `INT-011` qui relèvent de la représentation des interactions.
- Conserver toutes les garanties M1 : import sans SDK fournisseur, sans credentials ni réseau, APIs typées et CI multi-Python.
- Qualifier un codec explicite et versionné pour les objets de l'interaction, sans casser le codec `Model` de Phase 1.
- Disposer de preuves exactes sur le SHA intégré à `main` avant de prononcer M2 GO.

---

## 2. Source de vérité et traçabilité

| Source | Contrats utilisés | Nature |
|---|---|---|
| `ROADMAP.md` § `0.1.0a2` | `Role`, `Content`, `ContentPart`, `TextContent`, `ImageContent`, `Message`, `Conversation` optionnelle, extensions audio/vidéo/document | **Périmètre source** |
| `01_PYLLMKIT_REQUIREMENTS_ANALYSIS.md` | `AC-006`, `AC-007`, conversations, messages multimodaux | **Exigences source** |
| `02_PYLLMKIT_PRODUCT_VISION_AND_ARCHITECTURE_PRINCIPLES.md` | trajectoire `0.1.0a1 -> a2 -> a3` ; fitness functions ; découplage du provider | **Principes source** |
| `03_PYLLMKIT_SYSTEM_ARCHITECTURE.md` § Interaction | frontières Interaction Domain ; polymorphisme de `ContentPart` | **Architecture source** |
| `04_PYLLMKIT_DOMAIN_OBJECTS.md` § 38-47 | `Conversation`, `Message`, `Role`, `Content`, types multimodaux | **Vocabulaire source** |
| `05_PYLLMKIT_ENTITIES_AND_VALUE_OBJECTS.md` § 48-57 | `Message` Value Object ; `Conversation` Aggregate Root optionnel ; `Content` ordonné | **Classification DDD source** |
| `06_PYLLMKIT_DOMAIN_RELATIONSHIPS_AND_ERD.md` § 28-32 | Conversation 0..* Message ; Message 1 Content ; Content 1..* ContentPart | **Cardinalités source** |
| `07_PYLLMKIT_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md` § 12-13 | `INT-001` à `INT-011` et `MOD-003`, `MOD-005` | **Invariants source** |
| `08_PYLLMKIT_COMMANDS_QUERIES_AND_USE_CASES.md` § 13 | `BuildMessage`, `BuildConversation`, `ValidateInteraction` | **Cas d'usage source** |
| `09_PYLLMKIT_DOMAIN_EVENTS_CATALOG.md` | événements de domaine, non essentiels à la construction initiale d'un message | **Hors gate M2** |
| `01_PYLLMKIT_PHASE_1_IMPLEMENTATION_PLAN.md` | conventions de tâches, gates, ADR, tests, DoD | **Méthode antérieure** |
| `PYLLMKIT_PHASE_1_POST_IMPLEMENTATION_REVIEW.md` | retours d'expérience, mesures et points de vigilance | **Baseline post-implémentation** |
| `docs/quality/M1_GATE_REVIEW.md` (GitHub) | M1 GO et périmètre officiellement qualifié | **Preuve réelle** |

### 2.1. Ce qui est proposé ici, non imposé par les sources

La subdivision en **L2.1 / L2.2 / L2.3 / L2.4**, le mécanisme de source d'image (`MediaSourceRef`), le contrat JSON Interaction et les ADR-008 à ADR-013 ne sont pas des exigences préexistantes figées. Ce sont des **options d'architecture proposées**, qui doivent être validées avant tout engagement d'API.

### 2.2. Précaution documentaire

Les fichiers fondateurs `00` à `09` sont disponibles dans le contexte documentaire du projet, mais ne sont pas tous suivis dans le dépôt public actuel. **Ne pas déclarer comme « intégré à GitHub » un document uniquement présent dans les pièces du projet.** Créer un index de traçabilité GitHub ou synchroniser explicitement les sources sélectionnées, en respectant leurs statuts.

---

## 3. Périmètre de Phase 2

### 3.1. Inclus dans M2

| Domaine | Objets/contrats | Exigence minimale |
|---|---|---|
| Role | `Role` ; mécanisme explicite pour rôles non standard, selon ADR | Valeurs sémantiques valides et sans mapping provider caché |
| Message | `Message` Value Object, éventuels `name` et `metadata` bornés | `Role` valide, exactement un `Content`, construction sans ID imposé |
| Content | `Content`, `ContentPart`, `TextContent` | Ensemble ordonné non vide de parties, types définis |
| Image | `ImageContent`, source typed | Source exploitable, référence opaque ou URI, pas de téléchargement |
| Modalité | mapping de type `ContentPart -> Modality` | `TextContent -> text`, `ImageContent -> image` |
| Conversation | `Conversation` facultative | Si incluse : messages ordonnés, possibilité de conversation vide |
| Sérialisation | Codec Interaction versionné et explicite | Round-trip, erreurs déterministes, ordre préservé |
| Qualité | pytest, Ruff, mypy, tests offline, architecture, docs, examples, wheel et sdist | CI verte, comparaison avec baseline M1 |
| Gouvernance | ADR, PR, M2 GO/NO-GO | Décisions lisibles et preuve SHA exacte |

### 3.2. Hors périmètre / différé

| Sujet | Motif / cible |
|---|---|
| `InferenceRequest`, `InferenceRun`, `InferenceResponse`, `GenerationConfig` | `0.1.0a3` |
| `Tool`, `ToolCall`, `ToolResult`, `ToolChoice`, exécution d'outils | `0.1.0a4` ; même si le rôle `TOOL` est déjà connu |
| Structured output, JSON schema de réponse de modèle | `0.1.0a4` |
| Streaming, chunks, évènements d'inférence | `0.1.0b1` |
| Registry opérationnel, découverte de modèles, persisted conversation repository | `0.1.0b2` ou couches supérieures si réellement nécessaires |
| OpenAI/Anthropic/Google SDK, routing et appels réseau | Adapters futurs ; **interdits dans le Domain Core** |
| Conversions d'images/OCR, transcodage audio/vidéo, parsing PDF | Port/adapters/applications ultérieurs, **pas de transformation cachée dans les VOs** |
| Template engine / prompt manager central, mémoires conversationnelles persistées | Hors M2 ; à justifier séparément si besoin produit |
| Attachments massifs incorporés automatiquement au JSON, upload/fetch HTTP | Risques de taille/sécurité et couplage infra ; différés |
| Multi-provider effective capability resolution | Étape inter-couches future, déjà différée en M1 |

### 3.3. Invariants structurants

1. **`Message != Conversation != InferenceRequest`** : Message est un VO de représentation, Conversation est optionnelle, Request sera un objet distinct en `a3`.
2. **`Role` est sémantique, pas une chaîne fournie par un SDK** : traductions dans les adapters, jamais silencieuses dans le core.
3. **`Message` possède exactement un `Content` ; `Content` possède 1..* `ContentPart` ordonnées**.
4. **`TextContent` n'est pas `ImageContent`** et leur modality est identifiable sans provider.
5. **Aucune conversion implicite** : image -> OCR -> texte, audio -> transcription, document -> texte exigent des décisions explicites hors domaine.
6. **Aucun fetch** : enregistrer une référence ne signifie ni accéder au réseau ni charger un fichier.
7. **L'inconnu reste inconnu** : pas de capability effective inventée, pas de rôle non reconnu forcé vers `USER`.
8. **Le contrat existant `pyllmkit.domain` et la sérialisation `Model` restent rétrocompatibles** au sens garanti par M1.

---

## 4. Critères d'entrée - Definition of Ready

### 4.1. Baseline vérifiée

La référence `main` observée à la rédaction est :

```text
tawounfouet/pyllmkit
  main @ d7f06072d246819fb976c6a456949995ae33562d
  M1 = GO
  pytest = 137 passed
  couverture combinée = 89 %
  CI = Python 3.11, 3.12, 3.13 (SUCCESS)
  licence = MIT
  package metadata = 0.1.0a1 (non publié)
```

La Phase 2 doit démarrer d'une branche créée depuis **le SHA `main` effectivement observé au début de l'implémentation**, et non d'un ancien SHA mémorisé dans ce plan si le dépôt a évolué entre-temps.

### 4.2. Check-list P2-BOOT

- [ ] Vérifier la tête de `main`, la version du package, l'état du workflow CI et des PR ouvertes.
- [ ] Consulter la dernière CI `main`, et conserver son lien de preuve.
- [ ] Vérifier que les tests M1 sont conservés, sans changement de sémantique de `Model` ou `Modality`.
- [ ] Finaliser les ADR P2-008 à P2-013 (cf. § 5).
- [ ] Trancher le vocabulaire `Role`, types `ContentPart`, contrat de source d'image et codec.
- [ ] Décider si `Conversation` est implémentée dans cet incrément ou laissée à une couche supérieure.
- [ ] Publier l'index de sources documentaires de référence, avec lien vers les pièces non synchronisées.
- [ ] Établir une chaîne de PR dépendantes et la stratégie de versionnement (pas de publication accidentelle).
- [ ] Confirmer les invariants `INT-*`, `MOD-*`, `AC-006` et `AC-007` avec des cas de test nommés.

### 4.3. Conventions de pilotage

| Objet | Convention proposée | Exemple |
|---|---|---|
| Phase | `P2` | Phase 2 - Interaction Primitives |
| Bootstrap | `P2-BOOT` | Architecture Decisions & Domain Contract |
| Lots | `P2-L21` à `P2-L24` | L2.2 Content Domain |
| Tâches | `P2-L22-T01`, etc. | Création `ContentPart` |
| Gates internes | `G0`, `G1`, `G2`, `G3`, `G4` de P2 | Qualité / architecture |
| Jalon | `M2` | Interaction Foundations Qualified |
| Artefact | `v0.1.0a2` | Alpha candidate |
| États | TODO / READY / IN_PROGRESS / IN_REVIEW / BLOCKED / QUALIFIED | Suivi traçable |

**Règle :** une tâche qualifiée possède un **SHA**, des **preuves CI** et des critères d'acceptation explicitement vérifiés ; la simple existence d'une classe ne clôt pas la tâche.

---

## 5. ADR et décisions d'architecture de P2-BOOT

Les identifiants ci-dessous prolongent les sept ADR adoptées en Phase 1. Le contenu du tableau est un **arbitrage proposé**, pas une acceptation déjà enregistrée.

| ADR proposé | Question | Décision recommandée | Preuves de qualification |
|---|---|---|---|
| **ADR-008 - Role Taxonomy** | Enum strict ou rôles extensibles ? | Cinq rôles canoniques `SYSTEM`, `DEVELOPER`, `USER`, `ASSISTANT`, `TOOL` ; traiter explicitement les rôles non standard, sans downgrade silencieux | Tests rôles valides/inconnus, `TOOL` sans ToolResult implicite |
| **ADR-009 - Message & Conversation Ownership** | `Message` Entity ou VO ? Conversation obligatoire ? | `Message` = VO immuable, sans ID exigé ; `Conversation` = agrégat optionnel, aucune persistence requise | Égalité par valeur ; séquence ; construction de Message hors Conversation |
| **ADR-010 - Content Polymorphism** | Union typée ou classe de base/protocol ? | Hiérarchie de parties immuables, discriminant canonique explicite, ordre conservé ; pas de provider-native JSON | Tests discrimination, immutabilité, ordre |
| **ADR-011 - Media Sources and Safety** | Image en URL, bytes, asset ID ? | Value Object `MediaSourceRef` ou variantes équivalentes ; références structurées, non exécutables ; aucune lecture/fetch par les VOs | Cas URI/référence valides et invalides, absence d'I/O |
| **ADR-012 - Interaction JSON Schema** | Compatibilité avec schema v1 de Model ? | Codec Interaction **indépendant**, format explicite et versionné ; erreur sur types/champs inconnus ; ne pas modifier le codec Model | Round-trip texte/image, compatibilité M1, version inconnue rejetée |
| **ADR-013 - Multimodal Extension Policy** | Audio/vidéo/document complets à M2 ? | Texte et image **obligatoires** ; interfaces/points d'extension audio, vidéo, document explicités ; implémentations optionnelles sur preuve de besoin | Test de type, pas de faux support multimedia déclaré |

### 5.1. Critères d'adoption des ADR

Chaque ADR doit porter : **Context**, **Decision**, **Alternatives**, **Consequences**, **Status**, **Date**, **Acceptance Tests**, **Follow-ups**. Les arbitrages `Role`/`Message`/`ContentSource`/codec doivent être adoptés avant de geler les classes accessibles aux consommateurs.

### 5.2. Compatibilité avec les ADR-001 à ADR-007

- `ADR-001/002` : préserver les IDs typés et Value Objects immuables ; **ne pas ajouter `MessageId` par défaut** uniquement pour ressembler à une Entity.
- `ADR-003/006` : absence de support multimodal ne signifie pas conversion de contenu ; le resolver de capacités effectives est hors P2.
- `ADR-004` : le codec `Model` de schéma v1 est gelé ; Interaction possède son espace de schéma propre.
- `ADR-005` : `pyllmkit.domain` et les sous-packages sont des imports publics testés, sans import SDK.
- `ADR-007` : licence MIT maintenue ; l'approbation M2 n'autorise pas publication ou tags.

---

## 6. Architecture cible et dépendances

### 6.1. Vue DDD

```text
                           Interaction Domain

  Conversation? (Aggregate Root optionnelle)
        |
        | 0..* Message [ordre conservé]
        v
  Message (Value Object)
      |-- 1 Role (type symbolique)
      |-- 1 Content (Value Object)
      |     `-- 1..* ContentPart [ordre conservé]
      |              |-- TextContent
      |              |-- ImageContent --> MediaSourceRef
      |              |-- AudioContent?       [extension]
      |              |-- VideoContent?       [extension]
      |              `-- DocumentContent?    [extension]
      |-- name?     [selon ADR]
      `-- metadata? [selon ADR]

  ContentPart -> Modality [type déterminable]
  Modality --> pyllmkit.domain.modalities [existant M1]
```

### 6.2. Packages envisagés

```text
src/pyllmkit/
  __init__.py                       # existant M1
  domain/
    __init__.py                     # exports Phase 1 à préserver + exports P2 contrôlés
    errors/                         # existant M1, enrichissement minimal
    models/                         # existant M1 ; NON modifié sans justification
    capabilities/                   # existant M1 ; NON modifié sans justification
    modalities/                     # existant M1 ; utilisé par Interaction
    interactions/                   # NOUVEAU
      __init__.py
      roles.py
      message.py
      conversation.py              # optionnel selon ADR-009
      content.py
      parts.py
      sources.py                   # références de média ; nom proposé
      serialization.py            # codec Interaction indépendant
      errors.py                    # seulement si une erreur métier dédiée est nécessaire

tests/
  unit/domain/interactions/
    test_roles.py
    test_messages.py
    test_content.py
    test_text_content.py
    test_image_content.py
    test_conversation.py           # optionnel
  serialization/
    test_interaction_codec.py
  acceptance/
    test_ac_006_text_message.py
    test_ac_007_multimodal_message.py
  architecture/
    test_interaction_dependencies.py
  quality/
    test_interaction_package_api.py

examples/
  04_text_message.py
  05_multimodal_message.py
  06_conversation.py                # optionnel

docs/
  adr/ADR-008-...md ... ADR-013-...md
  concepts/interaction-domain.md
  api/interaction-domain.md
  quality/M2_GATE_REVIEW.md
  quality/PHASE_2_TRACEABILITY.md
```

**Les chemins sont proposés**, sans prétendre à leur existence sur `main`.

### 6.3. Règles d'import (fitness functions)

```text
pyllmkit.domain.interactions
  -> pyllmkit.domain.modalities   [types de Modality existants]
  -> pyllmkit.domain.errors       [erreurs de validation existantes]
  -> stdlib                       [dataclasses, enum, typing, etc.]

INTERDIT dans domain/interactions :
  -> provider SDK / HTTP / filesystems d'adapters
  -> pyllmkit.infrastructure, pyllmkit.providers, facade, application
  -> InferenceRequest, InferenceRun, ToolCall, streaming engine
```

Le module `interactions` ne doit pas importer `models` pour fabriquer de faux comportements de compatibilité ; la vérification de la possibilité d'invoquer une cible appartient plus tard aux services d'inférence et de résolution.

### 6.4. Relations et conventions immuables

- Séquences dans des `tuple` (ou autres VOs immuables explicitement décidés), et **jamais triées** : ordre métier conservé.
- `Content` et `Message` sont comparés **par valeur**, conformément à leur classification DDD du document `05`.
- Une Conversation peut être implémentée en tant qu'**agrégat identifié** avec snapshots immuables, sans stockage obligatoire.
- La représentation d'une source de média ne télécharge, ne décode et n'interprète aucun média.
- Le codec contient le discriminant de chaque partie, nécessaire à une relecture exacte.

---

## 7. Séquence d'implémentation et dépendances

```text
P2-BOOT  - audit / ADR / contrat de composants / CI
   |
   +---------------------------+
   |                           |
   v                           v
L2.1 Role                L2.2 ContentPart + TextContent
   |                           |
   +-------------+-------------+
                 |
                 v
           L2.1 Message (intégration)
                 |
                 +-----------------------+
                 |                       |
                 v                       v
           L2.3 ImageContent       L2.1 Conversation? (optionnel)
                 |
                 v
           L2.4 Tests / codec / docs / packaging (transversal)
                 |
                 v
             M2 Gate
                 |
                 v
       0.1.0a2 - candidat alpha, non publié
```

**Point d'attention :** l'ordre **numérique** des lots suit notre pilotage, mais les implémentations de `Role` et `ContentPart` peuvent avancer en parallèle. `Message` ne sera finalisé **qu'après le contrat `Content`**, sans écrire un faux objet temporaire susceptible de figer une mauvaise API.

| Ordre de décision | Travail | Prérequis | Preuve attendue |
|---|---|---|---|
| 0 | P2-BOOT | M1 GO + tête `main` observée | ADR, backlog, DoR, CI baseline |
| 1 | `Role`, `ContentPart`, `Content` de base | ADR-008/010 | Tests unitaires et types |
| 2 | `Message` texte et contrat AC-006 | Rôle + Content validés | API publique + test AC-006 |
| 3 | `ImageContent` et sources ; AC-007 | `ContentPart` stable, ADR-011 | Texte/image ordonnés + codec |
| 4 | `Conversation` optionnelle | ADR-009 et raison de besoin | Absence de dépendance obligatoire |
| Transversal | L2.4 Qualité | Tous les commits | CI, docs, couverture, packaging |
| Gate | M2 | Toutes tâches bloquantes qualifiées | GO/NO-GO sur SHA `main` |
| Post-gate | `0.1.0a2` publication éventuelle | M2 GO + autorisation distincte | Tag/Release/PyPI **si** explicitement décidés |

---

## 8. Lot L2.1 - Message Domain

### 8.1. Objectif

Créer un modèle du **message conversationnel** indépendant des schémas fournisseurs, et définir le statut **optionnel** de Conversation. La construction d'un Message ne dépend pas de la disponibilité d'une Conversation persistante.

### 8.2. Contrats attendus

| Type | DDD | Contrat |
|---|---|---|
| `Role` | Type symbolique / VO | `SYSTEM`, `DEVELOPER`, `USER`, `ASSISTANT`, `TOOL` ; pas de conversion implicite |
| `Message` | **Value Object** | Exactly one Role + exactly one Content, valeurs immuables, égalité par valeur |
| `Conversation` | Aggregate Root optionnelle | Identité propre si implémentée, 0..* Message ordonnés |
| `BuildMessage` | Factory ou comportement simple, **pas de service applicatif imposé** | Construction validée, indépendante de toute API provider |
| `BuildConversation` | Factory optionnelle | Ordre préservé, persistence non requise |

L'introduction d'un `MessageId` au core est **différée** tant qu'un use case de traçage/persistence ne l'exige pas. Un éventuel `ConversationId` est un typed ID distinct et non interchangeable avec `ModelId`.

### 8.3. Backlog détaillé L2.1

| ID | Tâche d'implémentation | Tests / preuve | Priorité |
|---|---|---|---|
| `P2-L21-T01` | Fixer via ADR-008 la taxonomie des rôles et la stratégie d'extension | Rôle connu/non reconnu, absence de remapping implicite | P0 |
| `P2-L21-T02` | Créer `Role` (ou VO symbolique équivalent) dans `interactions/roles.py` | Typage et validité de 5 rôles canoniques | P0 |
| `P2-L21-T03` | Fixer via ADR-009 la classification `Message`/`Conversation` | Égalité par valeur ; Conversation optionnelle | P0 |
| `P2-L21-T04` | Définir `Message` après validation de `Content` en L2.2 | Champs et constructeurs typés, immuabilité | P0 |
| `P2-L21-T05` | Garantir `Message.role` valide et `Message.content` obligatoire | Tests `INT-004`, `INT-005` | P0 |
| `P2-L21-T06` | Définir les politiques `name?` et `metadata?` sans valeurs mutables non contrôlées | Frozen, type strict, test de non-mutation | P1 |
| `P2-L21-T07` | Implémenter le cas d'usage `BuildMessage` (factory si besoin) | `AC-006` : message texte agnostique | P0 |
| `P2-L21-T08` | Décider puis, si justifié, implémenter `Conversation` et l'ajout de messages | `INT-001/002` ; 0..* messages ; aucune persistence | P1 optionnel |
| `P2-L21-T09` | Documenter ordre des messages, rôle `TOOL`, responsabilité des adapters | API docs, tests du cas `TOOL` sans tool calling | P1 |
| `P2-L21-T10` | Qualifier la PR de L2.1, sans toucher aux exports M1 | CI, tests M1 conservés, revue DDD | P0 |

### 8.4. Critères de sortie L2.1

- [ ] Message texte construit avec `Role.USER` (ou valeur canonique équivalente choisie).
- [ ] `Message` est un VO, sans identité imposée et sans SDK.
- [ ] Rôle invalide rejeté explicitement ; pas de mapping implicite.
- [ ] `Message` avec `Content` absent ou vide rejeté conformément à `INT-005`.
- [ ] L'ordre des messages ne change pas lorsqu'une Conversation optionnelle est utilisée.
- [ ] M1 toujours vert ; import public documenté et testé.

---

## 9. Lot L2.2 - Content Domain

### 9.1. Objectif

Fournir le **conteneur universel de contenu** et le sous-type texte minimal, sans introduire d'extensions multimodales non qualifiées ni traiter le contenu comme une simple chaîne.

### 9.2. Contrats attendus

| Type | Contrat métier | Invariant |
|---|---|---|
| `ContentPart` | Base polymorphe du contenu avec discriminant explicite | Type et modality déterminables |
| `Content` | Value Object contenant 1..* parties dans un ordre donné | `INT-003`, `INT-005` |
| `TextContent` | VO immuable, texte, `language?` selon ADR | `text` est `str` et jamais `None` (`INT-008`) |
| `ContentKind` ou discriminant équivalent | Identifiant typé dans le codec | Ne jamais inférer depuis un schéma provider |

**Politique de chaîne vide à trancher par ADR-010 :** les sources interdisent `TextContent.text is None`, mais **n'interdisent pas systématiquement `text == ""`**. Proposition : autoriser un `TextContent("")` si explicitement voulu ; refuser un `Content(parts=())`. Les tests reflèteront le choix, sans surinterpréter la spécification.

### 9.3. Backlog détaillé L2.2

| ID | Tâche d'implémentation | Tests / preuve | Priorité |
|---|---|---|---|
| `P2-L22-T01` | Adopter ADR-010 : polymorphisme, ordre, discriminant | ADR explicite et modèle de types revu | P0 |
| `P2-L22-T02` | Définir `ContentPart` comme contrat de base immuable, extensible sans provider | `isinstance`/types/mypy, aucune dépendance SDK | P0 |
| `P2-L22-T03` | Créer `TextContent(text, language?)` avec validation | `INT-008`, `str` requis, cas vide documenté | P0 |
| `P2-L22-T04` | Créer `Content(parts: tuple[ContentPart, ...])` | Type strict, 1..*, tuple immuable | P0 |
| `P2-L22-T05` | Préserver l'ordre exact, y compris deux parties identiques | `text, text, text` sans set, sans sort | P0 |
| `P2-L22-T06` | Définir une `Modality` canonique pour `TextContent` | `MOD-003`: `text`, type importé du M1 | P0 |
| `P2-L22-T07` | Rejeter `ContentPart` inconnu/non typé avant sérialisation | Erreurs explicites ; aucun silencieux fallback | P0 |
| `P2-L22-T08` | Définir les méthodes d'inspection sans inférence de capability | Ex : parts, type, modality sans appel provider | P1 |
| `P2-L22-T09` | Intégrer et stabiliser `Message` depuis L2.1 | `AC-006`, API d'import racine/sous-package | P0 |
| `P2-L22-T10` | Qualifier tests et documentation du domaine texte | CI + exemples + typecheck | P0 |

### 9.4. Critères de sortie L2.2

- [ ] `Content` refuse zéro partie sans exception métier approuvée.
- [ ] Une partie n'est pas automatiquement transformée ou normalisée.
- [ ] `TextContent.text` refuse `None` et tout type autre que `str`.
- [ ] `Content` est un Value Object immuable et comparable par valeur.
- [ ] `ContentPart -> Modality` fonctionne avec le `Modality` existant de Phase 1.
- [ ] L'exemple `AC-006` est exécutable sans réseau, clé API ou SDK.

---

## 10. Lot L2.3 - Multimodal Content

### 10.1. Objectif

Ajouter la représentation d'**images** dans un Message multimodal, puis établir des points d'extension honnêtes pour les autres médias. Le modèle de domaine n'est ni un chargeur de média, ni un proxy HTTP, ni un décodeur de formats.

### 10.2. Contrat des sources de média (ADR-011)

La spécification mentionne URL, référence de blob et asset ID, sans imposer un schéma précis. Proposition : une abstraction de **référence** plutôt qu'une dépendance à `pathlib`, `requests` ou à un asset fournisseur.

```text
MediaSourceRef  [VO conceptuel, nom provisoire]
  |-- UrlRef(url: str)          # seulement référence ; aucun fetch
  |-- AssetRef(asset_id: str)   # identifiant opaque ; aucune API provider
  `-- BinaryRef(reference: str) # blob externe identifié, sans bytes implicites
```

**Arbitrages obligatoires :** URI `http/https` ou autres schemes acceptés ; règles de non-vacuité ; `mime_type` optionnel ou requis ; `detail?` conceptuel non provider-native ; stratégie de sérialisation. Les URI ne doivent pas être utilisées comme prétexte pour exécuter des requêtes réseau. La protection SSRF de tout futur *fetcher* est à l'extérieur du domaine et nécessitera un contrôle dédié.

### 10.3. Objets cibles

| Type | Niveau M2 | Validation |
|---|---|---|
| `ImageContent` | **Obligatoire** | Référence de source exploitable, modality `image` |
| `MediaSourceRef` (ou équivalent) | **Obligatoire si ADR-011 l'adopte** | Source typée, pas de réseau, pas de lecture fichier |
| `AudioContent` | **Extension optionnelle** | Contrat futur et format explicite lorsque requis |
| `VideoContent` | **Extension optionnelle** | Point d'extension explicite, pas de promesse de décodage |
| `DocumentContent` | **Extension optionnelle** | Distinct de `TextContent`, pas de PDF parsing |
| `ToolCallContent`, `ToolResultContent` | **Exclus du GO M2** | Réservés à `0.1.0a4` |

### 10.4. Backlog détaillé L2.3

| ID | Tâche d'implémentation | Tests / preuve | Priorité |
|---|---|---|---|
| `P2-L23-T01` | Adopter ADR-011 : source image, formats, sécurité passive | Exemples et alternatives documentés | P0 |
| `P2-L23-T02` | Définir les types de référence de média décidés | Référence vide/invalide rejetée, pas de réseau | P0 |
| `P2-L23-T03` | Implémenter `ImageContent` immuable | `INT-009`, source obligatoire, `MOD-003` | P0 |
| `P2-L23-T04` | Qualifier `text -> image -> text` dans un `Content` | Ordre conservé, aucune concaténation implicite | P0 |
| `P2-L23-T05` | Distinguer modality `image` de capability `vision` | `MOD-003` et invariant M1 maintenus | P0 |
| `P2-L23-T06` | Adopter ADR-013 et documenter les extensions audio/vidéo/document | Aucune API fictive / pas de faux support | P1 |
| `P2-L23-T07` | Implémenter une variante additionnelle seulement si use case/ADR la rend nécessaire | Format requis si audio ; document distinct du texte | P2 conditionnel |
| `P2-L23-T08` | Démontrer `AC-007` : Message contenant texte + image | Test d'acceptation et exemple exécutable | P0 |
| `P2-L23-T09` | Préparer le codec discriminé pour image + textes | Round-trip, MIME, refs, ordre | P0 |
| `P2-L23-T10` | Qualifier refus des sources invalides, absence de fetch et de conversion | Tests négatifs, architecture, offline | P0 |

### 10.5. Critères de sortie L2.3

- [ ] `ImageContent` distingue sa source et sa modality du texte.
- [ ] Construction `TextContent -> ImageContent -> TextContent` déterministe et ordonnée.
- [ ] La construction d'un Message multimodal ne requiert ni URL valide accessible, ni HTTP, ni clé API.
- [ ] Une source absente ou invalide déclenche une erreur de domaine.
- [ ] La présence d'`ImageContent` ne fabrique pas une capability `vision` effective.
- [ ] `AudioContent`, `VideoContent`, `DocumentContent` sont soit des fonctionnalités réellement testées, soit **explicitement documentées comme différées** ; pas de stub présenté comme support complet.

---

## 11. Lot L2.4 - Quality, Testing, Documentation & Packaging

### 11.1. Objectif

Qualifier l'interaction-domain et son intégration **sans régression de M1**. Les tests et les exemples démarrent dès L2.1/L2.2 : L2.4 est **transversal**, pas un travail repoussé à la fin.

### 11.2. Backlog détaillé L2.4

| ID | Tâche d'implémentation | Preuve attendue | Priorité |
|---|---|---|---|
| `P2-L24-T01` | Conserver la CI Phase 1 et ajouter les suites Interaction | 137 tests M1 toujours verts + tests P2 | P0 |
| `P2-L24-T02` | Couvrir les erreurs de structure, rôle, ordre, type et références | Cas négatifs `INT-*`, messages invalides | P0 |
| `P2-L24-T03` | Mettre en place le codec Interaction versionné (ADR-012) | `Message -> dict -> JSON -> Message` | P0 |
| `P2-L24-T04` | Garantir distinction du codec Interaction et du codec Model v1 | Tests de sérialisation M1 inchangés | P0 |
| `P2-L24-T05` | Maintenir Ruff, mypy strict et la matrice Python 3.11/3.12/3.13 | CI verte par version | P0 |
| `P2-L24-T06` | Renforcer les tests des frontières et imports relatifs/dynamiques connus | Aucun SDK/HTTP/IO dans `domain/interactions` | P0 |
| `P2-L24-T07` | Rejouer les tests sans credentials et sans connexion réseau | Offline fixture + test de non-I/O | P0 |
| `P2-L24-T08` | Ajouter exemples exécutables texte et image | 2 exemples exécutés en CI | P0 |
| `P2-L24-T09` | Écrire les docs Concept / API / invariants / décisions ADR | Documentation revue et liée aux tests | P0 |
| `P2-L24-T10` | Capturer couverture et résultat de chaque version | Rapport horodaté et SHA exact ; pas de seuil inventé | P0 |
| `P2-L24-T11` | Construire wheel et sdist avec smoke install isolés | `python -m build`, imports Interaction installés | P0 |
| `P2-L24-T12` | Contrôler packaging, MIT, changelog, README, version alpha | Artefacts candidats sans publication | P0 |
| `P2-L24-T13` | Documenter la traçabilité exigences -> tests -> PR -> SHA | `PHASE_2_TRACEABILITY.md` | P0 |
| `P2-L24-T14` | Préparer le procès-verbal M2 GO/NO-GO | `M2_GATE_REVIEW.md` et preuves | P0 |
| `P2-L24-T15` | Réconcilier les remarques PIR pertinentes de Phase 1 | Suivi des écarts et actions documentaires | P1 |

### 11.3. Quality gates

- **Zéro** test bloquant échoué, erreur de typage strict ou lint bloquant sur le SHA de qualification.
- **Aucune régression M1** ; les 137 tests de référence restent dans la suite, sous réserve de renommages justifiés et traçables.
- La **couverture combinée de 89 % est une mesure de M1**, non un seuil M2 contractuel. Proposition : viser la couverture des branches critiques (rôles, polymorphisme, sources) et publier le taux sans promettre un chiffre avant adoption d'un standard.
- L'outil de validation des imports et la fixture réseau sont des **fitness functions ciblées**, pas une preuve de sécurité réseau exhaustive.
- Les fichiers construits et installés ne signifient pas qu'un package est publié sur PyPI.

---

## 12. Matrice de tests Phase 2

Cette matrice constitue un minimum. Les noms `TEST-I*` sont de **nouveaux identifiants de qualification**, distincts des invariants sources `INT-*`.

| Test | Description du scénario | Invariant / critère | Attendu |
|---|---|---|---|
| `TEST-I01` | Message `USER` avec une partie texte | `INT-004/005`, `AC-006` | Succès |
| `TEST-I02` | Rôle inconnu sans mapping explicite | `INT-004/006/007` | Échec explicite ou extension documentée |
| `TEST-I03` | `Message` sans Content | `INT-005` | Rejet |
| `TEST-I04` | `Content` sans partie | `INT-005` | Rejet |
| `TEST-I05` | `Content` texte-image-texte | `INT-003`, `AC-007` | Ordre identique |
| `TEST-I06` | `TextContent(text=None)` | `INT-008` | Rejet |
| `TEST-I07` | `TextContent(text="")` | ADR-010 | Conformité à la décision adoptée |
| `TEST-I08` | `ImageContent` sans source | `INT-009` | Rejet |
| `TEST-I09` | `ImageContent` avec `AssetRef` opaque | `INT-009` | Succès sans I/O |
| `TEST-I10` | `ContentPart` texte vs image | `MOD-003` | `text` ≠ `image` |
| `TEST-I11` | Image présente, capability `vision` non déclarée | `MOD-005`, M1 | Aucune capability inventée |
| `TEST-I12` | `Message` comparé à valeur égale | DDD VO | Égalité par valeur |
| `TEST-I13` | Mutation de `Content.parts` / métadonnées | Immutabilité | Rejet / non-mutation |
| `TEST-I14` | Conversation optionnelle avec messages ordonnés | `INT-001/002` | Succès si Conversation incluse |
| `TEST-I15` | Message construit hors Conversation | `INT-001` | Succès |
| `TEST-I16` | Serialization de message texte | `AC-006`, ADR-012 | Round-trip |
| `TEST-I17` | Serialization multimodale | `AC-007`, ADR-012 | Type/ref/ordre préservés |
| `TEST-I18` | Type ou version de codec inconnu | ADR-012 | Erreur explicite |
| `TEST-I19` | Codec `Model` v1 avant/après P2 | ADR-004, M1 | Tests M1 inchangés |
| `TEST-I20` | Import sans SDK/fetch/credentials | `INT-007`, AC-018 partiel | Succès hors réseau |
| `TEST-I21` | Message avec Role TOOL, sans ToolCall | Séparation `0.1.0a4` | Ne déclenche rien |
| `TEST-I22` | URI d'image non accessible | Aucune IO | Construction indépendante de l'accès |
| `TEST-I23` | Sdist/wheel import Interaction | Packaging | Succès en venv isolé |
| `TEST-I24` | Régression complète Phase 1 | M1 | Aucun test cassé |

### 12.1. Tests d'acceptation source

**AC-006 - Message texte agnostique :** construire un Message valide, l'exporter, le relire et constater que ni import provider ni credential ne sont nécessaires. **AC-007 - Message multimodal :** construire, sérialiser et relire un message contenant au moins un texte et une image, en conservant le discriminant, la source et l'ordre. Ces deux critères proviennent des exigences `01` et de la roadmap, sans extension arbitraire aux fonctionnalités d'inférence.

### 12.2. Exemples d'échec attendus

```python
# Pseudo-API illustrative : les exceptions exactes seront fixées par ADR.
Message(role=None, content=...)               # role invalide
Message(role=Role.USER, content=None)          # content absent
Content(parts=())                              # interdit par INT-005
TextContent(text=None)                         # interdit par INT-008
ImageContent(source=None)                      # interdit par INT-009
```

Les tests doivent vérifier le **type d'erreur de domaine** et le contexte suffisant, sans exposer de secret dans les messages d'erreur.

---

## 13. Gouvernance des PR, branches et commits

### 13.1. Workflow Git recommandé

```text
main  [M1 GO]
  |
  +-- feature/p2-boot-interaction-contracts      -> PR P2-BOOT
  |      |
  |      +-- feature/p2-l22-content-domain       -> PR L2.2
  |                 |
  |                 +-- feature/p2-l21-message-domain  -> PR L2.1
  |                            |
  |                            +-- feature/p2-l23-multimodal-content -> PR L2.3
  |                                       |
  |                                       +-- feature/p2-l24-quality-testing -> PR L2.4
  |                                                  |
  |                                                  +-- review/m2-qualification -> PR M2
  |
  +-- docs/m2-gate-go-record                     -> PR d'archivage APRES décision
```

Les branches peuvent être empilées comme en Phase 1 ; l'ordre de dépendance technique prime sur la numérotation des lots. **Ne jamais fusionner des PR empilées vers `main` sans mise à jour de base, vérification de la diff et CI sur SHA exact.**

### 13.2. Séquence de qualification

1. Créer la branche depuis le **dernier `main` vérifié**.
2. Implémenter une tâche et ses tests négatifs/positifs dans la même PR.
3. Exécuter Ruff, mypy strict, pytest offline et build à chaque étape.
4. Vérifier la présence des dossiers **source réels** dans l'arbre Git avant d'ajouter des fichiers, pour éviter l'écrasement d'une étape précédente.
5. Mettre à jour les dépendances des PR et rebaser/retargeter si nécessaire.
6. Relire les ADR et la sémantique exposée par les exports publics.
7. Fusionner **après** revue, puis refaire CI sur le SHA final de `main`.
8. Archiver le verdict M2 dans une PR documentaire et requalifier le SHA après fusion.

### 13.3. Evidence-first

Une PR doit énoncer ce qui est **réellement testé** (ex. « 175 passed sur SHA ... »), pas un objectif anticipé. Toute erreur CI mène à un correctif et à une nouvelle exécution ; **l'ancien statut vert n'est jamais attribué au nouveau SHA**.

---

## 14. Jalon M2 et critères GO / NO-GO

### 14.1. Gates internes proposés

| Gate | Définition | Evidence attendue |
|---|---|---|
| `G0` - Architecture Ready | ADR-008..013 décidées ; contract Domain / Role / Content et Codec fixé | ADR signées comme décisions de projet, tests candidats |
| `G1` - Content & Message Ready | L2.1 et L2.2 achevés | `AC-006`, `INT-004/005/008` |
| `G2` - Multimodal Ready | L2.3 achevé | `AC-007`, `INT-003/009`, `MOD-003/005` |
| `G3` - Quality Ready | L2.4, CI et packaging | Tests, typing, lint, offline, coverage, wheels/sdist |
| `G4` - Integration Ready | PR intégrées dans `main`, doc/README cohérents | SHA final et CI finale `main` |
| **M2** | **G0 + G1 + G2 + G3 + G4** | **GO ou NO-GO documenté** |

### 14.2. Definition of Done M2

- [ ] Tous les objets obligatoires du scope existent et sont importables depuis les chemins publics adoptés.
- [ ] `Message` et `Content` respectent les cardinalités 1 et 1..* ; l'ordre est stable.
- [ ] Cinq rôles canoniques au minimum, sans mapping provider implicite.
- [ ] `TextContent` et `ImageContent` ont une sémantique typée et testée.
- [ ] `AC-006` et `AC-007` passent en tests d'acceptation.
- [ ] `INT-*` du scope sont reliés à des preuves ; exceptions documentées et justifiées.
- [ ] Les objets `Conversation` restent optionnels pour tout message.
- [ ] Le codec Interaction est versionné, round-trip et ne casse pas le codec Model.
- [ ] Pas de SDK, HTTP, accès réseau ni credentials obligatoires dans le Domain Core.
- [ ] La suite Phase 1 ne régresse pas et le rapport de couverture est conservé.
- [ ] La CI Python 3.11/3.12/3.13 et les builds wheel/sdist sont réussis.
- [ ] Le README, les exemples et la référence API sont exacts et exécutables.
- [ ] Les ADR requises sont adoptées ou remplacées explicitement, sans fausse signature de tiers.
- [ ] Les PR sont fusionnées, `main` est testé sur son **commit final**.
- [ ] Le rapport `M2_GATE_REVIEW.md` porte un GO/NO-GO motivé et un SHA exact.

### 14.3. NO-GO obligatoire si

- Un rôle invalide est silencieusement converti en un rôle standard.
- Un `Content` vide est admis sans exception explicitement approuvée.
- L'ordre des ContentParts change au cours du round-trip JSON.
- Une représentation d'image déclenche un fetch ou transforme implicitement le contenu.
- Le core dépend d'un SDK provider ou d'un service réseau.
- Des tests existants M1 échouent ou le codec Model est cassé sans décision explicite de rupture.
- Les PR ou le SHA `main` ne sont pas qualifiés, ou les preuves de CI sont manquantes.
- La documentation prétend publier un package qui n'a pas été publié.

### 14.4. Format de procès-verbal M2

```markdown
# M2 - Interaction Foundations Qualified
- Date de revue :
- Responsable de décision :
- Commit main exact :
- Branch / PR incluses :
- CI GitHub (URL) :
- Python 3.11 / 3.12 / 3.13 :
- Tests passés / échoués :
- Couverture observée :
- AC-006 : PASS / FAIL
- AC-007 : PASS / FAIL
- Invariants INT/MOD : PASS / FAIL
- ADR 008-013 : ACCEPTED / REVISED / OPEN
- Codec Interaction : PASS / FAIL
- Régression M1 : PASS / FAIL
- Wheel / sdist : PASS / FAIL
- Risques ouverts :
- Décision M2 : GO / NO-GO
- Publication v0.1.0a2 : NON EFFECTUÉE / décision séparée
```

---

## 15. Politique de versionnement et publication

### 15.1. Ce que qualifie M2

M2 valide un **contrat d'interaction** dans le dépôt Python, avec un build de paquet installable. La propriété `version = "0.1.0a2"` (si adoptée dans le `pyproject.toml` en cours de travail) ne prouve **ni la création d'un tag**, **ni une GitHub Release**, **ni la publication sur PyPI**.

### 15.2. Préconditions d'une publication éventuelle

1. M2 GO formel et CI verte sur `main` final.
2. API publique et schéma Interaction gelés avec notes de compatibilité.
3. Revue licence MIT, titularité, contributors et métadonnées.
4. Contrôle des wheels/sdist, signatures/hashes si politique adoptée.
5. Décision explicite de publication, avec une procédure distincte et possibilité de rollback.

### 15.3. Position de la version précédente

La baseline `0.1.0a1` était qualifiée sous M1 mais **non publiée** à la date de revue. Si elle demeure non publiée lors de M2, la décision de publier `0.1.0a2` directement doit être explicite. Ne pas créer rétrospectivement un tag `v0.1.0a1` pour simuler une release.

---

## 16. Risques, compromis et réponses

| ID | Risque | Impact | Réponse / mesure |
|---|---|---|---|
| `P2-R01` | `Message` figé avant `Content` | Contrat cassant / surconception | Développer Role et Content d'abord ; finaliser Message ensuite |
| `P2-R02` | Role provider-specific dans core | Perte d'agnosticisme | ADR-008, tests de rôles inconnus, adapters ultérieurs |
| `P2-R03` | Toutes les modalités média implémentées prématurément | APIs non qualifiées | Texte + image obligatoires, extensions explicites |
| `P2-R04` | Source URI interprétée comme ordre de téléchargement | I/O non contrôlée / SSRF future | VO référentiel pur, aucun fetch ; contrôle au port futur |
| `P2-R05` | Mapping image vers capability vision implicite | Mensonge de capability | Tests `ImageContent` ≠ `Capability("vision")` |
| `P2-R06` | Ordre des parts perdu par sérialisation | Sens du message altéré | Tuple + round-trip ordonné, pas de sort/dict non ordonné |
| `P2-R07` | Codec Interaction modifie JSON Model v1 | Régression M1 | Codec dédié, tests M1 rejoués |
| `P2-R08` | Conversation obligatoire pour chaque message | Couplage au chat et à la persistence | Conversation facultative, Message indépendant |
| `P2-R09` | `Role.TOOL` introduit une exécution tools implicite | Dérive de périmètre | Type symbolique seulement ; `ToolCall` en a4 |
| `P2-R10` | README/API diverge des tests | Erreur d'adoption utilisateurs | Exemples Python exécutés en CI ; doc review |
| `P2-R11` | Des sources `00-09` restent hors dépôt | Traçabilité partielle | Index de références et statut de synchronisation |
| `P2-R12` | Couverture numérique déclarée sans norme | Faux sentiment de qualité | Mesurer, commenter les branches critiques, adopter seuil si désiré |
| `P2-R13` | PR empilées mal fusionnées ou mauvaise base Git tree | Pertes de fichiers, CI trompeuse | Comparaison arbres/diffs + CI sur SHA final |
| `P2-R14` | Alpha candidate confondue avec release publiée | Risque de communication/packaging | Documenter M2 ≠ release, procédure séparée |
| `P2-R15` | Données de média/URL sensibles exposées dans logs | Fuite d'information | Redaction dans erreurs/logs, pas d'impression de contenu/URI sensible |

---

## 17. Convention Software Design & Learning

Ce chantier sert aussi à formaliser les choix d'architecture, afin que chaque implémentation explique **ce qui est utilisé, pourquoi, quelles alternatives existent, et comment le vérifier**.

| Concept | Application Phase 2 | Preuve pédagogique attendue |
|---|---|---|
| **DDD** | `Message`/`Content` Value Objects ; Conversation optionnelle | Docstring et ADR sur identité/valeur |
| **SOLID - SRP** | Message n'infère pas ; MediaSourceRef ne télécharge pas | Tests de frontières et de non-I/O |
| **DIP / Hexagonal** | Domain importe uniquement des types du domaine / stdlib | Fitness function des imports |
| **Open/Closed** | Nouveaux `ContentPart` sans modifier arbitrairement Model | Discriminant/extension ADR et tests |
| **Composition over Inheritance** | `Message` compose un `Content` polymorphe | Diagramme et API publique |
| **Immutability** | Typed VOs et ordered tuple | Tests mutation/égalité |
| **KISS / YAGNI** | Pas de template manager ni Conversation persistence pour a2 | Exclusions assumées |
| **Explicit over Implicit** | `Role`, media source, modality, codec version | Tests d'échec explicites |
| **Contract & Regression Testing** | AC-006/007 + tests Phase 1 | Matrice de preuves et CI |

Le code doit conserver des docstrings décrivant **l'invariant**, pas seulement reformuler le nom des paramètres. Chaque tâche importante relie sa conception à un test et à une référence documentaire.

---

## 18. Backlog immédiat - ordre de démarrage

**Les dix prochaines actions, dans cet ordre de gouvernance :**

1. **`P2-BOOT-T01`** - Vérifier le `main` actuel, la CI M1 et les éventuelles évolutions postérieures à ce plan.
2. **`P2-BOOT-T02`** - Créer une branche P2-BOOT et un dossier de décision ADR-008..013.
3. **`P2-BOOT-T03`** - Décider `Role`, extensions non standard et rôle `TOOL`.
4. **`P2-BOOT-T04`** - Décider `Message` VO et `Conversation` optionnelle.
5. **`P2-BOOT-T05`** - Décider la hiérarchie `ContentPart`, sources et codec Interaction.
6. **`P2-BOOT-T06`** - Définir le chemin des packages publics et le respect des dépendances du M1.
7. **`P2-L22-T01/T02`** - Implémenter le noyau `ContentPart` après ADR.
8. **`P2-L21-T02`** - Implémenter `Role` et tester les rôles invalides.
9. **`P2-L22-T03/T04`** - Implémenter `TextContent` et `Content` ordonné non vide.
10. **`P2-L21-T04/T05`** - Composer `Message` et satisfaire la première version de `AC-006`.

**Première PR conseillée :** `P2-BOOT - Interaction Contracts & Architecture Decisions`, contenant les ADR, la structure des futurs packages (sans implémentation factice), les tests de fitness de départ et la liste de tâches.

---

## 19. Livrables de fin de Phase 2

| Document / artefact | Statut attendu à M2 |
|---|---|
| `02_PYLLMKIT_PHASE_2_IMPLEMENTATION_PLAN.md` | Plan approuvé et relié à la PR P2-BOOT |
| `docs/adr/ADR-008-*.md` à `ADR-013-*.md` | Décisions adoptées ou remplacées explicitement |
| `src/pyllmkit/domain/interactions/` | Objects Message/Content/Text/Image qualifiés |
| `tests/unit/domain/interactions/` | Invariants positif/négatif couverts |
| `tests/acceptance/test_ac_006_text_message.py` | AC-006 PASS |
| `tests/acceptance/test_ac_007_multimodal_message.py` | AC-007 PASS |
| `tests/serialization/test_interaction_codec.py` | Codec versionné testé |
| `examples/04_text_message.py` et `05_multimodal_message.py` | Exécutables en CI |
| `docs/concepts/interaction-domain.md` | Concepts et relations DDD |
| `docs/api/interaction-domain.md` | Signature publique réellement implémentée |
| `docs/quality/PHASE_2_TRACEABILITY.md` | Sources -> tâches -> tests -> CI |
| `docs/quality/M2_GATE_REVIEW.md` | Décision GO/NO-GO, SHA et preuves |
| `docs/quality/M2_PHASE_2_CLOSURE_SUMMARY.md` | Bilan post-implémentation après GO |
| `CHANGELOG.md`, `README.md`, `ROADMAP.md` | Informations cohérentes avec les faits |
| Wheel et sdist installables | Construits et testés, non nécessairement publiés |
| PR GitHub par lot et M2 | Fusionnées si et seulement si gates satisfaits |

---

## 20. Références et liens de vérification

### Documentation du projet

- `00_PYLLMKIT_EXPRESSION_DU_BESOIN.md`
- `01_PYLLMKIT_REQUIREMENTS_ANALYSIS.md`
- `02_PYLLMKIT_PRODUCT_VISION_AND_ARCHITECTURE_PRINCIPLES.md`
- `03_PYLLMKIT_SYSTEM_ARCHITECTURE.md`
- `04_PYLLMKIT_DOMAIN_OBJECTS.md`
- `05_PYLLMKIT_ENTITIES_AND_VALUE_OBJECTS.md`
- `06_PYLLMKIT_DOMAIN_RELATIONSHIPS_AND_ERD.md`
- `07_PYLLMKIT_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md`
- `08_PYLLMKIT_COMMANDS_QUERIES_AND_USE_CASES.md`
- `09_PYLLMKIT_DOMAIN_EVENTS_CATALOG.md`
- `ROADMAP.md` - section `0.1.0a2 - Interaction Primitives`
- `01_PYLLMKIT_PHASE_1_IMPLEMENTATION_PLAN.md`
- `PYLLMKIT_PHASE_1_POST_IMPLEMENTATION_REVIEW.md`

### Sources GitHub vérifiées

- Dépôt : https://github.com/tawounfouet/pyllmkit
- Baseline `main` à la rédaction : https://github.com/tawounfouet/pyllmkit/commit/d7f06072d246819fb976c6a456949995ae33562d
- Procès-verbal M1 : https://github.com/tawounfouet/pyllmkit/blob/main/docs/quality/M1_GATE_REVIEW.md
- CI M1 finale : https://github.com/tawounfouet/pyllmkit/actions/runs/40638604245
- ADR M1 : https://github.com/tawounfouet/pyllmkit/tree/main/docs/adr
- Package actuel : https://github.com/tawounfouet/pyllmkit/blob/main/pyproject.toml

---

## 21. Décision de lancement proposée

> **P2-BOOT : READY FOR IMPLEMENTATION, sous réserve de la revue des ADR de Phase 2.**  
> **M2 : NOT STARTED / NOT QUALIFIED.**  
> **`0.1.0a2` : VERSION CIBLE, NI PUBLIÉE NI TAGGÉE PAR CE PLAN.**

La Phase 2 doit hériter de la discipline validée en Phase 1 : **scope restreint, concepts explicites, ports séparés, tests d'invariants, qualité reproductible et verdict fondé sur un commit réellement vérifié**. Son résultat attendu est un langage de domaine suffisant pour construire des interactions textuelles et multimodales, que la Phase suivante (`0.1.0a3`) pourra ensuite utiliser pour décrire l'inférence.