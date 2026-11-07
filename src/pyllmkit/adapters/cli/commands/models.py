"""Typer subcommands for model catalog inspection and synchronization."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich import box
from rich.table import Table

from pyllmkit.adapters.inference.media_lifecycle import (
    POLICY,
    MediaLifecycle,
    media_model_policy,
)

from ..catalog import create_reference_catalog
from ..console import console
from ..discovery import get_discovered_models_path, sync_configured_providers
from ..discovery_snapshot_v2 import load_discovery_snapshot, snapshot_path
from ..formatting.panels import build_model_inspect_panel
from ..formatting.tables import build_models_table
from ..media_catalog_v2 import (
    diff_media_catalog,
    effective_lifecycle,
    load_media_catalog,
    reconcile_observed_ids,
)
from ..model_specs import get_model_spec

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
    pricing: Annotated[
        bool,
        typer.Option(
            "--pricing",
            "-p",
            help="Afficher les spécifications techniques et tarifs (contexte, $/1M tokens)",
        ),
    ] = False,
    media: Annotated[
        bool,
        typer.Option("--media", help="Afficher uniquement les routes du catalogue média v2"),
    ] = False,
) -> None:
    """Lister les modèles déclarés dans le catalogue."""
    if media:
        v2 = load_media_catalog()
        table = Table(title=f"Modèles médias - catalogue v{v2.schema_version}", box=box.ROUNDED)
        table.add_column("Modèle")
        table.add_column("API")
        table.add_column("Facturation")
        table.add_column("Cycle de vie")
        table.add_column("Tâches")
        for item in v2.models:
            if family and item.model_owner != family.lower().strip():
                continue
            table.add_row(
                item.public_model_id, item.api_provider, item.billing_provider,
                effective_lifecycle(item).value, ", ".join(item.capabilities.tasks),
            )
        console.print(table)
        return
    catalog = create_reference_catalog()
    models = catalog.models.list()

    if family:
        norm_fam = family.strip().lower()
        models = tuple(
            m for m in models
            if m.identity and m.identity.family and m.identity.family.value.lower() == norm_fam
        )

    table = build_models_table(models, show_pricing=pricing)
    console.print(table)


@models_app.command(name="inspect")
def inspect_model(
    model_id: Annotated[
        str,
        typer.Argument(
            help="Identifiant ou alias du modèle (ex: gpt-6-astra, claude-opus-4-6, gemini-3.8-flash)",
        ),
    ],
) -> None:
    """Afficher les caractéristiques techniques, fenêtres de contexte et tarifs d'un modèle."""
    spec = get_model_spec(model_id)
    if spec is None:
        console.print(f"[red]Erreur : Spécifications introuvables pour le modèle '{model_id}'.[/red]")
        raise typer.Exit(code=1)

    panel = build_model_inspect_panel(spec)
    console.print(panel)
    lifecycle = media_model_policy(model_id)
    if lifecycle.state is not MediaLifecycle.UNKNOWN:
        console.print(f"[bold]Cycle de vie :[/bold] {lifecycle.state.value}")
        if lifecycle.shutdown_date is not None:
            console.print(f"[bold]Retrait annoncé :[/bold] {lifecycle.shutdown_date.isoformat()}")
        if lifecycle.replacement:
            console.print(f"[bold]Remplacement candidat :[/bold] {lifecycle.replacement}")
        console.print(f"[dim]Source : {lifecycle.source_url}[/dim]")
    route = load_media_catalog().find(model_id)
    if route is not None:
        console.print(
            f"[bold]Route média v2 :[/bold] {route.api_provider} / {route.native_model_id} "
            f"(owner={route.model_owner}, billing={route.billing_provider})"
        )
        console.print(
            f"[bold]Tâches :[/bold] {', '.join(route.capabilities.tasks)} ; "
            f"observation : {route.availability} ; statut : {effective_lifecycle(route).value}"
        )


@models_app.command(name="lifecycle")
def list_media_lifecycle() -> None:
    """Inspect date-aware media model retirement status (no provider call)."""
    table = Table(title="Cycle de vie des modèles média - sources officielles", box=box.ROUNDED)
    table.add_column("Modèle")
    table.add_column("État")
    table.add_column("Date de retrait")
    table.add_column("Candidat")
    for model_id in sorted(POLICY):
        info = media_model_policy(model_id)
        table.add_row(
            model_id, info.state.value,
            info.shutdown_date.isoformat() if info.shutdown_date else "-",
            info.replacement or "-",
        )
    console.print(table)
    console.print("[dim]État documentaire, pas preuve d'accès API de ce compte.[/dim]")




