# PyLLMKit - P1-BOOT - Bootstrap & Architecture Decisions

> **Phase 1 - Fondations du framework**  
> **Unité** : `P1-BOOT`  
> **Précède** : `P1-L11 - Model Domain`, `P1-L12 - Capabilities & Modalities`, `P1-L13 - Quality & Testing`  
> **Jalon final de la phase** : `M1 - Domain Foundations Qualified`  
> **Version alpha cible** : `0.1.0a1` (PEP 440)

| Métadonnée | Valeur |
|---|---|
| Projet | PyLLMKit |
| Document | `P1_BOOT_PYLLMKIT_BOOTSTRAP_AND_ARCHITECTURE_DECISIONS.md` |
| Nature | Plan d'exécution + registre de décisions + procédure de vérification |
| Statut | **Bootstrap proposé en pull request ; validation de la CI et ADR en attente** |
| Référentiel | `ROADMAP.md`, `01_PYLLMKIT_PHASE_1_IMPLEMENTATION_PLAN.md`, sources `00` à `09` |
| Langage | Python >= 3.11 |
| Architecture | Domain-First ; Ports & Adapters ; Provider-Agnostic |
| Hors périmètre | Inference réelle, SDK providers, réseau, registry opérationnel, tool execution |

---

## 1. Objet et décisions d'entrée

`P1-BOOT` transforme les principes documentaires de PyLLMKit en un **environnement de développement contrôlable** avant l'implémentation des premières Entities et Value Objects. L'objectif n'est **pas** de certifier la Phase 1 : les lots `L1.1`, `L1.2` et `L1.3` restent à réaliser.

Le bootstrap doit livrer :

1. un état des lieux objectif du dépôt **avant toute mutation** ;
2. un ensemble de décisions d'architecture explicites (ADR) ;
3. une arborescence Python `src/` construisible ;
4. des garde-fous de dépendances ;
5. une configuration initiale de tests, lint, typing, CI et packaging ;
6. une preuve locale de la qualité du **squelette uniquement** ;
7. une frontière nette entre ce qui est créé, proposé, validé, qualifié et publié.

### 1.1 Ce qui vient des spécifications et ce qui relève de choix proposés

| Sujet | Exigence du référentiel | Choix de bootstrap proposé |
|---|---|---|
| Core indépendant des SDK | `00`, `02`, `03`, `07` | Zéro dépendance runtime P1, code du domaine sous `src/pyllmkit/domain/` |
| Identité du Model | `04`, `05`, `07` | `ModelId` Value Object typé immutable |
| Artifact distinct du Model | `04`, `06`, `07` | `ModelArtifact.model_id` référence logique par `ModelId` |
| Modality distincte de Capability | `04`, `07` | Packages spécialisés sans dépendance inverse à `Model` |
| UNKNOWN jamais inventé | `02`, `07` | Absence de déclaration explicite et absence de vérité par défaut |
| Python moderne et typé | `01` | Python >=3.11, mypy strict, Ruff, pytest |
| Séparation façade/domain/adapters | `02`, `03` | `domain/` seul au bootstrap ; ports/adapters reportés |
| Versions alphabétiques | `ROADMAP.md` | Métadonnée `0.1.0a1` en cible technique, pas statut de release |

**Important** : les choix de la colonne droite et les ADR associées sont proposés ; ils ne remplacent pas une décision de gouvernance du dépôt.

---

## 2. Scope et anti-scope

### Inclus

- `pyproject.toml` conforme au packaging Python moderne (backend setuptools/PEP 517).
- Package `src/pyllmkit/` et zones `domain/models`, `domain/capabilities`, `domain/modalities`, `domain/errors`.
- Error base `PyLLMKitError`, sans anticiper les erreurs détaillées du futur Model Domain.
- `py.typed`, `README.md`, `CHANGELOG.md`, `.gitignore`.
- Tests de smoke imports et guard AST contre les dépendances interdites.
- Fichiers ADR-001 à ADR-005 au statut `PROPOSED`.
- Workflow GitHub Actions de référence : Python 3.11, 3.12, 3.13 ; lint, type, tests, build, smoke install.
- Réalisation d'un build wheel et sdist en environnement local lorsque l'outillage est disponible.

