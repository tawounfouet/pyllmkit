"""Typer commands for execution history inspection (runs list, runs inspect)."""

import json
import os
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from ..config import get_config
from ..console import console
from ..formatting.errors import build_error_panel
from ..model_specs import compute_run_cost, format_pricing_provenance, get_model_spec
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
    table.add_column("Coût estimé", justify="right", style="green")
    table.add_column("Tarif vérifié", style="dim")
    table.add_column("Date (UTC)", style="dim")
    table.caption = "Prix du catalogue local, non temps réel; voir models inspect pour la source."

    for rec in records:
        status_style = "green" if rec.state == "completed" else "red"
        dur_str = f"{rec.duration_ms:.1f}" if rec.duration_ms is not None else "-"
        in_t = str(rec.input_tokens) if rec.input_tokens is not None else "-"
        out_t = str(rec.output_tokens) if rec.output_tokens is not None else "-"
        tokens_str = f"{in_t} / {out_t}"

        tot_cost, _ = compute_run_cost(
            rec.model_id,
            rec.input_tokens,
            rec.output_tokens,
            cached_tokens=rec.cached_tokens,
        )
        if tot_cost is not None:
            cost_cell = f"${tot_cost:.5f}" if tot_cost > 0 else "$0.00"
        elif rec.input_tokens is not None or rec.output_tokens is not None:
            cost_cell = "N/A"
        else:
            cost_cell = "-"

        spec = get_model_spec(rec.model_id)
        last_verified = (spec.last_verified or "date inconnue") if spec else "N/A"

        table.add_row(
            rec.run_id[:12] + "...",
            rec.model_id,
            rec.provider,
            rec.mode,
            f"[{status_style}]{rec.state}[/{status_style}]",
            rec.finish_reason or "-",
            dur_str,
            tokens_str,
            cost_cell,
            last_verified,
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

    _, cost_str = compute_run_cost(
        record.model_id,
        record.input_tokens,
        record.output_tokens,
        cached_tokens=record.cached_tokens,
    )
    if cost_str != "-":
        details.append(f"[bold]Coût estimé   :[/bold] [bold green]{cost_str}[/bold green]")
        details.append(f"[dim]{format_pricing_provenance(record.model_id)}[/dim]")
    elif record.input_tokens is not None or record.output_tokens is not None:
        details.append("[bold]Coût estimé   :[/bold] [dim]N/A (modèle hors catalogue tarifaire)[/dim]")

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
    allow_content_export: Annotated[
        bool,
        typer.Option("--allow-content-export", help="Autoriser cet export de conversations sensibles"),
    ] = False,
) -> None:
    """Exporter les runs archivés au standard ChatML JSONL avec consentement explicite."""
    if not allow_content_export:
        console.print("[red]Export refusé : ajouter --allow-content-export.[/red]")
        raise typer.Exit(code=1)
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
        # Exported raw content is sensitive. Avoid default world-readable files.
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        flags |= getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(output, flags, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + ("\n" if lines else ""))
        except BaseException:
            # fdopen closes on exit, but a failure before fdopen still needs cleanup.
            try:
                os.close(fd)
            except OSError:
                pass
            raise
        console.print(
            f"[bold green]✓[/bold green] {len(lines)} exemple(s) exporté(s) avec succès dans [bold cyan]{output}[/bold cyan]"
        )
    else:
        for line in lines:
            console.print(line)


@runs_app.command(name="prune", help="Supprimer les runs au-delà d’une période de rétention.")
def runs_prune(
    older_than_days: Annotated[
        int, typer.Option("--older-than-days", min=1, max=36500),
    ] = 30,
    yes: Annotated[
        bool, typer.Option("--yes", help="Confirmer explicitement la suppression irréversible"),
    ] = False,
) -> None:
    """Purge metadata and opted-in sensitive content in one transaction."""
    if not yes:
        console.print("[yellow]Suppression refusée : ajouter --yes.[/yellow]")
        raise typer.Exit(code=1)
    count = SqliteRunStore().prune_older_than_days(older_than_days)
    console.print(f"[green]{count} run(s) ancien(s) supprimé(s).[/green]")


@runs_app.command(name="purge-content", help="Expurger les contenus des runs conservés.")
def runs_purge_content(
    yes: Annotated[
        bool, typer.Option("--yes", help="Confirmer l'expurgation des prompts et réponses"),
    ] = False,
    run_id: Annotated[
        str | None, typer.Option("--run-id", help="Limiter l'expurgation à ce RunId"),
    ] = None,
) -> None:
    """Remove stored conversations, preserving usage and execution metadata."""
    if not yes:
        console.print("[yellow]Expurgation refusée : ajouter --yes.[/yellow]")
        raise typer.Exit(code=1)
    count = SqliteRunStore().purge_content(run_id)
    console.print(f"[green]{count} run(s) expurgé(s).[/green]")
