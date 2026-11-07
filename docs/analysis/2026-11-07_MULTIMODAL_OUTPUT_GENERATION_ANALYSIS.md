# PyLLMKit - Analyse d'ingénierie : Génération Multimodale en Sortie (Text-to-Image, Text-to-Audio/Speech, Text-to-Video)

- Date de référence : 2026-11-07
- Statut : DOCUMENT D'ANALYSE ET D'INGÉNIERIE DÉCISIONNELLE
- Portée : Conception et spécification de la génération de contenus multimédias en sortie (Text-to-Media) dans le domaine d'inférence, les adaptateurs de protocoles fournisseurs, l'interface CLI et le moteur FinOps
- Invariants stricts : Zéro dépendance d'exécution (`dependencies = []`), Domaine pur et passif (ADR-011), Couverture >= 95.00 %, Règle typographique stricte (pas de tiret cadratin U+2014)
- Fichiers source cibles :
  - [`src/pyllmkit/domain/inference/`](../../src/pyllmkit/domain/inference/) (`output.py`, `response.py`, `serialization.py`, `usage.py`, `request.py`)
  - [`src/pyllmkit/application/inference/`](../../src/pyllmkit/application/inference/) (`service.py`, `contracts.py`)
  - [`src/pyllmkit/adapters/inference/`](../../src/pyllmkit/adapters/inference/) (`openai_responses_mapping.py`, `google_gemini_mapping.py`, `media_generation_mapping.py`, etc.)
  - [`src/pyllmkit/adapters/cli/`](../../src/pyllmkit/adapters/cli/) (`commands/generate.py`, `commands/run.py`, `formatting/panels.py`, `model_specs.py`, `data/models_catalog.json`)

---

## 1. Contexte et Problématique

### 1.1 Ce qui a été accompli (Compréhension Multimodale en Entrée)
PyLLMKit supporte désormais la compréhension multimodale universelle en entrée :
- **Entités de Domaine** : [`ImageContent`](../../src/pyllmkit/domain/interactions/image.py), [`AudioContent`](../../src/pyllmkit/domain/interactions/audio.py) et [`VideoContent`](../../src/pyllmkit/domain/interactions/video.py) encapsulent les références passives [`MediaSourceRef`](../../src/pyllmkit/domain/interactions/media.py) (`uri`, `data`, `file`, `asset`).
- **Adaptateurs d'Inférence** : Les 6 fournisseurs (Gemini, OpenAI, Anthropic, xAI, Mistral, Ollama) encodent et transmettent fidèlement les médias aux modèles de vision et de traitement audio/vidéo.
- **CLI & FinOps** : La CLI accepte `--image`, `--audio`, `--video`, contrôle la taille des fichiers (< 100 Mo) et persiste les échanges au standard ChatML dans SQLite.

### 1.2 Le Goulet d'Étranglement Actuel (Sortie Strictement Textuelle)
Bien que les entrées soient multimodales, le canal de sortie d'inférence de PyLLMKit est aujourd'hui verrouillé sur le texte :
1. **Domaine (`output.py`)** :
   ```python
   # Minimal inference output Value Object
   class TextOutput:
       text: str
   InferenceOutput: TypeAlias = TextOutput
   ```
   Toute réponse ne contenant pas une instance de `TextOutput` est immédiatement rejetée par `InferenceResponse.__post_init__` avec `DomainValidationError`.
2. **Codec de Sérialisation (`serialization.py`)** :
   Le schéma JSON v1 n'autorise que `output.kind == "text"`. Impossible de persister ou désérialiser une image, une voix ou une vidéo générée.
3. **Résolution des Déploiements (`service.py`)** :
   Le pipeline de préparation impose en dur `required_output_modalities = frozenset((Modality("text"),))`. Un modèle purement générateur d'images (comme DALL-E 3) ou de voix (comme TTS-1) est systématiquement rejeté avec `no_compatible_deployment`.
4. **Interface CLI (`run.py`, `panels.py`)** :
   La CLI attend une chaîne de caractères à afficher dans la console Rich. Elle ne dispose d'aucune routine pour matérialiser des octets binaires (PNG, MP3, MP4) dans un fichier local sur le disque de l'utilisateur.

