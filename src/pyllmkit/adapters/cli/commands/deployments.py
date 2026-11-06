"""Typer subcommands for deployment inspection."""

from typing import Annotated

import typer

from ..catalog import create_reference_catalog
from ..console import console
from ..formatting.tables import build_deployments_table

deployments_app = typer.Typer(
    help="Inspection des déploiements et liaisons opérationnelles.",
    no_args_is_help=True,
)


@deployments_app.command(name="list")
def list_deployments(
    provider: Annotated[
        str | None,
        typer.Option("--provider", "-p", help="Filtrer par fournisseur (ex: openai, anthropic, ollama)"),
    ] = None,
) -> None:
    """Lister les déploiements configurés dans le catalogue."""
    catalog = create_reference_catalog()
    deployments = catalog.deployments.list()

    if provider:
        norm_prov = provider.strip().lower()
        deployments = tuple(
            d for d in deployments
            if (d.provider_id and d.provider_id.value.lower() == norm_prov)
            or (norm_prov == "ollama" and d.runtime == "ollama")
        )

    table = build_deployments_table(deployments)
    console.print(table)
