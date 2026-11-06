# PyLLMKit - Analyse d'ingénierie et architecture : CLI Typer + Rich

- Date de référence : 2026-11-06
- Statut : DOCUMENT D'ANALYSE ET DE CONCEPTION (Jalon 0.3.0+)
- Portée : Conception de la couche d'interface en ligne de commande (CLI)
- Contexte amont : Jalon 0.3.0 qualifié sur `main@ce16398` (752 scénarios de conformité, 6 adaptateurs natifs, streaming pull-driven)
- Références architecturales : ADR-049..059, Ports & Adapters, Clean Architecture

---

## 1. Vision et objectifs directeurs

La couche CLI a pour mission de fournir une interface opérateur ergonomique, réactive et visuellement riche pour explorer, diagnostiquer, exécuter et auditer les primitives de PyLLMKit sans nécessiter l'écriture de code Python ad hoc.

### Principes directeurs non négociables

1. **Driving Adapter pur (Adaptateur primaire)** :
   La CLI ne contient aucune logique métier ni règle de validation propriétaire. Elle traduit les arguments et options de la ligne de commande en objets de commande applicatifs (`InvokeCommand`, `ResolveDeploymentQuery`), délègue l'exécution à la couche `Application` (`InferenceService`, `DeploymentResolver`), puis formate les résultats pour la console.

2. **Zéro dépendance obligatoire dans le cœur** :
   Le cœur de PyLLMKit conserve strictement `dependencies = []` dans son `pyproject.toml`. Typer et Rich sont configurés comme des dépendances optionnelles sous l'extra `[project.optional-dependencies] cli = ["typer>=0.12", "rich>=13.7"]`.

