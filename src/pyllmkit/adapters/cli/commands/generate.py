"""Typer command group for multimodal generative inference (generate image, audio, video)."""

from datetime import UTC, datetime
from typing import Annotated

import typer

from pyllmkit.adapters.inference.media_http import MediaDiagnostics, MediaGenerationOptions
from pyllmkit.application.inference.contracts import (
    InvocationPortError,
    InvocationPreconditionError,
)
from pyllmkit.domain.inference import InferenceRequest, ModelTarget
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.models import ModelId
from pyllmkit.domain.registry.selection import DeploymentResolutionError

from ..catalog import create_reference_catalog, resolve_provider_for_model
from ..console import console
from ..formatting.errors import build_error_panel
from ..formatting.panels import build_response_panel, build_usage_panel
from ..media_saver import get_default_asset_path, save_output_media
from ..model_specs import get_model_spec
from ..prompt_file import PromptFileError, resolve_prompt
from ..service import create_cli_inference_service
from ..storage import RunRecord, SqliteRunStore

# Defaults point at models actually exposed by the provider APIs (verified 2026-11-07).
# Legacy ids (dall-e-3, tts-1, veo-2, imagen-3) stay usable in mock mode and when the
# account still has access to them.
DEFAULT_IMAGE_MODEL = "gpt-image-1-mini"
DEFAULT_AUDIO_MODEL = "gpt-4o-mini-tts"
DEFAULT_VIDEO_MODEL = "grok-imagine-video"

generate_app = typer.Typer(
    help="Génération multimédia (Images, Synthèse vocale TTS, Vidéos)",
    no_args_is_help=True,
)

_MockOption = Annotated[
    bool,
    typer.Option(
        "--mock/--live",
        help="Exécution simulée hors ligne (par défaut) ou appel réel au fournisseur avec --live",
    ),
]
_RecordOption = Annotated[
    bool,
    typer.Option("--record-content", help="Archiver le prompt dans l'historique local (désactivé par défaut)"),
]
_PromptFileOption = Annotated[
    str | None,
    typer.Option(
        "--prompt-file", "-f",
        help="Fichier .md/.txt contenant le prompt (en-tête YAML facultatif pour les réglages)",
    ),
]
_TimeoutOption = Annotated[
    float,
    typer.Option("--timeout", help="Délai maximal par requête HTTP en secondes"),
]


@generate_app.command(name="image")
def generate_image(
    prompt: Annotated[
        str | None,
        typer.Argument(help="Description textuelle de l'image à générer (ou @chemin.md)"),
    ] = None,
    prompt_file: _PromptFileOption = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model", "-m",
            help="Modèle image (gpt-image-1-mini, gpt-image-2, gemini-2.5-flash-image, grok-imagine-image...)",
        ),
    ] = None,
    output_file: Annotated[
        str | None,
        typer.Option("--out", "-o", help="Chemin du fichier où enregistrer l'image générée"),
    ] = None,
    size: Annotated[
        str | None,
        typer.Option("--size", help="Dimensions OpenAI (ex: 1024x1024, 1536x1024, auto)"),
    ] = None,
    quality: Annotated[
        str | None,
        typer.Option("--quality", help="Qualité : low|medium|high|auto (gpt-image), standard|hd (dall-e-3)"),
    ] = None,
    aspect_ratio: Annotated[
        str | None,
        typer.Option("--aspect-ratio", help="Ratio Gemini / xAI (ex: 1:1, 16:9, 9:16)"),
    ] = None,
    resolution: Annotated[
        str | None,
        typer.Option("--resolution", help="Résolution Gemini (1K, 2K, 4K) ou xAI (1k, 2k)"),
    ] = None,
    mock: _MockOption = True,
    record_content: _RecordOption = False,
    timeout: _TimeoutOption = 180.0,
) -> None:
    """Générer une image à partir d'une description textuelle (Text-to-Image)."""
    _generate_from_cli(
        "image", prompt, prompt_file, model, mock, output_file, record_content,
        {"size": size, "quality": quality, "aspect_ratio": aspect_ratio, "resolution": resolution},
        request_timeout_seconds=timeout,
    )


