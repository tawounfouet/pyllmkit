# Guide Complet et Exhaustif des Commandes de la CLI PyLLMKit

Ce guide de référence détaille l'ensemble des fonctionnalités, commandes, sous-commandes et options de l'interface en ligne de commande (CLI) de [`PyLLMKit`](../../README.md). Il s'adresse aux développeurs, architectes et ingénieurs de données souhaitant piloter, tester, observer et orchestrer des modèles de langage et modèles multimédias (texte, vision, audio, vidéo) de manière agnostique et déterministe.

Pour les guides thématiques spécialisés, consultez également :
- [Guide de Configuration et de Stockage](01_CLI_CONFIGURATION_AND_STORAGE_GUIDE.md) : cascade de configuration, clés d'API et base SQLite locale.
- [Guide de Génération d'Assets Multimédias](02_MEDIA_ASSET_GENERATION_GUIDE.md) : génération Text-to-Image, Text-to-Speech et Text-to-Video.

---

## Sommaire

1. [Principes de Conception de la CLI](#1-principes-de-conception-de-la-cli)
2. [Vue d'Ensemble des Commandes](#2-vue-densemble-des-commandes)
3. [Options Globales](#3-options-globales)
4. [Commande `run` : Inférence Bloquante](#4-commande-run--inférence-bloquante)
5. [Commande `stream` : Inférence en Flux Continu](#5-commande-stream--inférence-en-flux-continu)
6. [Commande `generate` : Génération Multimédia (Image, Audio, Vidéo)](#6-commande-generate--génération-multimédia-image-audio-vidéo)
7. [Commande `resolve` : Résolution Déterministe de Déploiement](#7-commande-resolve--résolution-déterministe-de-déploiement)
8. [Commande `models` : Exploration et Synchronisation du Catalogue](#8-commande-models--exploration-et-synchronisation-du-catalogue)
9. [Commande `providers` : Inspection des Fournisseurs](#9-commande-providers--inspection-des-fournisseurs)
10. [Commande `deployments` : Liaisons Opérationnelles](#10-commande-deployments--liaisons-opérationnelles)
11. [Commande `runs` : Historique, FinOps et Fine-Tuning](#11-commande-runs--historique-finops-et-fine-tuning)
12. [Commande `config` : Gestion de la Configuration](#12-commande-config--gestion-de-la-configuration)
13. [Commande `tools` : Validation des Schémas d'Outils](#13-commande-tools--validation-des-schémas-doutils)
14. [Sécurité, Confidentialité et Codes de Sortie](#14-sécurité-confidentialité-et-codes-de-sortie)
15. [Aide-Mémoire Rapide (Cheat Sheet)](#15-aide-mémoire-rapide-cheat-sheet)

---

## 1. Principes de Conception de la CLI

La CLI PyLLMKit est conçue selon des normes strictes issues du Domain-Driven Design (DDD) et de la clean architecture :

- **Zéro Dépendance Obligatoire d'Exécution** : La CLI repose sur les modules intégrés de Python 3.11+ et des bibliothèques d'interface standard (Typer et Rich). Aucune dépendance externe lourde ni SDK propriétaire (openai, anthropic, google-genai) n'est requis.
- **Sécurité et Mode Simulation (`--mock`) par Défaut** : Toute commande d'inférence s'exécute par défaut hors ligne sans consommer de quota ni exposer de token réseau. L'activation du réseau distant nécessite le drapeau explicite `--live`.
- **Confidentialité par Défaut (`--record-content`)** : Les métriques d'exécution (durée, tokens, modèle, coût estimé) sont toujours tracées dans la base locale SQLite, mais le contenu textuel des prompts et réponses n'est persisté que sur consentement explicite via l'option `--record-content`.
- **FinOps Local et Déterministe** : Calcul de coût calculé en temps réel selon les barèmes officiels vérifiés des fournisseurs, sans appel réseau de facturation.
- **Multimodalité Universelle Unifiée** : Prise en charge native des images, audios et vidéos aussi bien en entrée (questions multimodales) qu'en sortie (génération d'artifacts médias).

---

## 2. Vue d'Ensemble des Commandes

| Commande | Rôle Principal | Mode Par Défaut | Sortie Principale |
| :--- | :--- | :--- | :--- |
| `run` | Inférence textuelle et multimodale bloquante | Simulation (`--mock`) | Panneau réponse + Métriques d'usage |
| `stream` | Inférence en flux continu incrémental | Simulation (`--mock`) | Affichage temps réel + Statistiques flux |
| `generate` | Génération de médias (image, voix TTS, vidéo) | Simulation (`--mock`) | Média sauvegardé dans `assets/` + Fiche technique |
| `resolve` | Résolution de déploiement et compatibilité | Local (hors ligne) | Rapport de conformité matricielle |
| `models` | Liste, inspection technique et synchronisation catalogue | Local / Distant (`sync`) | Tableaux comparatifs et specs contextuelles |
| `providers` | Inspection des 6 fournisseurs certifiés | Local (hors ligne) | Règles de transport, runtimes et endpoints |
| `deployments` | Consultation des liaisons modèles-fournisseurs | Local (hors ligne) | Tableau des déploiements déclarés |
| `runs` | Audit FinOps, inspection, export JSONL, rétention | Base SQLite locale | Tableaux d'historique, métadonnées, exports |
| `config` | Visualisation et initialisation des fichiers de configuration | Fichiers locaux/globaux | Tableaux des clés masquées et chemins |
| `tools` | Validation syntaxique de schémas de fonctions (P4) | Local (hors ligne) | Diagnostic de conformité JSON Schema |

---

## 3. Options Globales

Ces options s'appliquent directement au binaire `pyllmkit` avant toute commande :

```bash
pyllmkit [OPTIONS] COMMAND [ARGS]...
```

### Options Disponibles

- `--version`, `-v` : Affiche le numéro de version de PyLLMKit et quitte immédiatement.
- `--config <chemin>`, `-c <chemin>` : Spécifie un fichier de configuration alternatif (`.yaml`, `.json`, `.toml`) prioritaire sur la cascade standard.
- `--help` : Affiche l'aide globale et la liste des commandes.

### Exemples

```bash
# Vérifier la version installée
pyllmkit --version

# Utiliser une configuration spécifique d'environnement de test
pyllmkit --config ./configs/production.yaml run "Bonjour" --live
```

---

## 4. Commande `run` : Inférence Bloquante

La commande `run` soumet une requête complète à un modèle de langage et attend la réponse intégrale avant d'afficher le résultat et son bilan FinOps.

### Syntaxe

```bash
pyllmkit run [OPTIONS] PROMPT
```

### Arguments et Options

| Option / Argument | Raccourci | Type | Défaut | Description |
| :--- | :--- | :--- | :--- | :--- |
| `PROMPT` | (positionnel) | `str` | *Requis* | Texte de la requête à soumettre au modèle. |
| `--model` | `-m` | `str` | `gpt-4o` | Modèle cible (ex: `claude-3-5-sonnet`, `gemini-2.0-flash`, `llama3.2`). |
| `--system` | `-s` | `str` | `None` | Instruction système préalable orientant le comportement du modèle. |
| `--temperature` | `-t` | `float` | `None` | Température d'échantillonnage (entre `0.0` et `2.0`). |
| `--max-tokens` | | `int` | `None` | Limite stricte du nombre de tokens générés en sortie. |
| `--mock / --live` | | `flag` | `--mock` | Exécution simulée hors ligne (`--mock`) ou appel réel via API (`--live`). |
| `--record-content` | | `flag` | `False` | Enregistrer le prompt et la réponse dans la base SQLite locale. |
| `--image` | `-i` | `str` (multiple) | `None` | Chemin de fichier local ou URL d'image(s) à attacher. |
| `--audio` | `-a` | `str` | `None` | Chemin de fichier local ou URL audio à attacher. |
| `--video` | `-v` | `str` | `None` | Chemin de fichier local ou URL vidéo à attacher. |
| `--output-file` | `-o` | `str` | `None` | Chemin où sauvegarder la réponse si le modèle produit un média. |

### Exemples d'Utilisation

#### A. Inférence Texte Simple (Mode Simulation)
```bash
pyllmkit run "Explique le théorème de Bayes en deux phrases" --model gpt-4o
```

Sortie console :
```text
╭──────────────────────────────────────── Réponse du modèle ────────────────────────────────────────╮
│ Le théorème de Bayes permet de calculer la probabilité conditionnelle d'un événement en combinant   │
│ des informations a priori et de nouvelles preuves observables.                                     │
╰────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭───────────────────────────────────── Statistiques d'exécution ─────────────────────────────────────╮
│ Run ID        : a1b2c3d4e5f67890123456789abcdef0                                                   │
│ Modèle        : gpt-4o                                                                             │
│ Fournisseur   : openai (simulation)                                                                │
│ Statut final  : completed                                                                          │
│ Durée         : 0.4 ms                                                                             │
│ Finish Reason : stop                                                                               │
│ Tokens In/Out : 22 / 34 (total: 56)                                                                │
│ Coût estimé   : $0.00040 ($0.00006 in + $0.00034 out)                                              │
╰────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

#### B. Inférence Réelle en Ligne (`--live`) avec Prompt Système
```bash
pyllmkit run "Rédige une fonction SQL de dédoublonnage" \
  --model claude-3-5-sonnet \
  --system "Tu es un expert PostgreSQL senior. Sois concis." \
  --temperature 0.2 \
  --live
```

#### C. Inférence Multimodale Vision (Analyse d'Image)
```bash
pyllmkit run "Décris les anomalies sur ce relevé technique" \
  --image ./data/diagramme.png \
  --model gemini-2.0-flash \
  --live
```

#### D. Sauvegarde avec Traçabilité du Contenu
```bash
pyllmkit run "Résume le contrat de maintenance" \
  --model mistral-large-2411 \
  --record-content \
  --live
```

---

## 5. Commande `stream` : Inférence en Flux Continu

La commande `stream` consomme les fragments de texte (tokens) dès leur émission par le modèle et les affiche progressivement sur le terminal, offrant une latence ressentie minimale (Time to First Token / TTFT).

### Syntaxe

```bash
pyllmkit stream [OPTIONS] PROMPT
```

### Options

La commande `stream` accepte les mêmes options que `run` :
- `--model`, `-m` : Identifiant du modèle cible.
- `--system`, `-s` : Prompt système.
- `--temperature`, `-t` : Température d'échantillonnage.
- `--max-tokens` : Limite de tokens générés.
- `--mock / --live` : Mode hors ligne ou appel réseau réel.
- `--record-content` : Consentement pour la persistance intégrale.
- `--image`, `-i`, `--audio`, `-a`, `--video`, `-v` : Pièces jointes multimédias.

### Exemple Pratique

```bash
pyllmkit stream "Raconte une citation courte sur la persévérance" \
  --model grok-4.20-0309-non-reasoning \
  --live
```

Sortie console :
```text
╭───────────────────────────── Réponse complète ─────────────────────────────╮
│ « Tombe sept fois, relève-toi huit. »                                       │
│ (Proverbe japonais)                                                         │
╰────────────────────────────────────────────────────────────────────────────╯
╭────────────────────── Statistiques de flux (Streaming) ────────────────────╮
│ Run ID        : 2157d49df063456b82d945f62e092ba1                           │
│ Modèle        : grok-4.20-0309-non-reasoning                               │
│ Fournisseur   : xai                                                        │
│ Statut final  : completed                                                  │
│ Durée         : 1460.0 ms (45.9 tok/s) (TTFT: 284.1 ms)                     │
│ Finish Reason : stop                                                       │
│ Tokens In/Out : 209 in / 67 out (total: 276)                               │
│ Coût estimé   : $0.00074 ($0.00042 in + $0.00032 out)                      │
╰────────────────────────────────────────────────────────────────────────────╯
```

---

## 6. Commande `generate` : Génération Multimédia (Image, Audio, Vidéo)

Le groupe de commandes `generate` permet de créer des artifacts multimédias autonomes (Text-to-Image, Text-to-Speech, Text-to-Video).

### Sous-Commandes Disponibles

1. `generate image` : Génération d'images haute définition.
2. `generate audio` : Synthèse vocale naturelle (Text-to-Speech).
3. `generate video` : Génération d'extraits vidéo à partir de descriptions.

---

### 6.1 `generate image`

#### Syntaxe

```bash
pyllmkit generate image [OPTIONS] PROMPT
```

#### Options Spécifiques

- `PROMPT` : Description textuelle de la scène ou du visuel souhaité.
- `--model`, `-m` : Modèle de diffusion (défaut : `dall-e-3`, alternatives : `dall-e-2`, `imagen-3`).
- `--out`, `-o` : Fichier de sortie. Si omis, le fichier est automatiquement enregistré dans `assets/images/<modele>_<horodatage>_<id>.png`.
- `--size` : Dimensions souhaitées (`1024x1024`, `1024x1792`, `1792x1024`).
- `--quality` : Niveau de finition (`standard` ou `hd`).
- `--mock / --live` : Simulation locale ou appel direct au fournisseur.

#### Exemples

```bash
# Mode simulation (génère un vrai PNG de test dans assets/images/)
pyllmkit generate image "Un chat astronaute explorant la planète Mars" --model dall-e-3

# Mode réel en direct via DALL-E 3
pyllmkit generate image "Logo vectoriel moderne pour une société d'IA" \
  --model dall-e-3 \
  --size 1024x1024 \
  --quality hd \
  --out ./exports/logo_ia.png \
  --live
```

---

### 6.2 `generate audio`

#### Syntaxe

```bash
pyllmkit generate audio [OPTIONS] PROMPT
```

#### Options Spécifiques

- `PROMPT` : Texte à vocaliser.
- `--model`, `-m` : Modèle TTS (défaut : `tts-1`, alternative : `tts-1-hd`).
- `--out`, `-o` : Fichier audio de destination (défaut : `assets/audios/<modele>_<horodatage>_<id>.wav` ou `.mp3`).
- `--voice` : Timbre de voix de synthèse (`alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`).
- `--mock / --live` : Simulation ou génération vocale réelle.

#### Exemples

```bash
# Synthèse vocale de simulation
pyllmkit generate audio "Bienvenue sur la plateforme de gestion des données" --model tts-1

# Synthèse vocale haute fidélité en direct
pyllmkit generate audio "Traitement du lot de données achevé avec succès." \
  --model tts-1-hd \
  --voice onyx \
  --out ./notifications/alert.mp3 \
  --live
```

---

### 6.3 `generate video`

#### Syntaxe

```bash
pyllmkit generate video [OPTIONS] PROMPT
```

#### Options Spécifiques

- `PROMPT` : Description cinématique de la séquence vidéo.
- `--model`, `-m` : Modèle de génération vidéo (défaut : `veo-2`).
- `--out`, `-o` : Chemin de la vidéo MP4 générée (défaut : `assets/videos/<modele>_<horodatage>_<id>.mp4`).
- `--mock / --live` : Simulation locale (conteneur H.264 valide) ou génération distante.

#### Exemple

```bash
pyllmkit generate video "Une vague turquoise s'écrasant sur du sable noir volcanique" \
  --model veo-2 \
  --out ./assets/videos/vague.mp4
```

---

## 7. Commande `resolve` : Résolution Déterministe de Déploiement

La commande `resolve` exécute l'algorithme de résolution de compatibilité matricielle. Elle détermine quel fournisseur, quel runtime et quel adaptateur seront utilisés pour un modèle cible donné, tout en validant les contraintes opérationnelles.

### Syntaxe

```bash
pyllmkit resolve --model <id_modele> [--provider <nom_fournisseur>]
```

### Options

- `--model`, `-m` : Identifiant ou alias du modèle (requis).
- `--provider`, `-p` : Filtrer optionnellement pour forcer un fournisseur spécifique.

### Exemple

```bash
pyllmkit resolve -m claude-3-5-sonnet -p anthropic
```

Sortie console :
```text
╭────────────────── Rapport de Résolution de Déploiement ──────────────────╮
│ Modèle cible          : claude-3-5-sonnet                                │
│ Statut de résolution  : SUCCÈS                                           │
│ Déploiement sélectionné: dep-anthropic-claude-3-5-sonnet                 │
│ Fournisseur résolu    : anthropic                                        │
│ Runtime certifié      : direct                                           │
│ Modalités supportées  : text (in/out), image (in)                        │
│ Outils supportés      : function_calling (native)                        │
│ Contexte maximal      : 200 000 tokens                                   │
╰──────────────────────────────────────────────────────────────────────────╯
```

---

## 8. Commande `models` : Exploration et Synchronisation du Catalogue

Ce groupe gère l'exploration, la tarification et la synchronisation du catalogue de modèles.

### 8.1 `models list`

Affiche les modèles déclarés dans le catalogue local.

```bash
# Lister tous les modèles
pyllmkit models list

# Filtrer par famille technologique
pyllmkit models list --family openai

# Afficher les tarifs et tailles de fenêtres de contexte
pyllmkit models list --pricing
```

Extrait du tableau avec `--pricing` :
```text
                                       Catalogue des modèles et tarifs                                        
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Modèle              ┃ Famille   ┃ Contexte     ┃ Max Sortie       ┃ Entrée /1M ┃ Sortie /1M ┃ Vérifié le   ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ gpt-4o              │ openai    │ 128 000 tok  │ 16 384 tok       │ $2.50      │ $10.00     │ 2026-11-07   │
│ claude-3-5-sonnet   │ anthropic │ 200 000 tok  │ 8 192 tok        │ $3.00      │ $15.00     │ 2026-11-07   │
│ gemini-2.0-flash    │ google    │ 1 048 576 tok│ 8 192 tok        │ $0.10      │ $0.40      │ 2026-11-07   │
│ dall-e-3            │ openai    │ -            │ 1 image          │ -          │ $0.0400/u  │ 2026-11-07   │
│ tts-1               │ openai    │ -            │ audio stream     │ -          │ $15.00/1Mch│ 2026-11-07   │
└─────────────────────┴───────────┴──────────────┴──────────────────┴────────────┴────────────┴──────────────┘
```

---

### 8.2 `models inspect`

Affiche la fiche d'ingénierie détaillée d'un modèle : limites de tokens, modalités, tarifs et provenance du barème.

```bash
pyllmkit models inspect gpt-4o
```

---

### 8.3 `models sync`

Interroge les points de terminaison officiels des fournisseurs configurés pour découvrir dynamiquement les nouveaux modèles mis à disposition sur votre compte.

```bash
# Synchroniser auprès de tous les fournisseurs configurés
pyllmkit models sync

# Synchroniser uniquement auprès de Google Gemini
pyllmkit models sync --provider google

# Sauvegarder le cache découvert dans le projet local (.pyllmkit/discovered_models.json)
pyllmkit models sync --local
```

---

## 9. Commande `providers` : Inspection des Fournisseurs

Permet d'inspecter les 6 fournisseurs d'inférence certifiés par PyLLMKit (`openai`, `anthropic`, `google`, `mistral`, `xai`, `ollama`).

### 9.1 `providers list`

```bash
pyllmkit providers list
```

Affiche les protocoles certifiés, variables de secret associées et profils d'exécution.

---

### 9.2 `providers inspect`

Affiche les règles d'étanchéité, l'URL officielle certifiée et la variable d'environnement requise pour un fournisseur donné.

```bash
pyllmkit providers inspect anthropic
```

Sortie console :
```text
╭───────────── Configuration Fournisseur : Anthropic ─────────────╮
│ Nom officiel       : Anthropic                                  │
│ Profil technique   : anthropic                                  │
│ Runtime            : direct                                     │
│ Endpoint approuvé  : https://api.anthropic.com/v1/messages      │
│ Variable de secret : ANTHROPIC_API_KEY                          │
│ Protocole          : messages-v1                                │
│                                                                 │
│ Note de sécurité : les clés d'API ne sont résolues qu'à         │
│ l'exécution et ne sont jamais journalisées.                     │
╰─────────────────────────────────────────────────────────────────╯
```

---

## 10. Commande `deployments` : Liaisons Opérationnelles

Affiche les déploiements configurés dans le catalogue d'inférence associant un modèle logique à un runtime fournisseur.

```bash
# Lister tous les déploiements
pyllmkit deployments list

# Filtrer par fournisseur
pyllmkit deployments list --provider mistral
```

---

## 11. Commande `runs` : Historique, FinOps et Fine-Tuning

Ce groupe permet d'auditer les exécutions locales, de surveiller les dépenses FinOps et d'exporter des jeux de données d'apprentissage.

### 11.1 `runs list`

Affiche le tableau récapitulatif des dernières inférences exécutées localement avec le statut de facturation et la durée.

```bash
# Afficher les 20 dernières exécutions (défaut)
pyllmkit runs list

# Limiter aux 50 dernières exécutions
pyllmkit runs list --limit 50
```

Exemple de sortie :
```text
                                             Historique des 20 dernières exécutions                                              
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Run ID          ┃ Modèle                       ┃ Fourni… ┃ Mode    ┃ Statut    ┃ Finish   ┃   Durée ┃   Tokens ┃    Coût ┃ Tarif    ┃ Date    ┃
┃                 ┃                              ┃         ┃         ┃           ┃          ┃    (ms) ┃          ┃  estimé ┃ vérifié  ┃ (UTC)   ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ 8e5a73e4b475... │ gemini-omni-1.2-flash        │ google  │ genera… │ completed │ stop     │ 15114.7 │ 15 / 5793│     N/A │ 2026-11… │ 2026-1… │
│ e39671628633... │ grok-imagine-video           │ xai     │ genera… │ completed │ stop     │ 18474.7 │    - / - │       - │ 2026-11… │ 2026-1… │
│ 2157d49df063... │ grok-4.20-0309-non-reasoning │ xai     │ stream  │ completed │ stop     │  1460.0 │ 209 / 67 │ $0.00074│ 2026-11… │ 2026-1… │
│ 8dd0df7d5987... │ dall-e-3                     │ openai  │ run     │ completed │ stop     │     0.4 │    - / - │       - │ 2026-11… │ 2026-1… │
│                 │                              │ (mock)  │         │           │          │         │          │         │          │         │
└─────────────────┴──────────────────────────────┴─────────┴─────────┴───────────┴──────────┴─────────┴──────────┴─────────┴──────────┴─────────┘
```

---

### 11.2 `runs inspect`

Affiche l'intégralité des métadonnées d'une exécution spécifique à partir de son `run_id` (durée, tokens détaillés, TTFT, prompt et réponse si enregistrés).

```bash
pyllmkit runs inspect 2157d49df063456b82d945f62e092ba1
```

---

### 11.3 `runs export`

Exporte l'historique des inférences consenties (`--record-content`) vers un fichier JSONL formaté pour l'entraînement ou le fine-tuning.

```bash
# Export au format ChatML (par défaut)
pyllmkit runs export --output ./exports/dataset_chatml.jsonl

# Export filtré sur un modèle spécifique au format Alpaca
pyllmkit runs export --model gpt-4o --format alpaca --output ./exports/dataset_alpaca.jsonl
```

---

### 11.4 `runs prune` et `runs purge-content`

Garantit le respect du cycle de rétention et de la politique de confidentialité locale :

```bash
# Supprimer définitivement les exécutions de plus de 30 jours
pyllmkit runs prune --days 30

# Expurger les prompts et réponses de tous les runs tout en conservant les métriques FinOps
pyllmkit runs purge-content
```

---

## 12. Commande `config` : Gestion de la Configuration

Ce groupe permet d'inspecter et d'initialiser les fichiers de configuration de la CLI.

### 12.1 `config show`

Affiche la configuration active, les fichiers détectés, les clés d'API masquées et les dossiers de stockage configurés.

```bash
pyllmkit config show
```

Extrait de la sortie :
```text
╭──────────────────────────────────────────────────────────────────────────────╮
│ Fichier local (projet)  : /chemin/projet/.pyllmkit.yaml (Prioritaire)        │
│ Fichier global (machine): ~/.config/pyllmkit/config.yaml (Fallback)          │
╰──────────────────────────────────────────────────────────────────────────────╯
                              Chemins de Stockage                               
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Ressource                      ┃ Source                 ┃ Chemin configuré   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ Base de données SQLite         │ Local (.pyllmkit.yaml) │ ./.pyllmkit/hist…  │
│ Dossier d'export par défaut    │ Local (.pyllmkit.yaml) │ ./exports          │
│ Dossier des artifacts / assets │ Local (.pyllmkit.yaml) │ ./assets           │
└────────────────────────────────┴────────────────────────┴────────────────────┘
```

---

### 12.2 `config path`

Affiche simplement le chemin absolu du fichier de configuration actif.

```bash
pyllmkit config path
```

---

### 12.3 `config init`

Crée un modèle de fichier de configuration pré-rempli et documenté.

```bash
# Initialiser la configuration globale (~/.config/pyllmkit/config.yaml)
pyllmkit config init

# Initialiser une configuration locale de projet (.pyllmkit.yaml)
pyllmkit config init --local

# Choisir le format de sérialisation (yaml, json, toml)
pyllmkit config init --local --format toml
```

---

## 13. Commande `tools` : Validation des Schémas d'Outils

La commande `tools validate` effectue une vérification syntaxique et structurelle stricte d'un fichier JSON définissant un outil ou une fonction selon le standard P4 de PyLLMKit.

### Syntaxe

```bash
pyllmkit tools validate <chemin_fichier_json>
```

### Exemple

```bash
pyllmkit tools validate ./schemas/get_weather.json
```

Sortie console en cas de conformité :
```text
[green]Succès : La définition d'outil dans 'get_weather.json' est conforme au standard P4-JSON-1.[/green]
Nom de la fonction : get_current_weather
Paramètres validés : 2 (location: string, unit: enum)
```

---

## 14. Sécurité, Confidentialité et Codes de Sortie

### Règles de Sécurité

1. **Isolation des Clés** : Les clés d'API saisies dans les fichiers locaux `.pyllmkit.yaml` ne sont jamais affichées en clair dans la console (masquage systématique `sk-proj-...6_cA`).
2. **Étanchéité Git** : Veillez à ce que `.pyllmkit*`, `*.db`, `exports/` et `assets/` soient inscrits dans votre `.gitignore`.
3. **Protection Réseau** : Aucun appel réseau n'est effectué sans la présence explicite du drapeau `--live`.

### Codes de Sortie (Exit Codes)

La CLI PyLLMKit utilise les conventions de code de retour POSIX standard pour faciliter l'intégration dans des scripts bash et pipelines CI/CD :

| Code | Signification | Contexte Typique |
| :---: | :--- | :--- |
| `0` | **Succès** | L'opération demandée s'est terminée normalement. |
| `1` | **Erreur Métier / Validation** | Modèle introuvable, paramètre non supporté, validation d'outil échouée. |
| `2` | **Erreur Technique / Réseau** | Échec de connexion réseau en mode live, clé API invalide, timeout. |

---

## 15. Aide-Mémoire Rapide (Cheat Sheet)

```bash
# Inférence rapide hors ligne (simulation)
pyllmkit run "Bonjour"

# Inférence en direct avec modèle spécifique
pyllmkit run "Rédige un poème" --model gpt-4o --live

# Streaming direct avec suivi temps réel
pyllmkit stream "Explique la relativité" --model gemini-2.0-flash --live

# Analyse d'image locale
pyllmkit run "Décris cette photo" --image ./photo.jpg --model gpt-4o --live

# Génération d'une image DALL-E 3
pyllmkit generate image "Un paysage de montagne" --model dall-e-3 --live

# Synthèse vocale audio OpenAI TTS
pyllmkit generate audio "Traitement terminé" --model tts-1 --voice alloy --live

# Inspection de l'historique et des coûts
pyllmkit runs list
pyllmkit runs inspect <run_id>

# Export pour le Fine-Tuning
pyllmkit runs export --output ./dataset.jsonl

# Vérification de la configuration active
pyllmkit config show
```

