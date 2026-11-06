"""Typer command for deterministic deployment resolution."""

from typing import Annotated

import typer

from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import ModelTarget
from pyllmkit.domain.models import ModelId
from pyllmkit.domain.providers import ProviderId
from pyllmkit.domain.registry.selection import (
    DeploymentRequirement,
    DeploymentResolutionError,
)

from ..catalog import create_reference_catalog
from ..console import console
from ..formatting.reports import build_resolution_panel


def resolve_command(
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="Identifiant du modèle cible (ex: gpt-4o, llama3.2)"),
    ],
    provider: Annotated[
        str | None,
        typer.Option("--provider", "-p", help="Filtrer optionnellement par fournisseur cible"),
    ] = None,
) -> None:
    """Résoudre de façon déterministe un déploiement éligible pour un modèle."""
    catalog = create_reference_catalog()
    resolver = DeploymentResolver(catalog.models, catalog.deployments, catalog.providers)

    target = ModelTarget(ModelId(model))
    req = (
        DeploymentRequirement(provider_id=ProviderId(provider.strip().lower()))
        if provider
        else DeploymentRequirement()
    )

    try:
        resolution = resolver.resolve(target, req)
        panel = build_resolution_panel(resolution.report)
        console.print(panel)
    except DeploymentResolutionError as exc:
        report = getattr(exc, "report", None)
        if report is not None:
            panel = build_resolution_panel(report)
            console.print(panel)
        else:
            console.print(f"[bold red]Échec de résolution :[/bold red] {exc}")
        raise typer.Exit(code=1) from None
    except DomainValidationError as exc:
        console.print(f"[bold red]Erreur de validation :[/bold red] {exc}")
        raise typer.Exit(code=1) from None
    except Exception as exc:
        console.print(f"[bold red]Erreur de résolution :[/bold red] {exc}")
        raise typer.Exit(code=2) from None
