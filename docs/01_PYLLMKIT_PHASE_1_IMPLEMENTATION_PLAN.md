# PyLLMKit - Plan d'implémentation de la Phase 1

> **PHASE 1 - Fondations du framework**  
> Lots : **L1.1 Model Domain**, **L1.2 Capabilities & Modalities**, **L1.3 Quality & Testing**  
> Jalon de sortie : **M1 - Fondations qualifiées**  
> Artefact cible : **`v0.1.0a1` - Model Domain Foundations**

| Métadonnée | Valeur |
|---|---|
| Projet | PyLLMKit |
| Référence documentaire | `01_PYLLMKIT_PHASE_1_IMPLEMENTATION_PLAN.md` |
| Référence de pilotage | `ROADMAP.md` - section `0.1.0a1` |
| Statut | **Plan proposé - non implémenté / non qualifié dans cette revue** |
| Date de rédaction | 2026-10-27 |
| Langage cible | Python >= 3.11 (préconisation des exigences) |
| Architecture | Domain-First, Ports & Adapters, Provider-Agnostic |
| Type de release | **Alpha** (`0.1.0a1` selon PEP 440) ; candidate à publication après M1 |
| Dépendances documentaires | `00` à `09` fournis ; documents `10` à `22` cités dans la roadmap mais non vérifiés ici |

---

## 1. Objet du document

Ce plan transforme la **Phase 1 - Fondations du framework** en unités de travail exécutables, vérifiables et traçables. Il précise, pour chaque lot : objectifs, objets Python, frontières, dépendances, tâches, preuves, tests, critères d'acceptation et conditions de clôture.

**Il ne certifie pas l'état du dépôt.** Aucun état réel du code, de la CI ou des tags ne doit être déduit de ce document. Les choix d'implémentation indiqués comme *propositions* sont à figer par ADR ou revue technique.

### 1.1 Résultat recherché

À la fin de la phase, on doit pouvoir **créer, caractériser, comparer et sérialiser** des modèles LLM au moyen d'objets de domaine Python explicitement typés, sans dépendre d'OpenAI, Anthropic, d'un endpoint, d'un compte cloud ou d'un réseau.

Trois résultats doivent être démontrés :

1. **L1.1** : les modèles ont une identité canonique et des artefacts distincts, avec règles DDD explicites.
2. **L1.2** : leurs capacités et modalités sont représentées sans les confondre ni inventer de support inconnu.
3. **L1.3** : les invariants, la sérialisation, les imports, la documentation et le packaging sont qualifiés par des tests reproductibles.

### 1.2 Positionnement dans la roadmap

```text
ROADMAP.md
  ├── P0 - Architecture baseline / corrections critiques
  ├── P1 - Référentiel documentaire et contrats
  └── IMPLEMENTATION
       └── PHASE 1 - FOUNDATIONS
            ├── L1.1 - Model Domain
            ├── L1.2 - Capabilities & Modalities
            ├── L1.3 - Quality & Testing (transversal)
            └── M1 - Domain Foundations Qualified
                 └── Candidat de publication v0.1.0a1

Après M1 : 0.1.0a2 - Interaction Primitives (roadmap existante)
```

**Note de cohérence** : `0.1.0a2` correspond aux primitives d'interaction dans `ROADMAP.md`, et non au registry. L'inférence, le streaming, les tools, les adapters et le registry opérationnel relèvent de jalons ultérieurs.

---

## 2. Périmètre : inclus, exclus et frontières

### 2.1 Inclus dans la Phase 1

- Identité et description logique des modèles : `ModelId`, `Model`, `ModelIdentity`, `ModelFamily`, `ModelVersion`.
- Objets nécessaires à une identité et une description fidèles : `ModelVariant`, `ModelRevision`, `ModelArchitecture`, `ModelLimits`, `ModelArtifact`, `ModelArtifactId`, `ProviderModelRef` (selon arbitrages).
- Description des capabilities : `Capability`, `CapabilityId`, `CapabilitySupport`, `SupportLevel`, `CapabilityConstraint`, `CapabilitySet`.
- Description des modalités : `Modality`, `ModalitySet`, **entrées** et **sorties** distinctes.
- Validations structurelles, identité/égalité, immutabilité des value objects, erreurs de domaine initiales et sérialisation nécessaire au MVP.
- Tests unitaires, d'invariants, de propriétés limites, de sérialisation, de dépendances, packaging local et exemples pédagogiques.

### 2.2 Exclus de la Phase 1

| Sujet | Raison / jalon ultérieur |
|---|---|
| `Conversation`, `Message`, `ContentPart` | `0.1.0a2` - Interaction Primitives |
| `InferenceRequest`, `InferenceRun`, `InferenceResponse` | `0.1.0a3` - Inference Primitives |
| Tool calling, structured output | `0.1.0a4` |
| Streaming opérationnel / événements d'inférence | `0.1.0b1` |
| ModelRegistry et discovery opérationnels | `0.1.0b2` |
| SDK provider / OpenAI Adapter / appels réseau | `0.2.0a1` et suivants |
| Routage automatique, retry, exécution d'outils, agents, RAG | Hors périmètre initial du framework ou autres couches |
| Résolution complète des *effective capabilities* entre modèle/déploiement/provider/endpoint | Préparer le contrat et la sémantique ; implémentation inter-couches ultérieure |