### 1.3 L'Objectif : Générer de Vraies Images, Audio et Vidéos
L'utilisateur a formulé le besoin explicite suivant : **générer de vraies images, du vrai audio et de vraies vidéos** à l'aide de modèles d'IA, et pouvoir les sauvegarder localement.

Pour répondre à ce besoin sans compromettre l'architecture robuste de PyLLMKit, nous devons concevoir la couche de **Génération Multimodale en Sortie (Text-to-Media)**.

---

## 2. Panorama des APIs et Protocoles de Génération Multimodale

Chaque grand fournisseur aborde la génération de médias selon deux paradigmes distincts qu'il convient d'unifier :

```
                  +----------------------------------------------+
                  |  PyLLMKit Ingestion / Orchestration Unifiée   |
                  +----------------------------------------------+
                                         |
                   +---------------------+---------------------+
                   |                                           |
                   v                                           v
       [Paradigme A : Endpoints Dédiés]            [Paradigme B : Chat Multimodal Natif]
       - OpenAI: /v1/images/generations (DALL-E)   - Google Gemini 2.0 (responseModalities: AUDIO)
       - OpenAI: /v1/audio/speech (TTS-1)          - OpenAI Realtime / GPT-4o-audio
       - Google: Vertex Imagen 3 (:predict)        - Modèles avec flux de sortie mixte (Texte + Media)
       - Google: Veo Video Generation
```

### 2.1 OpenAI
1. **Génération d'Images (`/v1/images/generations`)** :
   - *Modèles* : `dall-e-3`, `dall-e-2`.
   - *Payload Requête* :
     ```json
     {
       "model": "dall-e-3",
       "prompt": "Un chat astronaute explorant Mars, style néon cyberpunk",
       "size": "1024x1024",
       "quality": "standard",
       "response_format": "b64_json"
     }
     ```
   - *Réponse* : JSON contenant `data[0].b64_json` (payload base64) et `data[0].revised_prompt` (prompt réécrit par le modèle).
2. **Synthèse Vocale / TTS (`/v1/audio/speech`)** :
   - *Modèles* : `tts-1`, `tts-1-hd`.
   - *Payload Requête* :
     ```json
     {
       "model": "tts-1",
       "input": "Bonjour, bienvenue sur PyLLMKit !",
       "voice": "alloy",
       "response_format": "mp3",
       "speed": 1.0
     }
     ```
   - *Réponse* : Flux binaire direct (`audio/mpeg`, `audio/wav`).
3. **Chat Multimodal Natif (`/v1/chat/completions`)** :
   - *Modèles* : `gpt-4o-audio-preview`.
   - *Payload Requête* : `modalities: ["text", "audio"]`, `audio: {"voice": "alloy", "format": "wav"}`.
   - *Réponse* : Message assistant avec `audio.data` (base64) et `audio.transcript` (texte).

### 2.2 Google (Gemini API & Vertex AI)
1. **Génération d'Images (Imagen 3)** :
   - *API Vertex / Gemini* : `:predict` ou `:generateImages`.
   - *Payload Requête* :
     ```json
     {
       "instances": [{"prompt": "Un temple sous la pluie d'automne"}],
       "parameters": {"sampleCount": 1, "aspectRatio": "16:9", "outputOptions": {"mimeType": "image/png"}}
     }
     ```
   - *Réponse* : JSON avec `predictions[0].bytesBase64Encoded`.
2. **Audio Natif (Gemini 2.0 Flash / Live)** :
   - *API Gemini* : `generationConfig.responseModalities = ["AUDIO"]` ou `speechConfig`.
   - *Réponse* : Inline binaire encodé en base64 dans `candidates[0].content.parts[0].inlineData`.
3. **Génération Vidéo (Veo / DeepMind)** :
   - Text-to-Video avec génération de clips MP4 (job asynchrone retournant une URI ou un bucket GCS).

### 2.3 xAI (Grok) et Modèles Locaux
1. **xAI Imagine** :
   - Compatible avec l'endpoint OpenAI `/v1/images/generations` avec les modèles `grok-2-image` ou partenaires (Flux).
2. **Modèles Locaux (Ollama / Local Runners)** :
   - Support de la synthèse vocale locale via passerelle Piper/Coqui (TTS) ou diffusion locale (Stable Diffusion via endpoint compatible).

