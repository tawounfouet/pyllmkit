# Guide de Génération d'Assets Multimédias avec PyLLMKit

Ce guide couvre de bout en bout la génération d'assets (images, audio de synthèse vocale, vidéos) avec [`PyLLMKit`](../../README.md) : configuration, commandes CLI, modèles disponibles par fournisseur, options, stockage des fichiers, historique FinOps, API Python, architecture interne, dépannage et extension. Pour la configuration générale de la CLI (cascade de fichiers, base SQLite, exports), consultez d'abord le [Guide de Configuration et de Stockage](01_CLI_CONFIGURATION_AND_STORAGE_GUIDE.md). L'analyse de conception initiale se trouve dans [l'analyse de génération multimodale](../analysis/2026-11-07_MULTIMODAL_OUTPUT_GENERATION_ANALYSIS.md).

> État vérifié le **2026-11-07** avec des clés réelles OpenAI, Google Gemini API et xAI. La disponibilité des modèles dépend de votre compte : utilisez la [section 12](#13-vérifier-les-modèles-accessibles-avec-vos-clés) pour la vérifier.

---

## Sommaire

1. [Principes](#1-principes)
2. [Démarrage rapide](#2-démarrage-rapide)
3. [Configuration et clés d'API](#3-configuration-et-clés-dapi)
4. [Modèles disponibles](#4-modèles-disponibles)
5. [Générer des images](#5-générer-des-images)
6. [Générer de l'audio (Text-to-Speech)](#6-générer-de-laudio-text-to-speech)
7. [Générer des vidéos](#7-générer-des-vidéos)
8. [Prompts détaillés depuis un fichier `.md`](#8-prompts-détaillés-depuis-un-fichier-md)
9. [Générer un média avec `pyllmkit run`](#9-générer-un-média-avec-pyllmkit-run)
10. [Fichiers produits et emplacement](#10-fichiers-produits-et-emplacement)
11. [Historique, coûts et FinOps](#11-historique-coûts-et-finops)
12. [Mode simulation (mock)](#12-mode-simulation-mock)
13. [Vérifier les modèles accessibles avec vos clés](#13-vérifier-les-modèles-accessibles-avec-vos-clés)
14. [Utilisation depuis Python](#14-utilisation-depuis-python)
15. [Architecture interne](#15-architecture-interne)
16. [Erreurs et dépannage](#16-erreurs-et-dépannage)
17. [Ajouter un nouveau modèle](#17-ajouter-un-nouveau-modèle)
18. [Sécurité et confidentialité](#18-sécurité-et-confidentialité)
19. [Aide-mémoire](#19-aide-mémoire)

---

## 1. Principes

- **Hors ligne par défaut** : toute commande s'exécute en simulation, même si `defaults.live: true` figure dans la configuration. Seul le drapeau explicite `--live` déclenche un appel réseau facturable, invocation par invocation.
- **Zéro dépendance d'exécution** : les adaptateurs média utilisent uniquement la bibliothèque standard (`urllib`). Aucun SDK fournisseur n'est requis.
- **Routage par modalité** : le type de génération (image, audio, vidéo) est déduit des modalités de sortie déclarées dans le catalogue (`modalities_out`), jamais du nom du modèle.
- **Un seul média par appel** : chaque invocation produit exactement une image, un fichier audio ou une vidéo.
- **Matérialisation immédiate** : le média est reçu en mémoire puis écrit sur disque à la fin de la commande. Les URL temporaires des fournisseurs sont téléchargées tout de suite.
- **Erreurs explicites** : en cas d'échec, un code normalisé, un conseil et le message assaini du fournisseur sont affichés (ligne `Détails`).

---

## 2. Démarrage rapide

```bash
# 1. Vérifier la configuration active et la présence des clés
pyllmkit config show

# 2. Essayer sans réseau (fichiers de simulation valides)
pyllmkit generate image "Un phare breton à l'aube"

# 3. Générer pour de vrai (appel facturé)
pyllmkit generate image "Un phare breton à l'aube" --quality low --live
pyllmkit generate audio "Bonjour, bienvenue dans PyLLMKit." --voice nova --live
pyllmkit generate video "Une goutte d'eau tombant dans un bol, ralenti" --duration 6 --live

# 4. Retrouver les exécutions
pyllmkit runs list
```

Sans `--out`, les fichiers sont enregistrés dans `assets/images/`, `assets/audios/` ou `assets/videos/`.

---

## 3. Configuration et clés d'API

### 3.1 Clés par fournisseur

| Fournisseur | Clé dans `.pyllmkit.yaml` (`api_keys`) | Variable d'environnement | Usage média |
|---|---|---|---|
| OpenAI | `openai` ou `openai_api_key` | `OPENAI_API_KEY` | Images, TTS |
| Google Gemini API | `gemini`, `google` ou `gemini_api_key` | `GEMINI_API_KEY` | Images, TTS, vidéo |
| xAI | `xai` ou `xai_api_key` | `XAI_API_KEY` | Images, vidéo |

Anthropic, Mistral et Ollama ne proposent pas de génération de médias dans PyLLMKit.

Une variable d'environnement déjà définie dans le shell prime sur la valeur du fichier. Les clés contenant `...` (gabarits) sont ignorées.

### 3.2 Exemple de configuration projet

```yaml
# .pyllmkit.yaml (ignoré par Git via la règle .pyllmkit*)
api_keys:
  openai: "sk-proj-..."
  gemini: "..."
  xai: "xai-..."

storage:
  history_db: ".pyllmkit/history.db"
  export_dir: "./exports"
  assets_dir: "./assets"   # relatif au dossier du fichier de configuration
```

### 3.3 Répertoire des assets : ordre de priorité

1. Option `--out` / `-o` de la commande (fichier ou dossier).
2. Variable d'environnement `PYLLMKIT_ASSETS_DIR`.
3. `storage.assets_dir` de la configuration (locale, sinon globale).
4. `./assets` dans le répertoire courant.

```bash
PYLLMKIT_ASSETS_DIR=~/Desktop/rendus pyllmkit generate image "Logo minimaliste" --live
```

---

## 4. Modèles disponibles

### 4.1 Modèles disponibles (2026-11-07)

« Live » : génération réellement exécutée avec succès. « Listé » : modèle exposé par l'API de listing du fournisseur, pris en charge par l'adaptateur, mais pas encore appelé en génération.

| Type | Modèle | Fournisseur | Statut | Remarques |
|---|---|---|---|---|
| Image | `gpt-image-1-mini` | OpenAI | Live | **Défaut** de `generate image`, économique |
| Image | `gpt-image-1.5`, `gpt-image-2` | OpenAI | Listé | Meilleure fidélité |
| Image | `gemini-2.5-flash-image` | Google | Live | Respecte `--aspect-ratio` |
| Image | `gemini-3.1-flash-image`, `gemini-3-pro-image`, `gemini-nano-banana-2.1` | Google | Listé | Famille Gemini Image (Nano Banana) |
| Image | `grok-imagine-image` | xAI | Live | JPEG en sortie |
| Image | `grok-imagine-image-2.0` | xAI | Listé | Accepte `--quality` |
| Audio | `gpt-4o-mini-tts` | OpenAI | Live | **Défaut** de `generate audio`, accepte `--instructions` |
| Audio | `tts-1`, `tts-1-hd` | OpenAI | Live (`tts-1`) | Pas d'`--instructions` |
| Audio | `gemini-2.5-flash-preview-tts` | Google | Live | WAV 24 kHz mono, 30 voix |
| Audio | `gemini-3.8-flash-tts` | Google | Listé | Même interface que ci-dessus |
| Vidéo | `grok-imagine-video` | xAI | Live | **Défaut** de `generate video`, job asynchrone |
| Vidéo | `grok-imagine-video-1.5` | xAI | Listé | Jusqu'à 1080p natif |
| Vidéo | `gemini-omni-1.2-flash` | Google | Live | Audio natif, 3 à 15 s, réponse synchrone |
| Vidéo | `gemini-omni-1.1-flash` | Google | Listé | Redirigé vers 1.2 le 2026-12-03 |

### 4.2 Modèles historiques (simulation uniquement avec les clés testées)

| Modèle | Statut constaté | Alternative |
|---|---|---|
| `dall-e-3`, `dall-e-2` | `The model 'dall-e-3' does not exist` | `gpt-image-1-mini` |
| `imagen-3` (→ `imagen-3.0-generate-002`) | 404, non exposé par la clé Gemini API | `gemini-2.5-flash-image` |
| `veo-2` (→ `veo-2.0-generate-001`) | 404 ; Veo 3.1 preview arrêté le 2026-10-22 | `gemini-omni-1.2-flash` |

Ces entrées restent dans le catalogue : elles fonctionnent en simulation, et en live si votre compte y a encore accès (les adaptateurs Imagen `:predict` et Veo `:predictLongRunning` sont implémentés).

### 4.3 Consulter le catalogue

```bash
pyllmkit models list --pricing
pyllmkit models inspect gemini-omni-1.2-flash
```

---

## 5. Générer des images

```bash
pyllmkit generate image "<prompt>" [--model M] [--out CHEMIN] [--size WxH] [--quality Q]
                                   [--aspect-ratio R] [--resolution RES] [--live]
                                   [--record-content] [--timeout S]
```

### 5.1 Options selon le fournisseur

| Option | OpenAI `gpt-image-*` | OpenAI `dall-e-*` | Google Gemini Image | Google Imagen | xAI Grok Imagine |
|---|---|---|---|---|---|
| `--size` | `1024x1024`, `1024x1536`, `1536x1024`, `auto` | `1024x1024` (défaut), autres selon modèle | ignoré | ignoré | ignoré |
| `--quality` | `low`, `medium`, `high`, `auto` (`standard` → `medium`, `hd` → `high`) | `standard` (défaut), `hd` (dall-e-3) | ignoré | ignoré | `low`, `medium`, `auto` (2.0) |
| `--aspect-ratio` | ignoré | ignoré | ex. `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `5:4` | `aspectRatio` | `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `2:3`, `3:2`, `21:9`, `auto`... |
| `--resolution` | ignoré | ignoré | `1K`, `2K`, `4K` (`512` : 3.1 Flash) | ignoré | `1k`, `2k` |

Une option non pertinente pour le fournisseur choisi est simplement ignorée. Une valeur invalide est refusée par l'API et remonte en `invalid_request` avec le message du fournisseur.

### 5.2 Exemples

```bash
# OpenAI, paysage, qualité basse (le moins cher)
pyllmkit generate image "Bureau scandinave, lumière naturelle" --size 1536x1024 --quality low --live

# OpenAI haute fidélité
pyllmkit generate image "Affiche rétro d'un salon tech" -m gpt-image-2 --quality high --live

# Gemini, format bannière
pyllmkit generate image "Un phare au coucher du soleil, aquarelle" \
  -m gemini-2.5-flash-image --aspect-ratio 16:9 --live

# xAI, carré, vers un fichier précis
pyllmkit generate image "Un renard en papier découpé" -m grok-imagine-image \
  --aspect-ratio 1:1 --out ./visuels/renard.jpg --live
```

### 5.3 Ce qui est affiché

- Type MIME et dimensions **réelles** (lues dans l'en-tête PNG/JPEG du fichier reçu).
- Prompt révisé : prompt réécrit par le fournisseur s'il en renvoie un. Pour Gemini, c'est le texte d'accompagnement du modèle (ex. « Voici votre image ! »).
- Tokens d'entrée/sortie lorsque le fournisseur les publie (`gpt-image-*`, Gemini).

---

## 6. Générer de l'audio (Text-to-Speech)

```bash
pyllmkit generate audio "<texte à lire>" [--model M] [--out CHEMIN] [--voice V]
                                         [--instructions STYLE] [--live]
                                         [--record-content] [--timeout S]
```

### 6.1 Voix et formats

| Modèle | Voix (`--voice`) | Défaut | `--instructions` | Format produit |
|---|---|---|---|---|
| `gpt-4o-mini-tts` | `alloy`, `ash`, `ballad`, `coral`, `echo`, `fable`, `nova`, `onyx`, `sage`, `shimmer`, `verse` | `alloy` | Oui (style de diction) | MP3 (`audio/mpeg`) |
| `tts-1`, `tts-1-hd` | `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer` | `alloy` | Non (ignoré) | MP3 (`audio/mpeg`) |
| Gemini `*-tts` | `Zephyr`, `Puck`, `Charon`, `Kore`, `Fenrir`, `Leda`, `Orus`, `Aoede`, `Callirrhoe`, `Autonoe`, `Enceladus`, `Iapetus`, `Umbriel`, `Algieba`, `Despina`, `Erinome`, `Algenib`, `Rasalgethi`, `Laomedeia`, `Achernar`, `Alnilam`, `Schedar`, `Gacrux`, `Pulcherrima`, `Achird`, `Zubenelgenubi`, `Vindemiatrix`, `Sadachbia`, `Sadaltager`, `Sulafat` | `Kore` | Oui (préfixé au texte) | WAV PCM 16 bits, 24 kHz, mono |

Pour Gemini, l'API renvoie du PCM brut (`audio/L16;rate=24000`) : PyLLMKit l'encapsule automatiquement dans un conteneur WAV lisible partout, et calcule la durée exacte. Pour OpenAI, la durée affichée est une estimation (environ 2,5 mots par seconde), l'API ne la renvoyant pas.

### 6.2 Exemples

```bash
# Voix OpenAI avec style
pyllmkit generate audio "Votre rapport mensuel est prêt." --voice coral \
  --instructions "Ton chaleureux et posé, débit lent" --live

# Voix Gemini
pyllmkit generate audio "Bonjour Thomas, voici la voix Gemini." \
  -m gemini-2.5-flash-preview-tts --voice Puck --live

# Ancien modèle OpenAI, sortie nommée
pyllmkit generate audio "Notification : calcul terminé." -m tts-1-hd --out ./sons/notif.mp3 --live
```

---

## 7. Générer des vidéos

```bash
pyllmkit generate video "<prompt>" [--model M] [--out CHEMIN] [--duration N]
                                   [--aspect-ratio R] [--resolution RES]
                                   [--poll-timeout S] [--timeout S] [--live]
                                   [--record-content]
```

### 7.1 Paramètres par modèle

| Paramètre | xAI `grok-imagine-video*` | Google `gemini-omni-*` | Google `veo-*` (si accessible) |
|---|---|---|---|
| `--duration` | 1 à 15 s (défaut fournisseur : 8) | 3 à 15 s (défaut fournisseur : 10) | 4, 6 ou 8 s selon modèle |
| `--aspect-ratio` | `16:9` (défaut), `9:16`, `1:1`, `4:3`, `3:4`, `3:2`, `2:3`, `21:9`, `5:2` | `16:9` (défaut), `9:16` | `16:9`, `9:16` |
| `--resolution` | `480p` (défaut), `720p`, `1080p` | `360p`, `720p` (défaut), `1080p`, `4k` | `720p`, `1080p`, `4k` |
| Audio | Non | Oui, natif et synchronisé | Selon modèle |
| Mode d'appel | Job asynchrone + polling | Requête synchrone | Opération longue + polling |
| Délai observé | ~18 s pour 1 s en 480p | ~15 s pour 3 s en 360p | - |

La CLI accepte `--duration` entre 1 et 15 ; une valeur hors plage d'un modèle précis (ex. 2 s pour Omni) est refusée par le fournisseur avec un message explicite.

### 7.2 Délais d'attente

- `--timeout` (défaut 180 s) : délai maximal d'une requête HTTP (soumission, polling, téléchargement).
- `--poll-timeout` (défaut 900 s) : temps total maximal d'attente de fin de génération pour les modèles asynchrones (xAI, Veo). Pour Omni, dont la réponse est synchrone, la requête unique peut durer jusqu'au plus grand des deux délais.
- Au-delà, l'exécution échoue en `provider_timeout`. Pour xAI, l'identifiant `request_id` figure dans les détails.

### 7.3 Exemples

```bash
# xAI, format vertical pour réseaux sociaux
pyllmkit generate video "Une rue de Paris sous la pluie, néons" --duration 6 \
  --aspect-ratio 9:16 --resolution 720p --live

# Google Gemini Omni, avec audio natif
pyllmkit generate video "Un bateau en papier sur un étang calme, légères ondulations" \
  -m gemini-omni-1.2-flash --duration 6 --resolution 720p --live

# Test rapide et peu coûteux
pyllmkit generate video "Une goutte d'eau, ralenti" -m gemini-omni-1.2-flash \
  --duration 3 --resolution 360p --live
```

---

## 8. Prompts détaillés depuis un fichier `.md`

Pour un prompt long, versionné ou réutilisable, rédigez-le dans un fichier du dossier [`prompts/`](../../prompts/README.md) et passez-le avec `--prompt-file` (`-f`) ou la syntaxe `@chemin`. Disponible sur `generate image`, `generate audio`, `generate video` et `run`.

```bash
pyllmkit generate image -f prompts/images/affiche_salon_tech.md --live
pyllmkit generate image @prompts/images/affiche_salon_tech.md --live          # équivalent
pyllmkit generate audio -f prompts/audios/annonce_accueil.md --voice nova --live
pyllmkit generate video -f prompts/videos/teaser_produit.md --duration 3 --live
```

### 8.1 Format

```markdown
---
model: gemini-2.5-flash-image
aspect_ratio: 16:9
resolution: 2K
---
<!-- Note de travail : retirée avant l'envoi -->
# Affiche
## Composition
- ...
## Style
- ...
```

- **En-tête YAML facultatif** entre deux lignes `---` : réglages de génération, jamais envoyés au modèle.
- **Commentaires HTML** `<!-- ... -->` : supprimés avant l'envoi.
- **Corps** : envoyé tel quel. Le Markdown (titres, listes) structure bien un prompt d'image ou de vidéo ; pour l'audio, écrivez du texte simple, sinon les symboles risquent d'être lus.
- UTF-8, 1 Mo maximum, valeurs d'en-tête sur une seule ligne.

### 8.2 Clés d'en-tête

| Clé | `image` | `audio` | `video` |
|---|---|---|---|
| `model` | Oui | Oui | Oui |
| `size`, `quality` | Oui | - | - |
| `aspect_ratio`, `resolution` | Oui | - | Oui |
| `voice`, `instructions` | - | Oui | - |
| `duration` | - | - | Oui (`6` ou `6s`, entre 1 et 15) |

`aspect-ratio` et `aspect_ratio` sont équivalents. Une clé inconnue (ex. `modle`) bloque la commande ; une clé valide mais sans objet pour la sous-commande est signalée (`Réglages ignorés pour 'generate audio' : ...`) puis ignorée. Avec `run`, l'en-tête entier est ignoré (avertissement affiché) et seul le corps est utilisé.

### 8.3 Priorités et combinaison

1. Option de la ligne de commande (`--model`, `--quality`...).
2. Valeur de l'en-tête du fichier.
3. Valeur par défaut de la commande.

Un texte passé en plus de `-f` est ajouté à la fin du prompt du fichier, séparé par une ligne vide : un même fichier de style sert ainsi pour plusieurs sujets.

```bash
pyllmkit generate image -f prompts/images/affiche_salon_tech.md "Thème : cybersécurité" --quality low --live
```

### 8.4 Erreurs

Fichier introuvable, vide (après retrait de l'en-tête et des commentaires), non UTF-8, trop volumineux, clé inconnue ou durée hors plage : code `invalid_prompt_file`, code de sortie `2`, aucun appel réseau. Le chemin absolu du fichier chargé et le nombre de caractères envoyés sont affichés avant chaque génération.

---

## 9. Générer un média avec `pyllmkit run`

La commande générique `run` sait aussi produire un média lorsque le modèle ciblé est un modèle de génération :

```bash
pyllmkit run "Un aigle stylisé, logo vectoriel" -m gpt-image-1-mini --live
pyllmkit run "Un aigle stylisé" -m gpt-image-1-mini -o ./logo.png --live
```

Différences avec `generate` :

| | `generate image/audio/video` | `run` |
|---|---|---|
| Options média (`--size`, `--voice`, `--duration`...) | Oui | Non (valeurs par défaut du fournisseur) |
| Vérification du type (`generate image -m veo-2` refusé) | Oui | Non |
| Ligne `Détails` avec le message fournisseur | Oui | Non |
| Prompt système (`--system` ou `defaults.system_prompt`) | Non envoyé | Ignoré pour les médias : seuls les messages utilisateur forment le prompt |
| Option de sortie | `--out` / `-o` | `--output-file` / `-o` |

Préférez `generate` pour toute génération de média.

---

## 10. Fichiers produits et emplacement

### 10.1 Nommage par défaut

```
<assets_dir>/<catégorie>/<modèle>_<AAAAMMJJ_HHMMSS>_<8 premiers caractères du run_id>.<ext>
```

Exemple : `assets/videos/gemini-omni-1.2-flash_20261107_044733_8e5a73e4.mp4`. Les caractères `/` et `:` du nom de modèle sont remplacés par `_`.

| Catégorie | Dossier | Extensions |
|---|---|---|
| Images | `images/` | `.png`, `.jpg` (JPEG), `.webp` selon le MIME réel |
| Audio | `audios/` | `.mp3` (défaut), `.wav`, `.ogg` |
| Vidéo | `videos/` | `.mp4` |
| Texte (sortie non média) | `documents/` | `.txt` |

Le préfixe `<8 caractères>` correspond au Run ID affiché et permet de relier un fichier à son entrée dans `pyllmkit runs inspect`.

### 10.2 Option `--out`

- Chemin de fichier : le fichier est écrit tel quel (dossiers parents créés). L'extension n'est pas corrigée : choisissez-la en accord avec le format produit (voir tableaux ci-dessus).
- Dossier existant : le fichier y est créé sous le nom `<AAAAMMJJ_HHMMSS>_export.<ext>`.
- `~` est développé.

Si l'écriture échoue, la commande s'arrête avec le code de sortie `1` et le message d'erreur.

### 10.3 Git

Le `.gitignore` du projet exclut le contenu de `assets/` tout en conservant l'arborescence (`.gitkeep`). Les médias générés ne sont donc jamais commités par accident.

---

## 11. Historique, coûts et FinOps

### 11.1 Ce qui est enregistré

Chaque exécution `generate` (réussie ou échouée) est ajoutée à la base SQLite locale avec `mode = generate` : Run ID, modèle, fournisseur (suffixe `(mock)` en simulation), statut, code de fin ou d'erreur, durée, tokens si publiés. Le **prompt n'est enregistré qu'avec `--record-content`**. Le média lui-même n'est jamais stocké en base : seul le fichier sur disque le contient.

```bash
pyllmkit runs list                 # 20 dernières exécutions
pyllmkit runs inspect 8e5a73e4     # détail (préfixe de Run ID accepté)
pyllmkit runs inspect 8e5a73e4 --json
pyllmkit runs export -m gpt-image-1-mini -o ./exports/images.jsonl
```

### 11.2 Estimation des coûts

| Cas | Coût affiché |
|---|---|
| Run échoué ou simulé | `-` (« non facturé » dans `runs inspect`) |
| Modèle avec tarif catalogue et quantité connue | Montant estimé (ex. `$0.0400 (1 image)`) |
| Modèle sans tarif catalogue | `N/A` |
| Quantité inconnue (ex. durée vidéo non renvoyée) | `-` : aucune quantité n'est supposée |

Tarifs présents au catalogue (indicatifs, non temps réel) : `dall-e-3` 0,04 $/image, `dall-e-2` 0,02 $/image, `tts-1` 15 $/1M caractères, `tts-1-hd` 30 $/1M caractères, `imagen-3` 0,03 $/image, `veo-2` 0,15 $/seconde. Les modèles ajoutés en 2026-11 (`gpt-image-*`, `gpt-4o-mini-tts`, Gemini Image/TTS, Omni, Grok Imagine) n'ont pas encore de tarif vérifié et affichent `N/A`. Pour une facturation exacte, référez-vous aux consoles des fournisseurs ; xAI renvoie en plus un champ `usage.cost_in_usd_ticks` non exploité à ce jour.

---

## 12. Mode simulation (mock)

Sans `--live`, aucun appel réseau n'est effectué et des fichiers **réellement lisibles** sont produits en pur Python :

| Type | Fichier simulé | Métadonnées affichées |
|---|---|---|
| Image | PNG 24 bits 256x256 | 1024x1024 (indicatif), prompt révisé fictif |
| Audio | WAV PCM 16 bits 22 kHz, 2,0 s | 2,0 s, transcription fictive |
| Vidéo | MP4 court | 5,0 s, 1280x720 (indicatif) |

Usages : tester une chaîne de traitement, une CI, ou la structure des dossiers sans coût. Les options (`--size`, `--voice`...) ne modifient pas le fichier simulé. Le fournisseur apparaît comme `<nom> (simulation)` et l'historique comme `<nom> (mock)`.

---

## 13. Vérifier les modèles accessibles avec vos clés

Les API de listing sont gratuites. Les commandes ci-dessous lisent les clés depuis l'environnement ; n'affichez jamais la clé elle-même.

```bash
# OpenAI : modèles image, TTS, vidéo
curl -s https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY" \
  | jq -r '.data[].id' | grep -E 'image|tts|sora|audio' | sort

# Google Gemini API : modèles image, TTS, vidéo
curl -s "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  | jq -r '.models[] | "\(.name) \(.supportedGenerationMethods)"' | grep -E 'image|tts|omni|veo|imagen'

# Un modèle précis (certains, comme gemini-omni-*, peuvent manquer du listing mais être accessibles)
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-omni-1.2-flash" \
  -H "x-goog-api-key: $GEMINI_API_KEY" | jq '.displayName, .supportedGenerationMethods'

# xAI
curl -s https://api.x.ai/v1/models -H "Authorization: Bearer $XAI_API_KEY" | jq -r '.data[].id'
```

Les clés définies seulement dans `.pyllmkit.yaml` ne sont injectées dans l'environnement que pendant l'exécution de `pyllmkit` ; exportez-les dans votre shell pour utiliser `curl`.

---

## 14. Utilisation depuis Python

L'API publique de la CLI permet d'intégrer la génération dans un script ou un service :

```python
from pyllmkit.adapters.cli.catalog import create_reference_catalog
from pyllmkit.adapters.cli.media_saver import get_default_asset_path, save_output_media
from pyllmkit.adapters.cli.service import create_cli_inference_service
from pyllmkit.adapters.inference.media_http import MediaDiagnostics, MediaGenerationOptions
from pyllmkit.domain.inference import ImageOutput, InferenceRequest, ModelTarget
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.models import ModelId

catalog = create_reference_catalog()
diagnostics = MediaDiagnostics()
service = create_cli_inference_service(
    catalog,
    mock=True,  # False = appel réseau réel (clés lues dans l'environnement)
    media_options=MediaGenerationOptions(size="1536x1024", quality="low"),
    diagnostics=diagnostics,
)

request = InferenceRequest(
    ModelTarget(ModelId("gpt-image-1-mini")),
    (Message(Role.USER, Content((TextContent("Un phare breton à l'aube"),))),),
)
execution = service.invoke(request)

if execution.run.failure is not None:
    raise SystemExit(f"{execution.run.failure.code}: {diagnostics.last_error}")

output = execution.response.output
assert isinstance(output, ImageOutput)
path = get_default_asset_path(output, execution.run.run_id.value, "gpt-image-1-mini")
print(save_output_media(output, path), output.mime_type, output.width, output.height)
```

### 14.1 `MediaGenerationOptions`

| Champ | Type | Correspond à |
|---|---|---|
| `size` | `str \| None` | `--size` |
| `quality` | `str \| None` | `--quality` |
| `voice` | `str \| None` | `--voice` |
| `instructions` | `str \| None` | `--instructions` |
| `aspect_ratio` | `str \| None` | `--aspect-ratio` |
| `resolution` | `str \| None` | `--resolution` |
| `duration_seconds` | `int \| None` | `--duration` |
| `request_timeout_seconds` | `float` (180,0) | `--timeout` |
| `poll_timeout_seconds` | `float` (900,0) | `--poll-timeout` |
| `poll_interval_seconds` | `float` (5,0) | Intervalle de polling (xAI, Veo) |

`None` signifie « valeur par défaut du fournisseur ». Les options sont fixées à la construction du service : créez un service par jeu d'options.

### 14.2 Objets de sortie

| Classe | Champs utiles |
|---|---|
| `ImageOutput` | `media` (`MediaSourceRef` data URI), `mime_type`, `width`, `height`, `revised_prompt` |
| `AudioOutput` | `media`, `mime_type`, `duration_seconds`, `transcript` |
| `VideoOutput` | `media`, `mime_type`, `duration_seconds`, `width`, `height` |

`execution.response.usage` expose `input_tokens`, `output_tokens`, `total_tokens`, `reasoning_tokens`, `input_characters`, `output_media_units` et `output_media_seconds` lorsqu'ils sont connus (`None` sinon, jamais zéro par défaut).

`MediaDiagnostics` contient après un échec `last_error` (message assaini), `http_status` et, pour la vidéo xAI, `progress` (pourcentages de progression observés).

---

## 15. Architecture interne

```
pyllmkit generate <type>  ──►  InferenceService (résolution catalogue → déploiement)
                                         │
                                         ▼
                       RegisteredInferencePort (adaptateur par fournisseur)
                                         │
                                         ▼
                 MediaRoutingAdapter : modalités de sortie du déploiement
                    │                                        │
       sortie "text" incluse                      sortie image / audio / video
                    ▼                                        ▼
     adaptateur texte natif                OpenAIMediaAdapter | GoogleMediaAdapter
     (Responses, Gemini, xAI...)                  | XAIMediaAdapter
                                                         │
                                                         ▼
                                         media_http (HTTP, erreurs, diagnostics)
                                                         │
                                                         ▼
                                 ImageOutput / AudioOutput / VideoOutput (data URI)
                                                         │
                                                         ▼
                                  media_saver → assets/<catégorie>/<fichier>
```

### 15.1 Points d'accès utilisés

| Adaptateur | Cas | Requête | Réponse exploitée |
|---|---|---|---|
| `OpenAIMediaAdapter` | Image | `POST api.openai.com/v1/images/generations` | `data[0].b64_json` (ou `url` téléchargée) |
| `OpenAIMediaAdapter` | TTS | `POST api.openai.com/v1/audio/speech` | Corps binaire MP3 |
| `GoogleMediaAdapter` | Image Gemini | `POST .../v1beta/models/{m}:generateContent`, `responseModalities: [TEXT, IMAGE]`, `imageConfig` | `candidates[0].content.parts[].inlineData` |
| `GoogleMediaAdapter` | TTS Gemini | `:generateContent`, `responseModalities: [AUDIO]`, `speechConfig` | `inlineData` PCM → WAV |
| `GoogleMediaAdapter` | Imagen | `:predict` | `predictions[0].bytesBase64Encoded` |
| `GoogleMediaAdapter` | Omni | `POST .../v1beta/interactions`, `response_format: {type: video, ...}` | `steps[type=model_output].content[type=video].data` |
| `GoogleMediaAdapter` | Veo | `:predictLongRunning` puis `GET .../v1beta/{operation}` | `response.generateVideoResponse.generatedSamples[0].video.uri` |
| `XAIMediaAdapter` | Image | `POST api.x.ai/v1/images/generations` (`response_format: b64_json`) | `data[0].b64_json` |
| `XAIMediaAdapter` | Vidéo | `POST api.x.ai/v1/videos/generations` puis `GET /v1/videos/{request_id}` | `video.url` téléchargée immédiatement |

Les identifiants courts du catalogue Google sont traduits en identifiants natifs (`imagen-3` → `imagen-3.0-generate-002`, `veo-2` → `veo-2.0-generate-001`).

### 15.2 Fichiers source

| Fichier | Rôle |
|---|---|
| [`adapters/cli/commands/generate.py`](../../src/pyllmkit/adapters/cli/commands/generate.py) | Sous-commandes CLI, garde-fou de type, historique |
| [`adapters/cli/service.py`](../../src/pyllmkit/adapters/cli/service.py) | Fabrique de service, `MediaRoutingAdapter`, mode simulation |
| [`adapters/inference/media_http.py`](../../src/pyllmkit/adapters/inference/media_http.py) | Options, diagnostics, HTTP, mapping d'erreurs, utilitaires WAV/image |
| [`adapters/inference/openai_media.py`](../../src/pyllmkit/adapters/inference/openai_media.py) | OpenAI images et TTS |
| [`adapters/inference/google_media.py`](../../src/pyllmkit/adapters/inference/google_media.py) | Gemini Image/TTS, Imagen, Omni, Veo |
| [`adapters/inference/xai_media.py`](../../src/pyllmkit/adapters/inference/xai_media.py) | Grok Imagine image et vidéo |
| [`adapters/cli/media_saver.py`](../../src/pyllmkit/adapters/cli/media_saver.py) | Chemins par défaut et écriture disque |
| [`adapters/cli/mock_assets.py`](../../src/pyllmkit/adapters/cli/mock_assets.py) | Fichiers de simulation PNG/WAV/MP4 |
| [`adapters/cli/data/models_catalog.json`](../../src/pyllmkit/adapters/cli/data/models_catalog.json) | Modalités, tarifs, descriptions |

---

## 16. Erreurs et dépannage

### 16.1 Codes d'erreur

| Code | Cause typique | Action |
|---|---|---|
| `model_not_found` | Modèle retiré ou non accessible (`dall-e-3`, `veo-*`, `imagen-*`) | Choisir un modèle de la [section 4.1](#42-modèles-disponibles-2026-11-07) ; vérifier l'accès ([section 12](#13-vérifier-les-modèles-accessibles-avec-vos-clés)) |
| `credential_unavailable` | Clé absente, mal nommée ou refusée (HTTP 401) | `pyllmkit config show` ; vérifier `api_keys` et les alias |
| `permission_denied` | Clé valide sans droit sur ce modèle (HTTP 403) | Activer l'accès ou la facturation côté fournisseur |
| `invalid_request` | Paramètre invalide (taille, ratio, durée, voix) | Lire la ligne `Détails` et ajuster l'option |
| `content_filtered` | Prompt ou média bloqué par la modération | Reformuler le prompt |
| `rate_limited` | Quota dépassé (HTTP 429) | Patienter ou changer de modèle |
| `provider_overloaded` | Erreur serveur (HTTP 5xx) | Réessayer plus tard |
| `provider_timeout` | Requête ou génération trop longue | Augmenter `--timeout` / `--poll-timeout` |
| `provider_not_completed` | Job vidéo `failed`/`expired` ou statut non terminé | Lire `Détails`, réessayer ou reformuler |
| `connection_failure` | Réseau, DNS, proxy | Vérifier la connectivité |
| `unsupported_provider_output` | Réponse sans média exploitable | Réessayer ; signaler si systématique |
| `unsupported_capability` | Type demandé incompatible avec le modèle | Utiliser la sous-commande indiquée par le message |

### 16.2 Problèmes fréquents

**`generate image -m veo-2` est refusé.** Le garde-fou compare la sous-commande aux modalités du modèle avant tout appel : `'veo-2' produit (video), pas 'image'`. Utilisez `generate video`.

**« Fichier sauvegardé » mais l'extension ne correspond pas au contenu.** Vous avez imposé `--out fichier.png` pour un modèle xAI qui renvoie du JPEG. Omettez `--out` ou utilisez l'extension adaptée.

**Le coût affiche `N/A`.** Le modèle n'a pas encore de tarif vérifié dans le catalogue ; ce n'est pas une erreur.

**Une génération vidéo semble bloquée.** Les jobs vidéo prennent de quelques secondes à plusieurs minutes. La commande attend jusqu'à `--poll-timeout` (900 s par défaut) puis échoue proprement.

**La clé est bien dans `.pyllmkit.yaml` mais `credential_unavailable` persiste.** Une variable d'environnement non vide (par exemple une ancienne clé exportée dans votre shell) prime sur le fichier : `unset GEMINI_API_KEY` puis relancez. Vérifiez aussi que vous exécutez la commande depuis le projet (découverte de `.pyllmkit.yaml` dans le dossier courant ou ses parents).

---

## 17. Ajouter un nouveau modèle

Pour un modèle d'un fournisseur déjà pris en charge (OpenAI, Google, xAI) et d'une famille d'API existante :

1. Ajouter l'entrée dans [`models_catalog.json`](../../src/pyllmkit/adapters/cli/data/models_catalog.json) avec des `modalities_out` exclusivement média :

   ```json
   "gpt-image-3": {
     "id": "gpt-image-3", "name": "GPT Image 3", "family": "openai", "provider": "openai",
     "context_window": null, "max_output_tokens": null,
     "modalities_in": ["text"], "modalities_out": ["image"],
     "pricing": {"input_cost": null, "output_cost": null, "unit": "image"},
     "features": ["image_generation"], "description": "...",
     "source_url": "https://platform.openai.com/docs/models", "last_verified": "AAAA-MM-JJ"
   }
   ```

2. Déclarer le déploiement dans `reference_models_data` de [`catalog.py`](../../src/pyllmkit/adapters/cli/catalog.py) : `("gpt-image-3", "openai", "openai", "cloud", "global")`.
3. Aucune modification de routage n'est nécessaire : le `MediaRoutingAdapter` dirige automatiquement le modèle vers l'adaptateur média de son fournisseur selon `modalities_out`.
4. Unités de tarif reconnues par `compute_run_cost` : `image` (par image, `output_cost`), `1M characters` (TTS, `input_cost`), `second` (vidéo, `output_cost`). Laissez `null` tant que le prix n'est pas vérifié.
5. Si le modèle utilise une API différente (nouveau point d'accès ou nouveau format de réponse), ajoutez une branche dans l'adaptateur du fournisseur, sur le modèle de `_omni_video` dans `google_media.py`, et des tests hors réseau dans `tests/unit/adapters/inference/test_media_generation_adapters.py` (HTTP simulé en patchant `urllib.request.urlopen`).

---

## 18. Sécurité et confidentialité

- **Consentement réseau explicite** : `--live` à chaque invocation ; la configuration ne peut pas l'activer implicitement.
- **Secrets** : `.pyllmkit.yaml` est exclu de Git. Les messages d'erreur des fournisseurs sont assainis avant affichage : clé utilisée remplacée par `***`, motifs de clés (`sk-...`, `xai-...`, `AIza...`, `AQ....`) masqués, texte tronqué à 400 caractères.
- **Prompt** : seuls les messages utilisateur sont envoyés comme prompt média. Le prompt système de la configuration n'est jamais transmis à un générateur d'image ou de voix.
- **Historique** : métadonnées uniquement par défaut ; prompt archivé seulement avec `--record-content`.
- **URL temporaires** : les vidéos xAI et Veo sont téléchargées dès la fin du job (les URL expirent ; Google conserve les vidéos Veo 2 jours).
- **Mémoire** : le média transite en mémoire sous forme de data URI base64 avant écriture. Une vidéo 1080p de 15 s reste de l'ordre de quelques dizaines de Mo.
- **Filigranes** : les contenus Google (Veo, Omni, Gemini Image) portent un filigrane SynthID invisible.

---

## 19. Aide-mémoire

```bash
# Images
pyllmkit generate image "..." --live                                   # gpt-image-1-mini
pyllmkit generate image "..." --size 1536x1024 --quality high -m gpt-image-2 --live
pyllmkit generate image "..." -m gemini-2.5-flash-image --aspect-ratio 16:9 --resolution 2K --live
pyllmkit generate image "..." -m grok-imagine-image --aspect-ratio 1:1 --live

# Audio
pyllmkit generate audio "..." --voice nova --instructions "ton enjoué" --live   # gpt-4o-mini-tts
pyllmkit generate audio "..." -m gemini-2.5-flash-preview-tts --voice Kore --live

# Vidéo
pyllmkit generate video "..." --duration 6 --resolution 720p --live             # grok-imagine-video
pyllmkit generate video "..." -m gemini-omni-1.2-flash --duration 6 --aspect-ratio 9:16 --live

# Sortie et stockage
pyllmkit generate image "..." --out ./visuels/hero.png --live
PYLLMKIT_ASSETS_DIR=./rendus pyllmkit generate audio "..." --live

# Suivi
pyllmkit runs list
pyllmkit runs inspect <run_id>
pyllmkit models inspect <modèle>
pyllmkit generate video --help
```
