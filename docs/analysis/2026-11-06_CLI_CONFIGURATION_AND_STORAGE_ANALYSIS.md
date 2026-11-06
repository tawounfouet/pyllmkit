# PyLLMKit - Analyse d'ingénierie : Système de Configuration Hiérarchique et Persistance de Stockage

- Date de référence : 2026-11-06
- Statut : DOCUMENT D'ANALYSE ET D'INGÉNIERIE DÉCISIONNELLE
- Portée : Conception et mise en œuvre du moteur de configuration CLI, gestion des secrets, isolation des données de stockage et exports
- Contexte amont : Extension de la couche CLI Typer + Rich (ADR-049..059)
- Plan d'implémentation associé : [Plan d'implémentation Configuration & Stockage](../plans/2026-11-06_CLI_CONFIGURATION_AND_STORAGE_IMPLEMENTATION_PLAN.md)
- Guide pratique d'utilisation : [Guide de Configuration et de Stockage CLI](../guides/01_CLI_CONFIGURATION_AND_STORAGE_GUIDE.md)
- Fichiers source associés :
  - [`src/pyllmkit/adapters/cli/config.py`](../../src/pyllmkit/adapters/cli/config.py)
  - [`src/pyllmkit/adapters/cli/commands/config.py`](../../src/pyllmkit/adapters/cli/commands/config.py)
  - [`src/pyllmkit/adapters/cli/storage/sqlite_store.py`](../../src/pyllmkit/adapters/cli/storage/sqlite_store.py)
  - [`src/pyllmkit/adapters/cli/commands/runs.py`](../../src/pyllmkit/adapters/cli/commands/runs.py)

---

## 1. Contexte et Problématique Initiale

### Les limites du modèle "tout en ligne de commande"
Avant la mise en place de ce sous-système, l'utilisation de PyLLMKit en mode réel (`--live`) nécessitait une intervention manuelle répétitive et présentait plusieurs frictions majeures :

1. **Exports manuels répétés des variables d'environnement** :
   Pour chaque session terminal, l'opérateur devait déclarer ses clés d'API ligne par ligne :
   ```sh
   export OPENAI_API_KEY="sk-proj-..."
   export ANTHROPIC_API_KEY="sk-ant-..."
   export GEMINI_API_KEY="AIzaSy..."
   ```
   Ce modèle provoquait :
   - Une perte de temps à chaque ouverture de shell ou session tmux.
   - Un risque élevé d'exposition des secrets dans l'historique shell (`~/.zsh_history`, `~/.bash_history`).
   - Des erreurs fréquentes d'inattention (`authentication_failed`, clé oubliée ou tronquée).

2. **Répétition verbeuse des paramètres d'inférence** :
   À chaque appel, l'opérateur devait repréciser `--live`, `--model gpt-4o`, `--temperature 0.7`, sous peine de retomber sur le mode simulation hors ligne ou sur des paramètres non désirés.

3. **Absence d'isolation de la base de données d'historique** :
   Toutes les exécutions étaient enregistrées par défaut dans une base unique globale :
   `~/.config/pyllmkit/history.db`.
   Il était impossible d'isoler l'historique d'un projet client donné, d'un package ou d'une expérimentation R&D spécifique sans définir manuellement la variable `PYLLMKIT_HISTORY_DB`.

4. **Gestion manuelle des exports de jeux de données pour le Fine-Tuning** :
   L'export des historiques pour l'entraînement (ChatML JSONL) nécessitait de spécifier un chemin de sortie explicite à chaque extraction, sans point d'atterrissage structuré dans le dépôt de travail.

---

## 2. Contraintes d'Ingénierie Non Négociables

La conception de la solution a dû respecter rigoureusement les invariants architecturaux de PyLLMKit :

| Contrainte | Exigence architecturale | Solution retenue |
|---|---|---|
| **Zéro dépendance obligatoire** | `pyproject.toml` doit conserver `dependencies = []`. Interdiction formelle d'ajouter `python-dotenv`, `pydantic-settings` ou `dynaconf`. | Utilisation exclusive de `json` et `tomllib` (standard library Python >= 3.11). Parseur YAML léger intégré pour supporter le YAML sans dépendance externe. |
| **Sécurité des secrets (Zero-Leakage)** | Aucune clé secrète ne doit être affichée en clair dans la console ni commitée dans Git. | Masquage systématique des secrets (`mask_secret()`) et injection automatique de `.pyllmkit*` dans le fichier `.gitignore` local. |
| **Modèle hiérarchique (Local > Global)** | Inspiration directe du modèle Git (`.git/config` local surchargeant `~/.gitconfig` global). | Cascade hiérarchique avec découverte ascendante et fusion déterministe des clés. |
| **Résolution contextuelle des chemins** | Les chemins relatifs dans un fichier local (ex: `.pyllmkit/history.db`) ne doivent pas dépendre du répertoire de lancement de la commande (CWD). | Résolution absolue relative au répertoire parent du fichier de configuration découvert (`cfg_file.parent`). |

---

## 3. Architecture Décisionnelle : Le Modèle en Cascade

Pour résoudre simultanément la centralisation des secrets et l'isolation des données par projet, PyLLMKit introduit un mécanisme de **cascade à 4 niveaux** :