### Exclus

- Implémentations réelles de `Model`, `ModelIdentity`, `ModelFamily`, `ModelVersion`, `ModelArtifact` et autres classes du lot L1.1.
- Implémentations réelles de `Capability`, `CapabilitySet`, `Modality`, `ModalitySet` et autres classes du lot L1.2.
- `InferenceRequest`, `InferenceRun`, `InferenceResponse`, streaming, registry opérationnel, adapters providers.
- Appels réseau, credentials, secrets, API externes.
- Publication PyPI, création de tag, migration non revue du dépôt utilisateur.
- Attribution arbitraire de licence open source.

**Invariant d'architecture** : `Model != ModelArtifact != Deployment != Endpoint` ne doit pas être interprété comme une chaîne de composition. En particulier, `Model` peut exister sans Artifact, Deployment ou Endpoint.

---

## 3. Audit préalable du dépôt réel (non réalisé dans cet environnement)

Le squelette fourni ne prouve pas l'état du repository GitHub. Dès que le dépôt réel est disponible, exécuter les commandes de lecture ci-dessous **sans altérer son contenu** :

```bash
git remote -v
git status --short --branch
git branch -a
git tag --list
git log -5 --date=iso --oneline
find . -maxdepth 3 -type f | sort | head -150
find .github -maxdepth 3 -type f 2>/dev/null || true
python --version
```

Consigner :

- URL canonique du dépôt et branche de référence ;
- dernier commit exact, état du working tree, fichiers potentiellement en conflit ;
- licence, contraintes Python, `pyproject.toml`, build backend et dépendances existantes ;
- suites de tests et workflows existants ;
- tags, releases et décision éventuelle sur la version initiale ;
- présence d'autres documents `10` à `22` non fournis dans le corpus de référence de cet audit.

Si un projet Python existe déjà, **ne pas écraser** `pyproject.toml`, CI, README ou arborescence sans revue de différentiel. Le squelette local doit être traité comme *proposition à fusionner*.

### Gate BOOT-0 - Repository Baseline

- [ ] URL et branche du dépôt vérifiées.
- [ ] SHA de référence relevé.
- [ ] État existant des tests/CI/releases vérifié.
- [ ] Éventuels conflits avec le squelette listés.
- [ ] Décisions relatives à la licence et au package index documentées.

---

## 4. Décisions architecturales (ADR)

Les ADR constituent des **propositions documentées**. Leur statut doit passer à `ACCEPTED` seulement après une revue explicite dans le dépôt.

### ADR-001 - Typed IDs

**Décision proposée** : `ModelId` et `ModelArtifactId` sont des Value Objects distincts, immuables et non vides ; une chaîne littérale n'est pas un substitut sûr au-delà de l'API de parsing.

- Support Python proposé : `@dataclass(frozen=True, slots=True)`.
- Égalité : par valeur, avec distinction de type.
- Le format canonique de l'identifiant ne doit pas imposer un `provider` ni SemVer.
- Test : ID vide interdit, ID différent de nature non interchangeable, round-trip.

**Source** : `05` (Identifier), `07` (`MODEL-001`, `MODEL-003`).

### ADR-002 - Entity identity and immutable VOs

**Décision proposée** : les Value Objects (`ModelIdentity`, `ModelVersion`, `ModelLimits`, etc.) sont immuables par défaut ; `Model` et `ModelArtifact` sont des Entities dont l'égalité relève de leur identifiant.

- `Model` doit pouvoir évoluer sans changer d'identité logique.
- Mutation contrôlée par opérations métier ou remplacement de snapshot ; pas de champs publics librement mutables sans invariants.
- Ne pas introduire un `__hash__` incompatible avec une Entity mutable.
- Test : même ModelId, metadata différentes = même identité d'Entity ; VOs comparables par valeur.

**Source** : `05` (Entities & Value Objects), `07` (invariants).

