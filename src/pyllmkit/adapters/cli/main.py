"""Main Typer application entrypoint for PyLLMKit CLI."""

from importlib.metadata import PackageNotFoundError, version
from typing import Annotated

import typer

from .commands import (
    deployments_app,
    models_app,
    providers_app,
    resolve_command,
    run_command,
    runs_app,
    stream_command,
    tools_app,
)
from .console import console

app = typer.Typer(
    name="pyllmkit",
    help="Provider-agnostic Python domain primitives for language models.",
    no_args_is_help=True,
    add_completion=False,
)

# Enregistrement des sous-commandes d'inspection et de catalogue
app.add_typer(providers_app, name="providers")
app.add_typer(models_app, name="models")
app.add_typer(deployments_app, name="deployments")
app.command(name="resolve", help="Résolution déterministe de déploiement pour un modèle cible.")(
    resolve_command
)
app.command(name="run", help="Exécuter une inférence textuelle bloquante.")(run_command)
app.command(
    name="stream",
    help="Consommer une inférence en direct avec affichage incrémental (streaming).",
)(stream_command)
app.add_typer(runs_app, name="runs")
app.add_typer(tools_app, name="tools")


def _get_version() -> str:
    try:
        return version("pyllmkit")
    except PackageNotFoundError:
        return "0.1.0a2"


def version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold cyan]pyllmkit[/bold cyan] version [green]{_get_version()}[/green]")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Afficher la version de pyllmkit et quitter.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """CLI de gestion, inspection et inférence PyLLMKit."""