3. **Sécurité et Default-Deny préservés** :
   - Aucun secret (clé d'API, jeton) n'est jamais affiché en clair dans les commandes d'inspection ou dans les historiques.
   - Les appels réseau nécessitent une autorisation explicite (flag `--allow-live` ou variable d'environnement dédiée). Par défaut, la CLI opère en mode de vérification hermétique ou mock local.
   - Rejet immédiat de toute saisie non conforme avant tout engagement de calcul ou de transport.

4. **Déterminisme et transparence des diagnostics** :
   Lorsqu'une résolution échoue ou est ambiguë, la CLI affiche le rapport d'audit exhaustif (`DeploymentResolutionReport`) avec la liste explicite des rejets (`CandidateRejection`), sans jamais masquer une cause d'erreur.

---

## 2. Périmètre fonctionnel et commandes cibles

L'application CLI est structurée autour d'un point d'entrée unique `pyllmkit`, découpé en plusieurs sous-groupes de commandes :

### A. Groupe `providers` (Inspection des adaptateurs de fournisseurs)
- `pyllmkit providers list` :
  - Tableau Rich listant les 6 fournisseurs supportés (Ollama, OpenAI, Anthropic, Gemini, xAI, Mistral).
  - Indicateurs de transport : URL d'API par défaut, mode de transport (HTTP / loopback), statut des clés configurées (présente / absente, masquée).
- `pyllmkit providers inspect <provider_id>` :
  - Vue détaillée des capacités intrinsèques déclarées par le fournisseur, protocoles supportés et règles de sécurité (anti-SSRF, timeouts).

### B. Groupe `models` & `deployments` (Catalogue et découverte)
- `pyllmkit models list` :
  - Tableau des modèles déclarés avec pagination, tri par famille et filtres de capacités (ex : `--capability streaming`, `--modality image`).
- `pyllmkit deployments list` :
  - Liste des déploiements enregistrés (`deployment_id`, `model_id`, `provider_id`, `region`, `status`).
- `pyllmkit resolve --model <model_id> [--provider <provider_id>]` :
  - Exécute le `DeploymentResolver` déterministe.
  - Affiche le rapport de sélection avec coloration Rich : vert pour le déploiement retenu, rouge pour chaque candidat éliminé avec ses motifs précis (`REGION_MISMATCH`, `CAPABILITY_UNKNOWN`, etc.).

### C. Groupe `run` (Inférence texte bloquante)
- `pyllmkit run "Mon invite"` :
  - Options : `--model`, `--provider`, `--temperature`, `--max-tokens`, `--timeout`.
  - Exécution bloquante via `InferenceService.invoke()`.
  - Affichage soigné de la réponse textuelle, suivi d'un panneau d'audit : `RunId`, temps d'exécution, raison d'arrêt (`finish_reason`), comptage précis des tokens (`Usage`).

### D. Groupe `stream` (Inférence interactive en streaming)
- `pyllmkit stream "Mon invite"` :
  - Rendu incrémental temps réel avec `rich.live.Live`.
  - Reconstitution déterministe des deltas texte via le réducteur du domaine.
  - Gestion propre des interruptions clavier (`Ctrl+C`) : déclenche l'annulation locale du run sans fuite de connexion.

### E. Groupe `tools` (Outillage et validation de schémas)
- `pyllmkit tools validate <schema.json>` :
  - Valide hors ligne la conformité d'un schéma d'outil selon les règles strictes de PyLLMKit (nom ASCII 1..64, types d'arguments valides, absence de clés dupliquées).

---

### 3. Schéma d'architecture de la CLI

```text
[Utilisateur Terminal]
        |
        v
  [Typer Parser & CLI Options]  (adapters/cli/commands/run.py)
        |
        v  (Validation des flags et construction)
  [InvokeCommand / ResolveQuery]  (application/inference/contracts.py)
        |
        v  (Appel du Use Case unique)
  [InferenceService / DeploymentResolver]  (application/)
        |
        v  (Exécution du domaine et de l'adaptateur fournisseur)
  [InferenceExecution / StreamSession]  (domain/ + adapters/inference/)
        |
        v  (Formatage visuel sans logique métier)
  [Rich Formatters / Live Console]  (adapters/cli/formatting/)
        |
        v
[Affichage Terminal Riche]
```

---

## 4. Expérience utilisateur (Rich UX) et gestion des erreurs

### A. Rendu des tableaux de modèles et fournisseurs
Les tableaux exploitent les fonctionnalités avancées de Rich :
- En-têtes nets, bordures fines (`box.ROUNDED`), pagination propre.
- Badges de statuts : `[green]AVAILABLE[/green]`, `[yellow]PARTIAL[/yellow]`, `[red]UNSUPPORTED_VETO[/red]`.
- Nombres alignés à droite avec séparateurs de milliers.

### B. Panneau unifié de gestion des erreurs
Pour éviter toute fuite de stacktrace Python brute, les exceptions de domaine et d'infrastructure sont interceptées par un gestionnaire centralisé qui les projette dans un `rich.panel.Panel` rouge :

```text
┌─ Erreur d'inférence [rate_limited] ──────────────────────────────────────────┐
│                                                                             │
│  Le fournisseur 'openai' a rejeté la requête : quota temporairement atteint. │
│                                                                             │
│  • Code interne  : rate_limited                                             │
│  • Run ID        : run-98a7bc-20261106                                      │
│  • Action        : Patientez quelques instants ou basculez vers un autre     │
│                    déploiement via --provider mistral                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

Les codes d'erreur affichés correspondent exactement à la taxonomie unifiée du jalon S3 :
- `authentication_failed` (Clé d'API absente ou refusée)
- `permission_denied` (Droits insuffisants pour ce modèle)
- `rate_limited` (Seuil de requêtes dépassé)
- `provider_timeout` (Délai d'attente réseau expiré)
- `provider_overloaded` (Service distant temporairement indisponible)
- `invalid_request` (Paramètres de génération non supportés)

---

## 5. Persistance locale et gestion de configuration

Pour que la CLI soit réellement utilisable au quotidien entre deux exécutions distinctes :

### A. Emplacements de stockage standard
1. **Configuration locale** : `~/.config/pyllmkit/config.json` (ou `.pyllmkit.yaml` à la racine d'un projet).
   - Mémorise le fournisseur par défaut, les timeouts usuels et les endpoints privés éventuels.
2. **Catalogue de travail** : `~/.config/pyllmkit/catalog.json`.
   - Charge les définitions de modèles et déploiements personnalisés via `InMemoryCatalog` au démarrage de chaque commande.
3. **Historique des exécutions** : `~/.config/pyllmkit/history.db`.
   - Base de données SQLite locale (utilisant le module standard `sqlite3`, sans dépendance externe).
   - Enregistre chaque `InferenceRun` sérialisé via `run_to_dict` pour permettre la réinspection ultérieure (`pyllmkit runs list`, `pyllmkit runs inspect <run_id>`).

---

## 6. Arborescence des fichiers cibles

```text
src/pyllmkit/adapters/cli/
├── __init__.py                         # Package CLI
├── main.py                             # Instance principale Typer app & callback global
├── console.py                          # Console Rich partagée (stdout / stderr configurés)
├── config.py                           # Chargement de la configuration ~/.config/pyllmkit/
├── formatting/
│   ├── __init__.py
│   ├── tables.py                       # Générateurs de Table Rich (models, providers, deployments)
│   ├── panels.py                       # Générateurs de Panel Rich (résumés de run, tokens, coûts)
│   ├── reports.py                      # Formatage des rapports d'audit DeploymentResolutionReport
│   └── errors.py                       # Formatage des exceptions de domaine en panneaux d'erreur
└── commands/
    ├── __init__.py
    ├── providers.py                    # pyllmkit providers list / inspect
    ├── models.py                       # pyllmkit models list / inspect
    ├── deployments.py                  # pyllmkit deployments list
    ├── resolve.py                      # pyllmkit resolve
    ├── run.py                          # pyllmkit run
    ├── stream.py                       # pyllmkit stream
    └── tools.py                        # pyllmkit tools validate
```

---

## 7. Plan d'implémentation par lots (Phasage recommandé)

Pour respecter la rigueur méthodologique du projet (lots isolés, tests automatisés, pas de régression) :

| Lot | Contenu technique | Critères d'acceptation |
|---|---|---|
| **Lot CLI.1 - Boot & Packaging** | Déclaration de l'extra `[cli]` dans `pyproject.toml`, point d'entrée script `pyllmkit`, structure du sous-package, commande `pyllmkit --help` et version. | Clean install testée, zéro import de Typer si extra non installé, aide formatée. |
| **Lot CLI.2 - Catalogue & Inspection** | Commandes `providers list/inspect`, `models list`, `deployments list` et `resolve`. Formatage des tableaux et arbres Rich. | Tests unitaires avec `typer.testing.CliRunner`, rendu vérifié sur les 6 fournisseurs. |
| **Lot CLI.3 - Inférence texte (`run`)** | Commande `pyllmkit run` connectée à `InferenceService.invoke()`. Gestion des options de génération et affichage de l'usage. | Invocations offline vérifiées sur les mocks, gestion des erreurs via taxonomie S3. |
| **Lot CLI.4 - Streaming interactif (`stream`)** | Commande `pyllmkit stream` connectée à `StreamingInferenceService`. Rendu incrémental `rich.live.Live`, gestion propre de l'interruption `SIGINT`. | Flux textuel fluide, panneau de synthèse final, zéro socket orphelin à l'annulation. |
| **Lot CLI.5 - Persistance locale & Historique** | Implémentation du `SqliteRunStore` (stdlib `sqlite3`) et commande `pyllmkit runs list/inspect`. | Traçabilité des runs passés, aucune dépendance externe ajoutée. |

---

## 8. Conclusion et bénéfice architectural

L'ajout de cette couche CLI Typer + Rich transforme PyLLMKit en un **banc d'essai opérationnel complet** pour les développeurs et data engineers. Elle valorise immédiatement les 752 scénarios de conformité du jalon 0.3.0 en offrant une visualisation vivante, rigoureuse et interactive de la parité multi-fournisseurs.

