# ADR M1 - Catalogue multimodal v2, découvertes et provenance

- Date : 2026-11-07
- Statut : **implémenté sur la PR #114, qualification CI requise**
- Dépendances : [audit M0](../audits/MEDIA_MODEL_AVAILABILITY_AUDIT.md), [sécurité média](../quality/2026-11-07_MULTIMODAL_SECURITY_AND_CI_REMEDIATION.md)
- Backlog : MEDIA-101 à MEDIA-107
- Architecture : catalogue typé côté adaptateur d'infrastructure, sans modifier les entités de domaine `Model`, `ModelIdentity`, `Deployment`, `ProviderId` et `ModalitySet`

## Décision

Conserver les entités DDD existantes comme source de vérité de l'inférence, puis introduire **un read model multimodal versionné** pour les informations et contrôles qui ne relèvent pas du domaine d'exécution : capacités spécifiques aux médias, route API native, identité de l'éditeur, identité de l'opérateur API, canal de déploiement, facturation, source et date de vérification.

Séparer strictement trois niveaux :

1. **Catalogue déclaré** : document local statique `media_catalog_v2.json`, versionné, vérifié au chargement, 23 références de génération image/audio/vidéo issues du M0. Une information absente est **inconnue**, jamais `False` ni `0 $` par défaut.
2. **Observation fournisseur** : cache `discovered_models_v2.json`, enrichi **uniquement sur invocation explicite** de `pyllmkit models sync`. Les réponses `/models` peuvent être incomplètes/paginées et liées au compte ; elles ne prouvent pas le droit d'invoquer un modèle.
3. **Exécution live** : contrat d'inférence préexistant, dont la politique M0 refuse les IDs `retired` ou `unverified` avant récupération des credentials. Aucune observation ne supprime ces garde-fous, et aucune conversion automatique vers un autre endpoint payant n'est autorisée.

Les tarifs v2 et la garantie de budget restent du ressort de M2, pas du catalogue de capacités.

## Contrat de données

```json
{
  "schema_version": 2,
  "revision": "m1-2026-11-07.1",
  "updated_at": "2026-11-07",
  "models": [
    {
      "public_model_id": "gpt-image-2",
      "native_model_id": "gpt-image-2",
      "model_owner": "openai",
      "api_provider": "openai",
      "billing_provider": "openai",
      "deployment_channel": "direct",
      "lifecycle": "current",
      "availability": "catalog_only",
      "aliases": [],
      "capabilities": {
        "tasks": ["text_to_image"],
        "modalities_in": ["text"],
        "modalities_out": ["image"],
        "resolutions": [],
        "duration_seconds": [],
        "codecs": [],
        "aspect_ratios": [],
        "languages": [],
        "voices": [],
        "max_outputs": null,
        "reference_image": null,
        "api_sync": null,
        "api_async": null
      },
      "source_url": "https://developers.openai.com/api/docs/models/gpt-image-2",
      "verified_at": "2026-11-07"
    }
  ]
}
```

Les listes vides signifient *aucune capacité supplémentaire vérifiée*, **pas** une impossibilité technique. Les `null` représentent des limites ou modes d'API inconnus. Le fichier embarqué contient uniquement des capacités minimales explicitement compatibles avec la famille de génération ; les tâches `image_edit`, `image_to_video`, `speech_to_speech`, `text_to_music` et `text_to_sfx` sont **définies par le schéma, mais pas revendiquées pour des IDs sans preuve**. Chaque intégration validée devra enrichir cette matrice.

Les identités `model_owner`, `api_provider` et `billing_provider` sont **indépendantes**. Sur les 23 routes directes historiques, elles coïncident ; cela ne crée aucune hypothèse pour les futurs fournisseurs agrégés (fal, Runway, Replicate). L'identifiant logique seul peut être ambigu entre fournisseurs : `MediaCatalog.find` exige alors un `provider` explicite, sans sélectionner arbitrairement.

### Invariants

- **M1-INV-01** : la version de schéma doit valoir exactement 2 ; les versions inconnues sont rejetées, pas migrées silencieusement.
- **M1-INV-02** : les routes sont uniques par `(api_provider, public_model_id)` ; les alias ne se chevauchent pas dans un même fournisseur.
- **M1-INV-03** : une route de base validée ne peut pas être écrasée par un overlay ; `merge_media_catalog` admet uniquement des ajouts ou des copies identiques.
- **M1-INV-04** : le statut `retired` ou `unverified` du M0 **prime sur l'observation**. Les dates de retrait s'appliquent dynamiquement.
- **M1-INV-05** : une absence dans une liste fournisseur partielle ne devient pas `retired`. L'état d'observation est `observed` ou `catalog_only`.
- **M1-INV-06** : l'observation ne donne aucun prix, capacité ou droit d'accès ; les fournisseurs d'API et de facturation sont différenciés.
- **M1-INV-07** : aucun `--live` implicite ; aucun appel fournisseur lancé par `models availability`, `models diff`, `models list --media` ou `models inspect`.