### ADR-003 - UNKNOWN and capabilities

**Décision proposée** : les quatre niveaux explicitement déclarés restent `UNSUPPORTED`, `EMULATED`, `PARTIAL`, `NATIVE`. L'état `UNKNOWN` exprime une **absence de connaissance** et n'est jamais converti implicitement en support natif ou en absence de support.

- Implémentation envisagée : `None` ou type de résultat de consultation explicite (à figer lors de L1.2).
- Les contraintes d'un support `PARTIAL` sont conservées.
- Aucune comparaison par simple booléen ne doit faire perdre l'information.
- Tests : `UNKNOWN != NATIVE`, `UNKNOWN != UNSUPPORTED`, `EMULATED != NATIVE`.

**Source** : `02`, `07` (`CAP-*`).

### ADR-004 - Model/Artifact association & serialization

**Décision proposée** : un `ModelArtifact` référence un `ModelId` ; le modèle logique ne possède pas nécessairement d'artefact public.

- `ModelArtifact` possède son propre ID, son format et ses attributs physiques.
- Plusieurs artefacts peuvent référencer un même `ModelId`.
- `Deployment` et `Endpoint` sont **reportés** ; ne pas importer leur logique dans P1.
- Sérialisation future : schéma JSON explicite et versionné, et non `obj.__dict__` implicite.
- Tests : modèle sans artefact valide ; deux artefacts associés ; round-trip avec champs optionnels inconnus.

**Source** : `06` (ERD), `07` (`INV-004`, `MODEL-008`, `MODEL-009`).

### ADR-005 - Dependency Rule, packages and API

**Décision proposée** : projet `src/` ; standard library suffisante pour le core ; paquet principal `pyllmkit`, modules spécialisés `domain.models`, `domain.capabilities`, `domain.modalities`, `domain.errors` ; interfaces publiques réexportées seulement après qualification des objets.

- Aucun import de provider SDK, client HTTP, environnement ou adaptateur dans `domain`.
- Pas de dépendance `capabilities -> Model` ou `modalities -> Model` ; l'inverse par composition est permis.
- Tooling développement facultatif dans `[dev]` ; Python >=3.11.
- Tests de règles d'import et installabilité sans SDK.

**Source** : `02` (Dependency Rule), `03` (package topology), plan de Phase 1.

| ADR | Statut actuel | Livrable | Validation requise |
|---|---|---|---|
| ADR-001 | PROPOSED | `docs/adr/ADR-001-typed-identifiers.md` | Revue API + IDs |
| ADR-002 | PROPOSED | `docs/adr/ADR-002-identity-and-immutability.md` | Revue DDD + égalité |
| ADR-003 | PROPOSED | `docs/adr/ADR-003-unknown-capability-semantics.md` | Revue cas UNKNOWN |
| ADR-004 | PROPOSED | `docs/adr/ADR-004-model-artifact-and-serialization.md` | Revue ERD + codec |
| ADR-005 | PROPOSED | `docs/adr/ADR-005-dependencies-and-api.md` | Revue import graph |

### Gate BOOT-1 - Architecture Decision Ready

- [ ] Toutes les ADR passent de `PROPOSED` à `ACCEPTED`, ou possèdent un arbitrage temporaire responsable et daté.
- [ ] Les critères de rejet d'import et les frontières d'agrégats sont compris.
- [ ] Aucun SDK fournisseur ne dicte un objet du domaine.
- [ ] Les tests d'acceptation L1.1 / L1.2 sont alignés sur les décisions retenues.

---

## 5. Architecture cible du bootstrap

### 5.1 Dépendances du code (sens des flèches : **imports autorisés**)

```text
src/pyllmkit/domain/models/ --------> domain/capabilities/
             |                      \
             +-----------------------> domain/modalities/
             |
             +-----------------------> domain/errors/

domain/capabilities/ ----------------> domain/errors/
domain/modalities/ ------------------> domain/errors/

INTERDIT : domain -> application / facade / providers / infrastructure
INTERDIT : domain -> OpenAI / Anthropic / HTTP client / credentials
INTERDIT : capabilities ou modalities -> models (dépendance inverse)
```

