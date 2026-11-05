# PyLLMKit - P7 Provider Adapters - Critères d'entrée du prochain milestone

- Date : 2026-11-05
- Statut : **READY FOR P7-G0 ARCHITECTURE**, aucun adapter réseau P7 encore implémenté ni qualifié.
- Baseline fonctionnelle : M6 Registry & Discovery offline, main@6c58b052 ; gate archive main@670ccab9, leurs CI réussies.
- Référence de décision : `docs/quality/M6_GATE_REVIEW.md` (GO technique avec réserves, release NO-GO).
- Distribution source : `0.1.0a2`, version cible `0.1.0b2` toujours non autorisée.

## Prochain objectif

Faire de PyLLMKit un cadre agnostique pouvant **adapter** les contrats d'inférence et streaming M1-M6 vers un premier fournisseur réel sans introduire de SDK ni de secrets dans le domaine. Définir la couche d'adapters **après** la frontière descriptive P6, avec un nombre minimal de fournisseurs pilotes.

## P7-G0 - Architecture obligatoire avant l'implémentation

1. Définir `InferenceProviderAdapterPort`, une capacité de connexion explicite et un `AdapterRegistry` distinct du `ProviderCatalog` descriptif P6.
2. Rédiger l'ADR de frontière provider (suite logique après ADR-048 ; le numéro final est à réserver dans le registre ADR) : structures de requêtes/réponses, statuts, erreurs, serialization contract, types d'exception et mapping de capacités.
3. Définir un threat model : secrets, égress/SSRF, TLS, redaction logs, horodatages, storage, retries et timeouts.
4. Préciser les contrats sync/async, cycle de vie des ressources, cancellation, streaming réel et limitations SSE/HTTP.
5. Définir une matrice de compatibilité provider, versions d'API, tests offline de fixtures, tests contractuels simulés et essais opt-in en réseau.
6. Établir une règle explicite d'autorisation d'accès réseau et un chemin de configuration sans credentials en source.
7. Ne sélectionner un provider pilote que sur la base d'un contrat testé ; prévoir son adapter comme plugin optionnel, non comme dépendance imposée du noyau.
8. Préparer gates P7-G0.. selon le plan approuvé ; aucun code provider avant G0.

## Préconditions / dettes transverses non effacées par M6

- **#22** : la branche main n'est pas encore protégée. Configurer required checks et revues effectives avec droits d'administration avant toute distribution externe.
- **#35** : release séparée ; ni tag ni PyPI sans autorisation explicite et checklist.
- **#36** : finaliser les frontières provider, politique de sécurité, parsing et observabilité.
- Demander une revue humaine tierce des changements réseau et de sécurité, distincte de la revue assistée M6.

## Définition de prêt pour démarrer P7

**GO pour débuter P7-G0 :** M6 intégré à main avec CI exacte, documentation et tests à jour, responsabilités de domaine stables et risques restants répertoriés. **NO-GO pour déployer un Provider Adapter en production ou publier une release** tant que les contrôles de sécurité, de gouvernance, de compatibilité et de revue n'ont pas été satisfaits.

Prochaine action technique : produire le plan `P7_PROVIDER_ADAPTERS_IMPLEMENTATION_PLAN.md` et les nouvelles ADR d'adapter, puis qualifier P7-G0 avant toute PR d'implémentation.