@generate_app.command(name="audio")
def generate_audio(
    prompt: Annotated[
        str | None,
        typer.Argument(help="Texte à convertir en parole synthétisée (Text-to-Speech) (ou @chemin.md)"),
    ] = None,
    prompt_file: _PromptFileOption = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model", "-m",
            help="Modèle TTS (gpt-4o-mini-tts, tts-1, tts-1-hd, gemini-2.5-flash-preview-tts...)",
        ),
    ] = None,
    output_file: Annotated[
        str | None,
        typer.Option("--out", "-o", help="Chemin du fichier où enregistrer l'audio généré"),
    ] = None,
    voice: Annotated[
        str | None,
        typer.Option(
            "--voice",
            help="Voix : OpenAI (alloy, echo, fable, onyx, nova, shimmer...) ou Gemini (Kore, Puck, Charon...)",
        ),
    ] = None,
    instructions: Annotated[
        str | None,
        typer.Option("--instructions", help="Style de diction (gpt-4o-mini-tts, Gemini TTS)"),
    ] = None,
    mock: _MockOption = True,
    record_content: _RecordOption = False,
    timeout: _TimeoutOption = 180.0,
) -> None:
    """Générer un fichier audio vocal à partir d'un texte (Text-to-Speech)."""
    _generate_from_cli(
        "audio", prompt, prompt_file, model, mock, output_file, record_content,
        {"voice": voice, "instructions": instructions},
        request_timeout_seconds=timeout,
    )


@generate_app.command(name="video")
def generate_video(
    prompt: Annotated[
        str | None,
        typer.Argument(help="Description textuelle de la vidéo à générer (ou @chemin.md)"),
    ] = None,
    prompt_file: _PromptFileOption = None,
    model: Annotated[
        str | None,
        typer.Option("--model", "-m", help="Modèle vidéo (grok-imagine-video, grok-imagine-video-1.5, gemini-omni-1.2-flash...)"),
    ] = None,
    output_file: Annotated[
        str | None,
        typer.Option("--out", "-o", help="Chemin du fichier où enregistrer la vidéo générée"),
    ] = None,
    duration: Annotated[
        int | None,
        typer.Option("--duration", min=1, max=15, help="Durée souhaitée en secondes"),
    ] = None,
    aspect_ratio: Annotated[
        str | None,
        typer.Option("--aspect-ratio", help="Ratio (ex: 16:9, 9:16, 1:1)"),
    ] = None,
    resolution: Annotated[
        str | None,
        typer.Option("--resolution", help="Résolution (480p, 720p, 1080p)"),
    ] = None,
    poll_timeout: Annotated[
        float,
        typer.Option("--poll-timeout", help="Attente maximale de fin de génération (secondes)"),
    ] = 900.0,
    mock: _MockOption = True,
    record_content: _RecordOption = False,
    timeout: _TimeoutOption = 180.0,
) -> None:
    """Générer un extrait vidéo à partir d'une description textuelle (Text-to-Video)."""
    _generate_from_cli(
        "video", prompt, prompt_file, model, mock, output_file, record_content,
        {"duration": duration, "aspect_ratio": aspect_ratio, "resolution": resolution},
        request_timeout_seconds=timeout, poll_timeout_seconds=poll_timeout,
    )


_DEFAULT_MODELS = {
    "image": DEFAULT_IMAGE_MODEL,
    "audio": DEFAULT_AUDIO_MODEL,
    "video": DEFAULT_VIDEO_MODEL,
}
# Front matter keys meaningful for each sub-command.
_KIND_SETTINGS = {
    "image": {"size", "quality", "aspect_ratio", "resolution"},
    "audio": {"voice", "instructions"},
    "video": {"duration", "aspect_ratio", "resolution"},
}


def _generate_from_cli(
    kind: str,
    prompt: str | None,
    prompt_file: str | None,
    model: str | None,
    mock: bool,
    output_file: str | None,
    record_content: bool,
    cli_settings: dict[str, object],
    **timeouts: float,
) -> None:
    """Merge CLI options over prompt-file front matter, then run the generation."""
    try:
        doc = resolve_prompt(prompt, prompt_file)
    except PromptFileError as exc:
        console.print(build_error_panel("invalid_prompt_file", str(exc)))
        raise typer.Exit(code=2) from None

    ignored = sorted(set(doc.settings) - _KIND_SETTINGS[kind] - {"model"})
    if ignored:
        console.print(
            f"[yellow]Réglages ignorés pour 'generate {kind}' :[/yellow] {', '.join(ignored)}"
        )
    merged: dict[str, object] = {k: v for k, v in doc.settings.items() if k in _KIND_SETTINGS[kind]}
    merged.update({k: v for k, v in cli_settings.items() if v is not None})
    chosen_model = model or str(doc.settings.get("model") or "") or _DEFAULT_MODELS[kind]

    duration = merged.get("duration")
    if duration is not None and (not isinstance(duration, int) or not 1 <= duration <= 15):
        console.print(build_error_panel("invalid_prompt_file", "'duration' doit être compris entre 1 et 15 secondes"))
        raise typer.Exit(code=2)

    def _s(key: str) -> str | None:
        value = merged.get(key)
        return None if value is None else str(value)

    options = MediaGenerationOptions(
        size=_s("size"),
        quality=_s("quality"),
        voice=_s("voice"),
        instructions=_s("instructions"),
        aspect_ratio=_s("aspect_ratio"),
        resolution=_s("resolution"),
        duration_seconds=duration if isinstance(duration, int) else None,
        **timeouts,
    )
    if doc.source is not None:
        console.print(f"[dim]Prompt chargé depuis {doc.source} ({len(doc.text)} caractères)[/dim]")
    _execute_generation(doc.text, chosen_model, mock, output_file, options, record_content, expected_kind=kind)