### 2.3 Invariants non négociables

- `Model != Provider`, `Model != Deployment`, `Model != Endpoint`, `Model != ModelArtifact`.
- `Model` possède une identité stable ; un `Model` peut exister sans artefact public.
- Plusieurs `ModelArtifact` peuvent référencer **un même** `ModelId`, sans transformer un artefact en modèle logique.
- `ModelVersion` n'est **pas** astreint au format SemVer ; `ModelRevision` est distincte.
- `Capability != Modality` : **IMAGE** est une modality ; **VISION** est une capability.
- `UNKNOWN` / absence de metadata ne signifient ni `NATIVE`, ni `UNSUPPORTED`, ni `0`.
- Core pur : **aucun import provider SDK, appel HTTP, lecture de credentials, routing ou réseau**.
- Les value objects sont immuables de préférence ; les entities ont une identité et sont comparées par identité.

Références : `02` (principes), `05` (classification DDD), `06` (relations), `07` (`INV-001`, `INV-004`, `INV-006`, `MODEL-*`, `CAP-*`, `MOD-*`, `INV-011` à `INV-017`).

---

## 3. Prérequis / critères d'entrée (Definition of Ready)

**À vérifier avant le premier commit d'implémentation** :

- [ ] État actuel du repository inventorié : arborescence, branche, licence, version, CI, éventuel code préexistant.
- [ ] Décisions P0 bloquantes de `ROADMAP.md` vérifiées, notamment `ARCH-001` (Model / Artifact / Deployment) et `ARCH-002` (frontière des outils, sans code de tool calling dans P1).
- [ ] Vocabulaire des objets de Phase 1 et égalité DDD validés (`05`/`07`).
- [ ] ADR-01 : politique des **typed IDs** (`ModelId`, `ModelArtifactId`) et représentation des identifiants.
- [ ] ADR-02 : choix `dataclass(frozen=True)` / objets immuables / politique de mutation contrôlée pour `Model`.
- [ ] ADR-03 : traitement `UNKNOWN` / absence d'information et niveaux de support des capabilities.
- [ ] ADR-04 : représentation de la relation `Model ↔ ModelArtifact` et format de sérialisation.
- [ ] ADR-05 : politique de dépendances et des exports publics du package.

Si une ADR ne peut pas être tranchée avant le développement, ouvrir une décision temporaire explicite avec son responsable et le test qu'elle influence ; **ne pas masquer l'incertitude dans une valeur par défaut**.

### 3.1 Conventions de pilotage

- **Phase** : `P1`.
- **Lots** : `P1-L11`, `P1-L12`, `P1-L13`.
- **Tâches** : `P1-L11-T01`, etc.
- **Jalon** : `M1` - Domain Foundations Qualified.
- **Version** : `v0.1.0a1` (version alpha PEP 440 ; non équivalente à `0.1.0rc1`).
- Statuts : `TODO`, `READY`, `IN_PROGRESS`, `BLOCKED`, `IN_REVIEW`, `QUALIFIED`.
- Une tâche n'est `QUALIFIED` qu'avec **commit + tests + critère de sortie démontré**.

---

## 4. Découpage du travail / séquence d'exécution

```text
                ┌──────────────────────┐
                │ Préflight / ADR / CI │
                └──────────┬───────────┘
                           │
                 ┌─────────▼──────────┐
                 │ L1.1 Model Domain  │
                 │ IDs, Identity,     │
                 │ Model, Artifact    │
                 └─────────┬──────────┘
                           │
                 ┌─────────▼─────────────┐
                 │ L1.2 Capabilities &   │
                 │ Modalities            │
                 │ descriptors, sets     │
                 └─────────┬─────────────┘
                           │
                 ┌─────────▼───────────┐
                 │ L1.3 Qualification  │
                 │ tests/docs/packaging│
                 └─────────┬───────────┘
                           │
                 ┌─────────▼───────────┐
                 │ M1 - QUALIFIED      │
                 └─────────┬───────────┘
                           │
                 ┌─────────▼────────────┐
                 │ v0.1.0a1 - candidat │
                 │ à publication       │
                 └──────────────────────┘
```

**Exécution réelle** : le lot **L1.3 démarre dès le premier objet du L1.1** (tests et documentation en continu). Le graphe est un ordre de validation, pas une obligation de développer tous les tests à la fin.

| Ordre | ID | Travail | Dépendances | Livrable de sortie |
|---|---|---|---|---|
| 0 | P1-BOOT | Audit du dépôt, architecture cible, ADR, outils qualité | Documents `00–09`, `ROADMAP.md` | Baseline + décisions |
| 1 | P1-L11 | Value objects et entities Model Domain | BOOT | API modèle et tests |
| 2 | P1-L12 | Capabilities & Modalities | Identifiants / contrat `Model` suffisamment stable | Descriptors et collections qualifiés |
| 1–3 | P1-L13 | Testing, docs, architecture checks, packaging | Transversal | Rapport d'exécution reproductible |
| Gate | M1 | Revue des critères | L1.1, L1.2, L1.3 | Procès-verbal de qualification |
| Release | R1 | Candidat `v0.1.0a1` | M1 = GO | Wheel/sdist/tag selon procédure retenue |

