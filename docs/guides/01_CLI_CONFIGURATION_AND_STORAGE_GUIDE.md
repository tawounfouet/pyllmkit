# Guide de Configuration et de Stockage de la CLI PyLLMKit

Ce guide décrit le fonctionnement, la gestion et les meilleures pratiques pour configurer l'interface en ligne de commande (CLI) de [`PyLLMKit`](../../README.md), gérer la persistance de l'historique d'inférences, et exporter des jeux de données pour le Fine-Tuning. Pour l'analyse d'ingénierie et le plan d'implémentation associé, consultez également le [Document d'Analyse Système de Configuration](../analysis/2026-11-06_CLI_CONFIGURATION_AND_STORAGE_ANALYSIS.md) et le [Plan d'Implémentation Configuration & Stockage](../plans/2026-11-06_CLI_CONFIGURATION_AND_STORAGE_IMPLEMENTATION_PLAN.md).

---

## 1. Principes d'Architecture

La CLI PyLLMKit adopte les principes de conception suivants :
- **Zéro dépendance obligatoire** : Le moteur de configuration lit nativement le format JSON et TOML (intégré à Python >= 3.11). Le format YAML est pris en charge sans dépendance via un parseur interne, ou via `PyYAML` s'il est présent.
- **Sécurité et étanchéité Git** : Aucune clé secrète ni base de données locale ne doit être commitée dans le dépôt Git.
- **Cascade hiérarchique** : Vous pouvez centraliser vos clés d'API une seule fois au niveau de votre machine, tout en isolant vos données de stockage (base SQLite, exports) au niveau de chaque projet.

---

## 2. Hiérarchie de Découverte des Configurations

À chaque exécution de commande, PyLLMKit résout la configuration selon l'ordre de priorité suivant :

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Option explicite en ligne de commande : --config <fichier>          │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. Variable d'environnement globale : PYLLMKIT_CONFIG                  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. Configuration Locale du Projet : ./.pyllmkit.yaml (Prioritaire)     │
│    - Découverte dans le répertoire courant ou ses parents              │
│    - Base de données SQLite et exports isolés dans le projet           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. Configuration Globale de la Machine : ~/.config/pyllmkit/config.yaml│
│    - Fallback automatique pour les clés d'API et valeurs globales      │
└────────────────────────────────────────────────────────────────────────┘
```

### Mécanisme de Fusion (Cascade)
- Si un fichier local `.pyllmkit.yaml` existe, il a la **priorité**.
- Si une clé d'API ou un paramètre par défaut n'est pas redéfini dans le fichier local, PyLLMKit **hérite automatiquement** de la valeur définie dans le fichier global `~/.config/pyllmkit/config.yaml`.
- Les chemins relatifs configurés dans un fichier local (ex: `.pyllmkit/history.db`) sont résolus relativement au répertoire de ce fichier.

---

## 3. Initialisation Rapide (`pyllmkit config init`)

### A. Configuration globale pour toute la machine
À exécuter une seule fois pour enregistrer vos clés d'API générales :

```sh
pyllmkit config init --format yaml
```
- **Fichier créé** : `~/.config/pyllmkit/config.yaml`
- **Rôle** : Répertoire central de vos clés d'API (`openai`, `anthropic`, `gemini`, etc.) partagées par tous vos projets.

### B. Configuration locale pour un projet spécifique
À exécuter à la racine du dépôt de votre projet :

```sh
pyllmkit config init --local --format yaml

# Ou en version raccourcie :
pyllmkit config init -l -f yaml
```
- **Fichier créé** : `.pyllmkit.yaml` (à la racine de votre projet).
- **Protection Git automatique** : La commande ajoute automatiquement `.pyllmkit*`, `.pyllmkit/` et `*.db` dans le fichier `.gitignore` de votre projet.
- **Rôle** : Isoler l'historique SQLite (`.pyllmkit/history.db`) et les exports dans ce projet sans dupliquer vos clés d'API.

> **Note** : Si le fichier existe déjà, ajoutez le flag `--force` pour l'écraser.

---

## 4. Structure des Fichiers de Configuration

### Exemple YAML (`.pyllmkit.yaml` ou `~/.config/pyllmkit/config.yaml`)

```yaml
# 1. Clés d'API (injectées automatiquement dans os.environ)
api_keys:
  openai: "sk-proj-..."
  anthropic: "sk-ant-..."
  gemini: "AIzaSy..."
  mistral: "..."
  xai: "..."

# 2. Stockage de la base de données et des exports
storage:
  history_db: ".pyllmkit/history.db"   # Chemin relatif au projet ou absolu
  export_dir: "./exports"               # Dossier de destination des exports JSONL

# 3. Paramètres d'inférence par défaut
defaults:
  model: "gpt-4o"
  live: true                           # true = appels réels par défaut sans taper --live
  temperature: 0.7                     # Température de sampling par défaut
  max_tokens: 1500                     # Limite de tokens générés
  system_prompt: "Tu es un assistant IA expert et concis."
