# Changelog

## [Unreleased] - Support Multimodal Universel (Entrée & Génération de Médias)

### M1 - Catalogue multimodal v2 et découverte déterministe (2026-11-07)

- Fichier `media_catalog_v2.json` validé (23 routes), provenance datée, propriétaires du modèle / fournisseur d'API / acteur facturant séparés et capacités inconnues explicites.
- Contrats typés `MediaCatalog`, `MediaModelDescriptor`, `CapabilityMatrix`, résolution d'alias non ambiguë, lecture statique et merge non destructif.
- Snapshots de découverte `discovered_models_v2.json` versionnés, privés et atomiques, clés qualifiées par fournisseur, observations non exhaustives sans preuve d'accessibilité.
- Découverte réseau limitée aux endpoints prédéfinis ; compatibilité de cache v1 conservée avec correction des collisions entre fournisseurs.
- CLI `models list --media`, `models availability [--json]`, `models diff [--against PATH] [--json]` ; `models inspect` enrichi, `models sync` conserve son consentement explicite.
- [ADR M1](docs/architecture/ADR-M1-VERSIONED-MEDIA-CATALOG.md), tests hermétiques de schéma, ambiguïtés, migration, historique et comparaisons.


### M0 - Catalogue média et sécurité des dépréciations (2026-11-07)

- Audit source des 23 modèles strictement médias, avec statuts `current`, `deprecated`, `retired`, `unverified` et `unknown` : [rapport M0](docs/audits/MEDIA_MODEL_AVAILABILITY_AUDIT.md).
- Refus `model_retired` / `model_unverified` avant credentials et réseau, aussi dans les adaptateurs. Simulation historique conservée.
- Défaut image `gpt-image-2` ; défaut TTS historique `gpt-4o-mini-tts` maintenu avec avertissement et migration Realtime encore requise avant 2027-01-06.
- Prix d'anciens modèles retirés supprimés des estimations opérationnelles ; nouveau Veo 3.1 Lite sans prix forfaitaire inventé.
- Limite de 24 MiB pour les corps JSON média sortants, CI et tests de non-régression renforcés.

### 1. Compréhension Multimodale en Entrée (Input: Images, Audio, Vidéo)
- **Domaine `interactions`** :
  - Ajout des types de valeur immuables `AudioContent` et `VideoContent` (héritant de `ContentPart`) avec modality et format canoniques.
  - Évolution passive de `MediaSourceRef` pour supporter `kind in {"uri", "asset", "file", "data"}` avec validation syntaxique stricte (RFC 2397 pour data URI) et zéro E/S réseau au niveau du domaine.
  - Codec de sérialisation JSON v1 étendu pour `audio` et `video` avec aller-retour déterministe garanti.
- **Adaptateurs d'inférence (`adapters/inference`)** :
  - Déverrouillage multimodal et projection native vers les structures de transport respectives :
    - **Google Gemini** : support complet Images, Audio et Vidéo (`inlineData` / `fileData`).
    - **OpenAI** : support Images (`input_image`) et Audio (`input_audio`) ; rejet explicite Vidéo (`unsupported_capability`).
    - **Anthropic Claude** : support Images (base64 `media_type`) ; rejet Audio/Vidéo (`unsupported_capability`).
    - **xAI Grok & Mistral** : support Images (`image_url`) ; rejet Audio/Vidéo (`unsupported_capability`).
    - **Ollama** : support Images (base64 dans `images: []`) ; rejet Audio/Vidéo (`unsupported_capability`).
  - Filtrage des modalités par déploiement et rejet `unsupported_input_modality` conforme aux contrats M1/P7.
  - Helper d'infrastructure passif `media_mapping.py` sans dépendance externe (`dependencies = []`).
- **CLI (`run`, `stream`) & Expérience Utilisateur** :
  - Nouveaux drapeaux `--image` (`-i`), `--audio` (`-a`), `--video` (`-v`) sur `pyllmkit run` et `pyllmkit stream`.
  - Résolution des entrées (fichiers locaux, URLs HTTP/HTTPS, Data URIs base64). Mise à jour corrective : fichiers locaux limités à 16 MiB et requêtes média encodées limitées à 24 MiB, au lieu de 100 Mo d'entrée acceptés à tort.
  - Panneaux Rich : affichage explicite de la ligne `Modalités : text, image, audio, video` dans les métriques d'exécution.
  - Persistance ChatML : traçabilité des pièces jointes multimédias dans `history.db` pour fine-tuning et audit FinOps.

