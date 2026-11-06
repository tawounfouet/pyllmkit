"""Rich table formatters for PyLLMKit CLI."""

from collections.abc import Sequence

from rich import box
from rich.table import Table

from pyllmkit.adapters.cli.model_specs import get_model_spec
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.models import Model

# Known standard provider configurations
SUPPORTED_PROVIDERS = (
    {
        "id": "ollama",
        "name": "Ollama",
        "profile": "ollama",
        "runtime": "local (loopback)",
        "endpoint": "http://127.0.0.1:11434/api/chat",
        "env_var": "None (local service)",
        "protocol": "Native HTTP (JSONL streaming)",
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "profile": "openai",
        "runtime": "cloud",
        "endpoint": "https://api.openai.com/v1/responses",
        "env_var": "OPENAI_API_KEY",
        "protocol": "Responses API (SSE streaming)",
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "profile": "anthropic",
        "runtime": "cloud",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "env_var": "ANTHROPIC_API_KEY",
        "protocol": "Messages API (SSE streaming)",
    },
    {
        "id": "google",
        "name": "Google Gemini",
        "profile": "google",
        "runtime": "cloud",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models",
        "env_var": "GEMINI_API_KEY",
        "protocol": "Gemini Native (SSE streaming)",
    },
    {
        "id": "xai",
        "name": "xAI (Grok)",
        "profile": "xai",
        "runtime": "cloud",
        "endpoint": "https://api.x.ai/v1/responses",
        "env_var": "XAI_API_KEY",
        "protocol": "Responses API (SSE streaming)",
    },
    {
        "id": "mistral",
        "name": "Mistral AI",
        "profile": "mistral",
        "runtime": "cloud",
        "endpoint": "https://api.mistral.ai/v1/chat/completions",
        "env_var": "MISTRAL_API_KEY",
        "protocol": "Chat API (SSE streaming)",
    },
)


def build_providers_table() -> Table:
    """Build a styled Rich table listing the 6 supported providers."""
    table = Table(
        title="Fournisseurs d'inférence supportés (Phase 7 / Jalon 0.3.0)",
        box=box.ROUNDED,
        header_style="bold cyan",
        title_style="bold blue",
    )
    table.add_column("Fournisseur", style="bold white")
    table.add_column("Profil", style="dim")
    table.add_column("Runtime", style="magenta")
    table.add_column("Endpoint Approuvé", style="green")
    table.add_column("Secret / Auth", style="yellow")
    table.add_column("Protocole Transport", style="cyan")

    for p in SUPPORTED_PROVIDERS:
        runtime_badge = (
            f"[bold green]{p['runtime']}[/bold green]"
            if "local" in p["runtime"]
            else f"[bold blue]{p['runtime']}[/bold blue]"
        )
        table.add_row(
            p["name"],
            p["profile"],
            runtime_badge,
            p["endpoint"],
            p["env_var"],
            p["protocol"],
        )
    return table


def _format_tokens(num: int) -> str:
    """Format token count into compact human readable string (e.g. 1M, 128K, 32K)."""
    known_powers = {
        1_048_576: "1M",
        2_097_152: "2M",
        65_536: "64K",
        32_768: "32K",
        16_384: "16K",
        8_192: "8K",
        4_096: "4K",
    }
    if num in known_powers:
        return known_powers[num]
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M".replace(".0M", "M")
    if num >= 1_000:
        return f"{num / 1_000:.0f}K"
    return str(num)


def build_models_table(models: Sequence[Model], show_pricing: bool = False) -> Table:
    """Build a styled Rich table of declared Model entities with optional pricing."""
    title = "Catalogue des modèles logiques (Spécifications & Tarifs)" if show_pricing else "Catalogue des modèles logiques"
    table = Table(
        title=title,
        box=box.ROUNDED,
        header_style="bold cyan",
        title_style="bold blue",
    )
    table.add_column("Identifiant (ModelId)", style="bold white")
    table.add_column("Famille", style="dim")

    if show_pricing:
        table.add_column("Contexte", justify="right", style="cyan")
        table.add_column("In / 1M", justify="right", style="green")
        table.add_column("Out / 1M", justify="right", style="yellow")
        table.add_column("Cache R", justify="right", style="dim")
        table.add_column("Cache W", justify="right", style="dim")
    else:
        table.add_column("Capacités", style="green")
        table.add_column("Modalités In", style="yellow")
        table.add_column("Modalités Out", style="cyan")

    if not models:
        empty_cols = ["-"] * (6 if show_pricing else 4)
        table.add_row("[dim]Aucun modèle déclaré[/dim]", *empty_cols)
        return table

    for m in models:
        fam = m.identity.family.value if m.identity and m.identity.family else "-"
        if show_pricing:
            spec = get_model_spec(m.id.value)
            if spec:
                ctx_str = _format_tokens(spec.context_window)
                in_cost = f"${spec.pricing.input_cost:.2f}"
                out_cost = f"${spec.pricing.output_cost:.2f}"
                cr = f"${spec.pricing.cache_read:.2f}" if spec.pricing.cache_read is not None else "-"
                cw = f"${spec.pricing.cache_write:.2f}" if spec.pricing.cache_write is not None else "-"
                table.add_row(m.id.value, fam, ctx_str, in_cost, out_cost, cr, cw)
            else:
                table.add_row(m.id.value, fam, "-", "-", "-", "-", "-")
        else:
            caps = ", ".join(cap.id.value for cap in m.capabilities) if m.capabilities else "standard"
            in_modes = (
                ", ".join(mod.value for mod in m.modalities.input_modalities)
                if m.modalities and m.modalities.input_modalities
                else "text"
            )
            out_modes = (
                ", ".join(mod.value for mod in m.modalities.output_modalities)
                if m.modalities and m.modalities.output_modalities
                else "text"
            )
            table.add_row(
                m.id.value,
                fam,
                caps,
                in_modes,
                out_modes,
            )
    return table


def build_deployments_table(deployments: Sequence[Deployment]) -> Table:
    """Build a styled Rich table of active Deployment entities."""
    table = Table(
        title="Déploiements et liaisons opérationnelles",
        box=box.ROUNDED,
        header_style="bold cyan",
        title_style="bold blue",
    )
    table.add_column("Deployment ID", style="bold white")
    table.add_column("Model ID", style="cyan")
    table.add_column("Provider", style="yellow")
    table.add_column("Runtime", style="dim")
    table.add_column("Région", style="dim")
    table.add_column("Statut", style="bold")

    if not deployments:
        table.add_row("[dim]Aucun déploiement actif[/dim]", "-", "-", "-", "-", "-")
        return table

    for d in deployments:
        status_color = "green" if d.status is DeploymentStatus.AVAILABLE else "red"
        status_str = f"[{status_color}]{d.status.value}[/{status_color}]"
        table.add_row(
            d.id.value,
            d.model_id.value,
            d.provider_id.value if d.provider_id else "local",
            d.runtime or "-",
            d.region or "global",
            status_str,
        )
    return table

