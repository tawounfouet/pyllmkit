# PyLLMKit - M2 FinOps v2 - Audit initial G0

> Date : 2026-11-08
> Baseline : `main@9f51c6c656824fbdb24d3a82cf0ff1d5bf5e98e3` (PR #114 intégrée)
> Statut : **audit de code et contrat de domaine candidat**, qualification CI et intégration à vérifier
> Exclusions : tests réels facturants, validation de l'accès à un compte fournisseur, publication et claims production.

## 1. Constat vérifié dans la source

| ID | Composant | Évidence | Risque | Orientation |
|---|---|---|---|---|
| M2-A01 | `src/pyllmkit/adapters/cli/model_specs.py::ModelPricing` | `float | None`, `unit` symbolique, pas de révision ou période tarifaire | Dérive monétaire et tarif historique non traçable | `PriceVersion`, `Decimal`, validité et source |
| M2-A02 | `model_specs.py::get_model_spec` | Recherche par suffixes puis préfixe et fournisseur non exigé | Confusion de modèle/canal facturant | Clé exacte M1 et biller obligatoire |
| M2-A03 | `model_specs.py::compute_run_cost` | `image`, `1M characters`, `second` ou tokens, sans conditions de résolution/qualité/canal | Estimation insuffisante pour média composite | Rates dimensionnels, couverture partielle = inconnu |
| M2-A04 | `compute_run_cost` | Casts de compteurs en `int` et coefficients `float`; cached tokens sans tarif cache peuvent être valorisés à l'input général | Précision et interprétation indue de l'usage | Contrats stricts, aucun compteur inventé |
| M2-A05 | `docs/cli/SECURITY_PRIVACY_RETENTION_AND_PRICING.md` | Prix local affiché comme estimé et non comme facture | Frontière déjà documentée, pas encore moteur d'autorisation | Conserver provenance et séparation |
| M2-A06 | M1 `media_catalog_v2.py` | Clés `model_owner`, `api_provider`, `billing_provider`, `deployment_channel` distinctes | Base solide, mais pas de grille tarifaire | Réutiliser sans modifier le routage |
| M2-A07 | `domain/inference/usage.py` | Compteurs tokens, caractères, unités médias et secondes optionnels | Données observées partielles | `None != 0`, pas de facturation déduite |
| M2-A08 | M0 `MEDIA_MODEL_AVAILABILITY_AUDIT.md` | Tarifs retirés neutralisés et modèle retiré bloqué avant credentials | Barrière à ne pas réintroduire | Tester les régressions avant tout budget |
| M2-A09 | P7-L7.8 #81 | Qualification live et garde-fous opérationnels non clos | Budget non opposable / facturation indéterminée | GO uniquement hors ligne avant les gates opérationnels |

## 2. Principe critique

**Trois observations économiques ne doivent jamais fusionner** :

- Devis pré-appel `CostEstimate` : prévision calculée avec des quantités supposées, validée par prix/version et dimensions.
- Coût post-exécution : calcul fondé sur les métriques effectivement observées, qui restent éventuellement incomplètes.
- Charge facturée `InvoiceCharge` : constat fournisseur indépendant, sujet à crédits, arrondis, taxes, ajustements et décalages temporels.

Un devis complet n'est **pas** une borne maximale. Une politique de budget n'est pas une réservation atomique. Une absence de facture n'est pas un coût nul.

## 3. Livrable du premier incrément M2-G0

- Nouveau namespace `pyllmkit.domain.finops` pur et sans dépendance obligatoire.
- Contrats immuables pour `Money`, `MeteredQuantity`, `PriceRate`, `PriceVersion`, `PriceCatalog`, `CostEstimate`, `BudgetSnapshot`, `BudgetDecision`, `InvoiceCharge` et `CostReconciliation`.
- Fonctions pures `estimate_cost`, `assess_budget` et `reconcile_cost`.
- Tests négatifs : prix absents, révision ambiguë, dates, montant non fini, quantités manquantes, dimensions non tarifées, currency/biller mismatch, variance, identifiant de requête fournisseur absent ou incompatible, budget insuffisant et faux booléen de plafond.
- Jeu de tarifs **entièrement synthétique dans les tests** (ex. 0,08 USD/s et 0,12 USD/image) : **aucun tarif fournisseur revendiqué ni catalogue opérationnel créé**.

## 4. Dettes bloquantes après G0

| Gate | Dette | Validation requise |
|---|---|---|
| G1 | Pricing v2 JSON et historique à dates non chevauchantes | Schéma, source vérifiable et refus d'overrides malveillantes |
| G2 | Intégration des devis SDK/CLI et des quantités de sortie plafonnées | Tests mock des trois médias + textes ; veto avant secret |
| G3 | Gestion transactionnelle durable des budgets | Concurrence inter-processus, idempotence, réservation et reprise |
| G4 | Facture/usage distant et identifiants de rapprochement | Import autorisé, déduplication, règles taxes/crédits, audit |
| G5 | Qualification technique et gouvernance | Matrices complètes, CI PR puis main, pas de release implicite |

## 5. Verdict à ce stade

**GO pour implémenter et tester le contrat pur G0 hors réseau.**

**NO-GO** pour activer un veto budgétaire live présenté comme garanti ou déclarer une réconciliation réelle sans source de facturation. La production reste soumise à #81 et aux gates G1-G5.

La décision G0 définit une frontière de travail, et non une qualification définitive de M2.
