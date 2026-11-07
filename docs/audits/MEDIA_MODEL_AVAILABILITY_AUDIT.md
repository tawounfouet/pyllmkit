# PyLLMKit - M0 - Audit de disponibilité des modèles génératifs et remédiation de sécurité

> Date de revue : 2026-11-07
> Référence initiale : `main@99b5f7b32cc196f0890e272c8d6d52208097b57f`
> PR de remédiation : [#112](https://github.com/tawounfouet/pyllmkit/pull/112)
> Portée : modèles de **sortie strictement image, vidéo, audio** du catalogue JSON ; contrôles média, CLI, prix, tests hors ligne
> Décision : **GO sous réserve des gates CI exact-SHA** pour les corrections offline de M0 ; **NO-GO** pour certification provider-live / production / publication PyPI

## 1. Résumé exécutif

Le catalogue embarqué comptait **153 modèles** au point de départ. Un modèle vidéo documenté a été ajouté, portant l'inventaire à **154 références**, dont **23 références exclusivement médias** (à la différence des modèles mixtes texte + audio, non évalués ici comme produits média). L'état `AVAILABLE` d'un déploiement interne signifie *déclaré au catalogue*, pas *confirmé en temps réel chez le fournisseur*.

Le point critique était la coexistence de références retirées, de prix historiques et d'un routage `--live` qui pouvait transmettre des clés API avant de constater l'indisponibilité. Le correctif M0 introduit une politique de cycle de vie **par identifiant natif exact**, avec statut, source officielle, éventuelle date de coupure et candidat de migration. Les modèles retirés et un alias non vérifié sont refusés **avant consultation des credentials et avant réseau**, dans la CLI et directement dans les adaptateurs OpenAI, Google et xAI. Les modes mock demeurent utilisables pour les tests historiques.

### Définition des statuts

| Statut | Signification | Politique live |
|---|---|---|
| `current` | Identifiant documenté dans une source fournisseur datée | Éligible sous réserve des accès, sécurité et budgets |
| `deprecated` | Retrait annoncé à venir | Avertissement, puis refus automatique à l'échéance |
| `retired` | Retrait passé / annoncé effectif | Refus avant secrets et réseau |
| `unverified` | Alias non confirmé comme identifiant API natif | Refus avant secrets et réseau |
| `unknown` | Pas de preuve suffisante pour établir un statut | Non certifié : conserver la compatibilité, ne pas supposer la disponibilité |

La politique protège contre **les IDs connus à risque**, pas contre tous les IDs inventés. Pour une sécurité strictement basée sur une allowlist de modèles, une qualification de comptes et de capacités est nécessaire au jalon ultérieur.

## 2. Inventaire des 23 modèles de génération

**Légende :** `retired` et `deprecated` s'appuient sur les annonces de retrait fournisseur ; `unknown` signifie seulement que le statut public n'a pas été confirmé pendant l'audit. Aucun prix inconnu ne devient zéro. Les unités de tarif et la facturation réelle dépendent du fournisseur, de la résolution et parfois du canal de distribution.

| Catégorie | ID dans le catalogue | Provider | État au 2026-11-07 | Commentaire M0 |
|---|---|---|---|---|
| Image | `dall-e-2` | OpenAI | retired | Arrêt API 2026-05-12, prix obsolète neutralisé |
| Image | `dall-e-3` | OpenAI | retired | Arrêt API 2026-05-12, prix obsolète neutralisé |
| Image | `gpt-image-1-mini` | OpenAI | deprecated | Retrait annoncé 2026-12-01 |
| Image | `gpt-image-1.5` | OpenAI | deprecated | Retrait annoncé 2026-12-01 |
| Image | `gpt-image-2` | OpenAI | current | Nouveau défaut image, prix laissé inconnu tant que configuration insuffisante |
| Image | `imagen-3` | Google | retired | Modèle natif Imagen 3 retiré, tarif obsolète neutralisé |
| Image | `gemini-2.5-flash-image` | Google | retired | Retrait 2026-10-02, tarif obsolète neutralisé |
| Image | `gemini-3.1-flash-image` | Google | current | Modèle image actuel candidat de remplacement |
| Image | `gemini-3-pro-image` | Google | current | Modèle image documenté, vérifier droits et coûts |
| Image | `gemini-nano-banana-2.1` | Google | unverified | Nom catalogue non confirmé comme ID API ; refus live |
| Image | `grok-imagine-image` | xAI | current | API d'image documentée |
| Image | `grok-imagine-image-2.0` | xAI | current | Identifiant de génération d'image documenté |
| Audio | `tts-1` | OpenAI | deprecated | Arrêt 2027-01-06 |
| Audio | `tts-1-hd` | OpenAI | deprecated | Arrêt 2027-01-06 |
| Audio | `gpt-4o-mini-tts` | OpenAI | deprecated | Arrêt 2027-01-06 ; défaut audio provisoire, avertissement live |
| Audio | `gemini-2.5-flash-preview-tts` | Google | unknown | Ancien preview conservé, date de fin non établie |
| Audio | `gemini-3.8-flash-tts` | Google | current | Référence TTS officielle à qualifier pour l'adaptateur |
| Vidéo | `veo-2` | Google | retired | Fin d'endpoint 2026-06-30, prix neutralisé |
| Vidéo | `veo-3.1-lite-generate-preview` | Google | current | Nouvel ID catalogue ; tarif dépend de sortie et résolution, non chiffré |
| Vidéo | `gemini-omni-1.1-flash` | Google | current | Version publiquement documentée |
| Vidéo | `gemini-omni-1.2-flash` | Google | unknown | Historique du projet : tests live revendiqués ; ID absent de documentation publique trouvée |
| Vidéo | `grok-imagine-video` | xAI | current | API vidéo documentée |
| Vidéo | `grok-imagine-video-1.5` | xAI | current | Version documentée, disponibilité selon accès |

**Hors inventaire des 23 :** `imagen-4`, `veo-3`, `gpt-image-1` et `grok-imagine-image-quality` ne figurent pas dans la liste des 23 sorties média étudiées mais sont inclus dans la politique préventive, car des utilisateurs pourraient encore les appeler via des extensions/découvertes.

### Sources primaires consultées

- OpenAI - [dépréciations API](https://developers.openai.com/api/docs/deprecations) et [modèles API](https://developers.openai.com/api/docs/models/gpt-image-2). Retraits DALL-E 2/3 au 2026-05-12 ; modèles GPT Image 1 Mini/1.5 au 2026-12-01 ; `tts-1`, `tts-1-hd` et `gpt-4o-mini-tts` au 2027-01-06.
- OpenAI - [synthèse vocale](https://developers.openai.com/api/docs/guides/text-to-speech). Un modèle Realtime **ne se substitue pas** à un modèle `/v1/audio/speech` en changeant son ID.
- Google Gemini - [dépréciations](https://ai.google.dev/gemini-api/docs/deprecations), [modèles](https://ai.google.dev/gemini-api/docs/models), [Veo et tarifs](https://ai.google.dev/gemini-api/docs/pricing), [Gemini Omni](https://ai.google.dev/gemini-api/docs/models/gemini-omni-flash).
- xAI - [modèles](https://docs.x.ai/developers/models) et [migration d'alias image](https://docs.x.ai/developers/migration/imagine-image-quality-nov-2).

Les pages publiques établissent les notices générales, **pas les permissions d'un compte donné**. Les annonces peuvent évoluer ; la synchronisation automatique et l'historisation des statuts sont des travaux M1.

## 3. Corrections et preuves techniques

| Contrôle | État du code M0 | Vérification offline |
|---|---|---|
| Retrait connu | Fonction `require_live_media_model` appelée dans trois adaptateurs avant `resolve_secret` | Tests refus sans accès DNS/HTTP |
| IDs non natifs connus | `gemini-nano-banana-2.1` : refus explicite `model_unverified` | Test CLI sans réseau |
| Coupures futures | `media_model_policy(..., on_date=...)` et passage en retired à la date de fin | Tests des seuils 2026-12-01 et 2027-01-06 |
| Compatibilité | Les anciens ID demeurent utilisables en `--mock` | Scénario de démonstration historique |
| Pricing | `null` pour cinq prix retirés ; estimateur retourne inconnu `(None, "-")` | Tests des coûts historiques |
| Nouveau Veo | ID `veo-3.1-lite-generate-preview` référencé, coût au réel non inventé | Tests d'encodage et routage mock/provider simulé |
| CLI | Nouveau `models lifecycle`, statut et source dans `models inspect` | Test CLI hors réseau |
| Corps média JSON | Plafond de 24 MiB dans `media_http.http_bytes`, avant création du transport | Test négatif faux HTTP/DNS |
| Maintien des seuils | Ruff, mypy, pytest, conformance, build sur 3.11/3.12/3.13 | CI exact-SHA PR et main requises |

Les travaux M0 complètent le durcissement réseau déjà livré par la [PR #111](https://github.com/tawounfouet/pyllmkit/pull/111) et ne prétendent pas recertifier les transports `httpx` historiques.

## 4. Décisions et arbitrages

**M0-DEC-01.** Ne pas supprimer les anciens IDs des fichiers de simulation ou historiques ; la validité de l'archive ne prouve pas la disponibilité live.

**M0-DEC-02.** Refuser les ID retirés et explicitement non confirmés avant lecture des secrets, avec refus explicite. Ne pas router silencieusement vers un modèle potentiellement payant différent.

**M0-DEC-03.** `generate image` utilise désormais `gpt-image-2` en défaut. **Impact tarifaire potentiel** : le modèle choisi et son coût changent ; aucune génération payante n'a été lancée pour cette étude.

**M0-DEC-04.** L'ancien défaut `gpt-4o-mini-tts` est conservé avec un avertissement. La migration vers Realtime doit passer par **un nouvel adaptateur et contrat de transport**, et non une substitution d'identifiant. Échéance de retrait : 2027-01-06.

**M0-DEC-05.** Les prix de génération avec dénominateurs complexes (résolution, secondes, audio, qualité, canal de distribution) demeurent `null` si le modèle actuel `image/second/character` ne permet pas de faire un devis vérifiable.

**M0-DEC-06.** `gemini-omni-1.2-flash` est gardé pour compatibilité avec les essais live revendiqués par l'historique du dépôt, mais **la documentation publique consultée ne suffit pas à prouver l'ID ni son accès actuel**. Ne pas le classifier comme officiellement disponible sans test de découverte autorisé.

## 5. Sécurité - état et risques résiduels

| Risque | État M0 | Action ultérieure |
|---|---|---|
| Appel live d'un modèle retiré avec secrets | Corrigé pour IDs explicitement listés | Contrat d'allowlist/version fournisseur |
| Prix obsolète pour un modèle retiré | Corrigé dans l'estimateur et cinq entrées | Pricing v2 avec provenance, validité et unités |
| Corps JSON média trop volumineux | Rejeté avant réseau, limite 24 MiB | Test de charge et budgets mémoire |
| SSRF via téléchargements fournisseur | Garde-fous PR #111 conservés | Audit egress des transports `httpx` restants |
| Dérive d'ID de modèle ou accès compte | **Non certifié** sans découverte réelle | Vérification opt-in sans dépense, dossier d'évidence |
| Gestion des quotas, des coûts et annulation | **Non qualifiée live** | [P7-L7.8 #81](https://github.com/tawounfouet/pyllmkit/issues/81) |
| Provider-live : disponibilité, TLS réel, CDN | **Non certifiée** par tests synthétiques | Canaris opt-in, budgets validés, sans secrets en logs |
| Distribution et source taguée | `v0.3.0` historique inchangé | Nouvelle version seulement après autorisation distincte |

L'issue [#81](https://github.com/tawounfouet/pyllmkit/issues/81) demeure ouverte. Les tests hors ligne n'apportent pas de preuve de coût facturé ni de sûreté complète d'exploitation.

## 6. Définition de clôture M0

**GO technique M0** si, pour le commit final de la PR #112 et le commit fusionné sur `main`, les trois jobs Python 3.11/3.12/3.13 sont verts, avec Ruff, mypy strict, pytest, gates de conformité, packaging, tests de sécurité négatifs et GitGuardian ; la source des IDs est documentée et les prix obsolètes ne sont pas affichés.

**NO-GO opérationnel** pour toute déclaration `provider-live ready`, `production certified`, nouvelle release GitHub ou publication PyPI sans travaux P7-L7.8 et approbation spécifique.

### Suites proposées

1. **M0 reliquat / P7-L7.8** : qualification des transports `httpx` restants, budgets avant appels réels, tests d'annulation et observabilité.
2. **M1** : catalogue multimodal avec `ModelLifecycle`, `ModelOffer`, preuves, dates, aliases vérifiés et découverte active (plutôt qu'un dictionnaire statique par type de sortie).
3. **M2** : devis FinOps versionnés, unités composites, validité et prix par fournisseur/canal.
4. **M3-M4** : migration OpenAI Realtime TTS, nouvelles API musique/voix, Veo Lite et agrégateurs avec tests de contrat et budgets.

## 7. Traçabilité

- Roadmap produit : `PYLLMKIT_MULTIMODAL_MODELS_PRICING_ROADMAP_2026-11-07.md` (document de planification ; aucune publication Git correspondante présumée).
- Étude amont : `PYLLMKIT_BENCHMARK_GENERATIVE_MEDIA_API_PRICING_2026-11-07.md`.
- Code de base : `main@99b5f7b32cc196f0890e272c8d6d52208097b57f`.
- Réparation multimodale précédente : [PR #111](https://github.com/tawounfouet/pyllmkit/pull/111), [CI main #42339768357](https://github.com/tawounfouet/pyllmkit/actions/runs/42339768357).
- M0 : [PR #112](https://github.com/tawounfouet/pyllmkit/pull/112), voir ses checks pour la CI exacte de la livraison.

Date de statut, hypothèses et accès réels doivent être revalidés avant de transformer cette photographie du marché en contrats de disponibilité permanents.
