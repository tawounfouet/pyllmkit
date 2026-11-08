# PyLLMKit M2-G1 - Catalogue tarifaire JSON v2 et historique immuable

> Date : 2026-11-08
> Statut : livraison G1 candidate sur `feat/m2-finops-v2`
> Limite : catalogue déclaratif hors réseau, **aucun prix réel embarqué**, aucune autorisation de génération live
> Base : M1, [ADR-M1](../architecture/ADR-M1-VERSIONED-MEDIA-CATALOG.md), [ADR-M2](../architecture/ADR-M2-FINOPS-V2.md)

## Pourquoi ce catalogue est indépendant

M1 décrit le modèle, la route API, le fournisseur et l'acteur facturant. M2 ajoute une grille tarifaire propre, avec unité, dimensions, origine, période et version. Ni la présence d'une route M1, ni l'observation d'un ID dans `/models`, ni une date `verified_at` dans un fichier local ne prouvent le tarif réellement facturé pour un compte.

Le fichier livré `src/pyllmkit/adapters/cli/data/pricing_catalog_v2.json` contient `prices: []` tant que les preuves tarifaires opérationnelles ne sont pas collectées et qualifiées. **Absence de tarif = coût inconnu, jamais gratuit**.

## Contrat strict

```json
{
  "schema_version": 2,
  "revision": "sample-2026-11-08.1",
  "updated_at": "2026-11-08",
  "prices": [
    {
      "price_id": "test-video-720p-v1",
      "revision": "r1",
      "model_id": "test-video",
      "api_provider": "test-api",
      "billing_provider": "test-biller",
      "deployment_channel": "direct",
      "currency": "USD",
      "valid_from": "2026-11-01T00:00:00+00:00",
      "valid_to": "2026-12-01T00:00:00+00:00",
      "source_url": "https://example.org/fictional-price",
      "verified_at": "2026-11-08",
      "rates": [
        {
          "meter": "video_second",
          "amount": "0.08",
          "per": "1",
          "dimensions": {"resolution": "720p"}
        }
      ]
    }
  ]
}
```

**L'exemple est fictif**. Les valeurs ne correspondent à aucun prix fournisseur annoncé.

La structure stricte refuse les champs supplémentaires, les doublons de clés JSON à tous les niveaux, les décimaux encodés comme nombres JSON, les valeurs non finies, les prix négatifs, les dénominateurs nuls, les devises invalides et les dates sans fuseau. Les dimensions sont canoniquement triées, les montants préservent leur précision `Decimal`.

La date de fin est **exclusive**. Deux versions tarifaires d'une même route `(model_id, api_provider, billing_provider, deployment_channel)` ne peuvent pas se chevaucher. Une version déjà enregistrée ne peut pas être réécrite silencieusement lors d'une fusion de catalogues.

### Lecture via Python

```python
from datetime import UTC, datetime

from pyllmkit.adapters.cli.media_catalog_v2 import load_media_catalog
from pyllmkit.adapters.cli.pricing_catalog_v2 import load_price_catalog, resolve_media_price

catalogue = load_price_catalog()
route_catalogue = load_media_catalog()

tarif = resolve_media_price(
    catalogue,
    route_catalogue,
    identifier="gpt-image-2",
    api_provider="openai",
    at=datetime(2026, 11, 8, tzinfo=UTC),
)
assert tarif is None  # Aucune grille réelle n'est livrée avec G1
```

La résolution ne cherche **jamais** un prix par simple préfixe de modèle. Elle passe par la route exacte M1, en préservant `billing_provider` et `deployment_channel`. Les modèles `retired` ou `unverified` n'obtiennent pas de prix opérationnel, même si un fichier utilisateur invente une grille.

### Historique et extensibilité

- `parse_price_catalog_json` vérifie aussi les doublons de champs et la taille (1 MiB).
- `parse_price_catalog` vérifie l'enveloppe, les tarifs et le non-chevauchement sur l'ensemble de l'historique.
- `load_price_catalog(path)` charge seulement le fichier explicitement indiqué. Aucun overlay depuis le répertoire courant ne remplace les tarifs embarqués.
- `merge_price_catalog` n'accepte que des extensions historiques nouvelles, non chevauchantes ; une copie identique est tolérée.
- `price_catalog_to_dict` préserve les montants exacts sous forme de chaînes pour un aller-retour JSON vérifiable.
- Le module n'utilise ni réseau, ni credentials, ni facturation réelle. Il dépend seulement de la bibliothèque standard et du domaine PyLLMKit.

## Compatibilité avec les anciennes grilles

`models_catalog.json`, `ModelPricing`, `get_model_spec`, `compute_run_cost`, les simulations et les commandes existantes ne sont pas modifiés en G1.

La migration doit être **explicite**. Un tarif historique de l'ancien catalogue avec un prix float, sans révision et sans conditions de facturation ne peut pas être converti automatiquement en un `PriceVersion` opérationnel. Il faut collecter une source, la devise, le canal, la validité, les unités et les dimensions vérifiables.

Les prix locaux ou les grilles fournies par un tiers restent des **données déclarées**, pas des taux certifiés. Le futur devis G2 distinguera `pricing_source`, `pricing_revision`, `estimated` et `unknown`.

## Critères de qualification G1

Tests unitaires sans réseau et CI exact-SHA, Python 3.11/3.12/3.13, Ruff, mypy strict, conformance, wheel/sdist et GitGuardian. Vérifier les cas de dates aux frontières, versions doublonnées et chevauchantes, fournisseur facturant différent, dimension inconnue, dénominateur nul, JSON falsifié, fusion non destructive et modèle retiré.

**GO G1 offline ne signifie pas GO live** : G2 couvre le devis et le parcours CLI/SDK, G3 la réservation budgétaire atomique, G4 la preuve de facturation et le rapprochement, G5 la qualification de bout en bout. La qualification P7-L7.8 demeure indépendante.
