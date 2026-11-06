"""Rich error panel formatters for domain and infrastructure failures."""

from rich.panel import Panel

ERROR_HINTS = {
    "authentication_failed": "Clé d'API absente ou invalide. Définissez la variable d'environnement appropriée (ex: OPENAI_API_KEY).",
    "permission_denied": "Droits insuffisants pour accéder à ce modèle avec la clé fournie.",
    "rate_limited": "Quota d'appels temporairement dépassé. Patientez quelques instants ou basculez vers un autre modèle.",
    "provider_timeout": "Délai d'attente réseau dépassé. Vérifiez votre connectivité ou augmentez l'option --timeout.",
    "provider_overloaded": "Le service distant est temporairement surchargé. Réessayez dans un instant.",
    "invalid_request": "Paramètres de génération invalides ou non supportés par ce modèle.",
    "unsupported_input_modality": "Le modèle ne prend pas en charge la modalité demandée (seul le texte est supporté dans ce profil).",
    "target_not_routable": "La cible spécifiée ne peut être routée vers aucun déploiement actif.",
    "native_model_binding_missing": "Aucun alias natif configuré pour ce déploiement.",
}


def build_error_panel(error_code: str, details: str | None = None, run_id: str | None = None) -> Panel:
    """Format a normalized error into a clean, actionable Rich error panel."""
    hint = ERROR_HINTS.get(error_code, "Une erreur inattendue est survenue.")

    lines = [
        f"[bold red]Échec d'exécution :[/bold red] [bold white]{error_code}[/bold white]",
        "",
        f"[yellow]Conseil :[/yellow] {hint}",
    ]

    if details:
        lines.append(f"[dim]Détails  : {details}[/dim]")
    if run_id:
        lines.append(f"[dim]Run ID   : {run_id}[/dim]")

    return Panel(
        "\n".join(lines),
        title="[bold red]Erreur PyLLMKit[/bold red]",
        border_style="red",
    )

