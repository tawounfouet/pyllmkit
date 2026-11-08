"""Read-only FinOps CLI commands (M2-G2), no paid provider calls."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pyllmkit.adapters.cli.finops_quote import (
    load_quote_request,
    quote_media_scenario,
)
from pyllmkit.adapters.cli.media_catalog_v2 import load_media_catalog
from pyllmkit.adapters.cli.pricing_catalog_v2 import load_price_catalog
from pyllmkit.domain.finops.quoting import quote_to_dict

finops_app = typer.Typer(
    help="Devis pré-génération hors réseau. Aucun appel payant ni réservation budgétaire.",
    no_args_is_help=True,
    add_completion=False,
)


@finops_app.command(name="quote")
def quote_command(
    request: Annotated[
        Path,
        typer.Option("--request", "-r", help="Fichier de scénario JSON v1 explicite."),
    ],
    pricing_catalog: Annotated[
        Path | None,
        typer.Option(
            "--pricing-catalog",
            help="Catalogue tarifaire JSON v2 explicite. Défaut: catalogue embarqué vide.",
        ),
    ] = None,
) -> None:
    """Coter uniquement les composantes déclarées; ce résultat n'autorise pas le live."""
    try:
        scenario = load_quote_request(request)
        prices = load_price_catalog(pricing_catalog)
        quote = quote_media_scenario(scenario, prices=prices, media=load_media_catalog())
    except (OSError, ValueError) as exc:
        typer.echo(json.dumps({
            "status": "error",
            "reason": str(exc),
            "live_authorized": False,
        }, ensure_ascii=False))
        raise typer.Exit(code=2) from None

    typer.echo(json.dumps(quote_to_dict(quote), ensure_ascii=False))
    if not quote.scenario_priced:
        raise typer.Exit(code=3)
