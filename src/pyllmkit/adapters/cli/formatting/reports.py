"""Rich formatting for resolution and diagnostic reports."""

from rich import box
from rich.panel import Panel
from rich.table import Table

from pyllmkit.domain.registry.selection import DeploymentResolutionReport


def build_resolution_panel(report: DeploymentResolutionReport) -> Panel:
    """Format a DeploymentResolutionReport as a styled Rich Panel."""
    content: list[str] = []

    if report.selected_id is not None:
        content.append(f"[bold green]✔ Déploiement retenu :[/bold green] [bold white]{report.selected_id.value}[/bold white]\n")
    else:
        content.append("[bold red]✖ Aucun déploiement compatible unique sélectionné[/bold red]\n")

    content.append(f"Candidats examinés  : {len(report.considered)}")
    content.append(f"Candidats éligibles : {len(report.eligible)}")

    if report.rejected:
        table = Table(
            title="Détail des rejets de candidats",
            box=box.SIMPLE,
            header_style="bold red",
        )
        table.add_column("Déploiement", style="bold white")
        table.add_column("Motifs de rejet", style="red")

        for rej in report.rejected:
            reasons_str = ", ".join(rej.reasons)
            table.add_row(rej.deployment_id.value, reasons_str)

        return Panel(
            table,
            title="Diagnostic de Résolution Déterministe",
            border_style="green" if report.selected_id is not None else "red",
        )

    summary_text = "\n".join(content)
    return Panel(
        summary_text,
        title="Résultat de Résolution",
        border_style="green" if report.selected_id is not None else "yellow",
    )