@models_app.command(name="availability")
def media_availability(
    provider: Annotated[
        str | None,
        typer.Option("--provider", "-p", help="Filtrer par API fournisseur"),
    ] = None,
    task: Annotated[
        str | None,
        typer.Option("--task", "-t", help="Tâche média déclarée (ex: text_to_image)"),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", "-m", help="Identifiant public du modèle"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Résultats structurés sans accès réseau"),
    ] = False,
) -> None:
    """State declared lifecycle and cached API observations, never live availability."""
    catalog = load_media_catalog()
    try:
        selected = catalog.list(provider=provider, task=task)
        if model is not None:
            selected = tuple(x for x in selected if x.public_model_id == model)
        snapshot = load_discovery_snapshot(snapshot_path(get_discovered_models_path()))
    except ValueError as exc:
        console.print(f"[red]Catalogue invalide : {exc}[/red]")
        raise typer.Exit(code=2) from None
    recorded = snapshot.observed_ids()
    rows = [
        {
            "model": item.public_model_id,
            "api_provider": item.api_provider,
            "billing_provider": item.billing_provider,
            "lifecycle": effective_lifecycle(item).value,
            "observation": (
                "observed" if item.public_model_id in recorded.get(item.api_provider, set())
                else "catalog_only"
            ),
            "verified_at": item.verified_at.isoformat() if item.verified_at else None,
            "source_url": item.source_url,
        }
        for item in selected
    ]
    if json_output:
        typer.echo(json.dumps({
            "schema_version": 2, "revision": catalog.revision,
            "observation_revision": snapshot.revision,
            "models": rows, "account_access_verified": False,
        }, ensure_ascii=False))
        return
    table = Table(title="Disponibilité déclarative - aucun appel API", box=box.ROUNDED)
    table.add_column("Modèle")
    table.add_column("API")
    table.add_column("Facturant")
    table.add_column("Cycle de vie")
    table.add_column("Observation")
    for row in rows:
        table.add_row(
            str(row["model"]), str(row["api_provider"]),
            str(row["billing_provider"]), str(row["lifecycle"]),
            str(row["observation"]),
        )
    console.print(table)
    console.print(
        "[dim]observed = présent dans une liste fournisseur potentiellement partielle, "
        "PAS une preuve d'accès, de quota, de capacité ni de coût.[/dim]"
    )


@models_app.command(name="diff")
def diff_models(
    against: Annotated[
        Path | None,
        typer.Option("--against", help="Comparer avec un autre catalogue JSON v2"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Rapport de différences structuré hors réseau"),
    ] = False,
) -> None:
    """Compare static snapshots or reconcile incomplete provider listings, offline."""
    catalog = load_media_catalog()
    try:
        if against is not None:
            before = load_media_catalog(against)
            changes = diff_media_catalog(before, catalog)
            report: dict[str, object] = {
                "kind": "catalog_versions",
                "old_revision": before.revision,
                "new_revision": catalog.revision,
                **changes,
            }
        else:
            snapshot = load_discovery_snapshot(snapshot_path(get_discovered_models_path()))
            report = {
                "kind": "discovery_observations",
                "catalog_revision": catalog.revision,
                "observation_revision": snapshot.revision,
                "listing_complete": False,
                "differences": reconcile_observed_ids(catalog, snapshot.observed_ids()),
            }
    except (OSError, ValueError) as exc:
        console.print(f"[red]Comparaison impossible : {exc}[/red]")
        raise typer.Exit(code=2) from None
    if json_output:
        typer.echo(json.dumps(report, ensure_ascii=False))
        return
    console.print(f"[bold]Diff catalogue :[/bold] {report['kind']}")
    if against is not None:
        for name in ("added", "removed", "changed"):
            items = report[name]
            assert isinstance(items, tuple)
            console.print(f"[cyan]{name}[/cyan] ({len(items)}): {', '.join(items) or '-'}")
    else:
        differences = report["differences"]
        assert isinstance(differences, tuple)
        totals = {
            kind: sum(item["comparison"] == kind for item in differences)
            for kind in ("observed", "catalog_only", "observed_only")
        }
        console.print(json.dumps(totals, ensure_ascii=False))
        console.print(
            "[dim]Absence dans /models != retrait. Les listes sont incomplètes "
            "et ne valident pas les droits d'accès.[/dim]"
        )


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