---

## 5. Lot L1.1 - Model Domain

### 5.1 Objectif

Construire un modèle de domaine Python permettant de décrire le **modèle logique** et ses artefacts physiques indépendamment de tout fournisseur, runtime, deployment ou endpoint.

### 5.2 Objets et nature DDD

| Objet | Nature attendue | Responsabilité principale |
|---|---|---|
| `ModelId` | Identifier / Value Object | Identité logique canonique, stable, non vide |
| `ModelIdentity` | Value Object | Développeur, famille, génération, variant, spécialisation selon données connues |
| `ModelFamily` | Value Object canonique / Descriptor au MVP | Lignée d'un ensemble de modèles |
| `ModelVersion` | Value Object | Version/génération, sans obligation SemVer |
| `ModelVariant` | Value Object | Variante de taille, tier ou spécialisation |
| `ModelRevision` | Value Object | Révision/checkpoint distincte de version |
| `ModelArchitecture` | Value Object optionnel | Architecture connue ; inconnue admise |
| `ModelLimits` | Value Object optionnel | Context window, max output, etc. lorsqu'ils sont connus |
| `ModelArtifactId` | Identifier | Identité propre de l'artefact |
| `ModelArtifact` | Entity | Format physique, quantization, source, checksum, revision si connus |
| `ProviderModelRef` | Value Object optionnel | Alias provider-specific **distinct de `ModelId`** |
| `Model` | **Entity / Aggregate Root** | Identité stable, composition des descriptors et invariants |

Classification fondée sur `05_PYLLMKIT_ENTITIES_AND_VALUE_OBJECTS.md`. Les attributs détaillés et formes concrètes restent sujets aux ADR et à la revue d'API.

### 5.3 Relations canoniques

```text
Model (ModelId)
  ├── 1 ModelIdentity
  ├── 1 ModelFamily (valeur / référence canonique)
  ├── 0..1 ModelArchitecture
  ├── 0..1 ModelLimits
  ├── 0..* ProviderModelRef
  └── 0..* ModelArtifact (par ModelId ou ownership décidé)

Model 1 ─── 0..* Deployment  [RELATION CONCEPTUELLE FUTURE, non implémentée en P1]
Deployment 1 ─── 0..* Endpoint [HORS P1]
```

**Attention** : ne jamais représenter `Model → ModelArtifact → Deployment` comme une chaîne obligatoire.

### 5.4 Backlog détaillé L1.1

| ID | Tâche | Critère d'acceptation local | Preuve |
|---|---|---|---|
| P1-L11-T01 | Définir `ModelId` et `ModelArtifactId` typés | Valeurs non vides ; types non confondus | Tests identité / validation |
| P1-L11-T02 | Implémenter `ModelFamily`, `ModelVersion`, `ModelVariant`, `ModelRevision` | Variants indépendants, version non SemVer acceptée | Tests value objects |
| P1-L11-T03 | Implémenter `ModelIdentity` | Les champs sont cohérents ; pas de nom de provider imposé | Tests égalité + valeurs optionnelles |
| P1-L11-T04 | Implémenter `ModelArchitecture`, `ModelLimits` | Absence admise ; limites connues valides | Tests inconnus / limites |
| P1-L11-T05 | Implémenter `Model` comme entité | Égalité par `ModelId`, objets descriptifs bien composés | Tests agrégat |
| P1-L11-T06 | Implémenter `ModelArtifact` / rattachement au modèle | Deux artefacts différents pour un `ModelId` ; modèle sans artefact valide | Tests association |
| P1-L11-T07 | Ajouter `ProviderModelRef` descriptif si confirmé par ADR | Alias distinct de l'identité logique | Test anti-confusion |
| P1-L11-T08 | Définir erreurs et invariants du sous-domaine | Entrées impossibles rejetées sans appels réseau | Tests négatifs |
| P1-L11-T09 | Introduire sérialisation initiale versionnable | Round-trip fiable avec ID, version, artefacts et champs inconnus | Tests round-trip |
| P1-L11-T10 | Documenter l'API et exemples du modèle | Exemple `Model` autonome, sans SDK | `docs/concepts/model.md`, exemple |

### 5.5 Critères de sortie L1.1

- [ ] Construire plusieurs modèles d'une même famille avec versions/variants distincts.
- [ ] Créer un `Model` sans `ModelArtifact`, sans provider et sans deployment.
- [ ] Associer au moins deux `ModelArtifact` distincts au même `ModelId`.
- [ ] `ModelId` et `ModelArtifactId` possèdent leur identité propre.
- [ ] L'égalité d'un `Model` est identity-based ; les Value Objects sont value-based.
- [ ] Un `ModelVersion("2026-10")` est valide si la convention d'ID est respectée.
- [ ] Aucun champ inconnu ne devient une valeur d'architecture ou de limite inventée.
- [ ] Validations, documentation et sérialisation testées hors réseau.

---

## 6. Lot L1.2 - Capabilities & Modalities

### 6.1 Objectif

Rendre explicite **ce que sait faire le modèle** (*capability*) et **quels types d'entrée/sortie il accepte ou produit** (*modality*).