---

## 3. Les Quatre Piliers d'Ingénierie de la Génération Multimodale

### Pilier 1 : Modèle de Domaine Universel (`domain/inference`)

Le domaine doit accueillir des sorties multimédias riches sans enfreindre le principe fondamental du Domaine Pur et Passif (ADR-011) : aucune E/S réseau ou disque dans le domaine, manipulation exclusive d'objets de valeur immuables et de références typées.

```
                                +-------------------+
                                |  InferenceOutput  | (Union TypeAlias)
                                +-------------------+
                                          |
        +------------------+--------------+--------------+------------------+
        |                  |                             |                  |
        v                  v                             v                  v
+----------------+ +-----------------+           +-----------------+ +-----------------+
|   TextOutput   | |   ImageOutput   |           |   AudioOutput   | |   VideoOutput   |
+----------------+ +-----------------+           +-----------------+ +-----------------+
| text: str      | | media: Ref      |           | media: Ref      | | media: Ref      |
| kind: "text"   | | mime_type: str  |           | mime_type: str  | | mime_type: str  |
|                | | width: int?     |           | duration_sec: ? | | duration_sec: ? |
|                | | height: int?    |           | transcript: str?| | width/height: ? |
|                | | revised_prompt? |           | kind: "audio"   | | kind: "video"   |
|                | | kind: "image"   |           +-----------------+ +-----------------+
+----------------+ +-----------------+
```

#### A. Entités de Sortie dans [`src/pyllmkit/domain/inference/output.py`](../../src/pyllmkit/domain/inference/output.py)
```python
@dataclass(frozen=True, slots=True)
class ImageOutput:
    """Sortie d'inférence représentant une image générée."""
    media: MediaSourceRef
    mime_type: str = "image/png"
    width: int | None = None
    height: int | None = None
    revised_prompt: str | None = None

    def __post_init__(self) -> None:
        if type(self.media) is not MediaSourceRef:
            raise DomainValidationError("ImageOutput.media must be a MediaSourceRef")
        if type(self.mime_type) is not str or not self.mime_type.startswith("image/"):
            raise DomainValidationError("ImageOutput.mime_type must be a valid image MIME type")

    @property
    def kind(self) -> Literal["image"]:
        return "image"


@dataclass(frozen=True, slots=True)
class AudioOutput:
    """Sortie d'inférence représentant un flux ou fichier audio/vocal généré."""
    media: MediaSourceRef
    mime_type: str = "audio/mpeg"
    duration_seconds: float | None = None
    transcript: str | None = None

    def __post_init__(self) -> None:
        if type(self.media) is not MediaSourceRef:
            raise DomainValidationError("AudioOutput.media must be a MediaSourceRef")
        if type(self.mime_type) is not str or not self.mime_type.startswith("audio/"):
            raise DomainValidationError("AudioOutput.mime_type must be a valid audio MIME type")

    @property
    def kind(self) -> Literal["audio"]:
        return "audio"


@dataclass(frozen=True, slots=True)
class VideoOutput:
    """Sortie d'inférence représentant une vidéo générée."""
    media: MediaSourceRef
    mime_type: str = "video/mp4"
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None

    def __post_init__(self) -> None:
        if type(self.media) is not MediaSourceRef:
            raise DomainValidationError("VideoOutput.media must be a MediaSourceRef")
        if type(self.mime_type) is not str or not self.mime_type.startswith("video/"):
            raise DomainValidationError("VideoOutput.mime_type must be a valid video MIME type")

    @property
    def kind(self) -> Literal["video"]:
        return "video"


@dataclass(frozen=True, slots=True)
class MultiPartOutput:
    """Sortie composite (ex: texte explicatif + audio ou image) pour modèles natifs."""
    parts: tuple[TextOutput | ImageOutput | AudioOutput | VideoOutput, ...]

    def __post_init__(self) -> None:
        if type(self.parts) is not tuple or not self.parts:
            raise DomainValidationError("MultiPartOutput.parts must be a non-empty tuple")

    @property
    def kind(self) -> Literal["multipart"]:
        return "multipart"


InferenceOutput: TypeAlias = (
    TextOutput | ImageOutput | AudioOutput | VideoOutput | MultiPartOutput
)
```

