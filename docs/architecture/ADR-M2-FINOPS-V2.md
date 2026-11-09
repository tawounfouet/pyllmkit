# ADR M2 - FinOps v2 : tarifs versionnés, devis, budgets et facturation

- Date : 2026-11-08
- Statut : **proposé, fondation de domaine en PR**
- Base : `main@9f51c6c656824fbdb24d3a82cf0ff1d5bf5e98e3` (M1 fusionné)
- Prédecesseurs : [audit M0](../audits/MEDIA_MODEL_AVAILABILITY_AUDIT.md), [ADR M1](ADR-M1-VERSIONED-MEDIA-CATALOG.md)
- Limite : aucune certification d'accès fournisseur ni de facturation réelle.

## 1. Problème

M0 a neutralisé les prix historiques retirés et les routes interdites. M1 a livré un catalogue multimodal versionné et distingue `model_owner`, `api_provider`, `billing_provider` et `deployment_channel`.

Mais `ModelPricing` dans `model_specs.py` reste un modèle de présentation utilisant des `float`, quatre unités approximatives (tokens, image, caractères, secondes) et le rapprochement via `get_model_spec` et ses préfixes. Les conditions réelles de facturation peuvent exiger résolution, qualité, région, canal, vidéo avec ou sans audio, coût fixe de requête, classes de jetons et quantité de sorties. L'usage observé n'est pas une facture.

Il faut empêcher qu'un prix `null` soit affiché comme gratuit, qu'un devis indicatif autorise une génération non bornée, et qu'un échec ou une annulation locale soit assimilé à une absence de facture.

## 2. Décision DDD

Conserver les invariants : `Usage != Pricing != Cost`, `Model != Deployment`, `Registry != Runtime`. Ajouter un bounded context FinOps pur, composable, sans E/S ni SDK.

| Concept | Rôle | Classification |
|---|---|---|
| `Money` | Montant non négatif + devise | Value Object immuable, `Decimal` |
| `MeteredQuantity` | Quantité et dimensions explicites | Value Object |
| `PriceRate` | Coût par dénominateur et dimensions | Value Object |
| `PriceVersion` | Périmètre facturant, période, source et révision | Entité immuable versionnée |
| `PriceCatalog` | Résolution exacte, refus d'ambiguïté | Read model |
| `CostEstimate` | Projection de prix à un instant donné | Value Object |
| `BudgetSnapshot` | Limite, consommé et réservé | Value Object |
| `BudgetDecision` | Évaluation pure sur snapshot | Value Object, non autorisation |
| `InvoiceCharge` | Ligne externe observée | Fait importé |
| `CostReconciliation` | Comparaison écartée ou rapprochée | Projection dérivée |

Les identités tarifaires sont `(model_id, api_provider, billing_provider, deployment_channel, date)`. Tout prix concurrent applicable déclenche un refus, jamais un choix arbitraire. Les dates de fin sont exclusives. Une ancienne version reste consultable pour le coût historique.

La présence d'un modèle chez un fournisseur, dans M1, ne garantit pas que sa grille tarifaire est applicable au client. Les prix sont un catalogue autonome dont les sources et conditions sont prouvables séparément.

## 3. Calcul et statuts

```text
PriceVersion + MeteredQuantity* + horodatage
             |
             v
        CostEstimate
          /     \
     complet  incomplet
        |        |
        v        v
     montant   montant absent
        |
        +--> BudgetSnapshot + plafond prouve --> BudgetDecision
        |
        +--> Usage constaté --> coût après exécution (à intégrer)
        |
        +--> InvoiceCharge externe --> CostReconciliation
```

Un `CostEstimate` complet signifie que toutes les quantités *fournies* ont un tarif correspondant. Il ne prouve pas que les quantités sont un majorant du coût futur. Pour l'utiliser dans une politique budgétaire pré-appel, le service appelant doit prouver que les limites distantes de quantité sont effectivement respectées.

Le calcul monétaire est effectué en `Decimal` sans arrondi intermédiaire. Les tarifs doivent avoir un `source_url` HTTPS, un `verified_at`, une période, des unités et des dimensions exactes. Aucun prix réel n'est initialisé sans source qualifiée.

## 4. Garde-fous obligatoires pour le futur flux live

