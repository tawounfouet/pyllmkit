"""Typer commands for execution history inspection (runs list, runs inspect)."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from ..config import get_config
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
    table.add_column("Mode", style="blue")
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
            rec.mode,
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
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Afficher les données complètes au format JSON brut"),
    ] = False,
) -> None:
    """Afficher les détails complets d'un run archivé."""
    store = SqliteRunStore()
    target_id = run_id.strip()
    clean_prefix = target_id.rstrip(".").strip()
    record = store.get_run(target_id)

    if record is None and clean_prefix:
        # Recherche par préfixe (tolère les points de suspension '...' copiés depuis le tableau)
        all_runs = store.list_runs(limit=100)
        matches = [r for r in all_runs if r.run_id.startswith(clean_prefix)]
        if len(matches) == 1:
            record = matches[0]

    if record is None:
        panel = build_error_panel(
            "run_not_found",
            f"Aucune exécution trouvée avec l'identifiant '{run_id}'.",
        )
        console.print(panel)
        raise typer.Exit(code=1)

    if as_json:
        console.print_json(json.dumps(record.as_dict(), ensure_ascii=False))
        return

    details = [
        f"[bold]Run ID        :[/bold] {record.run_id}",
        f"[bold]Modèle        :[/bold] {record.model_id}",
        f"[bold]Fournisseur   :[/bold] {record.provider}",
        f"[bold]Mode          :[/bold] [bold blue]{record.mode}[/bold blue]",
        f"[bold]Statut        :[/bold] {record.state}",
        f"[bold]Finish Reason :[/bold] {record.finish_reason or '-'}",
        f"[bold]Durée         :[/bold] {record.duration_ms:.1f} ms" if record.duration_ms is not None else "[bold]Durée         :[/bold] -",
    ]
    if record.ttft_ms is not None:
        details.append(f"[bold]TTFT (1st tok):[/bold] {record.ttft_ms:.1f} ms")

    # Section FinOps Tokens
    tok_info = f"In: {record.input_tokens if record.input_tokens is not None else '-'} / Out: {record.output_tokens if record.output_tokens is not None else '-'}"
    if record.total_tokens is not None:
        tok_info += f" (Total: {record.total_tokens})"
    details.append(f"[bold]Tokens        :[/bold] {tok_info}")
    if record.cached_tokens is not None:
        details.append(f"[bold]Cached Tokens :[/bold] [green]{record.cached_tokens}[/green]")
    if record.reasoning_tokens is not None:
        details.append(f"[bold]Reasoning Tok.:[/bold] [magenta]{record.reasoning_tokens}[/magenta]")

    # Section Hyperparamètres (Evals)
    gen_parts = []
    if record.temperature is not None:
        gen_parts.append(f"temp={record.temperature}")
    if record.max_tokens is not None:
        gen_parts.append(f"max_tokens={record.max_tokens}")
    if gen_parts:
        details.append(f"[bold]Configuration :[/bold] {', '.join(gen_parts)}")
    if record.messages_json:
        details.append("[bold]Fine-Tuning   :[/bold] [green]Format ChatML / JSONL archivé[/green]")

    details.append(f"[bold]Date (UTC)    :[/bold] {record.created_at}")

    console.print(Panel("\n".join(details), title="Métadonnées du Run", border_style="cyan"))
    if record.system_prompt:
        console.print(Panel(record.system_prompt, title="Instruction Système", border_style="yellow"))
    console.print(Panel(record.prompt, title="Invite (Prompt)", border_style="blue"))
    if record.response_text:
        console.print(Panel(record.response_text, title="Réponse", border_style="green"))
    else:
        console.print(Panel("[dim]Aucun texte de réponse enregistré[/dim]", title="Réponse", border_style="dim"))


@runs_app.command(name="export", help="Exporter l'historique d'inférences au format JSONL pour le Fine-Tuning.")
def runs_export(
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Fichier de sortie .jsonl (affiche sur stdout si omis)"),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", "-m", help="Filtrer les runs par identifiant de modèle"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Nombre maximum de runs à exporter"),
    ] = 1000,
) -> None:
    """Exporter les runs archivés au standard ChatML JSONL (OpenAI, HuggingFace, Axolotl, Unsloth)."""
    store = SqliteRunStore()
    records = store.list_runs(limit=limit)
    if model:
        records = [r for r in records if r.model_id == model]

    valid_records = [r for r in records if r.state == "completed" and r.response_text]

    lines = []
    for r in valid_records:
        chatml_line = json.dumps({"messages": r.to_chatml_messages()}, ensure_ascii=False)
        lines.append(chatml_line)

    cfg = get_config()
    if output is None and cfg.storage.export_dir:
        from datetime import UTC, datetime

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        output = cfg.storage.export_dir / f"export_{stamp}.jsonl"

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        console.print(
            f"[bold green]✓[/bold green] {len(lines)} exemple(s) exporté(s) avec succès dans [bold cyan]{output}[/bold cyan]"
        )
    else:
        for line in lines:
            console.print(line)
