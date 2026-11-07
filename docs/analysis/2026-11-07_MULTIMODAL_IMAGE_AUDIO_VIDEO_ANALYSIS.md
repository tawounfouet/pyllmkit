# PyLLMKit - Analyse d'ingénierie : Intégration Multimodale Universelle (Images, Audio, Vidéo)

- Date de référence : 2026-11-07
- Statut : DOCUMENT D'ANALYSE ET D'INGÉNIERIE DÉCISIONNELLE
- Portée : Conception et mise en œuvre du support multimodal universel (Images, Audio, Vidéo) dans le domaine, les adaptateurs d'inférence, la CLI et la traçabilité FinOps
- Contexte amont : Clôture de la version 0.3.0, levée du périmètre `text_only_v1` (ADR-010..013, ADR-054, ADR-059)
- Fichiers source cibles :
  - [`src/pyllmkit/domain/interactions/`](../../src/pyllmkit/domain/interactions/) (`media.py`, `image.py`, `audio.py`, `video.py`, `serialization.py`)
  - [`src/pyllmkit/adapters/inference/`](../../src/pyllmkit/adapters/inference/) (`google_gemini_mapping.py`, `openai_responses_mapping.py`, `anthropic_messages_mapping.py`, `xai_responses_mapping.py`, `mistral_chat_mapping.py`, `ollama_adapter.py`)
  - [`src/pyllmkit/adapters/cli/`](../../src/pyllmkit/adapters/cli/) (`commands/run.py`, `commands/stream.py`, `formatting/panels.py`, `storage/sqlite_store.py`)

---

## 1. Contexte et État des Lieux Initial

