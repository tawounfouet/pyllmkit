"""Rich panel formatters for inference responses and execution summaries."""

from rich.panel import Panel

from pyllmkit.adapters.cli.model_specs import ModelSpec, compute_run_cost, pricing_provenance
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


def build_usage_panel(
    execution: InferenceExecution,
    model_name: str | None = None,
    provider_name: str | None = None,
) -> Panel:
    """Format execution metrics, tokens usage, finish reason, and FinOps cost."""
    run = execution.run
    response = execution.response

    duration_str = "-"
    duration_ms = 0.0
    if run.started_at is not None and run.finished_at is not None:
        duration_ms = (run.finished_at - run.started_at).total_seconds() * 1000
        duration_str = f"{duration_ms:.1f} ms"

    raw_finish = (
        response.finish_reason.code.value
        if (response and response.finish_reason)
        else "unknown"
    )
    finish_code = raw_finish

    in_tokens: int | None = None
    out_tokens: int | None = None
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None

    if response and response.usage:
        in_tokens = response.usage.input_tokens
        out_tokens = response.usage.output_tokens
        cached_tokens = response.usage.cached_input_tokens
        reasoning_tokens = response.usage.reasoning_tokens

    in_str = str(in_tokens) if in_tokens is not None else "-"
    out_str = str(out_tokens) if out_tokens is not None else "-"
    total_tokens = (
        (in_tokens or 0) + (out_tokens or 0)
        if (in_tokens is not None or out_tokens is not None)
        else None
    )

    tok_parts = [f"[yellow]{in_str} / {out_str}[/yellow]"]
    if total_tokens is not None:
        tok_parts.append(f"[dim](total: {total_tokens})[/dim]")
    if isinstance(cached_tokens, (int, float)) and cached_tokens > 0:
        tok_parts.append(f"[green](dont {int(cached_tokens)} en cache)[/green]")
    if isinstance(reasoning_tokens, (int, float)) and reasoning_tokens > 0:
        tok_parts.append(f"[magenta](dont {int(reasoning_tokens)} reasoning)[/magenta]")
    tokens_display = " ".join(tok_parts)

    tps_str = ""
    if duration_ms > 0 and out_tokens and out_tokens > 0:
        tps = out_tokens / (duration_ms / 1000)
        tps_str = f" [dim]({tps:.1f} tok/s)[/dim]"

    resolved_model = model_name
    if not resolved_model and hasattr(run, "request") and hasattr(run.request, "target"):
        target = getattr(run.request, "target", None)
        if target and hasattr(target, "model_id"):
            resolved_model = getattr(target.model_id, "value", None)

    stats = [
        f"[bold]Run ID        :[/bold] {run.run_id.value}",
    ]
    if resolved_model:
        stats.append(f"[bold]Modèle        :[/bold] [bold white]{resolved_model}[/bold white]")
    if provider_name:
        stats.append(f"[bold]Fournisseur   :[/bold] [yellow]{provider_name}[/yellow]")

    stats.extend([
        f"[bold]Statut final  :[/bold] [green]{run.state.value}[/green]",
        f"[bold]Durée         :[/bold] {duration_str}{tps_str}",
        f"[bold]Finish Reason :[/bold] [cyan]{finish_code}[/cyan]",
        f"[bold]Tokens In/Out :[/bold] {tokens_display}",
    ])

    if resolved_model:
        _, cost_str = compute_run_cost(
            resolved_model,
            in_tokens,
            out_tokens,
            cached_tokens=cached_tokens,
        )
        if cost_str != "-":
            stats.append(f"[bold]Coût estimé   :[/bold] [bold green]{cost_str}[/bold green]")
            stats.append(f"[dim]{pricing_provenance(resolved_model)}[/dim]")
        elif in_tokens is not None or out_tokens is not None:
            stats.append("[bold]Coût estimé   :[/bold] [dim]N/A (modèle hors catalogue tarifaire)[/dim]")

    return Panel(
        "\n".join(stats),
        title="Statistiques d'exécution",
        border_style="dim",
    )