La représentation ci-dessus concerne le **bootstrap et les prochains objets de P1**. Les ports, façades, services applicatifs et adapters seront ajoutés lorsque leurs vrais use cases seront développés. Ce n'est pas l'intégralité de l'architecture future du framework.

### 5.2 Architecture hexagonale future (ne pas implémenter dans BOOT)

```text
Applications
  -> Facade
     -> Application Services
        -> Domain Objects and Domain Services
        -> Ports / Protocols <--- Provider Adapters ---> External APIs / Runtimes
```

La flèche de gauche représente ici un **chemin d'invocation**, tandis que les adapters **implémentent** des ports et les importent depuis l'extérieur du cœur. Les diagrammes d'import et d'invocation doivent être maintenus séparément.

### 5.3 Fichiers du squelette livré

```text
PyLLMKit_P1_BOOT_scaffold/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── ROADMAP.md
├── .gitignore
├── .github/workflows/ci.yml
├── src/pyllmkit/
│   ├── __init__.py
│   ├── py.typed
│   └── domain/
│       ├── __init__.py
│       ├── models/__init__.py
│       ├── capabilities/__init__.py
│       ├── modalities/__init__.py
│       └── errors/{__init__.py,base.py}
├── tests/
│   ├── architecture/{guard.py,test_dependency_rules.py}
│   ├── packaging/test_import_smoke.py
│   ├── unit/domain/{models,capabilities,modalities}/
│   └── serialization/
├── docs/
│   ├── architecture/dependencies.md
│   ├── adr/ADR-001 ... ADR-005
│   ├── concepts/README.md
│   └── 01_PYLLMKIT_PHASE_1_IMPLEMENTATION_PLAN.md
└── examples/
```

**Remarque** : les `__init__.py` du domaine sont essentiellement des packages vides ; leur présence ne prouve pas que les objets métier existent.

### 5.4 Paramètres Python adoptés provisoirement

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pyllmkit"
version = "0.1.0a1"
requires-python = ">=3.11"
dependencies = []
```

- Le nom `pyllmkit` est **cible de projet**, pas une vérification de disponibilité d'index.
- `0.1.0a1` est la version cible du package local, **pas** une release qualifiée ou publiée.
- Une seule source de version, dans `pyproject.toml`; `__version__` la lit depuis les métadonnées du package installé.
- Licence : **non décidée** ; publication publique bloquée jusqu'à décision.

---

## 6. Backlog exécutable P1-BOOT

| Ticket | Intention | Actions concrètes | Preuve de sortie |
|---|---|---|---|
| P1-BOOT-T01 | Baseline du dépôt | Inventorier branches, SHA, fichier de build, CI, licence | `docs/audits/repository-baseline.md` complété |
| P1-BOOT-T02 | Contrats de P1 | Confronter `ROADMAP`, `00-09`, Phase 1 | Matrice des frontières P1 validée |
| P1-BOOT-T03 | ADR-001 | Typed IDs | ADR relue + tests futurs définis |
| P1-BOOT-T04 | ADR-002 | Entities et VOs | ADR relue + règles d'égalité définies |
| P1-BOOT-T05 | ADR-003 | UNKNOWN et SupportLevel | ADR relue + absence explicite définie |
| P1-BOOT-T06 | ADR-004 | Model/Artifact et sérialisation | ADR relue + relations séparées |
| P1-BOOT-T07 | ADR-005 | Dépendances et API | ADR relue + graphe d'imports validé |
| P1-BOOT-T08 | Bootstrap packaging | `pyproject.toml`, `src/`, `py.typed`, doc minimale | Installation locale réussie |
| P1-BOOT-T09 | Guardrails qualité | `pytest`, `ruff`, `mypy`, tests imports AST | Suite initiale verte |
| P1-BOOT-T10 | CI | Actions matrix 3.11-3.13 et build | Workflow fusionné et exécuté en distant |
| P1-BOOT-T11 | Reproducible builds | Wheel, sdist, installation sur environnement isolé | Logs de build + smoke import |
| P1-BOOT-T12 | Gate de qualification BOOT | Statut ADR, tests, SHA, écarts | Décision GO / NO-GO vers L1.1 |

**Traçabilité** : `P1-BOOT-T08` à `T11` peuvent être vérifiés partiellement sur le squelette local ; `T01`, `T10` (CI distante) et `T12` restent à confirmer après intégration réelle.

---

## 7. Commandes de bootstrap et qualification

### 7.1 Mise en route (sur un dossier séparé et revu)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest -q
python -m ruff check .
python -m mypy src/pyllmkit
python -m build
```