### 2. Génération Multimodale en Sortie (Output: Text-to-Image, Text-to-Audio/TTS, Text-to-Video)
- **Domaine `inference`** :
  - Nouvelles entités immuables `ImageOutput`, `AudioOutput`, `VideoOutput` et `MultiPartOutput` (composites) implémentant `InferenceOutput`.
  - Extension de `Usage` avec métriques non-tokens : `input_characters`, `output_media_units` (ex: décompte d'images), `output_media_seconds` (durée audio/vidéo).
  - Codec de sérialisation canonique v2 avec aller-retour sans perte pour toutes les variantes multimédias et structures de données passives `MediaSourceRef`.
  - Résolution dynamique des modalités dans `service.py` pour supporter automatiquement les modèles générateurs d'images, de voix et de vidéos.
- **Catalogue & FinOps Non-Tokens** :
  - Intégration des modèles génératifs de référence dans `models_catalog.json` : `dall-e-3`, `dall-e-2`, `tts-1`, `tts-1-hd`, `imagen-3`, `veo-2`.
  - Extension du calculateur `compute_run_cost` pour tarifer avec exactitude à l'unité (`unit == "image"`), au volume de caractères (`unit == "1M characters"`), ou à la durée (`unit == "second"`).
- **CLI & Matérialisation sur Disque (`media_saver.py`, `generate.py`)** :
  - Nouveau module d'écriture `media_saver.py` pour les Data URIs et fichiers locaux. Les téléchargements d'URL distantes arbitraires sont désormais refusés dans le saver ; les adaptateurs fournisseurs matérialisent au préalable les URLs approuvées.
  - Module `mock_assets.py` : génération en pur Python (zéro dépendance) de fichiers de simulation valides et lisibles dans Aperçu, QuickTime et Music (vrai PNG 24-bit 256x256, vrai WAV PCM 16-bit 22kHz 2.0s, conteneur MP4 H.264 2.0s).
  - Adaptateur live `OpenAIMediaAdapter` et `CompositeOpenAIAdapter` pour la génération réelle en direct avec OpenAI (`/v1/images/generations` pour DALL-E 3 et `/v1/audio/speech` pour TTS) via l'option `--live`.
  - Option universelle `-o / --output-file` sur `pyllmkit run` pour enregistrer directement le média généré sur disque.
  - Prise en charge de la configuration `storage.assets_dir` dans `.pyllmkit.yaml` (et variable d'environnement `PYLLMKIT_ASSETS_DIR`).
  - Sauvegarde automatique par défaut dans `assets/<catégorie>/<modèle>_<timestamp>_<run_id>.<ext>` lorsque `--out / -o` n'est pas spécifié :
    - `assets/images/` pour les images (`.png`, `.jpg`, `.webp`)
    - `assets/audios/` pour les audios vocaux (`.wav`, `.mp3`, `.ogg`)
    - `assets/videos/` pour les vidéos (`.mp4`)
    - `assets/documents/` pour les documents ou textes
  - Nouvelle sous-commande dédiée `pyllmkit generate` avec 3 déclinaisons :
    - `pyllmkit generate image <prompt> --model dall-e-3 [--out <path>] --size 1024x1024 --quality standard [--live]`
    - `pyllmkit generate audio <prompt> --model tts-1 [--out <path>] --voice alloy [--live]`
    - `pyllmkit generate video <prompt> --model veo-2 [--out <path>] [--live]`
  - Panneaux Rich dédiés avec métadonnées spécifiques et statut clair `Fournisseur : <nom> (simulation)` vs `Fournisseur : <nom>`.

### 2bis. Correctifs de la génération live (`pyllmkit generate ... --live`)
- **Diagnostic** : `dall-e-3`, `dall-e-2`, `imagen-3` et `veo-2` ne sont plus exposés par les API avec les clés du projet (`The model 'dall-e-3' does not exist`, Imagen/Veo absents de `models.list` Gemini). Les valeurs par défaut de `generate` échouaient donc systématiquement, et l'erreur était masquée derrière un `provider_protocol_error` sans détail.
- **Nouveaux modèles par défaut** (vérifiés en live le 2026-11-07) : `generate image` → `gpt-image-1-mini`, `generate audio` → `gpt-4o-mini-tts`, `generate video` → `grok-imagine-video`.
- **Catalogue** : ajout de `gpt-image-1-mini`, `gpt-image-1.5`, `gpt-image-2`, `gpt-4o-mini-tts`, `gemini-2.5-flash-image`, `gemini-3.1-flash-image`, `gemini-3-pro-image`, `gemini-nano-banana-2.1`, `gemini-2.5-flash-preview-tts`, `gemini-3.8-flash-tts`, `grok-imagine-image`, `grok-imagine-image-2.0`, `grok-imagine-video`, `grok-imagine-video-1.5`. Prix laissés inconnus (`null`) faute de source vérifiée. Les entrées historiques restent utilisables en simulation.
- **Routage** : `MediaRoutingAdapter` remplace `CompositeOpenAIAdapter` (alias conservé) et choisit l'adaptateur média selon les **modalités de sortie déclarées** du déploiement, et non plus selon des sous-chaînes du nom (`"dall-e"`, `"tts"`). Il est branché pour OpenAI, Google et xAI.
- **Nouveaux adaptateurs live** (stdlib uniquement, `dependencies = []`) :
  - `GoogleMediaAdapter` : images Gemini (`generateContent`, `responseModalities` IMAGE, `imageConfig`), TTS Gemini (PCM L16 24 kHz encapsulé en WAV), Imagen (`:predict`) et Veo (`:predictLongRunning` + polling), ces deux derniers si la clé y a accès.
  - `XAIMediaAdapter` : `grok-imagine-image` (`/v1/images/generations`) et `grok-imagine-video` (job `request_id`, polling `/v1/videos/{id}`, téléchargement immédiat du MP4 temporaire).
  - `OpenAIMediaAdapter` réécrit : prise en charge de `gpt-image-*` (sans `response_format`), dimensions réelles lues dans l'en-tête PNG/JPEG, MIME `audio/mpeg` standard, `instructions` pour `gpt-4o-mini-tts`.
- **Options CLI enfin transmises** : `--size`, `--quality`, `--voice` étaient ignorées (valeurs codées en dur). Ajout de `--aspect-ratio`, `--resolution`, `--instructions`, `--duration`, `--poll-timeout`, `--timeout` et `--record-content`.
- **Prompt** : seuls les messages `user` alimentent le prompt média. Auparavant le premier texte trouvé était utilisé, donc le `system_prompt` de la configuration avec `pyllmkit run`.
- **Erreurs explicites** : codes `model_not_found`, `content_filtered`, `rate_limited`, `permission_denied`... et ligne `Détails` reprenant le message du fournisseur, assaini (secrets masqués, 400 caractères max) via `MediaDiagnostics`.
- **Garde-fou** : `generate image -m veo-2` (modèle ne produisant pas le type demandé) est refusé avant tout appel réseau.
- **Vidéo Google** : Veo 3.1 preview est arrêté depuis le 2026-10-22 (doc officielle `ai.google.dev/gemini-api/docs/veo`). Ajout de `gemini-omni-1.2-flash` et `gemini-omni-1.1-flash` via l'Interactions API (`POST /v1beta/interactions`, `response_format.type = "video"`, réponse synchrone, MP4 base64 dans `steps[].content[]`), avec `--duration` (3 à 15 s), `--resolution` (360p à 4k) et `--aspect-ratio` (16:9, 9:16). Un `veo-*` introuvable suggère désormais `gemini-omni-1.2-flash`.
- **FinOps** : `compute_run_cost` n'invente plus de quantité inconnue (auparavant 1 image ou 5 s de vidéo par défaut), et `runs list` / `runs inspect` n'estiment plus de coût pour un run échoué ou simulé (ex. `$0.75` affiché sur des `veo-2` en 404).
- **Historique** : les runs `generate` sont tracés dans `history.db` (`mode = "generate"`, metadata-only, prompt seulement avec `--record-content`).

### 3. Qualification & Intégrité Globale
- **3 008 tests** constatés au commit initial multimodal (état historique, avant durcissement). Les chiffres actualisés et le SHA de référence sont consignés ci-dessous.
- **Couverture de branches globale : 92 %** (`pytest --cov=pyllmkit --cov-branch`). Les gates CI par module sont inchangés.
- Génération live validée le 2026-11-07 : `gpt-image-1-mini`, `gpt-4o-mini-tts`, `gemini-2.5-flash-image`, `gemini-2.5-flash-preview-tts`, `grok-imagine-image`, `grok-imagine-video`, `gemini-omni-1.2-flash`.
- **Zéro dépendance d'exécution ajoutée** (`dependencies = []`).
- **Règle typographique stricte** : aucun tiret cadratin U+2014, standard ASCII U+002D exclusif.

### 4. Correctifs de qualification et de sécurité post-multimodale (branche main, non taguée)

- **Réparation des gates CI** : scénarios multimodaux ajoutés aux tests de couverture ciblés des six fournisseurs, tests de rejet Gemini, couverture partagée du transport cloud ; seuils de couverture inchangés.
- **Transport media** : taille des réponses API limitée à 160 MiB, taille des téléchargements de médias et Data URIs limitée à 100 MiB, corps d'erreur lu sur 8 KiB maximum, exceptions inattendues assainies.
- **Réseau** : authentification vers des origines HTTPS explicitement autorisées, refus des proxies et redirections, résolution DNS publique et connexion TLS vers une IP validée, avec SNI/contrôle du certificat du nom d'origine. Les URLs de médias sortants non approuvées échouent volontairement, notamment sur CDN inconnu.
- **Fichiers** : téléchargement direct d'URLs interdit au saver CLI, décodage base64 strict, tailles bornées, préfixes de noms de fichier assainis.
- **Requêtes multimodales** : limites différenciées de 1 MiB pour le texte, 24 MiB pour le corps encodé image/audio/vidéo, et 16 MiB pour chaque fichier local. Ce dernier plafond remplace le plafond CLI antérieur de 100 Mo : **changement de compatibilité intentionnel**.
- **Confidentialité** : plus de message brut d'exception imprévue dans `generate`.
- **Qualification observée** : [CI #42339308625](https://github.com/tawounfouet/pyllmkit/actions/runs/42339308625), SHA `6861e0fd89606c4b4e7eee58fee9bf2709f0bb94`, **3 047 pytest PASS, 752 conformance PASS par Python 3.11/3.12/3.13**, Ruff, mypy strict et wheel/sdist. Une nouvelle CI sera exigée après ces notes.
- **Réserve** : cette campagne est **offline**. Pas de certification provider-live, ni de publication PyPI, ni de déplacement du tag `v0.3.0`. Voir [rapport de remédiation](docs/quality/2026-11-07_MULTIMODAL_SECURITY_AND_CI_REMEDIATION.md).

## [0.3.0] - 2026-11-07

### Version Git demandée par le mainteneur unique

- Version Python et CLI harmonisée à `0.3.0` ; tag Git demandé : `v0.3.0`.
- Socle indépendant des providers : modèles, artefacts, capacités, messages, requêtes/réponses d'inférence, outils descriptifs, sorties structurées, streaming et registry/discovery.
- Six adaptateurs natifs textuels : OpenAI, Anthropic, Google Gemini, xAI, Mistral et Ollama, avec inférence sync/async et streaming selon les restrictions effectives.
- CLI optionnel Typer/Rich : catalogue local, sélection, exécution mock par défaut, consentement `--live` invocation par invocation, historique SQLite metadata-only et vues FinOps.
- Confidentialité : `--record-content` par invocation, `--allow-content-export` pour JSONL, `runs purge-content --yes` pour expurgation logique, rétention opt-in.
- Tarification catalogue indicative, provenance locale affichée ; prix et limites absents conservés comme inconnus.
- Contrat `text_only_v1` et ADR-059 approuvés par le propriétaire pour le périmètre *offline* ; exceptions techniques documentées dans le dossier de jalon.
- Qualification déterministe : 2 825 tests pytest et 752 scénarios de conformité par version Python 3.11, 3.12 et 3.13 sur le socle validé, avec build wheel/sdist et vérifications depuis installation propre. Le SHA versionné doit être qualifié à nouveau avant création du tag.

### Compatibilité et restrictions

- Le passage de `0.1.0a2` à `0.3.0` matérialise un jalon de développement avant 1.0, pas une promesse de stabilité ABI définitive.
- Les scripts CLI comptant auparavant sur `defaults.live=True` doivent utiliser `--live` explicitement ; l'export sensible nécessite maintenant `--allow-content-export`.
- Les champs de prix/limites de catalogue peuvent être `None`, et les comptes de tokens partiels restent partiels.
- La qualification provider-live, DNS/peer-IP/TLS, SSRF/rebinding et budgets de coûts distants **n'est pas établie** ; le streaming synchrone réseau qui ne peut pas garantir son hard deadline reste fail-closed.
- Les 131 entrées du catalogue (15 catégories) ne sont pas 15 providers natifs exécutables.
- Les correctifs ne constituent ni audit de sécurité réseau réel ni certification de production.
- **Ce jalon autorise le tag Git demandé seulement**. Aucun déclenchement GitHub Release, TestPyPI, PyPI ou canari fournisseur n'est impliqué.

Voir [autorisation et périmètre du tag v0.3.0](docs/milestones/0.3.0/18_V030_TAG_SCOPE_AND_AUTHORIZATION_2026-11-07.md), [décision du mainteneur](docs/milestones/0.3.0/17_OWNER_SELF_ACCEPTANCE_AND_SCOPED_GATES_2026-11-07.md) et [compatibilité et migration](docs/milestones/0.3.0/16_COMPATIBILITY_AND_MIGRATION_PROPOSAL_2026-11-07.md).


## [Unreleased] - M6 Registry & Discovery technically qualified (no release)

- **GO technique avec réserves M6** pour Registry & Discovery hors réseau, PRs #59..#66 fusionnées, huit PV de gate G0..G7 archivés. Main code `6c58b052`, CI #42123870931 SUCCESS : 1189 tests, couverture branches 96,61 %, Python 3.11/3.12/3.13, Ruff, mypy et wheel/sdist avec exemples 23..28.
- Preuves archivées sur main `670ccab9`, CI #42124522939 SUCCESS ; rapport final `docs/quality/M6_GATE_REVIEW.md`, point d'entrée P7-G0 `docs/roadmap/P7_PROVIDER_ADAPTERS_ENTRY_CRITERIA.md`.
- Correctif de sûreté L6.6 : le digest SHA-256 lie les métadonnées complètes d'un batch à sa preview. Pas d'adapter live, de réseau ou de distribution.
- **NO-GO publication `0.1.0b2`** : version source `0.1.0a2` inchangée ; protection main, reviewer indépendant, release et frontières provider non clos (#22/#35/#36).


## [Unreleased] - Historique de la candidature P6 Registry & Discovery (désormais intégrée)

- Architecture ADR-039..048, provider/deployment descriptifs, registries, recherches typées, capacités et limites effectives, résolution déterministe.
- Offline Discovery & Merge : source statique, provenance UTC, conflit explicite, preview et commit atomique InMemory sous contrôle de version.
- Integration & Quality : tests P6-AC-001..056, exemples 23..28, architecture fitness, compatibilité M1-M5, clean wheel/sdist.
- Historique : les PRs #59..#66 étaient empilées avant qualification. Elles ont depuis été fusionnées et qualifiées sur main, sans changement de version ni publication. Réserves #22, #35 et #36 maintenues.

## [Unreleased] - M5 Streaming Domain technically qualified (no release)

- **GO technique avec réserves** pour Streaming hors réseau : [main@e733264c](https://github.com/tawounfouet/pyllmkit/commit/e733264cf914d1ada33dbd76df932102139533a4), [CI #42104049873](https://github.com/tawounfouet/pyllmkit/actions/runs/42104049873) SUCCESS (1048 tests cumulatifs, 96,08 % couverture avec branches, Python 3.11-3.13, Ruff, mypy, build et exemples wheel/sdist).
- P5-G0..G6 qualifiés, PRs #51 à #57 fusionnées. Neuf ADR-030..038, 48 AC, événements typés, ordre strict, ToolCallDelta raw, consommation sync/async, EOF/annulation, Streaming JSON v1 indépendant et exemples offline 18..22.
- [Revue finale M5](docs/quality/M5_GATE_REVIEW.md) et [PV G6](docs/quality/P5_G6_GATE_REVIEW.md) : domaine qualifié uniquement hors réseau ; aucun appel de modèle, executor ou transport provider.
- **NO-GO release / publication** : version toujours 0.1.0a2, cible 0.1.0b1 non publiée, issues #22/#35/#36 ouvertes, main non protégée et revue GitHub tierce absente.

## [Unreleased] - M4 Tooling & Structured Output technically qualified

- **GO technique avec réserves** pour le domaine hors ligne sur [main@92874b2e](https://github.com/tawounfouet/pyllmkit/commit/92874b2e97bcc130279e244bf1000c65a939d7e5), [CI #42093041970](https://github.com/tawounfouet/pyllmkit/actions/runs/42093041970) SUCCESS : 967 tests cumulatifs, 95,80 % global branch coverage, Python 3.11..3.13, Ruff et mypy strict.
- [M4_GATE_REVIEW.md](docs/quality/M4_GATE_REVIEW.md) : audit final indépendant des 14 causes obligatoires de NO-GO ; [P4_POST_IMPLEMENTATION_REVIEW.md](docs/quality/P4_POST_IMPLEMENTATION_REVIEW.md) : bilan de Phase 4.
- P4-G0..G5 GO techniques avec réserves, 40 recettes P4 tracées. L4.5 et seuil de couverture 95 % intégré via PRs #48 et #49.
- **Release NO-GO** : version source inchangée 0.1.0a2, issues #22/#35/#36 ouvertes, aucune publication/tag autorisée.


## [Unreleased] - Phase 4 Tooling & Structured Output (G5 qualified, M4 independently reviewed)

### Integrated on main (source only)
- P4-G0..G4 : ADR-022..029 acceptées, outils descriptifs non exécutables, ToolCall identity/results, validation de sorties structurées, composition séparée M3/P4 et codec Tooling JSON v1 strict.
- P4-G4 qualifié sur [main ab0257a0](https://github.com/tawounfouet/pyllmkit/commit/ab0257a0a9a08f2320b580340ba84c92609bbfc0), [CI #42089506022 SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42089506022), 954 tests cumulatifs et 96 % de couverture branches sur Python 3.11.
- Préparation L4.5 : documents d'architecture, traçabilité P4-AC-001..040, README, exemple 17, tests d'intégration et de packaging, precheck M4. **P4-G5 qualifié** après fusion [PR #48](https://github.com/tawounfouet/pyllmkit/pull/48) et [CI push/main #42092202193](https://github.com/tawounfouet/pyllmkit/actions/runs/42092202193) SUCCESS sur main@aad2656c (967 tests, 96 %, Python 3.11-3.13). **M4 est qualifié par la revue finale distincte, sans autorisation de diffusion.**
- Aucun SDK provider, exécuteur, Inference JSON v2, changement de version, tag, GitHub Release ou publication PyPI. Issues #22/#35/#36 ouvertes.


## [Unreleased] - M3 qualified domain source, not a release

### Qualification and governance
- Independent eleven-condition M3 GO/NO-GO review: **GO technique avec reserves for offline Inference Domain only** ([PV M3](docs/quality/M3_GATE_REVIEW.md)), baseline [main 4900523f](https://github.com/tawounfouet/pyllmkit/commit/4900523f8999b7c42fb184d44a9ccc090e56f26a), [CI #42069101048](https://github.com/tawounfouet/pyllmkit/actions/runs/42069101048), 802 tests / 95 % coverage, Python 3.11/3.12/3.13.
- Provider client/transport not shipped; main branch unprotected [#22](https://github.com/tawounfouet/pyllmkit/issues/22), independent human review still outstanding.
- Release `0.1.0a3` explicitly **NO-GO** until separate authorization, gate #22 evidence and release issue [#35](https://github.com/tawounfouet/pyllmkit/issues/35).
- Current metadata remains `0.1.0a2`; no version bump, tag, release, TestPyPI or PyPI upload.


### Post-Phase 3 operational closeout (documentation candidate, no release)
- Documented technical M3 final-review inputs, branch-protection governance and issue #22 evidence requirements.
- Defined separate version bump, build provenance, tag, GitHub Release and PyPI runbooks with explicit authorization and rollback.
- Specified future provider/HTTP boundary policies outside domain Value Objects: strict JSON text parsing, request limits, redaction, retries, idempotency and SSRF defense.
- Added repeatable PyKit learning/delivery workflow and PR review template.
- **No provider implementation, ruleset enforcement, version bump, tag or publication in this PR.**


## [Unreleased development] - L3.5 Integration & Packaging (G5 technical GO, not released)

### Integrated documentation and regression quality (pending G5 qualification)
- Harmonized README current gate status and runnable offline Inference Request/Response/Run JSON v1 walkthrough, P3-AC-030.
- Added consolidated `docs/api/inference.md`, Request/Response/Run conceptual guides, actual architecture contract diagram and JSON v1 schema guide.
- Added `PHASE_3_TRACEABILITY.md` linking all 30 P3 acceptance cases to tests, ADRs, PRs and qualified main CI.
- Added public root/subpackage import tests, release-metadata/license/typing tests, docs integrity checks and `examples/12_full_inference_walkthrough.py` smoke-tested from installed wheel/sdist.
- Resolved M2 PIR2-01/02/03 separately via [PR #31](https://github.com/tawounfouet/pyllmkit/pull/31), [main 2ec317de](https://github.com/tawounfouet/pyllmkit/commit/2ec317de98bd9d0897fe1e48801a9727e4f7ced6) and [CI #42057132634](https://github.com/tawounfouet/pyllmkit/actions/runs/42057132634) (789 tests, 95% coverage). Issue #20 completed.

**P3-G5 = GO technique avec reserves** sur [main 49cf26e](https://github.com/tawounfouet/pyllmkit/commit/49cf26e830819675a1c4cad9dfd2860fc977f0b6), [CI #42059417894 SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42059417894), 798 tests / 95 % coverage, Python 3.11/12/13, [PV G5](docs/quality/P3_G5_GATE_REVIEW.md). **M3 et release restent NON QUALIFIES.** Main protection issue #22 remains open. The repository still declares `0.1.0a2` and nothing has been tagged or published.


## [Unreleased development] - 0.1.0a3 Inference Primitives (G4 only, not released)

### Added (L3.4 - Inference JSON Codec & Quality)
- Strict independent INFERENCE_SCHEMA_VERSION=1: complete JSON-compatible dictionaries for InferenceRequest, InferenceResponse and all six InferenceRun snapshots.
- Exact required nullable keys; nested Interaction JSON v1 messages; canonical UTC timestamps; typed config, reason, usage and Run invariant validation.
- Negative schema and sanitized-error tests, P3-AC-021..028, six-state round-trips, offline example 11, clean wheel/sdist codec smoke tests and API guide.
- G4 qualification on [PR #29](https://github.com/tawounfouet/pyllmkit/pull/29), [main d72b1ce](https://github.com/tawounfouet/pyllmkit/commit/d72b1ce82a4a34c62888ad48b50bcf07537f83d1), [CI #42053906726](https://github.com/tawounfouet/pyllmkit/actions/runs/42053906726): **779 tests / 95 % coverage**, Python 3.11/3.12/3.13. [Gate report](docs/quality/P3_G4_GATE_REVIEW.md).

**Not implemented:** provider or network inference, streaming, HTTP parser duplicate-key policy, production release. Metadata remains 0.1.0a2.


## [Unreleased development] - 0.1.0a3 Inference Primitives (G3 only, not released)

### Added (L3.3 - Run Lifecycle Ready)
- Immutable `InferenceRun` Aggregate Root with six states, pure transitions, injected timezone-aware timestamps, terminal `finished_at`, RunId identity equality and strict snapshot invariants.
- `InferenceFailure` normalized snake_case codes and optional cancellation code, without native provider payload; response correlation checked during completion.
- P3-AC-014..020 and P3-AC-029, negative tests and reconstructed snapshot validation, offline example 10, public API docs and wheel/sdist smoke.
- G3 technical qualification: [PR #27](https://github.com/tawounfouet/pyllmkit/pull/27), [main 361791ff](https://github.com/tawounfouet/pyllmkit/commit/361791ff546612e10b407874c54014b1c0e1ce86), [CI #42044787119](https://github.com/tawounfouet/pyllmkit/actions/runs/42044787119), 679 tests, 94 % coverage and three Python versions. [G3 report](docs/quality/P3_G3_GATE_REVIEW.md).

**Still excluded:** real streaming, network/provider invocation, persistence, retry engine, event bus and Inference JSON v1 codec (L3.4). No version bump, tag or release.


## [Unreleased development] - 0.1.0a3 Inference Primitives (G2 only, not released)

### Added (L3.2 - Response Ready)
- Immutable InferenceRunId, TextOutput with explicit empty text, InferenceOutput conceptual alias, normalized FinishReasonCode and FinishReason with optional native provenance.
- Usage with five optional exact nonnegative counters, no inferred total or pricing, plus immutable InferenceResponse correlated by explicit RunId.
- Unit/negative and acceptance tests P3-AC-008..013, offline example 09, public API docs, updated architecture fitness checks and wheel/sdist smoke tests.
- G2 qualification based on [PR #25](https://github.com/tawounfouet/pyllmkit/pull/25), integrated main SHA 783aa4381dc05a4b9bc431faab282f2bbe37d38d, [CI #42039312011 SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42039312011): 545 tests, 94% coverage, three Python versions. [G2 gate report](docs/quality/P3_G2_GATE_REVIEW.md).

**Not yet in a3:** Run lifecycle, Inference JSON codec v1, tool execution, provider adapters, real streaming, HTTP, release or PyPI. Metadata stays 0.1.0a2.


## [Unreleased development] - 0.1.0a3 Inference Primitives (G1 only, not released)

### Added (L3.1 - Request Ready)
- Provider-free typed ModelTarget, DeploymentTarget, EndpointTarget and opaque Serving IDs.
- Immutable InferenceRequest for ordered Phase 2 Message values; strict GenerationConfig without provider-specific defaults.
- Explicit pure support evaluation from caller-supplied GenerationSupportSnapshot. Unknown remains unknown, known UNSUPPORTED is rejected (ADR-021 option A, P3-AC-007).
- Domain/root imports, offline acceptance tests P3-AC-001..007, Python 3.11-3.13 CI examples and clean wheel/sdist API smoke tests.
- G1 technical qualification based on main SHA f1ef04b8ff1bb52a1ee17defa0ec8b20f84ac9d3 and CI #42036557565: 432 tests, 93% coverage (Python 3.11). [G1 gate](docs/quality/P3_G1_GATE_REVIEW.md).

**Not implemented yet:** Response, Run, Inference JSON v1, tools, structured output, streaming, provider adapters and external invocation. Metadata stays 0.1.0a2 and no release is authorized.


All notable changes to PyLLMKit are tracked here. The metadata version does not imply external publication.

## [Unreleased] - 0.1.0a2 candidate

### Added (Phase 2)
- Canonical Role and immutable Message Value Object for provider-free text interactions (AC-006).
- Typed ordered ContentPart / TextContent / Content, with strict non-empty collections.
- Passive MediaSourceRef and ImageContent, preserving text/image/text ordering (AC-007).
- Independent Interaction JSON mapping schema v1 (ADR-012), with strict parsing, explicit version, and reversible text/image content including URI and asset references.
- G0/G1/G2 evidence, ADR-008 through ADR-013, L2.4 negative tests and offline examples.
- Python 3.11/3.12/3.13 CI checks, wheel/sdist Interaction API smoke tests.

### Compatibility and scope
- M1 Model and Artifact JSON codecs remain independent and unchanged.
- JSON input is a mapping; duplicate-key checks on raw JSON text are a caller/parser responsibility.
- URI validation is syntactic, not a security policy for fetching media.
- No provider adapters, Conversation aggregate, audio/video/document or tool execution.
- This is a **repository candidate only**: no Git tag, GitHub Release or PyPI publication. L2.4 G3 and integrated G4/M2 technical GO are qualified on `main` SHA `560d3a46c74cecebdf6a55301b2b8ca4e34331d4`. Publication remains a distinct, unapproved action.

## [Unreleased] - 0.1.0a1 candidate

### Added
- Provider-independent Model, ModelId, ModelIdentity, ModelFamily, ModelVersion, ModelVariant, ModelRevision and ModelArchitecture/ModelLimits value objects.
- Independent ModelArtifact entity and provider alias descriptor; identity-based equality and immutable snapshots.
- Capability, CapabilitySet, CapabilitySupport, typed constraints and explicit NATIVE/PARTIAL/EMULATED/UNSUPPORTED/UNKNOWN semantics.
- Input/output ModalitySet and distinct Modality descriptions.
- JSON-compatible Model/Artifact schema-v1 codecs with strict unknown-key rejection.
- Explicit `pyllmkit.domain` public imports and equivalent subpackage imports.
- Offline and negative architecture tests, acceptance traceability, branch coverage in CI.
- Python 3.11/3.12/3.13 lint/type/test/build matrix; clean wheel and sdist smoke installs.
- ADR-001 through ADR-007, MIT license and M1 qualification dossier.

### Constraints
- Effective provider/deployment capability resolution is not implemented.
- No registry, inference engine, provider adapters, streaming or tool execution.
- Schema-v1 read compatibility is one-way for older development snapshots.
- No GitHub release, git tag or PyPI publication as part of milestone qualification.