```
┌────────────────────────────────────────────────────────────────────────┐
│ NIVEAU 1 : Flag explicite en ligne de commande (--config / -c)         │
│ -> Autorité absolue. Écrase toute autre source.                        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ NIVEAU 2 : Variable d'environnement (PYLLMKIT_CONFIG)                  │
│ -> Utilisé pour les environnements de conteneurs, CI/CD ou tests.       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ NIVEAU 3 : Configuration Locale au Projet (.pyllmkit.yaml)             │
│ -> Découvert en remontant l'arborescence jusqu'à la racine Git.        │
│ -> Prioritaire sur la configuration globale.                           │
│ -> Isole la base SQLite (.pyllmkit/history.db) et les exports locaux.  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ NIVEAU 4 : Configuration Globale Machine (~/.config/pyllmkit/config.yml)│
│ -> Fallback pour les clés d'API et préférences par défaut de l'usager.│
└────────────────────────────────────────────────────────────────────────┘
```

### Règles de fusion (Merger)
Lorsqu'un fichier local et un fichier global coexistent :
1. **Clés d'API** : Les clés déclarées localement surchargent celles du fichier global. Les clés non redéfinies localement sont **héritées** du fichier global.
2. **Chemins de stockage** : Si le fichier local définit `history_db` ou `export_dir`, ils supplantent les valeurs globales.
3. **Paramètres d'inférence** : Les valeurs locales de `model`, `live`, `temperature`, `max_tokens` et `system_prompt` prennent le pas sur les valeurs globales.

---

## 4. Détail des Composants Techniques Implémentés

### A. Le modèle de données [`CliConfig`](../../src/pyllmkit/adapters/cli/config.py)
Découpé en trois blocs logiques immuables :
- `api_keys: dict[str, str]` : Mapping des clés normalisées (`openai`, `anthropic`, `google`, `mistral`, `xai`).
- `storage: StorageConfig` : Contient `history_db` et `export_dir`.
- `defaults: DefaultsConfig` : Modèle par défaut, activation du mode live, température, tokens, prompt système.

### B. Le parseur YAML léger sans dépendance
Pour éviter d'imposer l'installation de `PyYAML` tout en offrant la syntaxe YAML plébiscitée par les opérateurs, PyLLMKit intègre une stratégie à deux étages :
1. Si `PyYAML` est installé dans l'environnement, `yaml.safe_load()` est utilisé.
2. Si `PyYAML` est absent, la fonction interne `_parse_simple_yaml()` analyse la structure hiérarchique à 2 niveaux (clés racines et sous-sections indentées), convertit automatiquement les booléens (`true`/`false`) et les nombres (`int`/`float`), et charge la configuration sans aucune erreur.

### C. Injection automatique au démarrage Typer
Le point d'entrée principal [`src/pyllmkit/adapters/cli/main.py`](../../src/pyllmkit/adapters/cli/main.py) exécute `load_and_apply_config()` dans son callback racine `@app.callback()`.
Avant même que la commande cible (`run`, `stream`, `runs`) ne s'exécute :
- Les clés d'API résolues sont injectées dans `os.environ` si elles n'y sont pas déjà présentes.
- La variable `PYLLMKIT_HISTORY_DB` est synchronisée avec le chemin configuré.
- L'instance singleton `_ACTIVE_CONFIG` est mise à disposition des commandes.

### D. Liaison directe avec la couche de stockage SQLite
Le composant [`SqliteRunStore`](../../src/pyllmkit/adapters/cli/storage/sqlite_store.py) interroge directement `get_config().storage.history_db` avant de recourir au fallback historique. Toutes les inférences d'un projet atterrissent ainsi directement dans `.pyllmkit/history.db`.

---

## 5. Synthèse des Commandes Opérateur

### Initialisation
- **Global** : `pyllmkit config init --format yaml`
  Crée `~/.config/pyllmkit/config.yaml` pour centraliser les clés d'API de la machine.
- **Local** : `pyllmkit config init --local --format yaml`
  Crée `.pyllmkit.yaml` dans le repo courant et protège automatiquement le fichier en ajoutant `.pyllmkit*`, `.pyllmkit/` et `*.db` dans `.gitignore`.

### Inspection & Diagnostic
- `pyllmkit config show` :
  Affiche les fichiers actifs (local prioritaire + global fallback), la source de chaque clé (avec masquage partiel), et les chemins de stockage résolus de manière lisible et non tronquée.
- `pyllmkit config path` :
  Affiche le chemin absolu des fichiers de configuration identifiés.

### Exploitation et Fine-Tuning
- `pyllmkit run "Mon invite"` :
  Exécute l'inférence en exploitant directement le modèle et le mode live configurés.
- `pyllmkit runs export` :
  Exporte automatiquement l'historique du projet au format ChatML JSONL directement dans le dossier configuré (`./exports`).

---

## 6. Bénéfices Métier et Techniques Validés

1. **Expérience Développeur (DX)** : Suppression intégrale de la friction liée aux `export` manuels de variables d'environnement.
2. **Isolation Hermétique des Données** : Chaque sous-projet ou package gère sa propre base de données SQLite et ses propres datasets sans risque de collision.
3. **Sécurité Renforcée** : Les clés restent centralisées au niveau machine, évitant la duplication de secrets dans les repos Git.
4. **Conformité des Tests** : L'environnement de test automatisé isole hermétiquement `PYLLMKIT_CONFIG`, garantissant que les tests unitaires et de conformité restent strictement offline et déterministes (2781 tests passants avec 100% de succès).

