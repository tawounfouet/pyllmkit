"""Typer commands for execution history inspection (runs list, runs inspect)."""

from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from ..console import console
from ..formatting.errors import build_error_panel
from ..storage import SqliteRunStore

runs_app = typer.Typer(
    name="runs",
    help="Inspection de l'historique local des inférences exécutées.",
    no_args_is_help=True,
)


@runs_app.command(name="list", help="Lister les dernières inférences exécutées.")
def runs_list(
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Nombre maximum d'exécutions à afficher"),
    ] = 20,
) -> None:
    """Afficher le tableau récapitulatif des exécutions récentes."""
    store = SqliteRunStore()
    records = store.list_runs(limit=limit)

    if not records:
        console.print("[dim]Aucune exécution enregistrée dans l'historique local.[/dim]")
        return

    table = Table(title=f"Historique des {len(records)} dernières exécutions")
    table.add_column("Run ID", style="cyan", no_wrap=True)
    table.add_column("Modèle", style="magenta", no_wrap=True)
    table.add_column("Fournisseur", style="green")
    table.add_column("Statut", style="bold", no_wrap=True)
    table.add_column("Finish", style="yellow")
    table.add_column("Durée (ms)", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Date (UTC)", style="dim")

    for rec in records:
        status_style = "green" if rec.state == "completed" else "red"
        dur_str = f"{rec.duration_ms:.1f}" if rec.duration_ms is not None else "-"
        in_t = str(rec.input_tokens) if rec.input_tokens is not None else "-"
        out_t = str(rec.output_tokens) if rec.output_tokens is not None else "-"
        tokens_str = f"{in_t} / {out_t}"

        table.add_row(
            rec.run_id[:12] + "...",
            rec.model_id,
            rec.provider,
            f"[{status_style}]{rec.state}[/{status_style}]",
            rec.finish_reason or "-",
            dur_str,
            tokens_str,
            rec.created_at[:19],
        )

    console.print(table)


@runs_app.command(name="inspect", help="Inspecter le détail d'une inférence archivée.")
def runs_inspect(
    run_id: Annotated[
        str,
        typer.Argument(help="Identifiant unique (ou préfixe) de l'inférence"),
    ],
) -> None:
    """Afficher les détails complets d'un run archivé."""
    store = SqliteRunStore()
    record = store.get_run(run_id.strip())

    if record is None:
        # Search by prefix if exact match not found
        all_runs = store.list_runs(limit=100)
        matches = [r for r in all_runs if r.run_id.startswith(run_id.strip())]
        if len(matches) == 1:
            record = matches[0]

    if record is None:
        panel = build_error_panel(
            "run_not_found",
            f"Aucune exécution trouvée avec l'identifiant '{run_id}'.",
        )
        console.print(panel)
        raise typer.Exit(code=1)

    details = [
        f"[bold]Run ID        :[/bold] {record.run_id}",
        f"[bold]Modèle        :[/bold] {record.model_id}",
        f"[bold]Fournisseur   :[/bold] {record.provider}",
        f"[bold]Statut        :[/bold] {record.state}",
        f"[bold]Finish Reason :[/bold] {record.finish_reason or '-'}",
        f"[bold]Durée         :[/bold] {record.duration_ms:.1f} ms" if record.duration_ms else "[bold]Durée         :[/bold] -",
        f"[bold]Tokens        :[/bold] In: {record.input_tokens or '-'} / Out: {record.output_tokens or '-'}",
        f"[bold]Date (UTC)    :[/bold] {record.created_at}",
    ]

    console.print(Panel("\n".join(details), title="Métadonnées du Run", border_style="cyan"))
    console.print(Panel(record.prompt, title="Invite (Prompt)", border_style="blue"))
    if record.response_text:
        console.print(Panel(record.response_text, title="Réponse", border_style="green"))
    else:
        console.print(Panel("[dim]Aucun texte de réponse enregistré[/dim]", title="Réponse", border_style="dim"))