Ces dimensions doivent être représentées et interrogées indépendamment d'un SDK ; leur niveau de support doit être nuancé et leurs contraintes conservées.

### 6.2 Objets et contrats

| Objet | Nature attendue | Contrat initial |
|---|---|---|
| `CapabilityId` | Identifiant symbolique extensible | `chat`, `tool_calling`, `vision`, `structured_output`, etc. |
| `Capability` | Descriptor / Value Object | Caractéristique métier, sans identité d'Entity lourde |
| `SupportLevel` | Enum / type symbolique (ADR) | `UNSUPPORTED`, `EMULATED`, `PARTIAL`, `NATIVE` |
| `CapabilitySupport` | Value Object | Niveau, contraintes, notes facultatives |
| `CapabilityConstraint` | Value Object | Restrictions déclarées, p. ex. nombre de tools |
| `CapabilitySet` | Domain Collection | Représentation explicite et interrogation du support |
| `Modality` | Descriptor extensible | `text`, `image`, `audio`, `video`, `document` |
| `ModalitySet` | Domain Collection | Modalités d'entrée distinctes des sorties |

**Sémantique `UNKNOWN`** : les documents indiquent qu'une information inconnue ne doit jamais être présumée native ou non supportée. Le choix technique (état distinct, résultat de consultation, absence typée, etc.) doit être fixé par ADR-03 avant de figer l'API. Ne pas confondre `UNKNOWN` et les quatre niveaux de support attestés.

### 6.3 Backlog détaillé L1.2

| ID | Tâche | Critère d'acceptation local | Preuve |
|---|---|---|---|
| P1-L12-T01 | Créer `CapabilityId`, `Capability` | Taxonomie extensible, pas d'Enum figée pour toutes les capacités | Test d'extension |
| P1-L12-T02 | Créer `SupportLevel`, `CapabilitySupport` | Niveaux explicites ; sémantique d'inconnu documentée | Tests états |
| P1-L12-T03 | Créer `CapabilityConstraint` | Contraintes valides, explicites et comparables | Tests contraintes |
| P1-L12-T04 | Créer `CapabilitySet` | Support, recherche, union/intersection/différence **selon sémantique ADR** | Tests collections |
| P1-L12-T05 | Créer `Modality` et `ModalitySet` | Entrée/sortie séparées ; taxonomie extensible | Tests d'entrée/sortie |
| P1-L12-T06 | Composer `CapabilitySet`/`ModalitySet` dans `Model` | Un modèle connaît ses déclarations intrinsèques | Tests composition |
| P1-L12-T07 | Validation du support partiel / émulé / inconnu | Aucun `UNKNOWN` silencieusement converti en `NATIVE` | Tests négatifs |
| P1-L12-T08 | Documenter distinctions Capability/Modality | Cas `IMAGE` vs `VISION` expliqué | Guide + exemple |
| P1-L12-T09 | Préparer le futur contrat d'effective capability (sans serving) | Pas de dépendance à Deployment/Provider/Endpoint en P1 | Note de design + architecture test |

### 6.4 Comportements attendus

```text
Model
├── capability : chat         → NATIVE  (déclaration connue)
├── capability : tool_calling → PARTIAL (avec contraintes documentées)
├── capability : vision       → UNKNOWN (information insuffisante)
├── input_modalities         → {text, image}
└── output_modalities        → {text}
```

**Cet exemple est fictif et purement pédagogique.** Il n'attribue aucune capability réelle à un modèle existant.

À retenir :

- `image` décrit un **format/nature d'entrée ou de sortie** ; `vision` décrit une **fonctionnalité**.
- Une déclaration intrinsèque ne garantit **pas** le support effectif d'un deployment ou endpoint futur.
- Les contraintes spécifiques doivent rester interprétables et ne pas être effacées lors d'opérations de collection.
- La fusion restrictive des capabilities effectives à quatre niveaux reste une étape d'intégration ultérieure.

### 6.5 Critères de sortie L1.2

- [ ] Les capabilities sont extensibles au-delà des identifiants initiaux.
- [ ] Le niveau de support et les contraintes sont représentables sans booléen simpliste.
- [ ] L'absence d'information ne donne pas un support implicite.
- [ ] Deux `ModalitySet` distincts peuvent représenter entrées et sorties sans confusion.
- [ ] Un `Model` peut composer `CapabilitySet` et `ModalitySet`.
- [ ] Les opérations de collection annoncées sont déterministes et testées.
- [ ] La résolution effective multi-couches n'est pas présentée comme déjà implémentée.

---

## 7. Lot L1.3 - Quality & Testing

### 7.1 Objectif

Garantir que les primitives des lots 1.1 et 1.2 respectent leurs contrats, restent provider-agnostic et sont utilisables comme bibliothèque pédagogique Python.

**Ce lot est transversal** : ses tests accompagnent chaque objet dès son introduction.

### 7.2 Backlog détaillé L1.3

