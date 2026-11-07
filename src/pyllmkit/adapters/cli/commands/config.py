"""Typer commands for configuration management (pyllmkit config)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from ..config import (
    API_KEY_ENV_MAPPINGS,
    ensure_in_gitignore,
    generate_template_config,
    load_and_apply_config,
    mask_secret,
)
from ..console import console

config_app = typer.Typer(
    name="config",
    help="Gestion et inspection de la configuration PyLLMKit (clés API, chemins, valeurs par défaut).",
    no_args_is_help=True,
)


@config_app.command(name="show", help="Afficher la configuration active, les clés d'API et les chemins de stockage.")
def config_show() -> None:
    """Inspecter la configuration active avec cascade local/global."""
    cfg = load_and_apply_config()

    if cfg.config_path and cfg.global_config_path and cfg.config_path != cfg.global_config_path:
        header = (
            f"[bold]Fichier local (projet)  :[/bold] [cyan]{cfg.config_path}[/cyan] [bold green](Prioritaire)[/bold green]\n"
            f"[bold]Fichier global (machine) :[/bold] [dim]{cfg.global_config_path}[/dim] [blue](Fallback)[/blue]"
        )
    elif cfg.config_path:
        header = f"[bold]Fichier de configuration :[/bold] [cyan]{cfg.config_path}[/cyan]"
    else:
        header = "[bold]Fichier de configuration :[/bold] [dim]Aucun fichier actif (valeurs par défaut)[/dim]"

    console.print(Panel(header, border_style="cyan"))

    # Clés d'API
    key_table = Table(title="Clés d'API & Fournisseurs")
    key_table.add_column("Fournisseur", style="magenta")
    key_table.add_column("Variable d'env", style="green")
    key_table.add_column("Source", style="blue")
    key_table.add_column("Statut / Clé masquée", style="bold")

    providers = ["openai", "anthropic", "google", "mistral", "xai"]
    for prov in providers:
        canonical_env = API_KEY_ENV_MAPPINGS.get(prov, f"{prov.upper()}_API_KEY")
        local_val = cfg.local_api_keys.get(prov) or cfg.local_api_keys.get(f"{prov}_api_key")
        global_val = cfg.global_api_keys.get(prov) or cfg.global_api_keys.get(f"{prov}_api_key")
        env_val = os.environ.get(canonical_env)

        if local_val:
            source = "[green]Local (projet)[/green]"
            val_display = f"[green]{mask_secret(local_val)}[/green]"
        elif global_val:
            source = "[blue]Global (machine)[/blue]"
            val_display = f"[green]{mask_secret(global_val)}[/green]"
        elif env_val:
            source = "Environnement"
            val_display = f"[green]{mask_secret(env_val)}[/green]"
        else:
            source = "-"
            val_display = "[dim]Non configurée[/dim]"

        key_table.add_row(prov.capitalize(), canonical_env, source, val_display)

    console.print(key_table)

    # Chemins de stockage
    history_db = cfg.storage.history_db or Path.home() / ".config" / "pyllmkit" / "history.db"
    export_dir = cfg.storage.export_dir or Path.cwd()
    assets_dir = cfg.storage.assets_dir or Path.cwd() / "assets"

    is_local_db = (
        cfg.config_path is not None
        and cfg.storage.history_db is not None
        and history_db.is_relative_to(cfg.config_path.parent)
    )
    is_local_export = (
        cfg.config_path is not None
        and cfg.storage.export_dir is not None
        and export_dir.is_relative_to(cfg.config_path.parent)
    )
    is_local_assets = (
        cfg.config_path is not None
        and cfg.storage.assets_dir is not None
        and assets_dir.is_relative_to(cfg.config_path.parent)
    )

    storage_table = Table(title="Chemins de Stockage")
    storage_table.add_column("Ressource", style="cyan", no_wrap=True)
    storage_table.add_column("Source", style="blue", no_wrap=True)
    storage_table.add_column("Chemin configuré", style="yellow", overflow="fold")
    storage_table.add_row(
        "Base de données SQLite",
        "[green]Local (.pyllmkit.yaml)[/green]" if is_local_db else "[blue]Global (~/.config)[/blue]",
        str(history_db),
    )
    storage_table.add_row(
        "Dossier d'export par défaut",
        "[green]Local (.pyllmkit.yaml)[/green]" if is_local_export else "[dim]Défaut (courant)[/dim]",
        str(export_dir),
    )
    storage_table.add_row(
        "Dossier des artifacts / assets",
        "[green]Local (.pyllmkit.yaml)[/green]" if is_local_assets else "[dim]Défaut (./assets)[/dim]",
        str(assets_dir),
    )
    console.print(storage_table)

    # Valeurs par défaut
    defaults_lines = [
        f"[bold]Modèle par défaut      :[/bold] {cfg.defaults.model or 'gpt-4o'}",
        "[bold]Exécution live        :[/bold] [yellow]Uniquement avec --live explicite (defaults.live ignoré)[/yellow]",
        f"[bold]Température            :[/bold] {cfg.defaults.temperature if cfg.defaults.temperature is not None else '[dim]Non définie (défaut API)[/dim]'}",
        f"[bold]Max Tokens             :[/bold] {cfg.defaults.max_tokens if cfg.defaults.max_tokens is not None else '[dim]Non défini (défaut API)[/dim]'}",
        f"[bold]System Prompt          :[/bold] {cfg.defaults.system_prompt if cfg.defaults.system_prompt else '[dim]Non défini[/dim]'}",
    ]
    console.print(Panel("\n".join(defaults_lines), title="Inférence - Valeurs par défaut", border_style="blue"))


@config_app.command(name="path", help="Afficher le chemin du fichier de configuration actif.")
def config_path() -> None:
    """Afficher le chemin du fichier de configuration."""
    cfg = load_and_apply_config()
    if cfg.config_path and cfg.global_config_path and cfg.config_path != cfg.global_config_path:
        console.print(f"[bold green]✓[/bold green] Fichier local (prioritaire) : [bold cyan]{cfg.config_path}[/bold cyan]")
        console.print(f"[bold blue]ℹ[/bold blue] Fichier global (fallback)   : [dim]{cfg.global_config_path}[/dim]")
    elif cfg.config_path:
        console.print(f"[bold green]✓[/bold green] Fichier actif : [bold cyan]{cfg.config_path}[/bold cyan]")
    else:
        console.print("[dim]Aucun fichier de configuration trouvé dans les emplacements standard.[/dim]")


@config_app.command(name="init", help="Générer un fichier de configuration modèle (.yaml ou .json).")
def config_init(
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Chemin spécifique du fichier à créer"),
    ] = None,
    local: Annotated[
        bool,
        typer.Option("--local", "-l", help="Créer la configuration dans le projet local (.pyllmkit.yaml, prioritaire sur le global)"),
    ] = False,
    format_type: Annotated[
        str,
        typer.Option("--format", "-f", help="Format de configuration: 'yaml' (recommandé) ou 'json'"),
    ] = "yaml",
    force: Annotated[
        bool,
        typer.Option("--force", help="Écraser le fichier s'il existe déjà"),
    ] = False,
) -> None:
    """Initialiser un fichier de configuration prêt à l'emploi (global ou local)."""
    fmt = format_type.lower()
    if fmt not in ("yaml", "yml", "json"):
        console.print("[bold red]Format invalide.[/bold red] Utilisez 'yaml' ou 'json'.")
        raise typer.Exit(code=1)

    ext = "yaml" if fmt in ("yaml", "yml") else "json"

    if path is not None:
        target_path = path.expanduser().resolve()
        if target_path.suffix.lower() == ".json":
            fmt = "json"
        elif target_path.suffix.lower() in (".yaml", ".yml"):
            fmt = "yaml"
    elif local:
        target_path = (Path.cwd() / f".pyllmkit.{ext}").resolve()
    else:
        cfg_dir = Path.home() / ".config" / "pyllmkit"
        target_path = cfg_dir / f"config.{ext}"

    if target_path.exists() and not force:
        console.print(
            f"[bold yellow]Le fichier '{target_path}' existe déjà.[/bold yellow] Utilisez '--force' pour l'écraser."
        )
        raise typer.Exit(code=1)

    content = generate_template_config(format_type=fmt, local=local)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")

    console.print(
        f"[bold green]✓[/bold green] Fichier de configuration généré avec succès dans : [bold cyan]{target_path}[/bold cyan]"
    )

    if local:
        added = ensure_in_gitignore(target_path.parent)
        if added:
            console.print("[bold green]✓[/bold green] Ajouté '.pyllmkit*' à .gitignore pour exclure la configuration et la base SQLite locale.")

    console.print("[dim]Vous pouvez maintenant éditer ce fichier pour y renseigner vos clés d'API et paramètres.[/dim]")
    load_and_apply_config(target_path)