`python3.11` peut être remplacé par `python3.12` ou `python3.13` selon l'environnement.

### 7.2 Smoke checks

```bash
python -c "import pyllmkit; import pyllmkit.domain; print(pyllmkit.__version__)"
python -c "import pyllmkit.domain.models, pyllmkit.domain.capabilities, pyllmkit.domain.modalities"
python -m pytest tests/architecture tests/packaging -q
```

Le smoke check ne doit pas importer `Model` tant que L1.1 ne l'a pas créé : ce serait un faux signal d'échec du bootstrap.

### 7.3 Tests d'architecture requis

- Recherche AST des imports directs connus de SDK, HTTP, infrastructure et façade dans `domain`.
- Tests négatifs vérifiant que le gardien détecte effectivement un import interdit.
- Extension prévue : contrôler explicitement les imports relatifs traversant les frontières de packages ; le garde AST seul ne remplace pas une revue du graphe d'imports.
- Le test statique n'est **pas** un sandbox de sécurité ou une preuve absolue d'absence d'import dynamique.

### 7.4 CI proposée

```text
push/pull_request
 -> checkout
 -> Python 3.11/3.12/3.13
 -> pip install -e .[dev]
 -> ruff check
 -> mypy strict
 -> pytest
 -> build wheel + sdist
 -> install wheel + smoke import
```

Le workflow CI est présent dans le squelette mais sa bonne exécution sur GitHub ne peut pas être certifiée ici.

### 7.5 Baseline mesurée dans le squelette local

| Contrôle | Résultat observé | Portée |
|---|---|---|
| Version locale d'exécution | Python 3.13.5 | Environnement local uniquement |
| `pip install --no-build-isolation --no-deps -e .` | Succès | Installation editable du squelette |
| `pytest -q` | **4 passed** | Smoke imports et tests de garde AST |
| `compileall` | Succès | Compilation syntaxique des modules |
| `pip wheel --no-deps --no-build-isolation` | Succès | Wheel local créé |
| `setuptools.build_meta.build_sdist` | Succès | Sdist local créé |
| `ruff check` / `mypy` | **Non exécutés** (non installés localement) | Contrôles à réaliser en CI/environnement dev |
| GitHub Actions | **Non exécuté** | Aucun statut CI distant connu |
| Tests métiers L1.1/L1.2 | **Non exécutés / non applicables au bootstrap** | Objets métier non implémentés |
| Publication PyPI / Git tag | **Non effectuée** | Version alpha non publiée |

Ces observations démontrent la reproductibilité **partielle** du bootstrap et ne doivent pas être présentées comme la réussite de M1.

---

## 8. Definition of Done - P1-BOOT

### Gating qualitatif

- [ ] `G-BOOT-01` - État réel du dépôt consigné avec SHA exact.
- [ ] `G-BOOT-02` - Diff éventuel avec la structure préexistante vérifié.
- [ ] `G-BOOT-03` - ADR-001 à ADR-005 acceptées ou arbitrages temporaires tracés.
- [x] `G-BOOT-04` - Squelette Python local construit avec packages ciblés.
- [x] `G-BOOT-05` - Packaging editable et import smoke démontrés localement.
- [x] `G-BOOT-06` - Tests de frontière initiaux présents et verts localement.
- [x] `G-BOOT-07` - Wheel et sdist générés localement.
- [ ] `G-BOOT-08` - Ruff et mypy validés sur le squelette intégré.
- [ ] `G-BOOT-09` - GitHub Actions vertes sur le commit exact de référence.
- [ ] `G-BOOT-10` - Licence et conditions de publication décidées.
- [ ] `G-BOOT-11` - Revue GO/NO-GO enregistrée dans le dépôt.