| ID | Tâche | Critère d'acceptation local | Preuve |
|---|---|---|---|
| P1-L13-T01 | Initialiser `pyproject.toml`, `src/` et `tests/` | Installation locale minimale possible | Installation dans venv vierge |
| P1-L13-T02 | Configurer `pytest` et fixtures de domaine | Tests purs, rapides et hors réseau | Rapport pytest |
| P1-L13-T03 | Ajouter contrôle format/lint/type-check | Code et API typés ; aucun problème bloquant | Rapports outils |
| P1-L13-T04 | Tester equality, identifiants, valeur vs entité | Matrice identity/value passée | Tests DDD |
| P1-L13-T05 | Tester invariants `MODEL-*`, `CAP-*`, `MOD-*` | Invalides rejetés, inconnus préservés | Parametrized / property tests |
| P1-L13-T06 | Tester sérialisation / désérialisation | Round-trip et données optionnelles maîtrisées | Tests serialization |
| P1-L13-T07 | Ajouter fitness tests d'architecture | Aucun import SDK/HTTP/env/secrets depuis domain | Détection imports interdits |
| P1-L13-T08 | Ajouter vérification isolation réseau | Suite du core réussit sans réseau | CI / suite offline |
| P1-L13-T09 | Produire documentation conceptuelle et références API | Concepts DDD et exemples reproductibles | docs + README |
| P1-L13-T10 | Préparer CI et build du package | Wheel + sdist installables et importables | Artefacts local build |
| P1-L13-T11 | Préparer note de version, matrice de traçabilité | Aucun critère MVP hors P1 annoncé comme terminé | Rapport M1 + release notes |

### 7.3 Matrice de tests de Phase 1

| Référence | Scénario | Type | Résultat attendu |
|---|---|---|---|
| TEST-M01 | `ModelId` vide | Unitaire négatif | ValidationError / erreur de domaine décidée |
| TEST-M02 | `ModelId` distinct de `ModelArtifactId` | Unitaire | Identités non interchangeables |
| TEST-M03 | Deux `Model` avec même ID | Unitaire | Identiques au sens Entity |
| TEST-M04 | Deux `ModelIdentity` égaux par contenu | Unitaire | Égaux au sens Value Object |
| TEST-M05 | Famille avec plusieurs versions et variantes | Unitaire | Cas valide |
| TEST-M06 | Version non SemVer | Unitaire | Acceptée |
| TEST-M07 | Architecture non renseignée | Unitaire | Valeur inconnue / absente préservée |
| TEST-M08 | Modèle sans artefact | Unitaire | Cas valide |
| TEST-M09 | Deux artefacts pour un modèle | Unitaire | Références correctes |
| TEST-M10 | Limite négative | Unitaire négatif | Rejet de valeur invalide |
| TEST-C01 | Capability inconnue/non déclarée | Unitaire | Jamais assimilée à NATIVE |
| TEST-C02 | Support natif vs partiel vs émulé | Unitaire | États correctement distingués |
| TEST-C03 | Contraintes sur support partiel | Unitaire | Contraintes conservées |
| TEST-C04 | Collection capabilities extensible | Unitaire | Nouvel ID possible |
| TEST-C05 | Opérations sur CapabilitySet | Propriété / unitaire | Règles sémantiques respectées |
| TEST-MOD01 | Input modalities ≠ output modalities | Unitaire | Orientation conservée |
| TEST-MOD02 | IMAGE ≠ VISION | Unitaire | Aucune confusion de concept |
| TEST-S01 | Sérialiser/désérialiser objets publics | Intégrité | Round-trip valide |
| TEST-A01 | `import pyllmkit.domain` sans SDK | Architecture | Import réussi |
| TEST-A02 | Interdire imports providers/HTTP dans domain | Architecture | Aucun import interdit |
| TEST-A03 | Tests sans réseau/credentials | Isolation | Suite réussie hors ligne |
| TEST-P01 | Installer wheel/sdist | Packaging | Installation/import réussis |

Pour tous les tests négatifs, le type d'erreur exact sera figé par ADR/API contract : l'exemple ci-dessus ne présume pas que la classe finale porte littéralement le nom `ValidationError`.

### 7.4 Outillage recommandé (proposition, non constat de l'existant)

- Tests : `pytest`, éventuellement `pytest-cov` et tests de propriétés (`hypothesis`) si justifiés.
- Qualité : `ruff` ; typage : `mypy` **ou** `pyright`, décision de repo.
- Packaging : backend PEP 517, build via `python -m build`.
- Dépendances runtime : **standard library autant que possible** ; aucune dépendance obligatoire à `openai`, `anthropic`, `google-genai`, `ollama`, `litellm`, `langchain`, `httpx` pour le core.
- CI : installation dans un environnement propre, lint, typing, unit tests, architecture tests, build, smoke import.