def _record_history(
    execution: object,
    *,
    model: str,
    provider: str,
    prompt: str,
    record_content: bool,
) -> None:
    """Persist metadata-only run record for FinOps (best effort, never fails the command)."""
    try:
        run = execution.run  # type: ignore[attr-defined]
        response = execution.response  # type: ignore[attr-defined]
        dur_ms = None
        if run.started_at and run.finished_at:
            dur_ms = (run.finished_at - run.started_at).total_seconds() * 1000
        usage = response.usage if response is not None else None
        finish = None
        if response is not None and response.finish_reason is not None:
            finish = response.finish_reason.code.value
        elif run.failure is not None:
            finish = run.failure.code
        SqliteRunStore().record_run(
            RunRecord(
                run_id=run.run_id.value,
                model_id=model,
                provider=provider,
                prompt=prompt if record_content else "",
                response_text=None,
                state=run.state.value,
                finish_reason=finish,
                input_tokens=usage.input_tokens if usage else None,
                output_tokens=usage.output_tokens if usage else None,
                duration_ms=dur_ms,
                created_at=(run.started_at or run.finished_at or datetime.now(UTC)).isoformat(),
                total_tokens=usage.total_tokens if usage else None,
                cached_tokens=None,
                reasoning_tokens=None,
                ttft_ms=None,
                temperature=None,
                max_tokens=None,
                system_prompt=None,
                mode="generate",
                messages_json=None,
            )
        )
    except Exception:
        pass


def _execute_generation(
    prompt: str,
    model: str,
    mock: bool,
    output_file: str | None,
    options: MediaGenerationOptions | None = None,
    record_content: bool = False,
    expected_kind: str | None = None,
) -> None:
    spec = get_model_spec(model.strip())
    if expected_kind is not None and spec is not None and expected_kind not in spec.modalities_out:
        produced = ", ".join(spec.modalities_out) or "inconnu"
        console.print(build_error_panel(
            "unsupported_capability",
            f"'{model}' produit ({produced}), pas '{expected_kind}'. "
            f"Utilisez 'pyllmkit generate {spec.modalities_out[0]}' ou un autre --model.",
        ))
        raise typer.Exit(code=1)
    catalog = create_reference_catalog()
    diagnostics = MediaDiagnostics()
    service = create_cli_inference_service(
        catalog, mock=mock, media_options=options, diagnostics=diagnostics,
    )

    request = InferenceRequest(
        ModelTarget(ModelId(model.strip())),
        (Message(Role.USER, Content((TextContent(prompt.strip()),))),),
    )

    try:
        if not mock:
            console.print(f"[dim]Génération en cours avec [bold]{model}[/bold] (appel live)...[/dim]")
        execution = service.invoke(request)
        prov_name = resolve_provider_for_model(catalog, model)
        prov_display = f"{prov_name} (simulation)" if mock else prov_name
        _record_history(
            execution, model=model, provider=f"{prov_name} (mock)" if mock else prov_name,
            prompt=prompt, record_content=record_content,
        )

        if execution.run.failure is not None:
            panel = build_error_panel(
                execution.run.failure.code,
                diagnostics.last_error,
                execution.run.run_id.value,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        console.print(build_response_panel(execution, model))
        console.print(build_usage_panel(execution, model_name=model, provider_name=prov_display))

        if execution.response is not None:
            target_path = output_file
            if target_path is None:
                target_path = str(
                    get_default_asset_path(
                        execution.response.output,
                        execution.run.run_id.value,
                        model,
                    )
                )
            try:
                saved = save_output_media(execution.response.output, target_path)
                console.print(f"[bold green]Fichier sauvegardé avec succès dans :[/bold green] [cyan]{saved}[/cyan]")
            except Exception as exc:
                console.print(f"[bold red]Erreur lors de la sauvegarde du fichier :[/bold red] {exc}")
                raise typer.Exit(code=1) from None

    except (InvocationPortError, InvocationPreconditionError) as exc:
        panel = build_error_panel(exc.code, diagnostics.last_error)
        console.print(panel)
        raise typer.Exit(code=1) from None
    except DeploymentResolutionError as exc:
        code = getattr(exc, "code", "no_compatible_deployment")
        panel = build_error_panel(code, str(exc))
        console.print(panel)
        raise typer.Exit(code=1) from None
    except typer.Exit:
        raise
    except Exception:
        # Never echo arbitrary exception text: provider/IO failures may embed secrets.
        panel = build_error_panel(
            "unexpected_error",
            "Erreur interne pendant la génération. Détails masqués pour protéger les secrets.",
        )
        console.print(panel)
        raise typer.Exit(code=2) from None