## Découverte, stockage et sécurité

Le cache v2 possède `schema_version=2`, `revision` entier croissant, une observation horodatée par fournisseur et des identifiants de modèles exclusivement. Les endpoints sont fixes, le contenu réseau plafonné à 1 MiB, les redirections/proxies sont refusés, les erreurs réseau ne propagent pas de secret, les corps JSON invalides sont rejetés. Les observations ont **`complete=false` obligatoire** tant que la pagination exhaustive de chaque fournisseur n'est pas implémentée.

La fusion est qualifiée par **`(provider, model_id)`**, pas par ID seul. Une synchronisation réussie remplace uniquement la vue du fournisseur concerné. Si la synchronisation échoue ou est ignorée, la dernière observation de ce fournisseur est conservée sans être qualifiée de récente.

L'écriture du cache v2 est atomique avec un fichier temporaire privé (`0600` sur systèmes POSIX), sans clés API, headers d'authentification ni prompts. Le fichier de cache historique `discovered_models.json` reste lisible et continue d'être alimenté pour préserver les usages existants ; la correction des collisions y est rétrocompatible.

La découverte utilise les seuls endpoints connus. Elle **n'exécute aucun modèle**, n'effectue aucune requête de génération et n'ouvre aucun appel payant. La disponibilité, les capacités et la facturation live ne sont pas certifiées.

## Interface utilisateur et migration

```bash
pyllmkit models list                        # compatibilité historique
pyllmkit models list --media                # routes média v2 déclarées
pyllmkit models inspect gpt-image-2         # informations historiques + route M1
pyllmkit models availability --provider openai --task text_to_image
pyllmkit models availability --model dall-e-3 --json
pyllmkit models diff --json                  # rapprochement local avec observations
pyllmkit models diff --against ./prior.json # différence de deux catalogues v2
pyllmkit models sync --provider openai       # réseau explicite, listing, non génération
```

Les nouveaux résultats JSON distinguent `lifecycle` et `observation`, et contiennent `account_access_verified: false`. **Aucun champ `available: true` n'est déduit d'un listing.** `models list`, `models inspect` et `models sync` conservent leurs options antérieures. La commande `models diff --against` exige un document au schéma v2, sans convertir silencieusement du JSON v1.

### Politique de migration de v1

- Les 154 modèles du catalogue général `models_catalog.json` et les contrats `ModelSpec` ne sont pas modifiés par M1.
- Les 23 routes médias v2 sont un complément typé en lecture seule. Les paramètres pricing historiques, s'ils existent, ne deviennent pas des garanties opérationnelles.
- Les anciens enregistrements `discovered_models.json` restent acceptés (ID, fournisseur et champs descriptifs filtrés), et une synchronisation explicite écrit **en plus** le cache v2.
- Les anciennes exécutions `--mock` et le tag `v0.3.0` ne sont pas modifiés.
- Une extension du catalogue doit apporter une provenance HTTPS, une date de vérification si disponible et une identité du canal facturant ; elle ne peut pas remplacer une route de base approuvée.

## Tests et gates

Tests sans E/S fournisseur : schéma invalide, ID/alias ambigu, double route, mode actuel/déprécié/retiré, fournisseur de facturation distinct, données de découverte invalides, comparaison déterministe, cache ancien, deux fournisseurs partageant un nom de modèle, absence de clé dans le cache, fichier atomique et permissions privées, CLI JSON, `models diff` sans réseau et absence de retrait inféré depuis des listings incomplets.

Le jalon **M1 GO offline** exige les trois matrices Python, Ruff, mypy strict, pytest, 752 conformance par environnement, packaging et GitGuardian sur le SHA exact de la PR puis sur `main`.

## Hors périmètre, explicitement

La synchronisation paginée exhaustive, la découverte des droits d'un compte, les devis/reconciliations de prix par canal (M2), les jobs média durables (M3), la génération musique/effets/édition par nouveaux fournisseurs (M4), les tests de dépenses, egress des autres transports et la certification de production (P7-L7.8) ne sont **pas** implémentés dans M1. Ne pas confondre un contrat de tâches extensible avec la livraison d'un adaptateur génératif.

## Décision

**Adopter le catalogue versionné v2 en lecture seule et le cache d'observations v2 sans remplacer les contrats historiques.** Une évolution de version de package et une release commerciale resteront des décisions séparées ; M1 n'autorise ni trafic génératif payant, ni PyPI, ni nouveau tag.