def build_stream_usage_panel(
    run_id: str,
    duration_ms: float,
    finish_reason: str | None,
    in_tokens: int | None = None,
    out_tokens: int | None = None,
    cached_tokens: int | None = None,
    reasoning_tokens: int | None = None,
    ttft_ms: float | None = None,
    model_name: str | None = None,
    provider_name: str | None = None,
    exit_code: int = 0,
) -> Panel:
    """Format execution metrics and FinOps cost for streaming sessions."""
    finish_code = finish_reason or "unknown"
    status_str = (
        "[green]completed[/green]"
        if exit_code == 0
        else f"[red]failed (exit {exit_code})[/red]"
    )

    in_str = str(in_tokens) if in_tokens is not None else "-"
    out_str = str(out_tokens) if out_tokens is not None else "-"
    total_tokens = (
        (in_tokens or 0) + (out_tokens or 0)
        if (in_tokens is not None or out_tokens is not None)
        else None
    )

    tok_parts = [f"[yellow]{in_str} / {out_str}[/yellow]"]
    if total_tokens is not None:
        tok_parts.append(f"[dim](total: {total_tokens})[/dim]")
    if isinstance(cached_tokens, (int, float)) and cached_tokens > 0:
        tok_parts.append(f"[green](dont {int(cached_tokens)} en cache)[/green]")
    if isinstance(reasoning_tokens, (int, float)) and reasoning_tokens > 0:
        tok_parts.append(f"[magenta](dont {int(reasoning_tokens)} reasoning)[/magenta]")
    tokens_display = " ".join(tok_parts)

    tps_str = ""
    if duration_ms > 0 and out_tokens and out_tokens > 0:
        tps = out_tokens / (duration_ms / 1000)
        tps_str = f" [dim]({tps:.1f} tok/s)[/dim]"

    stats = [
        f"[bold]Run ID        :[/bold] {run_id}",
    ]
    if model_name:
        stats.append(f"[bold]Modèle        :[/bold] [bold white]{model_name}[/bold white]")
    if provider_name:
        stats.append(f"[bold]Fournisseur   :[/bold] [yellow]{provider_name}[/yellow]")

    dur_line = f"{duration_ms:.1f} ms{tps_str}"
    if ttft_ms is not None:
        dur_line += f" [dim](TTFT: {ttft_ms:.1f} ms)[/dim]"

    stats.extend([
        f"[bold]Statut final  :[/bold] {status_str}",
        f"[bold]Durée         :[/bold] {dur_line}",
        f"[bold]Finish Reason :[/bold] [cyan]{finish_code}[/cyan]",
        f"[bold]Tokens In/Out :[/bold] {tokens_display}",
    ])

    if model_name:
        _, cost_str = compute_run_cost(
            model_name,
            in_tokens,
            out_tokens,
            cached_tokens=cached_tokens,
        )
        if cost_str != "-":
            stats.append(f"[bold]Coût estimé   :[/bold] [bold green]{cost_str}[/bold green]")
            stats.append(f"[dim]{pricing_provenance(model_name)}[/dim]")
        elif in_tokens is not None or out_tokens is not None:
            stats.append("[bold]Coût estimé   :[/bold] [dim]N/A (modèle hors catalogue tarifaire)[/dim]")

    return Panel(
        "\n".join(stats),
        title="Statistiques de flux (Streaming)",
        border_style="dim",
    )


def build_model_inspect_panel(spec: ModelSpec) -> Panel:
    """Format rich technical specifications, context window, and pricing for a model."""
    in_modes = ", ".join(spec.modalities_in) if spec.modalities_in else "text"
    out_modes = ", ".join(spec.modalities_out) if spec.modalities_out else "text"
    features_str = ", ".join(spec.features) if spec.features else "standard"

    cr_str = (
        f"${spec.pricing.cache_read:.2f}"
        if spec.pricing.cache_read is not None
        else "N/A"
    )
    cw_str = (
        f"${spec.pricing.cache_write:.2f}"
        if spec.pricing.cache_write is not None
        else "N/A"
    )

    lines = [
        f"[bold cyan]Nom du modèle    :[/bold cyan] {spec.name} ([dim]{spec.id}[/dim])",
        f"[bold]Famille / Provider :[/bold] {spec.family.capitalize()} / [yellow]{spec.provider}[/yellow]",
        f"[bold]Fenêtre Contexte :[/bold] [green]{spec.context_window:,} tokens[/green]",
        f"[bold]Max Output Tokens:[/bold] [green]{spec.max_output_tokens:,} tokens[/green]",
        f"[bold]Modalités In/Out  :[/bold] [yellow]{in_modes}[/yellow] -> [cyan]{out_modes}[/cyan]",
        f"[bold]Fonctionnalités  :[/bold] [magenta]{features_str}[/magenta]",
        "",
        "[bold underline]Tarification indicative, catalogue local (non vérifiée en temps réel) :[/bold underline]",
        f"  - [bold]Input Tokens  :[/bold] [green]${spec.pricing.input_cost:.2f}[/green]",
        f"  - [bold]Output Tokens :[/bold] [yellow]${spec.pricing.output_cost:.2f}[/yellow]",
        f"  - [bold]Cache Read    :[/bold] [dim]{cr_str}[/dim]",
    ]
    if spec.pricing.cache_write_12h is not None:
        lines.extend([
            f"  - [bold]Cache Write (30m):[/bold] [dim]{cw_str}[/dim]",
            f"  - [bold]Cache Write (12h):[/bold] [dim]${spec.pricing.cache_write_12h:.2f}[/dim]",
        ])
    else:
        lines.append(f"  - [bold]Cache Write   :[/bold] [dim]{cw_str}[/dim]")

    if spec.pricing_modalities:
        lines.extend([
            "",
            "[bold underline]Tarification multimodale détaillée :[/bold underline]",
        ])
        for mod, costs in spec.pricing_modalities:
            inp = f"${costs['input_cost']:.2f}" if costs.get("input_cost") is not None else "N/A"
            outp = f"${costs['output_cost']:.2f}" if costs.get("output_cost") is not None else "N/A"
            cr = f"${costs['cache_read']:.2f}" if costs.get("cache_read") is not None else "N/A"
            lines.append(
                f"  - [bold]{mod.capitalize():<6} :[/bold] In [green]{inp}[/green] / Out [yellow]{outp}[/yellow] (Cache Read [dim]{cr}[/dim])"
            )

    if spec.description:
        lines.extend([
            "",
            "[bold underline]Description & Rôle :[/bold underline]",
            f"  {spec.description}",
        ])

    lines.append(f"  - [dim]{pricing_provenance(spec.id)}[/dim]")

    if spec.source_url or spec.last_verified:
        lines.extend([
            "",
            "[bold underline]Documentation & Audit FinOps :[/bold underline]",
        ])
        if spec.source_url:
            lines.append(
                f"  - [bold]Source officielle :[/bold] [link={spec.source_url}][blue underline]{spec.source_url}[/blue underline][/link]"
            )
        if spec.last_verified:
            lines.append(
                f"  - [bold]Dernier relevé    :[/bold] [dim]{spec.last_verified}[/dim]"
            )

    return Panel(
        "\n".join(lines),
        title=f"Spécifications techniques : {spec.name}",
        border_style="cyan",
    )