Commandes indicatives **après mise en place des outils** :

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m ruff check .
python -m mypy src/pyllmkit
python -m build
python -c "from pyllmkit.domain import Model, ModelIdentity, ModelFamily; print('domain import ok')"
```

La commande `pip install -e '.[dev]'` suppose un extra `dev` explicitement défini dans le `pyproject.toml`. Les chemins d'import publics seront ajustés à l'API retenue ; ce bloc est une **cible**, pas une preuve d'existence actuelle.

### 7.5 Qualité exigée pour M1

- **Obligatoire** : tests des invariants critiques et critères AC ciblés réussis (aucune exception sur ces scénarios).
- **Obligatoire** : zéro échec dans la suite des tests de domaine qualifiant M1.
- **Obligatoire** : imports provider interdits détectables automatiquement.
- **Obligatoire** : typage/lint sur le périmètre de la release sans échec bloquant.
- **Obligatoire** : construction et installation locales du wheel et du sdist.
- **Option de gouvernance à valider** : cible de couverture de branches sur `pyllmkit.domain` (une valeur éventuelle sera définie par l'équipe ; les documents fondateurs n'imposent pas de pourcentage précis).

---

## 8. Architecture de packages proposée pour `v0.1.0a1`

Cette arborescence est une **proposition de bootstrap**, compatible avec les bounded contexts et la topologie logique de `03`. Elle ne préjuge pas du contenu actuel du dépôt.

```text
pyllmkit/
├── pyproject.toml
├── README.md
├── ROADMAP.md
├── LICENSE
├── CHANGELOG.md
├── src/
│   └── pyllmkit/
│       ├── __init__.py
│       └── domain/
│           ├── __init__.py
│           ├── models/
│           │   ├── __init__.py
│           │   ├── identifiers.py
│           │   ├── identity.py
│           │   ├── descriptors.py
│           │   ├── artifact.py
│           │   └── model.py
│           ├── capabilities/
│           │   ├── __init__.py
│           │   ├── identifiers.py
│           │   ├── descriptors.py
│           │   ├── support.py
│           │   └── collection.py
│           ├── modalities/
│           │   ├── __init__.py
│           │   └── collection.py
│           └── errors/
│               ├── __init__.py
│               └── base.py
├── tests/
│   ├── unit/
│   │   ├── domain/models/
│   │   ├── domain/capabilities/
│   │   └── domain/modalities/
│   ├── architecture/
│   ├── serialization/
│   └── packaging/
├── docs/
│   ├── concepts/
│   │   ├── model.md
│   │   ├── artifact.md
│   │   ├── capabilities.md
│   │   └── modalities.md
│   ├── architecture/
│   │   └── phase-1-boundaries.md
│   └── adr/
├── examples/
│   ├── 01_define_model.py
│   ├── 02_define_artifacts.py
│   └── 03_describe_capabilities.py
└── .github/workflows/
    └── ci.yml
```

**Pas de `providers/`, `registry/`, `inference/`, `streaming/` opérationnels imposés dans cette première release.** Ils seront créés lorsque leurs contrats et use cases seront effectivement nécessaires. Si l'équipe choisit de prévoir certains packages vides, ils ne doivent pas être annoncés comme implémentés.

### 8.1 Règle de dépendances

```text
pyllmkit.domain.models ───────┐
                              ├──> value objects / domain primitives
pyllmkit.domain.capabilities ─┤
pyllmkit.domain.modalities ───┘

