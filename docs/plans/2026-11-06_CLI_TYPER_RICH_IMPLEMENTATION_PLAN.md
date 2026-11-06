# PyLLMKit - Plan d'implémentation : CLI Typer + Rich

> **Statut :** PLAN D'IMPLÉMENTATION DIRECTEUR (Jalon CLI / 0.3.1+)
>
> **Date de référence :** 6 novembre 2026.
>
> **Baseline GitHub qualifiée :** [`main@ce16398`](https://github.com/tawounfouet/pyllmkit/commit/ce16398) (Jalon 0.3.0 consolidé, 2 731 tests, 752 scénarios de conformité multi-fournisseurs, CI Python 3.11/3.12/3.13 verte).
>
> **Document d'analyse amont :** [`docs/analysis/2026-11-06_CLI_TYPER_RICH_ANALYSIS.md`](../analysis/2026-11-06_CLI_TYPER_RICH_ANALYSIS.md).
>
> **Autorité de décision :** Propriétaire du projet. Aucun code CLI n'est implémenté par ce document de cadrage.

---

## 0. Résumé exécutif et invariants de conception

Ce plan détaille la réalisation complète de la première interface utilisateur en ligne de commande (CLI) de PyLLMKit. 

La CLI agit comme un **Driving Adapter (adaptateur primaire d'entrée)**. Son unique responsabilité est de collecter les options de la ligne de commande, d'instancier les contrats de commande applicatifs (`InvokeCommand`, `ResolveDeploymentQuery`), d'appeler les cas d'usage éprouvés (`InferenceService`, `StreamingInferenceService`, `DeploymentResolver`), puis de projeter les résultats via des composants visuels Rich (tableaux, panneaux, flux en direct).

### Invariants stricts

1. **Étanchéité du cœur de domaine** :
   - `dependencies = []` demeure intact dans `pyproject.toml`.
   - Typer et Rich sont strictement optionnels et isolés dans `[project.optional-dependencies] cli = ["typer>=0.12", "rich>=13.7"]`.
   - Interdiction formelle d'importer `typer` ou `rich` dans `src/pyllmkit/domain/` et `src/pyllmkit/application/` (contrôlé par test AST dans `tests/architecture/`).
2. **Pas de logique métier dans la CLI (Thin Controller)** :
   - Toute validation de paramètres, sélection de modèles ou gestion d'état appartient au domaine et à l'application.
3. **Sécurité et Default-Deny** :
   - Aucun secret ni clé d'API en clair dans la console.
   - Le mode live exige un opt-in explicite (`--allow-live`), interdisant tout appel réseau imprévu.
4. **Gestion unifiée des erreurs** :
   - Interception globale des exceptions de domaine et projection dans des panneaux Rich exploitant la taxonomie d'erreurs normalisée du Jalon S3 (`authentication_failed`, `rate_limited`, `provider_timeout`, etc.).

---

## 1. Découpage par lots et chaîne de gates

| Lot | Désignation | Livrable principal | Gate associé |
|---|---|---|---|
| **CLI-L1** | Packaging & Skeleton | Extra `[cli]`, entrypoint console `pyllmkit`, console Rich partagée, aide `--help` | **CLI-G1 - Boot Ready** |
| **CLI-L2** | Catalogue & Inspection | Commandes `providers list/inspect`, `models list`, `deployments list`, `resolve` | **CLI-G2 - Inspection Ready** |
| **CLI-L3** | Inférence texte bloquante | Commande `pyllmkit run`, options de génération, rapport d'usage et d'erreurs | **CLI-G3 - Invocation Ready** |
| **CLI-L4** | Streaming interactif | Commande `pyllmkit stream`, affichage incrémental `rich.live.Live`, gestion `SIGINT` | **CLI-G4 - Streaming Ready** |
| **CLI-L5** | Outillage & Stockage local | Commande `tools validate`, stockage local SQLite `~/.config/pyllmkit/history.db` | **CLI-G5 - Tooling & Store Ready** |
| **CLI-L6** | Intégration & Recette | Matrice de 25 critères d'acceptation, documentation, exemples exécutables | **CLI-G6 - Final Qualification** |

---

## 2. Matrice des critères d'acceptation (CLI-AC-001 à CLI-AC-025)

| ID | Domaine | Description de l'exigence |
|---|---|---|
| **CLI-AC-001** | Packaging | `pip install pyllmkit[cli]` installe correctement Typer et Rich. |
| **CLI-AC-002** | Isolation | Un environnement sans `[cli]` peut importer `pyllmkit` sans erreur `ModuleNotFoundError`. |
| **CLI-AC-003** | Point d'entrée | La commande `pyllmkit --help` affiche la liste des sous-commandes disponibles. |
| **CLI-AC-004** | Version | `pyllmkit --version` affiche la version exacte du package sans importer de transport. |
| **CLI-AC-005** | Providers List | `pyllmkit providers list` affiche un tableau Rich des 6 fournisseurs supportés. |
| **CLI-AC-006** | Providers Inspect | `pyllmkit providers inspect <nom>` affiche les détails du fournisseur et masque les secrets. |
| **CLI-AC-007** | Models List | `pyllmkit models list` liste les modèles déclarés avec leurs capacités principales. |
| **CLI-AC-008** | Deployments List | `pyllmkit deployments list` liste les déploiements actifs et leurs fournisseurs associés. |
| **CLI-AC-009** | Resolve Déterministe | `pyllmkit resolve --model <id>` sélectionne le déploiement unique ou affiche les rejets. |
| **CLI-AC-010** | Resolve Ambigu | En cas de candidatures multiples, la CLI affiche l'erreur `AmbiguousDeploymentError`. |
| **CLI-AC-011** | Run Nominal | `pyllmkit run "texte"` exécute une inférence bloquante sur le modèle configuré. |
| **CLI-AC-012** | Run Usage | La sortie de `run` affiche un panneau Rich contenant `input_tokens`, `output_tokens` et la durée. |
| **CLI-AC-013** | Run Finish Reason | La raison d'arrêt native est affichée fidèlement selon le contrat canonique. |
| **CLI-AC-014** | Erreur Rate Limit | Une erreur 429 est affichée sous forme de panneau rouge `[rate_limited]` sans stacktrace. |
| **CLI-AC-015** | Erreur Auth | Une absence de clé d'API est signalée sous forme de panneau clair `[authentication_failed]`. |
| **CLI-AC-016** | Stream Nominal | `pyllmkit stream "texte"` affiche les deltas de texte au fur et à mesure de leur émission. |
| **CLI-AC-017** | Stream Cancellation | Une interruption clavier (`Ctrl+C`) déclenche `cancel()` propre sans socket orphelin. |
| **CLI-AC-018** | Stream Summary | À la clôture du flux, un récapitulatif compact est affiché sous le texte généré. |
| **CLI-AC-019** | Tools Validate | `pyllmkit tools validate schema.json` valide la conformité du schéma hors ligne. |
| **CLI-AC-020** | Tools Reject | Un schéma d'outil non conforme (ex: nom non ASCII) est rejeté avec un message explicite. |
| **CLI-AC-021** | Config Locale | La CLI charge la configuration par défaut depuis `~/.config/pyllmkit/config.json`. |
| **CLI-AC-022** | SQLite History | Chaque run exécuté via la CLI est consigné dans `~/.config/pyllmkit/history.db`. |
| **CLI-AC-023** | Runs List | `pyllmkit runs list` liste l'historique des invocations passées avec statut et durée. |
| **CLI-AC-024** | Architecture Guard | Aucun import interdit n'est présent dans `src/pyllmkit/adapters/cli/`. |
| **CLI-AC-025** | Non-régression | Les 2 731 tests existants continuent de passer à 100 % sur Python 3.11, 3.12 et 3.13. |

---

## 3. Détail des lots d'implémentation

### Lot CLI-L1 : Packaging & Squelette de base
- **Objectif** : Mettre en place l'infrastructure du sous-package CLI et son exposition console.
- **Modifications de fichiers** :
  - `pyproject.toml` : ajout de l'extra `cli` et de la directive `[project.scripts] pyllmkit = "pyllmkit.adapters.cli.main:app"`.
  - `src/pyllmkit/adapters/cli/__init__.py` : export du point d'entrée.
  - `src/pyllmkit/adapters/cli/main.py` : instance `typer.Typer(no_args_is_help=True)`, callback pour `--version`.
  - `src/pyllmkit/adapters/cli/console.py` : singleton `rich.console.Console` configuré pour stdout et stderr.
- **Tests associés** : `tests/cli/test_cli_boot.py` (vérification de `--help`, `--version` et comportement d'isolation).
- **Gate de validation** : **CLI-G1**.

---

### Lot CLI-L2 : Commandes d'inspection du catalogue
- **Objectif** : Permettre l'exploration visuelle des métadonnées du jalon M6 et des 6 adaptateurs P7.
- **Création de fichiers** :
  - `src/pyllmkit/adapters/cli/formatting/tables.py` : constructeurs de tableaux Rich pour modèles, déploiements et fournisseurs.
  - `src/pyllmkit/adapters/cli/formatting/reports.py` : mise en forme soignée du rapport `DeploymentResolutionReport`.
  - `src/pyllmkit/adapters/cli/commands/providers.py` : sous-commandes `list` et `inspect`.
  - `src/pyllmkit/adapters/cli/commands/models.py` : sous-commande `list`.
  - `src/pyllmkit/adapters/cli/commands/deployments.py` : sous-commande `list`.
  - `src/pyllmkit/adapters/cli/commands/resolve.py` : commande de simulation de résolution.
- **Tests associés** : `tests/cli/test_cli_catalog.py` (vérification des sorties tableaux et gestion des filtres).
- **Gate de validation** : **CLI-G2**.

---

### Lot CLI-L3 : Commande d'inférence texte bloquante (`run`)
- **Objectif** : Connecter la CLI à l'`InferenceService` pour exécuter une inférence ponctuelle.
- **Création de fichiers** :
  - `src/pyllmkit/adapters/cli/commands/run.py` : commande principale d'exécution.
  - `src/pyllmkit/adapters/cli/formatting/panels.py` : affichage du résultat sous forme de panneau textuel et statistiques d'usage.
  - `src/pyllmkit/adapters/cli/formatting/errors.py` : traducteur universel des exceptions du domaine en panneaux Rich d'erreur.
- **Flux d'exécution** :
  1. Parse l'invite et les options (`--model`, `--provider`, `--temperature`, `--timeout`).
  2. Construit l'`InferenceRequest` et appelle `inference_service.invoke()`.
  3. Affiche le texte retourné, la raison d'arrêt et le récapitulatif de tokens.
  4. En cas d'erreur (`InvocationPortError`, `NoCompatibleDeploymentError`), intercepte et affiche le panneau d'erreur idoine.
- **Tests associés** : `tests/cli/test_cli_run.py` (tests nominaux sur mocks locaux et tests négatifs d'erreurs d'API).
- **Gate de validation** : **CLI-G3**.

---

### Lot CLI-L4 : Commande de streaming interactif (`stream`)
- **Objectif** : Offrir une expérience console en direct fluide avec rendu incrémental.
- **Création de fichiers** :
  - `src/pyllmkit/adapters/cli/commands/stream.py` : commande de streaming.
  - `src/pyllmkit/adapters/cli/formatting/live_stream.py` : gestionnaire `rich.live.Live` captant les événements `TextDelta`.
- **Règles clés** :
  - Utilisation de `StreamingInferenceService.open_stream()`.
  - Gestion rigoureuse de `KeyboardInterrupt` (`SIGINT`) : appel explicite à `session.cancel()`, affichage d'un avertissement propre en console, puis sortie sans trace d'erreur.
- **Tests associés** : `tests/cli/test_cli_stream.py` (vérification de la séquence d'affichage et test d'interruption simulée).
- **Gate de validation** : **CLI-G4**.

---

### Lot CLI-L5 : Outillage & Persistance locale SQLite
- **Objectif** : Ajouter l'outil de validation de schémas et l'historisation locale sans dépendance externe.
- **Création de fichiers** :
  - `src/pyllmkit/adapters/cli/commands/tools.py` : sous-commande `tools validate <path>`.
  - `src/pyllmkit/adapters/cli/storage/sqlite_store.py` : adaptateur léger `SqliteRunStore` écrivant dans `~/.config/pyllmkit/history.db`.
  - `src/pyllmkit/adapters/cli/commands/runs.py` : sous-commandes `runs list` et `runs inspect <run_id>`.
- **Tests associés** : `tests/cli/test_cli_tools.py`, `tests/cli/test_cli_storage.py`.
- **Gate de validation** : **CLI-G5**.

---

### Lot CLI-L6 : Intégration globale, Documentation & Exemples
- **Objectif** : Consolidation, audit de qualité et packaging final.
- **Livrables** :
  - `examples/42_cli_programmatic_walkthrough.py` : démonstration de l'appel programmatique de la CLI via `CliRunner`.
  - `docs/api/cli-reference.md` : manuel d'utilisation de toutes les commandes et options.
  - `tests/quality/test_cli_boundaries.py` : test d'architecture statique (AST) vérifiant l'étanchéité des imports.
- **Gate de validation** : **CLI-G6 - Final Acceptance**.

---

## 4. Matrice des risques et conditions strictes de NO-GO

Toute survenance de l'une des conditions suivantes entraînera le refus immédiat du jalon :

1. **Régression des dépendances du cœur** : toute importation directe de `typer` ou `rich` dans `src/pyllmkit/domain/` ou `src/pyllmkit/application/`.
2. **Fuite de secret** : affichage en clair ou dans les logs d'une clé d'API résolue lors d'une commande d'inspection.
3. **Dégradation silencieuse** : interception d'une erreur d'inférence masquant le code d'erreur réel ou remplaçant silencieusement un fournisseur défaillant par un autre.
4. **Stacktrace non contrôlée** : crash non intercepté de la CLI avec affichage d'une trace Python brute face à une erreur réseau ou de domaine attendue.
5. **Régression de la suite existante** : échec de l'un des 2 731 tests du socle M1-0.3.0.
6. **Couverture de code insuffisante** : taux de couverture par branches inférieur à 95 % sur le sous-package `src/pyllmkit/adapters/cli/`.

---

## 5. Stratégie d'exécution des tests en CI

Les tests de la CLI seront exécutés avec le harnais standard `typer.testing.CliRunner` :
- Environnement hermétique sans accès réseau ni dépendance externe.
- Utilisation de fixtures et mocks des adaptateurs de fournisseurs (issus du jalon 0.3.0).
- Simulation des dimensions de terminal fixes pour garantir des assertions textuelles stables sous Rich.
- Validation multi-OS (Linux, macOS, Windows) sur les trois versions Python cibles (3.11, 3.12, 3.13).

