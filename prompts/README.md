# Prompts PyLLMKit

Ce dossier contient des prompts détaillés, versionnés avec le projet, à passer à la CLI via `--prompt-file` (`-f`) ou la syntaxe `@chemin`.

```bash
pyllmkit generate image -f prompts/images/affiche_salon_tech.md --live
pyllmkit generate image @prompts/images/affiche_salon_tech.md --live      # équivalent
pyllmkit generate audio -f prompts/audios/annonce_accueil.md --voice coral --live
pyllmkit generate video -f prompts/videos/teaser_produit.md --live
pyllmkit run -f prompts/images/affiche_salon_tech.md -m gpt-4o            # texte seul, en-tête ignoré
```

## Format d'un fichier

```markdown
---
model: gemini-2.5-flash-image
aspect_ratio: 16:9
resolution: 2K
---
<!-- Commentaire de travail : jamais envoyé au modèle -->
# Sujet
Le texte du prompt, en Markdown libre...
```

- **En-tête YAML facultatif** (entre deux lignes `---`) : réglages de génération. Il n'est jamais envoyé au modèle.
- **Commentaires HTML** `<!-- ... -->` : retirés avant l'envoi, pour annoter le prompt librement.
- **Corps** : envoyé tel quel (titres, listes et gras Markdown compris), espaces de début et de fin retirés.
- Encodage UTF-8, 1 Mo maximum.

## Clés d'en-tête autorisées

| Clé | `generate image` | `generate audio` | `generate video` |
|---|---|---|---|
| `model` | Oui | Oui | Oui |
| `size` | Oui | - | - |
| `quality` | Oui | - | - |
| `aspect_ratio` | Oui | - | Oui |
| `resolution` | Oui | - | Oui |
| `voice` | - | Oui | - |
| `instructions` | - | Oui | - |
| `duration` | - | - | Oui (entier, `6` ou `6s`) |

Une clé inconnue (faute de frappe) bloque la commande avec un message explicite. Une clé valide mais sans objet pour la sous-commande est signalée puis ignorée. Les valeurs tiennent sur une ligne ; `aspect-ratio` et `aspect_ratio` sont équivalents.

## Priorités

1. Option passée en ligne de commande (`--model`, `--aspect-ratio`...).
2. Valeur de l'en-tête du fichier.
3. Valeur par défaut de la commande.

Si un texte est passé **en plus** de `-f`, il est ajouté à la fin du prompt du fichier, ce qui permet de réutiliser un fichier de style avec un sujet variable :

```bash
pyllmkit generate image -f prompts/images/affiche_salon_tech.md "Thème : cybersécurité" --live
```

## Limites de longueur côté fournisseurs

| Modèle | Limite indicative du prompt |
|---|---|
| `gpt-image-*` | ~32 000 caractères |
| `dall-e-3` | 4 000 caractères |
| `tts-1`, `tts-1-hd`, `gpt-4o-mini-tts` | 4 096 caractères de texte à lire |

Un dépassement est refusé par le fournisseur (`invalid_request`, détail affiché).

Guide complet : [docs/guides/02_MEDIA_ASSET_GENERATION_GUIDE.md](../docs/guides/02_MEDIA_ASSET_GENERATION_GUIDE.md).