AUCUN : domain -> providers / HTTP / credentials / facade
```

Le module `Model` peut **composer** `CapabilitySet` et `ModalitySet`, mais ces deux sous-domaines ne doivent pas dépendre d'une entité `Model`. Les imports circulaires sont interdits ; le bootstrap doit favoriser l'absence de dépendances intermodules inutiles.

### 8.2 Principes et patterns pédagogiques exploités

| Principe / pattern | Application réelle dans P1 | Anti-pattern évité |
|---|---|---|
| DDD - Ubiquitous Language | Noms `Model`, `ModelArtifact`, `Capability`, `Modality` | `dict[str, Any]` sans sémantique |
| DDD - Entity / Aggregate Root | `Model` identifié par `ModelId` | Comparaison de `Model` uniquement par tous les champs |
| DDD - Value Object | `ModelIdentity`, `ModelVersion`, `ModelLimits` | Mutations incontrôlées |
| DDD - Domain Collection | `CapabilitySet`, `ModalitySet` | `list` dénuée de règles |
| Single Responsibility (SOLID) | Identité, artefact, capability et modality séparés | Classe `Model` monolithique |
| Dependency Inversion | Core indépendant des fournisseurs (ports viendront après) | Core basé sur schémas SDK |
| KISS / YAGNI | Pas de runtime, resolver ou registry avant le besoin | Infrastructure prématurée |
| Explicit over Implicit | `UNKNOWN` et contraintes explicites | Valeurs par défaut trompeuses |

---

## 9. Traçabilité des exigences et critères MVP

Les critères `AC-*` sont ceux du document `01`. **Le M1 ne prétend pas satisfaire l'ensemble du MVP.**

| Critère source | Périmètre M1 | Lot | Preuve requise |
|---|---|---|---|
| `AC-001` - Créer un modèle sans SDK | **À satisfaire** | L1.1 / L1.3 | Import + instance en environnement propre |
| `AC-002` - Plusieurs variants d'une famille | **À satisfaire** | L1.1 | Tests variants/famille |
| `AC-004` - Décrire les modalités | **À satisfaire** | L1.2 | Input/output modalities tests |
| `AC-005` - Décrire les capabilities | **À satisfaire** | L1.2 | CapabilitySet/support tests |
| `AC-018` - Tests domaine hors réseau | **À satisfaire pour le périmètre P1** | L1.3 | Suite hors ligne |
| `AC-003` - Plusieurs deployments | **Hors M1** | Futur | Pas de test affirmant son support complet |
| `AC-006` à `AC-017` (hors `AC-018`) | **Hors M1 sauf contribution structurelle** | Futur | Suivi dans ROADMAP.md |

Exigences fonctionnelles particulièrement concernées : `FR-001` à `FR-004`, `FR-006` à `FR-010`, et principes de qualité `NFR-001` à `NFR-005`, `NFR-008`, `NFR-011` (au niveau du scope P1). Ne pas interpréter ce tableau comme la validation globale de toutes les exigences concernées.

---

## 10. Jalons internes et Gate M1

### 10.1 Points de contrôle

| Gate | Événement | Condition vérifiable |
|---|---|---|
| G0 - Architecture Ready | Décisions P1 nécessaires adoptées | ADR minimales, package contract, anti-dépendances |
| G1 - Model Domain Ready | L1.1 qualifié | Tous critères §5.5 + tests associés |
| G2 - Capability & Modality Ready | L1.2 qualifié | Tous critères §6.5 + tests associés |
| G3 - Quality Ready | L1.3 qualifié | Tests, docs, build, import clean |
| **M1 - Foundations Qualified** | **G0 + G1 + G2 + G3 acceptés** | **AC ciblés satisfaits ; aucune anomalie bloquante** |

### 10.2 Definition of Done du jalon M1

- [ ] Lot **L1.1** livré et qualifié.
- [ ] Lot **L1.2** livré et qualifié.
- [ ] Lot **L1.3** livré et qualifié.
- [ ] Toutes les primitives annoncées dans le scope `0.1.0a1` de `ROADMAP.md` sont soit implémentées et testées, soit explicitement retirées par ADR + mise à jour de roadmap **avant** le GO.
- [ ] Invariants `Model != Provider`, `Model != Deployment`, `Model != ModelArtifact`, `Capability != Modality` vérifiés.
- [ ] AC-001, AC-002, AC-004, AC-005 et AC-018 (pour P1) vérifiés avec preuves.
- [ ] Aucun SDK provider, aucun appel réseau, aucun secret requis pour importer et tester `pyllmkit.domain`.
- [ ] Package typé, linté, documenté ; exemples reproductibles.
- [ ] Sérialisation conforme au contrat initial, round-trip validé.
- [ ] Wheel/sdist construits et installés dans un environnement propre.
- [ ] Rapport de qualification lié à un commit exact (SHA), aux commandes exécutées et à leurs résultats.
- [ ] Décision de gate formelle : **GO** / **NO-GO** avec réserves explicites.

### 10.3 Format de procès-verbal

```text
M1 - Domain Foundations Qualified
Date : À renseigner
Commit SHA : À renseigner
Lots : L1.1 [statut] / L1.2 [statut] / L1.3 [statut]
ADRs approuvées : À renseigner
Tests domain : ... passed / ... failed
Architecture checks : PASS / FAIL
Typing & lint : PASS / FAIL
Offline import / tests : PASS / FAIL
Build wheel/sdist : PASS / FAIL
Installation clean : PASS / FAIL
AC-001 / AC-002 / AC-004 / AC-005 / AC-018(P1) : PASS / FAIL
Anomalies bloquantes : À renseigner
Décision : GO / NO-GO
Responsable(s) validation : À renseigner
```

---

## 11. Qualification et publication de `v0.1.0a1`

### 11.1 Précision terminologique

L'expression « release candidate `v0.1.0a1` » désigne ici **un artefact alpha candidat à publication**. Au sens PEP 440, `0.1.0a1` est une **préversion alpha**, et non un suffixe formel `rc` (release candidate). On conserve le nom souhaité pour le jalon, sans confondre son statut qualité avec la syntaxe du numéro de version.

### 11.2 Procédure de release proposée

1. Réaliser une revue de version et geler le périmètre à publier.
2. Fixer la version Python du package à `0.1.0a1` dans le mécanisme retenu (une seule source de vérité).
3. Exécuter la CI complète contre le **commit exact** destiné à la release.
4. Construire wheel + sdist ; tester leurs installations respectives dans un environnement propre.
5. Vérifier métadonnées du package, README, licence, exports publics, changelog et notes de version.
6. Produire un rapport de qualification M1 et une décision GO/NO-GO.
7. **En cas de GO seulement**, préparer le tag `v0.1.0a1`, la release GitHub et la publication PyPI selon la politique du dépôt (par exemple Trusted Publishing si configuré).
8. Vérifier après publication que l'artefact publié correspond à l'artefact qualifié ; conserver les hashes et les liens de preuve.

**Important** : aucune release, publication PyPI, tag Git ou CI réussie n'est affirmée comme existante aujourd'hui.

### 11.3 Critères de refus / NO-GO

- Identifiants logiques confondus avec les alias d'un fournisseur.
- Modèle imposant artificiellement un artefact, un deployment ou un SDK.
- Capability inconnue présentée comme native, ou modality confondue avec capability.
- Value objects mutables sans justification ; égalité Entity non conforme.
- Tests du core dépendants du réseau, d'une clé API ou d'un provider.
- Build non installable ou API annoncée non importable.
- Aucun rapport reproductible permettant d'associer les résultats à un commit.

---

## 12. Risques et réponses

| Risque | Impact | Mesure de maîtrise |
|---|---|---|
| Surmodélisation (`Model` trop complexe) | Délai, API illisible | Core minimal, ADR, règle YAGNI |
| Copie des SDK providers | Couplage structurel | Interdiction imports + tests d'architecture |
| Artifacts liés de manière obligatoire à Deployment | Violation modèle de domaine | Tests `Model` sans artefact / déploiement |
| Taxonomies figées | Difficulté d'extension | Identifiants symboliques extensibles |
| `UNKNOWN` mal traité | Fausses annonces de capabilities | ADR-03 + tests inconnus |
| Immutabilité et collections incomplètes | États impossibles | Value objects frozen et encapsulation |
| Sérialisation tardive | Breaking changes inutiles | Round-trip dès L1.1 |
| Qualité ajoutée à la fin | Rework | L1.3 transversal dès BOOT |
| Publication prématurée | Version non qualifiée | Gate M1 obligatoire et artefact identifié |
| Scope creep (registry, inference, adapter) | Phase 1 sans fin | Backlog différé et interdictions explicites |

---

## 13. Backlog immédiat - ordre de démarrage

Le premier chantier concret est un **vertical slice indépendante** montrant identité de modèle + capacités + modalités + tests, sans provider.

- [ ] **Step 0** : analyser réellement le repo et ouvrir/valider les ADR nécessaires.
- [ ] **Step 1** : `pyproject.toml`, package `src/`, suite pytest minimale, commande d'import `pyllmkit.domain`.
- [ ] **Step 2** : implémenter `ModelId`, `ModelFamily`, `ModelVersion`, `ModelIdentity` avec tests de valeurs invalides.
- [ ] **Step 3** : implémenter `Model` et son égalité identity-based.
- [ ] **Step 4** : implémenter `ModelArtifact` et le cas `Model` sans artefact.
- [ ] **Step 5** : implémenter `CapabilityId`, `CapabilitySupport`, `CapabilitySet` et les contraintes.
- [ ] **Step 6** : implémenter `Modality` et `ModalitySet` (input/output).
- [ ] **Step 7** : composer le `Model` avec ses capability/modalities et tester les inconnus.
- [ ] **Step 8** : sérialisation, checks d'import et tests d'architecture.
- [ ] **Step 9** : compléter docstrings, exemples, README, CHANGELOG, CI et packaging.
- [ ] **Step 10** : tenir la revue de jalon **M1** et décider GO/NO-GO pour `v0.1.0a1`.

---

## 14. Livrables officiels de fin de Phase 1

| Référence | Livrable | Produit par |
|---|---|---|
| DEL-P1-01 | Package Python `pyllmkit.domain.models` | L1.1 |
| DEL-P1-02 | Package Python `pyllmkit.domain.capabilities` | L1.2 |
| DEL-P1-03 | Package Python `pyllmkit.domain.modalities` | L1.2 |
| DEL-P1-04 | Tests unitaires, invariants et architecture | L1.3 |
| DEL-P1-05 | Référence API, guides conceptuels et exemples | L1.1 + L1.2 + L1.3 |
| DEL-P1-06 | ADR validées et architecture de packages | BOOT + L1.3 |
| DEL-P1-07 | Build wheel/sdist et procédure d'installation | L1.3 |
| DEL-P1-08 | Rapport de qualification de jalon M1 | M1 |
| DEL-P1-09 | Candidat alpha `v0.1.0a1` (tag/release uniquement si GO et publication décidée) | R1 |

---

## 15. Références documentaires

- `00_PYLLMKIT_EXPRESSION_DU_BESOIN.md` - intention et frontière du framework.
- `01_PYLLMKIT_REQUIREMENTS_ANALYSIS.md` - exigences FR/NFR, MVP, `AC-001` à `AC-018`.
- `02_PYLLMKIT_PRODUCT_VISION_AND_ARCHITECTURE_PRINCIPLES.md` - Domain First, provider agnostic, invariants et séparation Model/Artifact.
- `03_PYLLMKIT_SYSTEM_ARCHITECTURE.md` - Domain Core et topologie de packages cible.
- `04_PYLLMKIT_DOMAIN_OBJECTS.md` - catalogue d'objets Model / Capability / Modality.
- `05_PYLLMKIT_ENTITIES_AND_VALUE_OBJECTS.md` - Entity, Aggregate Root, Value Objects, Identifiers et Domain Collections.
- `06_PYLLMKIT_DOMAIN_RELATIONSHIPS_AND_ERD.md` - cardinalités et relations Model/Artifact/Deployment.
- `07_PYLLMKIT_DOMAIN_INVARIANTS_AND_BUSINESS_RULES.md` - invariants MODEL/CAP/MOD et règles de données inconnues.
- `08_PYLLMKIT_COMMANDS_QUERIES_AND_USE_CASES.md` - use cases futurs, distinction orchestration applicative / domaines purs.
- `09_PYLLMKIT_DOMAIN_EVENTS_CATALOG.md` - limite entre faits métier et streaming, hors scope P1.
- `ROADMAP.md` - trajectoire des versions et critères de qualification.

> **Décision structurante** : Phase 1 est terminée lorsque **les concepts sont corrects, les invariants prouvés et le package installable**, et non lorsqu'un modèle distant peut déjà être invoqué. L'invocation viendra dans les releases suivantes.