```

### Exemple JSON équivalent (`.pyllmkit.json` ou `config.json`)

```json
{
  "api_keys": {
    "openai": "sk-proj-...",
    "anthropic": "sk-ant-..."
  },
  "storage": {
    "history_db": ".pyllmkit/history.db",
    "export_dir": "./exports"
  },
  "defaults": {
    "model": "gpt-4o",
    "live": true,
    "temperature": 0.7,
    "max_tokens": 1500,
    "system_prompt": "Tu es un assistant IA expert et concis."
  }
}
```

---

## 5. Inspection et Diagnostic de la Configuration

### Afficher la configuration active avec `pyllmkit config show`

```sh
pyllmkit config show
```

Cette commande affiche un tableau détaillé en console :
- **Fichiers actifs** : Indique si un fichier local surcharge un fichier global.
- **Clés d'API & Fournisseurs** : Liste les clés configurées avec masquage de sécurité (ex: `sk-pro...cdef`) et leur source (`Local (projet)`, `Global (machine)`, ou `Environnement`).
- **Chemins de stockage** : Affiche les chemins absolus résolus de la base de données SQLite et du dossier d'export.
- **Valeurs par défaut** : Modèle cible, état du mode Live, température et prompt système.

### Afficher l'emplacement du fichier actif avec `pyllmkit config path`

```sh
pyllmkit config path
```
Exemple de sortie :
```
✓ Fichier local (prioritaire) : /Users/awf/workspace/professionnal/webtech/packages/pyllmkit/.pyllmkit.yaml
ℹ Fichier global (fallback)   : /Users/awf/.config/pyllmkit/config.yaml
```

---

## 6. Flux d'Exécution et Fine-Tuning

Une fois la configuration en place, toutes les commandes bénéficient automatiquement des paramètres définis.

### Inférence directe
Plus besoin de spécifier `--live` ni `--model` si configurés dans les valeurs par défaut :
```sh
# Exécution bloquante standard
pyllmkit run "Explique la méthode RAG en 2 phrases"

# Exécution en streaming temps réel
pyllmkit stream "Raconte un court haïku sur le vent d'automne"
```

### Consultation de l'historique local
Toutes les exécutions sont archivées silencieusement dans votre base SQLite locale (`.pyllmkit/history.db`) :
```sh
# Lister les 5 dernières exécutions
pyllmkit runs list -n 5

# Inspecter un run spécifique
pyllmkit runs inspect <run_id>

# Dump JSON brut complet (FinOps, métadonnées, tokens de raisonnement)
pyllmkit runs inspect <run_id> --json
```

### Export pour Fine-Tuning au format ChatML JSONL
Pour exporter directement votre historique au format officiel OpenAI / Hugging Face SFTTrainer :
```sh
# Export automatique dans le dossier configuré (ex: ./exports/export_20261106_203000.jsonl)
pyllmkit runs export

# Export vers un fichier spécifique
pyllmkit runs export --model gpt-4o --output dataset_finetuning.jsonl
```

Chaque ligne du fichier généré respecte strictement la spécification ChatML :
```json
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

---

## 7. Découverte et Synchronisation des Modèles (`pyllmkit models`)

PyLLMKit intègre un catalogue enrichi de plus de 30 modèles de référence (`gpt-4o`, `gpt-4o-mini`, `claude-3-5-sonnet`, `claude-3-5-haiku`, `gemini-1.5-pro`, `gemini-1.5-flash`, `mistral-large`, `deepseek-r1`, etc.).

### A. Consulter les modèles reconnus
```sh
# Lister tous les modèles du catalogue
pyllmkit models list

# Filtrer par famille de fournisseur (ex: openai, anthropic, google, mistral, meta, xai)
pyllmkit models list --family openai
```

### B. Synchroniser en direct le catalogue auprès de vos fournisseurs (`models sync`)
Pour interroger automatiquement les APIs des fournisseurs dont les clés sont configurées dans votre fichier `.pyllmkit.yaml` ou `~/.config/pyllmkit/config.yaml` et enregistrer tous les modèles accessibles :

```sh
# Synchroniser tous les fournisseurs configurés
pyllmkit models sync

# Synchroniser un fournisseur spécifique
pyllmkit models sync --provider openai

# Sauvegarder dans le cache local du projet (.pyllmkit/discovered_models.json)
pyllmkit models sync --local
```

Tous les modèles découverts sont immédiatement reconnus par `pyllmkit resolve`, `pyllmkit run` et `pyllmkit stream`.

---

## 8. Tableau Récapitulatif des Commandes

| Commande | Rôle |
|---|---|
| `pyllmkit config init` | Génère le fichier global dans `~/.config/pyllmkit/config.yaml` |
| `pyllmkit config init --local` | Génère le fichier local `.pyllmkit.yaml` et met à jour `.gitignore` |
| `pyllmkit config show` | Affiche la configuration active, les clés masquées et les chemins résolus |
| `pyllmkit config path` | Affiche le chemin absolu du fichier de configuration en vigueur |
| `pyllmkit models list` | Liste l'ensemble des modèles déclarés et reconnus dans le catalogue |
| `pyllmkit models sync` | Découvre et synchronise les modèles en direct via les APIs des fournisseurs |
| `pyllmkit resolve --model <id>` | Résout de manière déterministe le déploiement associé à un modèle cible |
| `pyllmkit run "<prompt>"` | Exécute une inférence en utilisant les clés et paramètres configurés |
| `pyllmkit stream "<prompt>"` | Exécute une inférence en streaming direct avec mesure TTFT |
| `pyllmkit runs list` | Affiche les dernières exécutions enregistrées dans la base SQLite |
| `pyllmkit runs inspect <id> --json` | Exporte toutes les métadonnées d'un run au format JSON brut |
| `pyllmkit runs export -o <file>` | Exporte les inférences au format ChatML JSONL pour le Fine-Tuning |