#### B. Mise à jour de `InferenceResponse`
Dans [`src/pyllmkit/domain/inference/response.py`](../../src/pyllmkit/domain/inference/response.py) :
```python
if not isinstance(self.output, (TextOutput, ImageOutput, AudioOutput, VideoOutput, MultiPartOutput)):
    raise DomainValidationError("InferenceResponse.output must be a valid InferenceOutput")
```

#### C. Codec de Sérialisation Canonique v2 dans [`serialization.py`](../../src/pyllmkit/domain/inference/serialization.py)
Extension de `_OUTPUT_FIELDS` et prise en charge bidirectionnelle sans perte :
- `output.kind == "text"` : `{"kind": "text", "text": "..."}`
- `output.kind == "image"` :
  `{"kind": "image", "media": {"kind": "data|uri|file", "value": "..."}, "mime_type": "...", "width": 1024, "height": 1024, "revised_prompt": "..."}`
- `output.kind == "audio"` :
  `{"kind": "audio", "media": {"kind": "data|uri|file", "value": "..."}, "mime_type": "...", "duration_seconds": 3.5, "transcript": "..."}`
- `output.kind == "video"` :
  `{"kind": "video", "media": {"kind": "data|uri|file", "value": "..."}, "mime_type": "...", "duration_seconds": 5.0}`
- `output.kind == "multipart"` :
  `{"kind": "multipart", "parts": [...]}`

#### D. Résolution Dynamique des Modalités de Sortie dans `service.py`
Dans [`src/pyllmkit/application/inference/service.py`](../../src/pyllmkit/application/inference/service.py) :
Le calcul de `required_output_modalities` ne doit plus être codé en dur à `text`. Il doit être déduit de la configuration de génération ou d'une exigence explicite :
```python
# Extraction des modalités de sortie demandées (par défaut: text si non spécifié)
req_outputs = request.target_output_modalities or frozenset((Modality("text"),))

resolution = self._resolver.resolve(
    target,
    DeploymentRequirement(
        required_input_modalities=req_inputs,
        required_output_modalities=req_outputs,
    ),
)
```

---

### Pilier 2 : Adaptateurs Wire Format Spécialisés et Routage des Protocoles

Pour conserver la règle de zéro dépendance (`dependencies = []`), tous les appels réseau sont exécutés via la bibliothèque standard Python (`urllib.request`, `http.client`, `base64`, `json`).

```
                    +------------------------------------+
                    |     InferencePort.invoke(...)      |
                    +------------------------------------+
                                      |
                 +--------------------+--------------------+
                 |                                         |
                 v                                         v
   [Modalité de sortie: "text"]             [Modalité de sortie: "image" / "audio"]
                 |                                         |
                 v                                         v
   Chat Completions Wire Mapping            Media Generation Wire Mapping
   (ex: /v1/chat/completions)               (ex: /v1/images/generations ou /v1/audio/speech)
                 |                                         |
                 v                                         v
            TextOutput                           ImageOutput / AudioOutput
```

#### A. Adaptateur OpenAI Spécialisé
Dans [`src/pyllmkit/adapters/inference/openai_media_mapping.py`](../../src/pyllmkit/adapters/inference/) :
1. **Génération d'Image (DALL-E 3)** :
   - Détection : le modèle appartient à la famille image (ex: `dall-e-3`, `dall-e-2`) ou la modalité de sortie requise est `image`.
   - Endpoint : `POST https://api.openai.com/v1/images/generations`
   - Headers : `Authorization: Bearer <API_KEY>`, `Content-Type: application/json`
   - Body :
     ```python
     payload = {
         "model": prepared.alias,
         "prompt": extract_prompt_text(request),
         "size": "1024x1024",
         "response_format": "b64_json",
     }
     ```
   - Extraction de la réponse :
     ```python
     b64_data = response_json["data"][0]["b64_json"]
     revised = response_json["data"][0].get("revised_prompt")
     data_uri = f"data:image/png;base64,{b64_data}"
     output = ImageOutput(
         media=MediaSourceRef(kind="data", value=data_uri),
         mime_type="image/png",
         width=1024,
         height=1024,
         revised_prompt=revised,
     )
     ```
