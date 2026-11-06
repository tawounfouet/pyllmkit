"""Typer subcommands for model catalog inspection."""

from typing import Annotated

import typer

from ..catalog import create_reference_catalog
from ..console import console
from ..formatting.tables import build_models_table

models_app = typer.Typer(
    help="Exploration du catalogue des modèles.",
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
