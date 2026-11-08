# PyLLMKit M2-G2 - Devis pré-génération hors réseau (SDK + CLI)

- Date : 2026-11-08
- Statut : G2 candidat, PR #115, sans fusion
- Prérequis : M2-G0 domaine FinOps, M2-G1 catalogue tarifaire versionné, M1 modèle multimodal versionné
- Garantie de sécurité : **le devis n'autorise jamais un appel payant, même s'il est chiffré**.

## 1. Objectif et frontières

Un appel multimodal peut être facturé en images, jetons, caractères, secondes de vidéo/audio ou combinaisons de compteurs et dimensions (qualité, résolution, canal, etc.). Une simple multiplication du nombre d'images ne prouve pas le montant final.

G2 implémente une **cotation d'un scénario déclaré**, sans accès réseau ni secrets. Il manque encore un plan de facturation certifié indépendant de la requête, la preuve de plafonds réels fournisseur, une réservation atomique du budget (G3) et les factures (G4).

Les objets de domaine `QuoteScenario`, `QuoteComponent`, `QuoteLine`, `PreflightQuote` et la fonction `quote_scenario` sont indépendants de toute bibliothèque de CLI et de toute connexion fournisseur. Le service `quote_media_scenario` résout la route M1 et la version tarifaire G1 exacte.

### États de cotation

| État | Montant | Raison | Autorisation live |
|---|---|---|---|
| `priced_scenario` | Montant exact pour **les seules composantes déclarées** | `declared_components_priced_only` | **Non** |
| `unknown` | `null` | `missing_tariff` | **Non** |
| `incomplete` | `null` | `missing_meter_rate` ou `missing_quantity_bound` | **Non** |
| `error` en CLI | Aucun devis | Requête JSON, route, tâche, modèle ou tarification invalide | **Non** |

La valeur `0` est autorisée uniquement si le compteur déclaré est **explicitement** égal à zéro et si son tarif existe. La valeur `null` exprime une information inconnue, jamais une gratuité supposée.

## 2. Exemple minimal de scénario JSON v1

Fichier `scenario.json` :

```json
{
  "schema_version": 1,
  "model_id": "gpt-image-2",
  "api_provider": "openai",
  "task": "text_to_image",
  "at": "2026-11-08T12:00:00+00:00",
  "parameters": {
    "quality": "high"
  },
  "components": [
    {
      "meter": "image",
      "maximum": "2",
      "dimensions": {"quality": "high"}
    },
    {
      "meter": "input_token",
      "maximum": "1000",
      "dimensions": {}
    }
  ]
}
```

L'exemple représente une **hypothèse de compteurs**, pas un profil tarifaire complet ou certifié pour ce modèle. Le nombre de jetons réel pourrait être différent ; une composante facturée pourrait être absente.

Le module refuse les paramètres comptabilisés sous une dimension non sélectionnée, les composants dupliqués, les maxima booléens/flottants ou négatifs, les timestamps sans zone et les clés JSON dupliquées, y compris dans les objets imbriqués. Le nombre de composantes est borné à 64 et la taille JSON à 64 KiB.

## 3. CLI

```shell
# Catalogue embarqué : prices=[], donc coût inconnu et sortie 3
pyllmkit finops quote --request scenario.json

# Catalogue tarifaire EXPLICITE (valeurs synthétiques ou vérifiées séparément)
pyllmkit finops quote --request scenario.json --pricing-catalog synthetic-prices.json
```

La sortie est du JSON stable avec `amount.value` au format décimal textuel, `currency`, `source_url`, `price_revision`, `catalog_revision`, `missing_rates`, `missing_bounds`, les lignes de coût et trois invariants explicites :

```json
{
  "coverage": "declared_components_only",
  "live_authorized": false,
  "provider_quote_verified": false,
  "atomic_budget_reserved": false
}
```

Ce fragment est un **extrait de champs**, pas une réponse complète de la commande.

Codes de sortie :
- `0` : scénario chiffré hors réseau pour les seuls composants déclarés.
- `2` : requête ou route invalide, sans exécution fournisseur.
- `3` : prix ou quantités inconnus, pas de montant total.

L'utilisation de `--pricing-catalog` est toujours explicite. Aucun prix de l'ancien `ModelPricing` utilisant `float` n'est réemployé, et aucun override local automatique n'est autorisé.

## 4. Python SDK

```python
from datetime import UTC, datetime
from decimal import Decimal

from pyllmkit.adapters.cli.media_catalog_v2 import load_media_catalog
from pyllmkit.adapters.cli.pricing_catalog_v2 import load_price_catalog
from pyllmkit.adapters.cli.finops_quote import quote_media_scenario
from pyllmkit.domain.finops.quoting import QuoteComponent, QuoteScenario, quote_to_dict

scenario = QuoteScenario(
    model_id="gpt-image-2",
    api_provider="openai",
    task="text_to_image",
    at=datetime(2026, 11, 8, tzinfo=UTC),
    parameters=(("quality", "high"),),
    components=(
        QuoteComponent("image", Decimal("2"), (("quality", "high"),)),
        QuoteComponent("input_token", Decimal("1000")),
    ),
)
quote = quote_media_scenario(
    scenario,
    prices=load_price_catalog(),
    media=load_media_catalog(),
)
assert quote.amount is None
assert quote.reason == "missing_tariff"
assert not quote.live_authorized
print(quote_to_dict(quote))
```

Un scénario calculé avec un fichier tarifaire synthétique peut produire un total, mais sa couverture demeure `declared_components_only`. Le service ne prend jamais un total positif pour la preuve d'une autorisation et ne résout jamais une grille à partir du seul préfixe de modèle.

Les paramètres de capacité M1 sont contrôlés quand ils sont documentés : tâches prises en charge, résolution, codec, ratio, voix, langue, durée et plafond de sorties. Une liste de capacités vide dans M1 signifie **information inconnue** et non prise en charge certifiée.

## 5. Exclusions et gates restants

- **Pas de branchement** sur `generate --live` à ce stade : pas de régression sur les exécutants ni de consentement live implicite.
- **Pas d'activation de l'autorisation budgétaire** depuis `quote.scenario_priced`. Une quote ne prouve ni l'exhaustivité des compteurs ni le caractère réellement borné côté fournisseur.
- **G3** doit fournir un profil de comptage fiable, un plafond vérifiable dans l'adaptateur réel, la réservation atomique, le contrôle des retries/fallbacks et le veto avant secrets.
- **G4** doit importer les coûts facturés avec identifiants de requête, dédoublonnage, taxes, crédits et devises.
- **G5** doit confirmer la sécurité et les qualifications intégrées, sans confondre CI offline et coût payé.
- La certification fournisseur live P7-L7.8 est indépendante.

Les tests de G2 n'utilisent que des montants fictifs et aucun secret ou appel payant.
