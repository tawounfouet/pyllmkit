"""Typer commands for tools schema validation (tools validate)."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.tooling.definitions import Tool, validate_tool_name
from pyllmkit.domain.tooling.schema import ToolSchema

from ..console import console
from ..formatting.errors import build_error_panel

tools_app = typer.Typer(
    name="tools",
    help="Validation locale et outillage pour les définitions d'outils et schémas P4-JSON-1.",
    no_args_is_help=True,
)


@tools_app.command(name="validate", help="Valider un fichier JSON de définition d'outil ou schéma.")
def tools_validate(
    path: Annotated[
        Path,
        typer.Argument(
            help="Chemin vers le fichier JSON contenant la définition de l'outil ou le schéma",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
) -> None:
    """Valider la conformité d'un outil ou d'un schéma d'arguments au profil P4-JSON-1."""
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        panel = build_error_panel("invalid_json", f"Syntaxe JSON invalide : {exc}")
        console.print(panel)
        raise typer.Exit(code=1) from None
    except Exception as exc:
        panel = build_error_panel("file_read_error", f"Impossible de lire le fichier : {exc}")
        console.print(panel)
        raise typer.Exit(code=1) from None

    if not isinstance(data, dict):
        panel = build_error_panel("invalid_format", "Le document JSON racine doit être un objet {}")
        console.print(panel)
        raise typer.Exit(code=1)

    try:
        if "name" in data and ("schema" in data or "parameters" in data):
            # Format Tool complet
            name = validate_tool_name(str(data["name"]))
            description = str(data["description"]) if data.get("description") is not None else None
            raw_schema = data.get("schema") or data.get("parameters")
            if not isinstance(raw_schema, dict):
                raise DomainValidationError("schema/parameters doit être un dictionnaire")
            tool_schema = ToolSchema(raw_schema)
            tool = Tool(name=name, description=description, schema=tool_schema)

            raw_props = tool.schema.value.get("properties")
            props = list(raw_props.keys()) if isinstance(raw_props, dict) else []
            props_str = ", ".join(props) if props else "(aucun)"

            details = [
                f"[bold]Nom de l'outil :[/bold] [green]{tool.name}[/green]",
                f"[bold]Description    :[/bold] {tool.description or '(aucune)'}",
                f"[bold]Profil schéma  :[/bold] [cyan]{tool.schema.profile}[/cyan]",
                f"[bold]Propriétés     :[/bold] {props_str}",
            ]
            console.print(
                Panel(
                    "\n".join(details),
                    title="Outil validé avec succès",
                    border_style="green",
                )
            )

        elif "type" in data:
            # Format schéma brut
            tool_schema = ToolSchema(data)
            raw_props = tool_schema.value.get("properties")
            props = list(raw_props.keys()) if isinstance(raw_props, dict) else []
            props_str = ", ".join(props) if props else "(aucun)"

            details = [
                f"[bold]Profil schéma :[/bold] [cyan]{tool_schema.profile}[/cyan]",
                f"[bold]Type racine   :[/bold] {tool_schema.value.get('type')}",
                f"[bold]Propriétés    :[/bold] {props_str}",
            ]
            console.print(
                Panel(
                    "\n".join(details),
                    title="Schéma P4-JSON-1 validé avec succès",
                    border_style="green",
                )
            )
        else:
            panel = build_error_panel(
                "unrecognized_tool_format",
                "Le fichier doit contenir soit une définition d'outil (name + schema), soit un schéma (type)",
            )
            console.print(panel)
            raise typer.Exit(code=1)

    except DomainValidationError as exc:
        panel = build_error_panel("schema_validation_error", str(exc))
        console.print(panel)
        raise typer.Exit(code=1) from None
