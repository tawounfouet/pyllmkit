"""Rich error panel formatters for domain and infrastructure failures."""

from rich.panel import Panel

ERROR_HINTS = {
    "authentication_failed": "Clé d'API absente ou invalide. Définissez la variable d'environnement appropriée (ex: OPENAI_API_KEY).",
    "permission_denied": "Droits insuffisants pour accéder à ce modèle avec la clé fournie.",
    "rate_limited": "Quota d'appels temporairement dépassé. Patientez quelques instants ou basculez vers un autre modèle.",
    "provider_timeout": "Délai d'attente réseau dépassé. Vérifiez votre connectivité ou augmentez l'option --timeout.",
    "provider_overloaded": "Le service distant est temporairement surchargé. Réessayez dans un instant.",
    "provider_not_completed": "La génération n'a pas pu se terminer normalement (ex: budget --max-tokens trop restreint ayant provoqué une troncature, ou interruption distante). Augmentez --max-tokens ou allégez le prompt.",
    "provider_model_mismatch": "Le modèle retourné par le fournisseur ne correspond pas à l'alias demandé.",
    "provider_protocol_error": "Erreur de protocole ou trame non conforme reçue du fournisseur.",
    "connection_failure": "Échec de connexion réseau au fournisseur distant.",
    "invalid_request": "Paramètres de génération invalides ou non supportés par ce modèle.",
    "unsupported_input_modality": "Le modèle ne prend pas en charge la modalité demandée (seul le texte est supporté dans ce profil).",
    "target_not_routable": "La cible spécifiée ne peut être routée vers aucun déploiement actif.",
    "native_model_binding_missing": "Aucun alias natif configuré pour ce déploiement.",
    "model_not_found": "Modèle inconnu ou non accessible avec cette clé chez le fournisseur. Vérifiez l'identifiant (ex: dall-e-3 est retiré, utilisez gpt-image-1-mini) ou vos droits d'accès.",
    "credential_unavailable": "Clé d'API absente ou refusée. Renseignez api_keys dans .pyllmkit.yaml ou la variable d'environnement du fournisseur.",
    "content_filtered": "La requête ou le média généré a été bloqué par la modération du fournisseur. Reformulez le prompt.",
    "unsupported_provider_output": "Le fournisseur n'a renvoyé aucun média exploitable.",
    "unsupported_capability": "Ce fournisseur ou modèle ne prend pas en charge ce type de génération.",
    "live_authorization_required": "Appel réseau non autorisé : ajoutez --live pour exécuter réellement la génération.",
    "invalid_prompt_file": "Fichier prompt inutilisable (introuvable, vide, non UTF-8 ou en-tête invalide).",
    "run_not_found": "Aucune exécution archivée ne correspond à cet identifiant. Utilisez 'pyllmkit runs list' pour afficher les Run IDs existants.",
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

