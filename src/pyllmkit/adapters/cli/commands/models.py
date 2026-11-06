"""Typer subcommands for model catalog inspection and synchronization."""

from typing import Annotated

import typer
from rich import box
from rich.table import Table

from ..catalog import create_reference_catalog
from ..console import console
from ..discovery import sync_configured_providers
from ..formatting.tables import build_models_table

models_app = typer.Typer(
    help="Exploration et synchronisation du catalogue des modèles.",
    no_args_is_help=True,
)


@models_app.command(name="list")
def list_models(
    family: Annotated[
        str | None,
        typer.Option("--family", "-f", help="Filtrer par famille de modèle (ex: meta, openai, anthropic)"),
    ] = None,
) -> None:
    """Lister les modèles déclarés dans le catalogue."""
    catalog = create_reference_catalog()
    models = catalog.models.list()

    if family:
        norm_fam = family.strip().lower()
        models = tuple(
            m for m in models
            if m.identity and m.identity.family and m.identity.family.value.lower() == norm_fam
        )

    table = build_models_table(models)
    console.print(table)


@models_app.command(name="sync")
def sync_models(
    provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            "-p",
            help="Filtrer par fournisseur cible (openai, anthropic, google, mistral, xai, ollama)",
        ),
    ] = None,
    local: Annotated[
        bool,
        typer.Option(
            "--local",
            "-l",
            help="Sauvegarder le cache des modèles dans le projet local (.pyllmkit/discovered_models.json)",
        ),
    ] = False,
) -> None:
    """Interroger les APIs des fournisseurs configurés pour découvrir et synchroniser les modèles."""
    console.print("[cyan]Synchronisation du catalogue des modèles auprès des fournisseurs...[/cyan]")
    total, results = sync_configured_providers(target_provider=provider, local=local)

    table = Table(title="Résultat de synchronisation des modèles", box=box.ROUNDED)
    table.add_column("Fournisseur", style="bold cyan")
    table.add_column("Modèles", justify="right")
    table.add_column("Statut / Détails")

    saved_path: str | None = None
    for prov_name, info in results.items():
        status = info.get("status", "unknown")
        count = info.get("count", 0)
        msg = info.get("message", "")
        if "path" in info and saved_path is None:
            saved_path = str(info["path"])

        if status == "success":
            table.add_row(prov_name, str(count), f"[green]{msg}[/green]")
        elif status == "skipped":
            table.add_row(prov_name, "-", f"[dim]{msg}[/dim]")
        else:
            table.add_row(prov_name, "0", f"[yellow]{msg}[/yellow]")

    console.print(table)

    if saved_path:
        console.print(f"[green]✓ {total} modèle(s) synchronisé(s) et sauvegardé(s) dans :[/green] [bold]{saved_path}[/bold]")
    else:
        console.print("[yellow]ℹ Aucun modèle supplémentaire n'a été découvert (vérifiez vos clés d'API configurées).[/yellow]")
