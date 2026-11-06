"""Rich panel formatters for inference responses and execution summaries."""

from rich.panel import Panel

from pyllmkit.application.inference.contracts import InferenceExecution


def build_response_panel(execution: InferenceExecution, model_name: str) -> Panel:
    """Format a successful InferenceResponse with output text."""
    response = execution.response
    if response is None:
        return Panel("[dim]Aucune réponse générée[/dim]", title="Réponse", border_style="yellow")

    text = response.output.text
    return Panel(
        text,
        title=f"Réponse du modèle [{model_name}]",
        border_style="green",
    )


def build_usage_panel(execution: InferenceExecution) -> Panel:
    """Format execution metrics, tokens usage, and finish reason."""
    run = execution.run
    response = execution.response

    duration_str = "-"
    if run.started_at is not None and run.finished_at is not None:
        duration_ms = (run.finished_at - run.started_at).total_seconds() * 1000
        duration_str = f"{duration_ms:.1f} ms"

    raw_finish = (
        response.finish_reason.code.value
        if (response and response.finish_reason)
        else "stop"
    )
    if raw_finish == "unknown" and run.state.value == "completed":
        finish_code = "stop"
    else:
        finish_code = raw_finish

    in_tokens = "-"
    out_tokens = "-"
    if response and response.usage:
        if response.usage.input_tokens is not None:
            in_tokens = str(response.usage.input_tokens)
        if response.usage.output_tokens is not None:
            out_tokens = str(response.usage.output_tokens)

    stats = [
        f"[bold]Run ID        :[/bold] {run.run_id.value}",
        f"[bold]Statut final  :[/bold] [green]{run.state.value}[/green]",
        f"[bold]Durée         :[/bold] {duration_str}",
        f"[bold]Finish Reason :[/bold] [cyan]{finish_code}[/cyan]",
        f"[bold]Tokens In/Out :[/bold] [yellow]{in_tokens} / {out_tokens}[/yellow]",
    ]

    return Panel(
        "\n".join(stats),
        title="Statistiques d'exécution",
        border_style="dim",
    )