2. **Synthèse Vocale (OpenAI TTS-1)** :
   - Détection : modèle de type `tts-1` ou `tts-1-hd` ou modalité de sortie `audio`.
   - Endpoint : `POST https://api.openai.com/v1/audio/speech`
   - Extraction de la réponse : le flux d'octets brut est encodé en base64 pour construire un `MediaSourceRef(kind="data", value=f"data:audio/mpeg;base64,{b64_str}")`.

#### B. Adaptateur Google Gemini / Vertex
- Pour **Imagen 3** : appel à l'endpoint `:predict` de Vertex AI / Gemini API, avec extraction du champ `bytesBase64Encoded` et construction d'un `ImageOutput`.
- Pour **Gemini 2.0 Live / Native Audio** : envoi de `responseModalities: ["AUDIO", "TEXT"]`, réception du chunk audio encodé base64, retourné sous forme de `MultiPartOutput(parts=(TextOutput(transcript), AudioOutput(audio_ref)))`.

#### C. Mode Simulation / Hors Ligne Déterministe (`mock=True`)
Pour garantir des tests unitaires et d'acceptation 100 % passants sans dépendance au réseau ni coût API :
- Génération d'une image SVG/PNG minimale valide en base64 (ex: 1x1 pixel transparent ou SVG géométrique décoratif).
- Génération d'un silence audio WAV valide (en-tête RIFF de 44 octets avec données nulles).
- Génération d'un conteneur MP4 minimaliste de simulation.

---

### Pilier 3 : Interface CLI & Sauvegarde des Médias sur Disque

L'expérience utilisateur en ligne de commande doit être immédiate, élégante et productive.

#### A. Architecture des Commandes CLI
Nous proposons deux chemins d'accès ergonomiques :
1. **Option d'export dans `pyllmkit run`** :
   ```bash
   pyllmkit run "Un lion majestueux sur un rocher" --model dall-e-3 -o ./lion.png
   pyllmkit run "Message d'accueil pour le répondeur" --model tts-1 -o ./repondeur.mp3
   ```
   Lorsque le modèle cible produit une sortie de type média, le flag `-o / --output-file` écrit directement les octets décodés dans le fichier spécifié.
2. **Sous-commande dédiée `pyllmkit generate`** pour un contrôle fin :
   ```bash
   pyllmkit generate image "Cyberpunk Tokyo in 2088" --model dall-e-3 --out ./tokyo.png --size 1024x1024 --quality hd
   pyllmkit generate audio "Bienvenue chez Seqens" --model tts-1 --voice alloy --out ./intro.mp3 --format mp3
   pyllmkit generate video "Une cascade dans la forêt tropicale" --model veo-2 --out ./cascade.mp4
   ```

#### B. Matérialisation Sécurisée des Fichiers Binaires
Dans un nouveau module [`src/pyllmkit/adapters/cli/media_saver.py`](../../src/pyllmkit/adapters/cli/) :
```python
def save_output_media(output: InferenceOutput, target_path: Path) -> Path:
    """Décode et écrit le média généré sur disque en toute sécurité."""
    target_path = target_path.expanduser().resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(output, (ImageOutput, AudioOutput, VideoOutput)):
        media_ref = output.media
        if media_ref.kind == "data":
            # Parsing strict du format RFC 2397 : data:<mime>;base64,<payload>
            header, b64_payload = media_ref.value.split(",", 1)
            raw_bytes = base64.b64decode(b64_payload)
            target_path.write_bytes(raw_bytes)
            return target_path
        elif media_ref.kind == "uri":
            # Téléchargement via urllib standard si URL distante retournée
            with urllib.request.urlopen(media_ref.value) as response:
                target_path.write_bytes(response.read())
            return target_path

    raise ValueError("Sortie non convertible en fichier média binaire")
```

#### C. Rendu Visuel dans la Console Rich
Dans [`src/pyllmkit/adapters/cli/formatting/panels.py`](../../src/pyllmkit/adapters/cli/formatting/panels.py) :
- Si la sortie est un `ImageOutput` :
  ```
  ╭────────────────────────── Réponse du modèle [dall-e-3] ──────────────────────────╮
  │ Image générée avec succès !                                                      │
  │                                                                                  │
  │ Dimensions     : 1024x1024 (image/png)                                           │
  │ Fichier créé   : /Users/awf/workspace/lion.png (1.4 Mo)                          │
  │ Prompt révisé  : "A magnificent male lion standing proudly on a high rock..."     │
  ╰──────────────────────────────────────────────────────────────────────────────────╯
  ```
