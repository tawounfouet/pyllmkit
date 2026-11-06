"""Typer subcommands for provider catalog inspection."""

from typing import Annotated

import typer
from rich.panel import Panel

from ..console import console
from ..formatting.tables import SUPPORTED_PROVIDERS, build_providers_table

providers_app = typer.Typer(
    help="Inspection des fournisseurs d'inférence supportés.",
    no_args_is_help=True,
)


@providers_app.command(name="list")
def list_providers() -> None:
    """Lister les 6 fournisseurs d'inférence certifiés par PyLLMKit."""
    table = build_providers_table()
    console.print(table)


@providers_app.command(name="inspect")
def inspect_provider(
    name: Annotated[
        str,
        typer.Argument(help="Identifiant du fournisseur (ex: ollama, openai, anthropic, google, xai, mistral)"),
    ],
) -> None:
    """Afficher les détails de connexion et règles d'un fournisseur."""
    norm_name = name.strip().lower()
    matched = next((p for p in SUPPORTED_PROVIDERS if p["id"] == norm_name or p["profile"] == norm_name), None)

    if matched is None:
        console.print(f"[bold red]Erreur :[/bold red] Fournisseur inconnu '{name}'.")
        console.print("Fournisseurs valides : " + ", ".join(p["id"] for p in SUPPORTED_PROVIDERS))
        raise typer.Exit(code=1)

    details = [
        f"[bold]Nom officiel       :[/bold] {matched['name']}",
        f"[bold]Profil technique   :[/bold] {matched['profile']}",
        f"[bold]Runtime            :[/bold] {matched['runtime']}",
        f"[bold]Endpoint approuvé  :[/bold] [green]{matched['endpoint']}[/green]",
        f"[bold]Variable de secret :[/bold] [yellow]{matched['env_var']}[/yellow]",
        f"[bold]Protocole          :[/bold] [cyan]{matched['protocol']}[/cyan]",
        "",
        "[dim]Note de sécurité : les clés d'API ne sont résolues qu'à l'exécution et ne sont jamais journalisées.[/dim]",
    ]

    panel = Panel(
        "\n".join(details),
        title=f"Configuration Fournisseur : {matched['name']}",
        border_style="cyan",
    )
    console.print(panel)