1. Résoudre l'identité M1 exacte et le statut M0. Refuser `retired` et `unverified` avant credentials.
2. Déterminer la grille tarifaire valable pour le **facturant** et le canal réellement invoqué, non seulement le développeur du modèle.
3. Construire des quantités maximales explicites et prouver l'applicabilité des paramètres (`resolution`, `duration`, `quality`, `max_outputs`, etc.). Si une classe de coût reste inconnue, refuser l'autorisation automatique.
4. Évaluer le budget. L'estimation ne constitue ni un maximum garanti ni une réservation.
5. Utiliser ensuite un `BudgetReservationPort` **atomique et persistant** (compare-and-swap/transaction), par clé d'idempotence et domaine de facturation. Réserver **avant** l'accès aux secrets/réseau.
6. Interdire retries/fallback payants sans nouvelle autorisation et nouvelle réservation, y compris après timeout.
7. Lors d'un succès, d'un timeout, d'une annulation ou d'un échec, préserver la réservation jusqu'à détermination du coût facturable. Une annulation locale ne prouve pas l'arrêt du travail distant.
8. Collecter le `Usage` fournisseur et calculer un coût post-exécution, sans le présenter comme facturé.
9. Importer via un `BillingEvidencePort` les lignes de facture/usage payant identifiables (provider_request_id, ID facture, période, devise, dimensions, taxes/crédits).
10. Rapprocher les estimations, usages, charges et remboursements. Exiger une correspondance explicite du `provider_request_id` avant de conclure `matched` ; le même montant seul ne suffit pas. Exporter la variance, les écarts de devises, les lignes sans correspondance et les coûts partiels. Ne jamais affecter arbitrairement une charge commune à un run.

L'autorisation opérationnelle exige également la qualification de sécurité provider-live P7-L7.8 #81. Aucun appel génératif payant ne doit être ajouté aux tests CI ordinaires.

## 5. Règles d'échec

- **Missing price, dimension, quantity** : `amount=None`, jamais 0.
- **Exact zero rate or quantity** : 0 explicite si toutes les données sont connues.
- **Currency mismatch** : pas de conversion FX implicite.
- **Overlapping versions** : erreur de résolution, pas de première entrée choisie.
- **Price expired** : refus au moment de l'évaluation.
- **Quote unbounded** : refus de la politique budgétaire.
- **No invoice / unmatched external charge** : état séparé, jamais zéro facturé.
- **Provider mismatch** : rapprochement indéterminé.
- **Request cancelled** : facturation potentielle en attente, pas de libération automatique.

## 6. Phasage des gates M2

| Gate | Livraison | Sortie attendue |
|---|---|---|
| **G0** | Audit, contrats DDD, tests purs hors réseau | Périmètre et inconnus explicités, CI sur SHA exact |
| **G1** | Catalogue tarifaire JSON v2 strict, versions et provenance, migration legacy | Schéma, overlays contrôlés, tests de sécurité |
| **G2** | Devis pré-appel CLI/SDK, couverture des paramètres et coûts composites | Devis explicite ou refus, mock inchangé |
| **G3** | Réservations budgétaires durables et atomiques | Concurrence, idempotence, timeouts, crash/restart, veto avant secret |
| **G4** | Réconciliation fournisseur / factures et export d'audit | Lignes dédoublonnées, variances, devises et taxes explicites |
| **G5** | Qualité complète et intégration | CI 3.11/3.12/3.13, tests, lint, mypy, conformance, packaging, GitGuardian |

Le premier incrément implémente les contrats purs de G0. En particulier `assess_budget` est un **policy checker**, pas un système de réservation ni une approbation live. Il ne doit pas être connecté directement aux adaptateurs producteurs avant G2 et G3.

## 7. Compatibilité et gouvernance

- Conserver `compute_run_cost`, `ModelPricing`, les anciennes commandes CLI et les données historiques, sans les considérer comme une nouvelle preuve de prix opérationnels.
- Ne modifier ni le catalogue des 154 références, ni les 23 routes M1 pendant G0.
- Aucun changement de version, tag, release, PyPI ou accès réseau pour cette PR.
- Conserver les simulations historiques et la non-disponibilité des modèles retirés en live.
- La CI d'une PR et la CI post-fusion sont des preuves distinctes ; un test offline ne certifie pas les coûts effectivement facturés.