### 1.1 Ce qui a été accompli en Phase 2 et en version 0.3.0
PyLLMKit a été pensé dès sa genèse pour la multimodalité (invariant INT-003 : le contenu d'un message est une séquence ordonnée de parties de contenu `ContentPart`) :
- **Invariant `INT-003` / `AC-007`** : Le domaine dispose déjà de [`ImageContent`](../../src/pyllmkit/domain/interactions/image.py) et de [`MediaSourceRef`](../../src/pyllmkit/domain/interactions/media.py). Un `Message` peut légitimement contenir du texte et une image alternés sans réordonnancement implicite.
- **Référence passive `MediaSourceRef` (ADR-011)** : L'objet de valeur du domaine ne télécharge pas de média, ne fait pas d'E/S réseau et ne stocke pas de gros blocs d'octets en mémoire, protégeant ainsi le domaine pur.
- **Catalogue de modèles FinOps** : Le catalogue [`models_catalog.json`](../../src/pyllmkit/adapters/cli/data/models_catalog.json) intègre déjà les champs `modalities_in` (`text`, `image`, `audio`, `video`) et les grilles tarifaires multimodales détaillées (ex: `gpt-realtime-2.1` avec ventilation Audio, Texte, Image).

### 1.2 Le verrou actuel : le périmètre `text_only_v1`
En version 0.3.0, les adaptateurs d'inférence (Phase 7) ont été volontairement restreints au profil textuel strict pour garantir une qualification déterministe hors réseau :
```python
# Présent dans tous les adaptateurs d'inférence (Gemini, OpenAI, Anthropic, xAI, Mistral) :
if len(message.content.parts) != 1:
    raise InvocationPortError("unsupported_content_structure")
part = message.content.parts[0]
if type(part) is not TextContent:
    raise InvocationPortError("unsupported_content_structure")
```
Conséquences de cette restriction :
1. **Rejet systématique des messages multimodaux** : Dès qu'une requête contient un `ImageContent`, l'adaptateur lève `unsupported_content_structure`, empêchant l'inférence vision sur GPT-4o, Claude 3.5 Sonnet ou Gemini 2.0 Flash.
2. **Absence de types de domaine pour l'audio et la vidéo** : Bien que `Modality("audio")` et `Modality("video")` existent dans le vocabulaire M1, aucune classe concrète `AudioContent` ni `VideoContent` n'a été implémentée (différé par ADR-013).
3. **Absence de flags CLI** : `pyllmkit run` et `pyllmkit stream` n'acceptent que l'argument textuel `prompt`. Impossible de passer un fichier image, un extrait audio ou une vidéo.

---

## 2. Objectifs et Exigences d'Ingénierie

L'objectif est d'offrir une expérience multimodale native, unifiée et sûre, respectant scrupuleusement les principes fondamentaux de PyLLMKit :

1. **Zéro dépendance d'exécution (`dependencies = []`)** :
   - Traitement des fichiers multimédias, détection MIME type (`mimetypes`), encodage base64 (`base64`) et hachage (`hashlib`) réalisés exclusivement avec la bibliothèque standard Python.
2. **Principe du Domaine Pur et Passif (ADR-011)** :
   - Le domaine ne fait aucun appel réseau ni lecture disque. Il manipule des références typées (`MediaSourceRef`).
   - La matérialisation (lecture de fichier local, conversion en base64 pour les fournisseurs qui l'exigent) est déléguée aux adaptateurs d'infrastructure (CLI et adaptateurs d'inférence).
3. **Typage strict et préservation de l'ordre** :
   - Séquentialité stricte : si l'utilisateur envoie `[Texte, Image, Audio, Texte]`, cet ordre exact est transmis aux fournisseurs supportant le multi-part.
4. **Gestion granulaire des capacités par fournisseur** :
   - Rejet explicite avec code d'erreur `unsupported_capability` si une modalité demandée (ex: vidéo) n'est pas supportée par le modèle ou le fournisseur ciblé.

---

## 3. Architecture Détaillée : Les Quatre Piliers

### Pilier 1 : Modèle de Domaine (`interactions`)

#### A. Entités `AudioContent` et `VideoContent`
Création de deux nouvelles classes de valeur immuables héritant de `ContentPart` :
- [`src/pyllmkit/domain/interactions/audio.py`](../../src/pyllmkit/domain/interactions/audio.py) :
  ```python
  @dataclass(frozen=True, slots=True)
  class AudioContent(ContentPart):
      source: MediaSourceRef
      format: str | None = None  # ex: "wav", "mp3", "aac"

      @property
      def kind(self) -> str:
          return "audio"

      @property
      def modality(self) -> Modality:
          return Modality("audio")
  ```
- [`src/pyllmkit/domain/interactions/video.py`](../../src/pyllmkit/domain/interactions/video.py) :
  ```python
  @dataclass(frozen=True, slots=True)
  class VideoContent(ContentPart):
      source: MediaSourceRef
      format: str | None = None  # ex: "mp4", "webm", "mov"

      @property
      def kind(self) -> str:
          return "video"

      @property
      def modality(self) -> Modality:
          return Modality("video")
  ```

#### B. Évolution de `MediaSourceRef` (ADR-011 étendu)
Pour permettre l'utilisation locale de fichiers et les flux de données en mémoire sans violer les invariants de sécurité :
- `kind="uri"` : URL absolue HTTP ou HTTPS passif validée syntaxiquement.
- `kind="asset"` : identifiant opaque pour stockage référencé ou asset ID distant.
- `kind="file"` : référence vers un chemin de fichier local (validé en syntaxe par le domaine, lu uniquement par les adaptateurs autorisés).
- `kind="data"` : data URI standardisé (`data:<mime_type>;base64,<payload>`) pour les médias pré-encodés.

#### C. Codec de Sérialisation JSON v2
Mise à jour de [`serialization.py`](../../src/pyllmkit/domain/interactions/serialization.py) :
- Prise en charge des discriminants `kind="audio"` et `kind="video"`.
- Aller-retour garanti sans altération : `message_from_dict(message_to_dict(message)) == message`.

---

### Pilier 2 : Adaptateurs Fournisseurs (`adapters/inference`)

Chaque fournisseur possède ses propres spécificités de protocole. Les adaptateurs doivent traduire les `ContentPart` vers le format cible natif :

#### 1. Google Gemini (`google_gemini_mapping.py`)
Google Gemini offre le support multimodal le plus vaste (Images, Audio, Vidéo) :
- Les parties sont projetées dans la liste `parts` de chaque contenu.
- Si `MediaSourceRef` est une URL HTTP(S) ou un File URI Google : `{"fileData": {"fileUri": url, "mimeType": mime}}`.
- Si `MediaSourceRef` est un fichier local ou base64 : `{"inlineData": {"mimeType": mime, "data": b64_data}}`.
- Prise en charge native complète : JPEG, PNG, WEBP, MP3, WAV, AAC, MP4, MOV.

#### 2. OpenAI (`openai_responses_mapping.py`)
- **Images** : Format standard Vision :
  `{"type": "image_url", "image_url": {"url": url_or_data_uri}}`.
- **Audio** (ex: GPT-4o Audio / GPT Realtime) :
  `{"type": "input_audio", "input_audio": {"data": b64_data, "format": "wav" | "mp3"}}`.
- **Vidéo** : OpenAI ne supportant pas la vidéo directe en entrée de chat standard, lever `unsupported_capability`.

#### 3. Anthropic Claude (`anthropic_messages_mapping.py`)
- **Images** : Claude accepte les images en base64 :
  `{"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64_data}}`.
- **Audio / Vidéo** : Non supportés nativement dans l'API Messages standard. Détection et levée de `unsupported_capability`.

#### 4. xAI Grok (`xai_responses_mapping.py`)
- **Images** : Compatible format image OpenAI (`image_url`).
- **Audio / Vidéo** : Non supportés.

#### 5. Mistral (`mistral_chat_mapping.py`)
- **Images** : Modèles Pixtral (ex: `pixtral-12b`) supportant `{"type": "image_url", "image_url": "..."}`.

#### 6. Ollama (`ollama_adapter.py`)
- **Images** : Champ `images` natif (liste de chaînes base64) sur les modèles multimodaux (ex: `llama3.2-vision`).

---

### Pilier 3 : Interface CLI & Ergonomie Utilisateur (`adapters/cli`)

#### A. Nouvelles options de commande
Extension des commandes `pyllmkit run` et `pyllmkit stream` :
```python
@run_app.command()
def run(
    prompt: str = typer.Argument(..., help="Prompt textuel initial"),
    image: list[Path] = typer.Option(None, "--image", "-i", help="Chemin(s) d'image(s) ou URL à attacher"),
    audio: Optional[Path] = typer.Option(None, "--audio", "-a", help="Fichier audio (WAV, MP3, etc.) à attacher"),
    video: Optional[Path] = typer.Option(None, "--video", "-v", help="Fichier vidéo (MP4, MOV, etc.) à attacher"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    live: bool = typer.Option(False, "--live"),
)
```

#### B. Pipeline de matérialisation des médias (Couche CLI)
1. **Validation d'existence et taille** : Vérifier que les fichiers existent et respectent des limites saines (ex: max 20 Mo par image/audio, max 100 Mo par vidéo).
2. **Détection du type MIME** : Détermination via `mimetypes.guess_type` avec replis standards.
3. **Encapsulation dans le domaine** :
   - Création des `ImageContent`, `AudioContent`, `VideoContent`.
   - Assemblage ordonné dans le `Content` du `Message(Role.USER, ...)`.

#### C. Affichage et traçabilité
- **Panneau de réponse** : Affichage des vignettes / chemins des fichiers multimédias attachés.
- **Statistiques** : Ligne explicite `Modalités : text, image (2), audio (1)`.
- **Stockage SQLite (`history.db`)** : Stockage des métadonnées de média (chemins, tailles, types MIME) sans alourdir la base avec les binaires bruts.

---

### Pilier 4 : FinOps & Tarification Multimodale

Le catalogue [`models_catalog.json`](../../src/pyllmkit/adapters/cli/data/models_catalog.json) est déjà prêt à accueillir cette tarification :
- Prise en compte des tarifs spécifiques lorsque le fournisseur décompte des tokens audio ou image distincts (ex: grille `pricing_modalities` avec `audio` input/output et `image` input).
- Calcul transparent dans `compute_run_cost` pour refléter fidèlement le coût des requêtes multimédias.

---

## 4. Matrice de Compatibilité par Fournisseur

| Fournisseur | Texte | Images (JPEG/PNG/WEBP) | Audio (WAV/MP3) | Vidéo (MP4/MOV) | Format Transport |
|---|---|---|---|---|---|
| **Google Gemini** | Supporté | Supporté | Supporté | Supporté | `inlineData` / `fileData` |
| **OpenAI** | Supporté | Supporté | Supporté | Non supporté | `image_url` / `input_audio` |
| **Anthropic** | Supporté | Supporté | Non supporté | Non supporté | `type: image, base64` |
| **xAI Grok** | Supporté | Supporté | Non supporté | Non supporté | `image_url` |
| **Mistral** | Supporté | Supporté (Pixtral) | Non supporté | Non supporté | `image_url` |
| **Ollama** | Supporté | Supporté (Vision) | Non supporté | Non supporté | `images: [base64]` |

---

## 5. Stratégie de Qualification et Règles de Sécurité

1. **Sécurité SSRF et isolation réseau** :
   - Aucun appel réseau déclenché par la couche domaine.
   - Les tests de domaine et de sérialisation s'exécutent entièrement hors ligne (offline).
2. **Tests d'invariants et cas négatifs** :
   - Rejet des sources vides, types de fichiers non reconnus ou médias corrompus.
   - Vérification du comportement en cas de dépassement de quota ou rejet provider (`unsupported_capability`).
3. **Maintien des seuils de qualité** :
   - Couverture de test globale strictement supérieure à **95.00 %** avec rapport de couverture.
   - Zéro dépendance tierce ajoutée dans `pyproject.toml`.

---

## 6. Prochaines Étapes Opérationnelles

1. **Phase 1 : Domaine** :
   - Créer `src/pyllmkit/domain/interactions/audio.py` et `video.py`.
   - Étendre `MediaSourceRef` (`kind="file"`, `kind="data"`).
   - Mettre à jour `serialization.py` et écrire les tests unitaires associés dans `tests/unit/domain/interactions/`.
2. **Phase 2 : Adaptateurs d'Inférence** :
   - Implémenter le dispatch multimodal dans les 6 adaptateurs.
   - Écrire les tests de mapping et de conformité (`test_p7_*`).
3. **Phase 3 : CLI & Persistance** :
   - Ajouter les options `--image`, `--audio`, `--video` dans `run` et `stream`.
   - Tester l'enregistrement dans SQLite et l'affichage dans les panneaux Rich.
4. **Phase 4 : Documentation & Changelog** :
   - Documenter les exemples multimodaux dans `docs/` et préparer la note de version.

