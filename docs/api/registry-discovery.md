# PyLLMKit - API Registry & Discovery P6 (candidat hors réseau)

## 1. Frontière de domaine

PyLLMKit P6 représente des modèles, fournisseurs descriptifs et deployments, puis recherche, résout et fusionne des snapshots hors ligne. Ce n'est pas une implémentation d'API provider ou un SDK exécutable.

Objets : `Model`/`ModelId` réutilisés de M1, `DeploymentId` et targets de M3, `ProviderId`/`InferenceProvider`, `Deployment`/`DeploymentStatus` introduits en L6.1. Le provider est un descriptif distinct des futurs adapters exécutables.

## 2. Registres typés et recherches

- `InMemoryCatalog.models` : `ModelRegistryPort` ; enregistre, retourne, liste, recherche et supprime les Models.
- `InMemoryCatalog.providers` : `ProviderCatalogPort` ; métadonnées de providers uniquement.
- `InMemoryCatalog.deployments` : `DeploymentRegistryPort` ; exige un Model existant et un Provider existant lorsque la référence n'est pas None.
- `ModelQuery` et `DeploymentQuery` sont immuables, stricts et conjonctifs. Les résultats sont triés par ID.
- `CatalogSearchService` orchestre la recherche sans muter les registres.

## 3. Capacités et limites effectives

- `CapabilityResolver.resolve(model, deployment, provider, capability_ids)` calcule des preuves par couche.
- UNKNOWN reste None ; UNSUPPORTED exerce un veto ; PARTIAL et EMULATED restent distincts et explicites.
- Un provider absent est NOT_APPLICABLE uniquement si la référence ProviderId du deployment est structurellement None.
- `LimitResolver.resolve` calcule la plus petite borne supérieure connue et identifie les résultats provisoires.
- Les conflits de contraintes ne sont pas coercés. La sémantique M1 `CapabilitySet.intersection` n'est pas modifiée.

## 4. Sélection déterministe

- `DeploymentResolver` accepte `ModelTarget` ou `DeploymentTarget` et un `DeploymentRequirement`.
- La sélection n'aboutit que lorsqu'un unique deployment satisfait tous les critères stricts.
- Aucun candidat : `NoCompatibleDeploymentError` ; plusieurs candidats : `AmbiguousDeploymentError`.
- Pas de premier candidat implicite, ni basculement automatique, ni mesure de santé réseau. `AVAILABLE` est un statut déclaré dans le catalogue.

## 5. Découverte et fusion atomique

- `DiscoverySourcePort` produit un `DiscoveryResult` immuable avec `MetadataSource`, `observed_at` UTC, providers, models et deployments.
- `StaticDiscoverySource` renvoie une fixture fournie par le programme ; aucune ingestion HTTP ou SDK.
- `CatalogMergeService.preview(batch, now=...)` réalise le dry-run sans mutation et fournit additions, rejouements, conflits de champs et références manquantes.
- `CatalogMergeService.apply(batch, preview, now=...)` requiert exactement cette prévisualisation, puis valide la version du catalogue et remplace le snapshot entier en mémoire.
- Stratégie MVP : `MergePolicy.FAIL_ON_CONFLICT` exclusivement. Aucun last-writer-wins ni priorité automatique à la date la plus récente.
- Toute référence manquante ou collision annule le lot entier. Un import identique rejoué est une opération sans effet.

## 6. Exemples

```bash
python examples/23_define_provider_deployment.py
python examples/24_registry_search.py
python examples/25_effective_capabilities_limits.py
python examples/26_deployment_resolution.py
python examples/27_offline_discovery_merge.py
python examples/28_full_registry_walkthrough.py
```

Les six scénarios sont hors réseau et exécutés par la CI sur les distributions wheel/sdist ainsi que sur le checkout.

## 7. Limites et gouvernance

L'atomicité est strictement locale à un catalogue InMemory et prévue en utilisation séquentielle. Elle ne garantit pas les transactions concurrentes multi-thread ni les transactions distribuées. Aucun parseur de fichier arbitraire non fiable n'est livré et aucune API de provider n'est appelée.

Consulter `docs/architecture/PHASE_6_REGISTRY_ARCHITECTURE.md`, les ADR-039..048, la matrice `docs/quality/PHASE_6_TRACEABILITY.md` et les PR de P6.

Le jalon M6 et la version cible 0.1.0b2 ne sont pas qualifiés à ce stade. Aucun tag, release ou PyPI publish.
