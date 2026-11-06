# PyLLMKit - Plan d'implémentation : Système de Configuration Hiérarchique et Persistance de Stockage CLI

> **Statut :** PLAN D'IMPLÉMENTATION DIRECTEUR (Jalon CLI Config & Storage / 0.3.1+)
>
> **Date de référence :** 6 novembre 2026.
>
> **Baseline GitHub qualifiée :** [`main@ce16398`](https://github.com/tawounfouet/pyllmkit/commit/ce16398) (Jalon 0.3.0 consolidé, 2 731 tests, CI Python 3.11/3.12/3.13 verte).
>
> **Document d'analyse amont :** [`docs/analysis/2026-11-06_CLI_CONFIGURATION_AND_STORAGE_ANALYSIS.md`](../analysis/2026-11-06_CLI_CONFIGURATION_AND_STORAGE_ANALYSIS.md).
>
> **Guide d'utilisation associé :** [`docs/guides/01_CLI_CONFIGURATION_AND_STORAGE_GUIDE.md`](../guides/01_CLI_CONFIGURATION_AND_STORAGE_GUIDE.md).
>
> **Autorité de décision :** Propriétaire du projet.

---

## 0. Résumé exécutif et invariants de conception

Ce plan d'implémentation définit l'architecture, le découpage par lots, les contrats techniques détaillés et la trajectoire de qualification du système de configuration hiérarchique et de persistance des données pour l'interface en ligne de commande (CLI) de PyLLMKit.

### Problème résolu
Avant ce développement, l'opérateur devait exporter manuellement ses clés d'API à chaque session shell (`export OPENAI_API_KEY=...`), repréciser systématiquement les paramètres d'inférence (`--live`, `--model gpt-4o`), et mutualisait l'ensemble de ses traces d'exécution dans une base SQLite globale unique sans possibilité d'isolation par projet ou d'export structuré pour le Fine-Tuning.

### Invariants stricts

1. **Zéro dépendance obligatoire** :
   - `pyproject.toml` conserve strictement `dependencies = []`.
   - Utilisation exclusive des bibliothèques standard `json` et `tomllib` (Python >= 3.11).
   - Prise en charge native du format YAML via un parseur interne récursif léger, avec délégation transparente vers `PyYAML` uniquement si la bibliothèque est installée.
2. **Architecture hiérarchique en cascade à 4 niveaux** :
   - Niveau 1 : Option explicite CLI (`--config <fichier>` / `-c <fichier>`).
   - Niveau 2 : Variable d'environnement globale (`PYLLMKIT_CONFIG`).
   - Niveau 3 : Fichier local au projet (`.pyllmkit.yaml` / `.pyllmkit.json` découvert en remontant jusqu'à la racine Git).
   - Niveau 4 : Fichier global utilisateur (`~/.config/pyllmkit/config.yaml` / `config.json`).
3. **Sécurité et Zero-Leakage Git** :
   - Masquage systématique des clés d'API lors de l'inspection en console (`mask_secret()`).
   - Ajout automatique des motifs d'exclusion (`.pyllmkit*`, `.pyllmkit/`, `*.db`, `exports/`, `*.jsonl`) dans le `.gitignore` du projet lors de l'initialisation locale.
4. **Résolution contextuelle et déterministe des chemins** :
   - Tout chemin relatif configuré dans un fichier local (ex: `.pyllmkit/history.db`, `./exports`) est résolu par rapport au répertoire parent du fichier de configuration (`cfg_file.parent`), éliminant toute dépendance au répertoire de travail courant (CWD).
5. **Isolation étanche des tests et non-régression** :
   - Harnais de test isolé via `PYLLMKIT_CONFIG=/dev/null` dans `tests/conftest.py`.
   - Maintien rigoureux des 2 731 tests existants et garantie de non-régression.

---

## 1. Découpage par lots et chaîne de gates

| Lot | Désignation | Livrable principal | Gate associé |
|---|---|---|---|
| **CFG-L1** | Moteur de configuration & Résolution | Modèles de données `CliConfig`, découverte ascendante, fusion cascade, parseur YAML intégré | **CFG-G1 - Config Engine Ready** |
| **CFG-L2** | Commandes CLI d'administration | Groupe `pyllmkit config` : `init`, `show`, `path` avec rendu Rich et gestion `.gitignore` | **CFG-G2 - CLI Config Ready** |
| **CFG-L3** | Intégration Typer & Dépendances d'inférence | Hook `@app.callback()` d'injection globale, fallback dynamique des paramètres dans `run` et `stream` | **CFG-G3 - Runtime Injection Ready** |
| **CFG-L4** | Persistance SQLite & Export Fine-Tuning | Liaison contextuelle de `SqliteRunStore`, commande `runs export` au format ChatML JSONL | **CFG-G4 - Storage & Dataset Ready** |
| **CFG-L5** | Qualification, Documentation & Recette | Suite de tests dédiée, guides pratiques, analyse d'ingénierie et validation 100 % verte | **CFG-G5 - Production Qualification** |

---

## 2. Matrice des critères d'acceptation (CFG-AC-001 à CFG-AC-020)

| ID | Domaine | Description de l'exigence |
|---|---|---|
| **CFG-AC-001** | Parsing YAML | Un fichier `.pyllmkit.yaml` est parsé sans erreur même en l'absence de `PyYAML` dans l'environnement. |
| **CFG-AC-002** | Parsing JSON | Un fichier `.pyllmkit.json` est parsé fidèlement avec typage strict via `json.loads`. |
| **CFG-AC-003** | Cascade Prioritaire | Une valeur définie dans un fichier local surcharge la valeur correspondante du fichier global. |
| **CFG-AC-004** | Héritage Cascade | Une clé d'API définie uniquement dans le fichier global est héritée lors de l'exécution dans un projet local. |
| **CFG-AC-005** | Option CLI | L'argument `--config <path>` écrase toutes les configurations locales et globales découvertes. |
| **CFG-AC-006** | Variable d'Env | `PYLLMKIT_CONFIG` permet de cibler un fichier de configuration explicite en environnement headless / CI. |
| **CFG-AC-007** | Init Global | `pyllmkit config init` génère un fichier modèle dans `~/.config/pyllmkit/config.yaml`. |
| **CFG-AC-008** | Init Local | `pyllmkit config init --local` génère `.pyllmkit.yaml` à la racine du projet courant. |
| **CFG-AC-009** | Protection Git | `config init --local` ajoute automatiquement `.pyllmkit*` dans le fichier `.gitignore` local. |
| **CFG-AC-010** | Protection Écrasement | `config init` échoue proprement si le fichier existe déjà, sauf si l'option `--force` est spécifiée. |
| **CFG-AC-011** | Masquage Secret | `pyllmkit config show` affiche les clés d'API sous forme masquée (`sk-pr...cdef`) et indique leur source. |
| **CFG-AC-012** | Chemins Non Tronqués | Les chemins absolus de stockage s'affichent lisiblement sans troncature agressive dans `config show`. |
| **CFG-AC-013** | Résolution Relative | Un chemin relatif `.pyllmkit/history.db` est résolu par rapport au dossier du fichier `.pyllmkit.yaml`. |
| **CFG-AC-014** | Injection Env | Au démarrage de la CLI, les clés d'API configurées sont injectées dans `os.environ` si non présentes. |
| **CFG-AC-015** | Run Defaults | `pyllmkit run` utilise automatiquement le modèle et le mode configurés par défaut sans flag verbeux. |
| **CFG-AC-016** | Stream Defaults | `pyllmkit stream` respecte les paramètres configurés (température, tokens max, prompt système). |
| **CFG-AC-017** | SQLite Contextuel | Les exécutions s'enregistrent dans la base locale du projet lorsque celle-ci est configurée. |
| **CFG-AC-018** | Export ChatML | `pyllmkit runs export` génère un fichier JSONL conforme à la spécification ChatML pour le Fine-Tuning. |
| **CFG-AC-019** | Isolation Tests | L'exécution de la suite pytest n'est pas polluée par la configuration personnelle locale de l'opérateur. |
| **CFG-AC-020** | Non-régression | Les 2 731 tests existants et les tests de conformité demeurent 100 % passants. |

---

## 3. Détail technique des lots d'implémentation et extraits de code

### Lot CFG-L1 : Moteur de configuration & Découverte hiérarchique
- **Fichier créé** : [`src/pyllmkit/adapters/cli/config.py`](../../src/pyllmkit/adapters/cli/config.py)
- **Objectif** : Fournir une abstraction typée immuable capable de charger, fusionner et valider les configurations sans imposer de dépendances externes.

#### 1. Structures de données immuables typées
```python
@dataclass(frozen=True)
class StorageConfig:
    history_db: Path = Path("~/.config/pyllmkit/history.db").expanduser()
    export_dir: Path = Path("~/.config/pyllmkit/exports").expanduser()

@dataclass(frozen=True)
class DefaultsConfig:
    model: str = "gpt-4o"
    live: bool = False
    temperature: float = 0.7
    max_tokens: int = 1000
    system_prompt: str = "Tu es un assistant IA concis et précis."

@dataclass(frozen=True)
class CliConfig:
    api_keys: dict[str, str] = field(default_factory=dict)
    storage: StorageConfig = field(default_factory=StorageConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    config_file: Path | None = None
```

#### 2. Découverte locale ascendante jusqu'à la racine Git
```python
def find_config_file(start_dir: Path | None = None) -> Path | None:
    current = (start_dir or Path.cwd()).resolve()
    candidates = [".pyllmkit.yaml", ".pyllmkit.yml", ".pyllmkit.json", ".pyllmkit.toml"]
    while True:
        for name in candidates:
            cand = current / name
            if cand.is_file():
                return cand
        if (current / ".git").is_dir() or current.parent == current:
            break
        current = current.parent
    return None
```

#### 3. Parseur YAML récursif léger à zéro dépendance
```python
def _parse_simple_yaml(text: str) -> dict[str, Any]:
    res: dict[str, Any] = {}
    current_section: str | None = None

    def _cast(val: str) -> Any:
        v = val.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            return v[1:-1]
        v_lower = v.lower()
        if v_lower in ("true", "yes", "on"):
            return True
        if v_lower in ("false", "no", "off"):
            return False
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            pass
        return v

    for line in text.splitlines():
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            continue
        if not line.startswith(" ") and ":" in line:
            key, _, val = line.partition(":")
            val_s = val.strip()
            if not val_s:
                current_section = key.strip()
                res[current_section] = {}
            else:
                res[key.strip()] = _cast(val_s)
                current_section = None
        elif line.startswith("  ") and current_section and ":" in line:
            sub_key, _, sub_val = line.partition(":")
            res[current_section][sub_key.strip()] = _cast(sub_val.strip())

    return res
```

#### 4. Résolution contextuelle des chemins relatifs
```python
# Résolution contextuelle par rapport au répertoire parent du fichier découvert
if isinstance(hist_str, str) and hist_str.strip():
    hist_path = Path(hist_str)
    if not hist_path.is_absolute() and base_dir is not None:
        hist_path = (base_dir / hist_path).resolve()
    else:
        hist_path = hist_path.expanduser()
```

#### 5. Masquage de sécurité des secrets en console
```python
def mask_secret(secret: str | None) -> str:
    if not secret:
        return "[red]Non configuré[/red]"
    if len(secret) <= 8:
        return "****"
    return f"{secret[:5]}...{secret[-4:]}"
```

- **Gate associée** : **CFG-G1 - Config Engine Ready**.

---

### Lot CFG-L2 : Sous-commandes CLI d'administration (`config`)
- **Fichier créé** : [`src/pyllmkit/adapters/cli/commands/config.py`](../../src/pyllmkit/adapters/cli/commands/config.py)
- **Objectif** : Permettre à l'opérateur d'initialiser, d'inspecter et de diagnostiquer la configuration active via des commandes Typer et des rendus Rich.

#### 1. Initialisation et protection automatique `.gitignore`
```python
def _update_gitignore(project_root: Path) -> bool:
    gitignore = project_root / ".gitignore"
    patterns = [".pyllmkit*", ".pyllmkit/", "*.db", "exports/", "*.jsonl"]
    existing = gitignore.read_text("utf-8").splitlines() if gitignore.is_file() else []
    missing = [p for p in patterns if p not in existing]
    if missing:
        with open(gitignore, "a", encoding="utf-8") as f:
            if existing and existing[-1].strip():
                f.write("\n")
            f.write("# PyLLMKit local configuration & stores\n")
            for p in missing:
                f.write(f"{p}\n")
        return True
    return False

@config_app.command("init")
def config_init(
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
    fmt: str = typer.Option("yaml", "--format", "-f"),
    local: bool = typer.Option(False, "--local", "-l"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    # Détermination de la cible (local ./.pyllmkit.yaml ou global ~/.config/pyllmkit/config.yaml)
    target = path or (Path.cwd() / f".pyllmkit.{fmt}" if local else get_default_config_path(fmt=fmt))
    if target.is_file() and not force:
        console.print(f"[yellow]Le fichier '{target}' existe déjà. Utilisez '--force' pour l'écraser.[/yellow]")
        raise typer.Exit(1)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template, encoding="utf-8")
    if local:
        _update_gitignore(Path.cwd())
```

#### 2. Commande d'inspection `config show` avec traçabilité des sources
```python
@config_app.command("show")
def config_show() -> None:
    cfg = get_config()
    table = Table(title="Clés d'API & Fournisseurs", box=box.ROUNDED)
    table.add_column("Fournisseur", style="bold cyan")
    table.add_column("Variable d'env", style="dim")
    table.add_column("Source", style="green")
    table.add_column("Statut / Clé masquée")

    for prov, env_var in PROVIDERS:
        key = cfg.api_keys.get(prov.lower())
        source = "Local (projet)" if is_local else "Global (machine)"
        table.add_row(prov, env_var, source, mask_secret(key))

    console.print(table)
```

#### 3. Découverte dynamique et synchronisation des modèles (`pyllmkit models sync`)
- **Fichier créé** : [`src/pyllmkit/adapters/cli/discovery.py`](../../src/pyllmkit/adapters/cli/discovery.py)
- **Fichier mis à jour** : [`src/pyllmkit/adapters/cli/commands/models.py`](../../src/pyllmkit/adapters/cli/commands/models.py)
- **Objectif** : Interroger directement les APIs distantes des fournisseurs configurés via `urllib.request` (bibliothèque standard, zéro dépendance) pour découvrir en direct tous les modèles disponibles et alimenter le cache local (`discovered_models.json`) réinjecté dans [`create_reference_catalog()`](../../src/pyllmkit/adapters/cli/catalog.py).

```python
@models_app.command("sync")
def sync_models(
    provider: Optional[str] = typer.Option(None, "--provider", "-p"),
    local: bool = typer.Option(False, "--local", "-l"),
) -> None:
    total, results = sync_configured_providers(target_provider=provider, local=local)
    # Affiche le tableau Rich des modèles découverts par fournisseur
```

- **Gate associée** : **CFG-G2 - CLI Config Ready**.

---

### Lot CFG-L3 : Intégration Typer & Dépendances d'inférence
- **Fichiers modifiés** :
  - [`src/pyllmkit/adapters/cli/main.py`](../../src/pyllmkit/adapters/cli/main.py)
  - [`src/pyllmkit/adapters/cli/commands/run.py`](../../src/pyllmkit/adapters/cli/commands/run.py)
  - [`src/pyllmkit/adapters/cli/commands/stream.py`](../../src/pyllmkit/adapters/cli/commands/stream.py)

#### 1. Hook de démarrage `@app.callback()` dans `main.py`
```python
@app.callback()
def main_callback(
    config_file: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Chemin explicite vers le fichier de configuration."),
    ] = None,
) -> None:
    load_and_apply_config(config_path=config_file)
```

#### 2. Injection globale et synchronisation d'environnement
```python
def load_and_apply_config(config_path: Path | None = None) -> CliConfig:
    global _ACTIVE_CONFIG
    cfg = load_config(explicit_path=config_path)
    _ACTIVE_CONFIG = cfg

    # 1. Injection des clés d'API résolues dans os.environ
    for k, v in cfg.api_keys.items():
        env_var = PROVIDER_ENV_MAP.get(k.lower())
        if env_var and env_var not in os.environ and v:
            os.environ[env_var] = v

    # 2. Configuration du store SQLite
    os.environ["PYLLMKIT_HISTORY_DB"] = str(cfg.storage.history_db)
    return cfg
```

#### 3. Prise en compte transparente dans `pyllmkit run` et `stream`
```python
# Exemple dans src/pyllmkit/adapters/cli/commands/run.py
cfg = get_config()
target_model = model or cfg.defaults.model
is_live = live if live is not None else cfg.defaults.live
effective_temp = temperature if temperature is not None else cfg.defaults.temperature
effective_max_tokens = max_tokens if max_tokens is not None else cfg.defaults.max_tokens
```

- **Gate associée** : **CFG-G3 - Runtime Injection Ready**.

---

### Lot CFG-L4 : Persistance SQLite contextuelle & Export Fine-Tuning
- **Fichiers modifiés** :
  - [`src/pyllmkit/adapters/cli/storage/sqlite_store.py`](../../src/pyllmkit/adapters/cli/storage/sqlite_store.py)
  - [`src/pyllmkit/adapters/cli/commands/runs.py`](../../src/pyllmkit/adapters/cli/commands/runs.py)

#### 1. Résolution dynamique du store SQLite
```python
class SqliteRunStore:
    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            cfg = get_config()
            self._db_path = cfg.storage.history_db
        else:
            self._db_path = db_path
```

#### 2. Commande `pyllmkit runs export` (Format ChatML JSONL)
```python
@runs_app.command("export")
def runs_export(
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
) -> None:
    cfg = get_config()
    store = SqliteRunStore()
    records = store.list_runs(limit=10000, model=model)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = output or (cfg.storage.export_dir / f"export_{ts}.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for r in records:
            messages = []
            if r.system_prompt:
                messages.append({"role": "system", "content": r.system_prompt})
            messages.append({"role": "user", "content": r.prompt})
            messages.append({"role": "assistant", "content": r.response_text})
            f.write(json.dumps({"messages": messages}, ensure_ascii=False) + "\n")
            count += 1

    console.print(f"[green]✓ {count} exemple(s) exporté(s) avec succès dans {out_path}[/green]")
```

- **Gate associée** : **CFG-G4 - Storage & Dataset Ready**.

---

### Lot CFG-L5 : Qualification, Documentation & Recette
- **Fichiers créés / adaptés** :
  - [`tests/cli/test_cli_config.py`](../../tests/cli/test_cli_config.py)
  - [`tests/conftest.py`](../../tests/conftest.py)

#### 1. Isolation étanche dans `tests/conftest.py`
```python
@pytest.fixture(autouse=True)
def isolate_pyllmkit_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isole les tests de la configuration personnelle de la machine."""
    import pyllmkit.adapters.cli.config as cfg_module
    cfg_module._ACTIVE_CONFIG = None
    monkeypatch.setenv("PYLLMKIT_CONFIG", "/dev/null")
```

#### 2. Tests unitaires automatisés
```python
def test_cli_config_local_overrides_global(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Écriture du fichier global
    global_cfg = tmp_path / "global.yaml"
    global_cfg.write_text("api_keys:\n  openai: global_key\ndefaults:\n  model: gpt-3.5-turbo\n")
    # 2. Écriture du fichier local
    local_cfg = tmp_path / "project" / ".pyllmkit.yaml"
    local_cfg.parent.mkdir()
    local_cfg.write_text("defaults:\n  model: gpt-4o\n")
    # 3. Chargement et vérification de la cascade
    cfg = load_config(explicit_path=None)
    assert cfg.defaults.model == "gpt-4o"          # Surcharge locale
    assert cfg.api_keys["openai"] == "global_key"  # Héritage global
```

- **Gate associée** : **CFG-G5 - Production Qualification**.

---

## 4. Matrice des risques et conditions strictes de NO-GO

Toute survenance de l'une des conditions suivantes entraîne le blocage immédiat de la livraison :

1. **Régression de dépendances** : Présence de dépendances de parsing externes obligatoires dans `pyproject.toml`.
2. **Fuite de secret** : Affichage d'une clé d'API en clair lors d'un `pyllmkit config show` ou oubli d'exclusion dans `.gitignore`.
3. **Pollution croisée de tests** : Exécution d'un appel réseau réel en test unitaire causée par la présence d'une configuration globale `live: true` sur la machine de développement.
4. **Collision de chemins relatifs** : Résolution erronée d'un chemin de base de données relative au répertoire CWD au lieu du répertoire racine du projet.
5. **Régression de la suite de tests** : Échec d'un seul test parmi les 2 731 tests de la suite historique.

---

## 5. Stratégie de qualification et validation de conformité

1. **Tests unitaires et d'isolation** :
   ```sh
   pytest tests/cli/test_cli_config.py tests/cli/test_cli_storage.py -v
   ```
2. **Suite complète de non-régression** :
   ```sh
   pytest tests/
   # Résultat validé : 2 781 tests passés avec succès
   ```
3. **Audit de style et vérification statique des types** :
   ```sh
   ruff check src/ tests/
   mypy src/
   # Résultat validé : 0 erreur sur les 143 fichiers sources
   ```
4. **Contrôle typographique et intégrité documentaire** :
   - Strict respect de la règle d'exclusion du tiret cadratin (`U+2014`).
   - Utilisation exclusive de liens relatifs pour toute référence entre fichiers.