**Décision actuelle : `NOT QUALIFIED` pour P1-BOOT sur le dépôt réel.** On dispose d'un **prototype de bootstrap local vérifié partiellement**, pas d'un commit intégralement revu et qualifié.

### Critère de passage vers `P1-L11`

`P1-L11` peut commencer dès que les **ADR nécessaires à ModelId, Model et ModelArtifact** sont approuvées, que l'intégration au dépôt ne détruit rien d'existant et que les vérifications de base sont reproductibles. Les contrôles complets de P1-L13 se poursuivront en transversal.

---

## 9. Risques et parades

| Risque | Impact | Parade |
|---|---|---|
| Écrasement d'un repo existant | Régression et perte de travaux | Inventaire et diff avant intégration |
| ADR proposées prises pour acceptées | Implémentations divergentes | Statuts explicites + revue |
| `0.1.0a1` confondu avec une release publiée | Communication trompeuse | Séparer version metadata / build / tag / publication |
| Squelette vide présenté comme domaine implémenté | Faux avancement | README et tests limités au BOOT |
| IDs `str` interchangeables | Bugs de frontière | ADR-001 + typed identifiers |
| Model nécessite un Artifact | Invariant violé | ADR-004 + test sans artefact |
| UNKNOWN converti implicitement | Capabilities inventées | ADR-003 + tests négatifs |
| Imports SDK dans domain | Perte du provider-agnostic | Guard AST + revue imports et architecture |
| Fausses garanties du guard AST | Dépendances dynamiques non détectées | Revue, tests réseau, import graph, contrôles additionnels |
| Licence absente avant publication | Incertitude juridique | G-BOOT-10 explicite |

---

## 10. Handoff vers P1-L11, P1-L12 et P1-L13

### P1-L11 - Model Domain

Ordre recommandé : `ModelId` / `ModelArtifactId` -> `ModelFamily` / `ModelVersion` -> `ModelIdentity` -> `ModelLimits` / `ModelArchitecture` -> `Model` -> `ModelArtifact` -> sérialisation et tests.

Les signatures exactes doivent correspondre aux ADR acceptées ; les classes ne figurent **pas encore** dans le squelette de P1-BOOT.

### P1-L12 - Capabilities & Modalities

Implémenter séparément `CapabilityId`, `Capability`, `CapabilitySupport`, `CapabilitySet`, `Modality`, `ModalitySet`, puis les composer avec `Model`. Conserver l'absence d'information.

### P1-L13 - Quality & Testing

Étendre les tests du bootstrap vers les invariants DDD, les propriétés de collections, les round-trips de sérialisation, l'absence de SDK et l'installation des artefacts dans un environnement vierge.

### Préparation du jalon M1

M1 ne peut être qualifié que si **les lots 1.1, 1.2 et 1.3** sont réellement implémentés, intégrés, testés et vérifiables sur un commit donné. Le bootstrap seul n'y suffit pas.

---

## 11. Livrables

1. **Document maître** : `P1_BOOT_PYLLMKIT_BOOTSTRAP_AND_ARCHITECTURE_DECISIONS.md` (ce document).
2. **Archive source** : `PyLLMKit_P1_BOOT_scaffold.zip` (squelette, tests, CI, ADRs).
3. **Build local de démonstration** : wheel et sdist issus du squelette (aucune fonctionnalité métier de L1.1/L1.2).
4. **Prochain lot** : `P1-L11-T01 - ModelId / ModelArtifactId`, une fois les ADR pertinentes revues.

**Rappel final** : la fin de `P1-BOOT` se définit par la stabilisation des **choix, frontières et outils**, pas par le nombre de classes créées. Les fonctionnalités métier appartiennent aux lots suivants.