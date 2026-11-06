# Référence de la CLI PyLLMKit

La CLI `pyllmkit` est un adaptateur de pilotage (Driving Adapter) basé sur **Typer** et **Rich**. Elle permet d'inspecter le catalogue de modèles et déploiements, de tester la résolution déterministe, d'exécuter des inférences textuelles bloquantes ou en flux continu (streaming), de valider des schémas d'outils (P4-JSON-1) et de consulter l'historique d'exécution local.

---

## 1. Installation et dépendances optionnelles

Conformément à la règle d'architecture stricte de PyLLMKit, le noyau (`src/pyllmkit/domain`) a **zéro dépendance externe**. La CLI et sa mise en forme Rich sont packagées dans l'extra optionnel `cli` :

```bash
# Installation avec l'interface en ligne de commande
pip install "pyllmkit[cli]"
```

Une fois installé, le point d'entrée exécutable `pyllmkit` est disponible dans le PATH, ou exécutable via `python -m pyllmkit.adapters.cli`.

---

## 2. Vue d'ensemble des commandes

```
Usage: pyllmkit [OPTIONS] COMMAND [ARGS]...

Options:
  --version, -v   Afficher la version de pyllmkit et quitter.
  --help          Afficher l'aide générale.

Commandes :
  providers       Inspection des 6 fournisseurs d'inférence supportés.
  models          Exploration du catalogue de modèles et filtrage par famille.
  deployments     Inspection des déploiements et runtimes associés.
  resolve         Simulation déterministe de la résolution de déploiement.
  run             Exécution d'une inférence textuelle bloquante.
  stream          Consommation en streaming avec affichage incrémental Rich.
  runs            Consultation et inspection de l'historique local SQLite.
  tools           Validation locale de définitions d'outils et schémas P4-JSON-1.
```

---

## 3. Commandes d'inspection du catalogue

### `pyllmkit providers list`
Affiche le tableau des fournisseurs d'inférence intégrés (Phase 7 / Jalon 0.3.0) :
- Fournisseurs couverts : Ollama (local), OpenAI (cloud), Anthropic (cloud), Google Gemini (cloud), xAI Grok (cloud), Mistral AI (cloud).
- Colonnes : Nom, Profil technique, Runtime, Endpoint approuvé, Variable de secret, Protocole / Transport.

```bash
pyllmkit providers list
```

### `pyllmkit providers inspect <provider_id>`
Affiche la fiche détaillée d'un fournisseur sous forme de panneau Rich.
- **Règle de sécurité** : les clés d'API et secrets ne sont jamais affichés ni journalisés en clair.

```bash
pyllmkit providers inspect openai
pyllmkit providers inspect ollama
```

### `pyllmkit models list [OPTIONS]`
Liste les modèles déclarés dans le catalogue de référence.
- Options :
  - `--family, -f TEXT` : filtrer par famille de modèle (ex: `meta`, `openai`, `anthropic`).

```bash
pyllmkit models list
pyllmkit models list --family meta
```

### `pyllmkit deployments list [OPTIONS]`
Liste les déploiements opérationnels reliant les modèles aux fournisseurs.
- Options :
  - `--provider, -p TEXT` : filtrer par identifiant de fournisseur.

```bash
pyllmkit deployments list
pyllmkit deployments list --provider mistral
```

### `pyllmkit resolve --model <model_id>`
Simule la résolution déterministe selon les exigences de modalités textuelles.
- Affiche le déploiement retenu (`DeploymentId`), le nombre de candidats examinés et éligibles.
- En cas d'échec (modèle inconnu ou aucun déploiement compatible), affiche un panneau d'erreur et sort avec le code `1`.

```bash
pyllmkit resolve --model gpt-4o
```

---

## 4. Inférence textuelle (`run` et `stream`)

### `pyllmkit run <prompt> [OPTIONS]`
Exécute une inférence synchrone et bloquante.
- Arguments :
  - `prompt` : texte de l'invite utilisateur.
- Options :
  - `--model, -m TEXT` : identifiant du modèle cible (défaut : `gpt-4o`).
  - `--system, -s TEXT` : instruction système préalable optionnelle.
  - `--temperature, -t FLOAT` : température d'échantillonnage (0.0 à 2.0).
  - `--max-tokens INTEGER` : nombre maximal de tokens générés en sortie.
  - `--mock / --live` : basculer entre la simulation hermétique hors ligne (par défaut : simulation) et les véritables appels réseau.

```bash
# Inférence par défaut (simulation offline)
pyllmkit run "Explique la photosynthèse en deux phrases."

# Inférence avec modèle et instruction système
pyllmkit run "Résume ce contrat" --model claude-3-5-sonnet --system "Tu es un juriste spécialisé."
```

### `pyllmkit stream <prompt> [OPTIONS]`
Consomme un flux continu d'événements et rend les deltas textuels en direct grâce à `rich.live.Live`.
- Gère proprement `Ctrl+C` (`KeyboardInterrupt`) : annule la session via `session.cancel()`, affiche un bandeau d'interruption et sort avec le code `130`.

```bash
pyllmkit stream "Raconte une fable en prose" --model gpt-4o
```

---

## 5. Historique local et persistance SQLite (`runs`)

Pour assurer une traçabilité complète sans imposer de dépendance externe lourde (ORM ou base de données distante), PyLLMKit embarque un adaptateur léger `SqliteRunStore` s'appuyant exclusivement sur le module standard `sqlite3` de Python.

- Emplacement par défaut : `~/.config/pyllmkit/history.db`.
- Surcharge hermétique : via la variable d'environnement `PYLLMKIT_HISTORY_DB`.

### `pyllmkit runs list [OPTIONS]`
Affiche le tableau récapitulatif des dernières inférences exécutées.
- Options :
  - `--limit, -n INTEGER` : nombre d'exécutions à afficher (défaut : 20).

```bash
pyllmkit runs list
pyllmkit runs list --limit 5
```

### `pyllmkit runs inspect <run_id>`
Inspecte une exécution spécifique à partir de son Run ID ou d'un préfixe unique.
- Affiche les métadonnées complètes, l'invite initiale, la réponse générée, la durée d'exécution et les métriques de tokens.

```bash
pyllmkit runs inspect 36af42490fd4
```

---

## 6. Outillage et validation de schémas (`tools`)

### `pyllmkit tools validate <path>`
Valide localement la conformité d'une définition d'outil ou d'un schéma d'arguments au profil structurel **P4-JSON-1**.
- Vérifie la syntaxe JSON.
- Vérifie la conformité du profil strict (interdiction des mots-clés non supportés comme `$schema`, `patternProperties`, etc.).
- Valide l'identifiant ASCII de l'outil et ses contraintes d'arité.

```bash
pyllmkit tools validate path/to/my_tool.json
```

---

## 7. Codes de sortie (Exit Codes)

| Code | Signification |
|:---:|:---|
| `0` | Succès de l'opération. |
| `1` | Erreur fonctionnelle ou métier (modèle inconnu, rejet de résolution, schéma invalide, échec fournisseur). |
| `2` | Erreur inattendue ou exception non rattrapée. |
| `130` | Interruption par l'utilisateur (`SIGINT` / `Ctrl+C`). |