- Si la sortie est un `AudioOutput` :
  ```
  ╭────────────────────────── Réponse du modèle [tts-1] ─────────────────────────────╮
  │ Audio de synthèse généré avec succès !                                           │
  │                                                                                  │
  │ Format         : audio/mpeg                                                      │
  │ Durée estimée  : 3.2 secondes                                                    │
  │ Fichier créé   : /Users/awf/workspace/intro.mp3 (52 Ko)                           │
  ╰──────────────────────────────────────────────────────────────────────────────────╯
  ```

---

### Pilier 4 : FinOps et Modèle Économique Non-Token

La tarification des modèles de génération de médias ne repose pas sur les tokens par million. PyLLMKit doit adapter son moteur FinOps.

#### A. Grille Comparatif des Modèles Économiques
| Modalité | Fournisseur / Modèle | Unité d'œuvre | Coût unitaire standard |
|---|---|---|---|
| **Image** | OpenAI DALL-E 3 (Standard 1024x1024) | Image générée | **$0.040** / image |
| **Image** | OpenAI DALL-E 3 (HD 1024x1792 / 1792x1024) | Image générée | **$0.120** / image |
| **Image** | OpenAI DALL-E 2 (512x512) | Image générée | **$0.018** / image |
| **Image** | Google Imagen 3 (Vertex AI) | Image générée | **$0.030** / image |
| **Audio (TTS)** | OpenAI TTS-1 | 1M caractères texte en entrée | **$15.00** / 1M caractères ($0.015 / 1k car) |
| **Audio (TTS)** | OpenAI TTS-1-HD | 1M caractères texte en entrée | **$30.00** / 1M caractères ($0.030 / 1k car) |
| **Audio (TTS)** | Google Cloud Text-to-Speech (Neural2) | 1M caractères texte en entrée | **$16.00** / 1M caractères |
| **Audio Natif** | GPT-4o-Audio (Sortie) | 1M tokens audio | **$100.00** / 1M tokens audio |
| **Vidéo** | Google Veo / Runway / Sora | Seconde de vidéo | **$0.10 à $0.25** / seconde |

#### B. Enrichissement du Modèle FinOps dans `Usage`
Dans [`src/pyllmkit/domain/inference/usage.py`](../../src/pyllmkit/domain/inference/usage.py) :
```python
@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None
    cached_input_tokens: int | None = None
    # Nouvelles métriques non-tokens pour médias génératifs :
    input_characters: int | None = None
    output_media_units: int | None = None     # Nombre d'images générées (ex: 1)
    output_media_seconds: float | None = None  # Durée audio/vidéo générée
```

#### C. Extension de `compute_run_cost` dans `model_specs.py`
Dans [`src/pyllmkit/adapters/cli/model_specs.py`](../../src/pyllmkit/adapters/cli/model_specs.py) :
```python
def compute_media_run_cost(
    model_name: str,
    spec: ModelSpec,
    usage: Usage | None,
    output: InferenceOutput | None,
    prompt_len_chars: int = 0,
) -> tuple[float | None, str]:
    """Calcul du coût estimé pour les modèles générateurs de médias."""
    unit = spec.pricing.unit

    if unit == "image":
        # Facturation à l'image générée
        unit_cost = spec.pricing.output_cost or 0.04
        images_count = usage.output_media_units if (usage and usage.output_media_units) else 1
        total = images_count * unit_cost
        return total, f"${total:.4f} ({images_count} image{'s' if images_count > 1 else ''})"

    if unit == "1M characters":
        # Facturation au volume de caractères (TTS)
        unit_cost = spec.pricing.input_cost or 15.00
        chars = (usage.input_characters if (usage and usage.input_characters) else prompt_len_chars)
        total = (chars / 1_000_000) * unit_cost
        return total, f"${total:.5f} ({chars} caractères)"

    if unit == "second":
        # Facturation à la seconde de vidéo
        sec_cost = spec.pricing.output_cost or 0.10
        seconds = usage.output_media_seconds if (usage and usage.output_media_seconds) else 5.0
        total = seconds * sec_cost
        return total, f"${total:.4f} ({seconds:.1f}s vidéo)"

    # Fallback tokens classique
    return compute_run_cost(...)
```

---

## 4. Matrice de Décision et Arbitrages Techniques

| Question de Conception | Option A | Option B | Arbitrage Décisionnel Retenu |
|---|---|---|---|
| **Stockage mémoire des binaires** | Fichiers temporaires sur disque (`/tmp`) | Encodage Data URI base64 en mémoire (`MediaSourceRef(kind="data")`) | **Option B** : Conserve la pureté du domaine (ADR-011), sans état résiduel sur disque et compatible avec la sérialisation JSON canonique. |
| **Point d'entrée CLI** | Extension unique de `run` avec `-o` | Sous-commande dédiée `generate` (image, audio, video) | **Synergie A + B** : `run -o` pour la concision universelle, et `pyllmkit generate` pour les options avancées (voix, qualité, résolution). |
| **Téléchargement externe** | Dépendance externe (requests, aiohttp) | Bibliothèque standard (`urllib.request`) | **Option B** : Respect strict du contrat `dependencies = []`. |
| **Gestion des erreurs API** | Exception brute crashant la CLI | Interception propre et affichage dans le panneau d'erreur Rich | **Option B** : Continuité de service et codes de rejet normalisés (`content_policy_violation`, `unsupported_output_modality`). |

---

## 5. Plan de Réalisation et Jalons d'Implémentation

```
[Phase 1 : Domaine d'Inférence]
  |-- Création de ImageOutput, AudioOutput, VideoOutput, MultiPartOutput (output.py)
  |-- Mise à jour de InferenceResponse (response.py)
  |-- Évolution du Codec JSON v2 (serialization.py)
  |-- Extension de Usage (usage.py)
  +-- Tests unitaires de domaine stricts (100 % passants)
        |
        v
[Phase 2 : Catalogue & Moteur FinOps Non-Token]
  |-- Ajout des modèles génératifs dans models_catalog.json (dall-e-3, tts-1, imagen-3, etc.)
  |-- Évolution de ModelPricing et compute_run_cost dans model_specs.py
  +-- Tests unitaires FinOps et tarification image/audio
        |
        v
[Phase 3 : Adaptateurs de Protocoles Fournisseurs]
  |-- Module de mapping génération média (media_generation_mapping.py)
  |-- Branchement endpoints OpenAI (/v1/images/generations, /v1/audio/speech)
  |-- Branchement Vertex / Gemini (Imagen 3, audio natif)
  |-- Mocks déterministes hors ligne pour les tests
  +-- Tests d'acceptation adaptateurs sans dépendance réseau
        |
        v
[Phase 4 : CLI & Persistance Fichiers]
  |-- Module d'écriture disque sécurisée (media_saver.py)
  |-- Prise en charge de -o / --output-file dans run_command
  |-- Implémentation de la sous-commande pyllmkit generate (image, audio, video)
  |-- Panneaux Rich dédiés aux médias générés (panels.py)
  +-- Tests CLI complets (mock live, écriture fichiers, rapports d'erreur)
        |
        v
[Phase 5 : Qualification Globale et Documentation]
  |-- Vérification de la couverture globale >= 95.00 %
  |-- Vérification Ruff, Mypy et règle typographique U+2014
  +-- Mise à jour de CHANGELOG.md et documentation utilisateur
```

---

## 6. Synthèse et Prochaine Étape

Ce document cadre exhaustivement l'architecture technique nécessaire pour offrir une génération multimodale de premier ordre dans PyLLMKit.

En respectant scrupuleusement les invariants de pureté architecturale, de zéro dépendance et de couverture de code supérieure à 95.00 %, PyLLMKit deviendra une boîte à outils unifiée capable à la fois de **comprendre** (Vision, Écoute) et de **créer** (Images, Voix, Vidéos) avec une traçabilité FinOps exemplaire.

La prochaine étape consiste à recueillir la validation de l'utilisateur sur cette conception avant d'engager la Phase 1 du développement.

