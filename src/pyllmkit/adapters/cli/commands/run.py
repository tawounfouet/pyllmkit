"""Typer command for blocking text inference (run)."""

import json
from datetime import UTC, datetime
from typing import Annotated

import typer

from pyllmkit.application.inference.contracts import (
    InvocationPortError,
    InvocationPreconditionError,
)
from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.inference import (
    AudioOutput,
    GenerationConfig,
    GenerationSupportSnapshot,
    ImageOutput,
    InferenceRequest,
    ModelTarget,
    MultiPartOutput,
    ParameterSupport,
    VideoOutput,
)
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.models import ModelId
from pyllmkit.domain.registry.selection import DeploymentResolutionError

from ..catalog import create_reference_catalog, resolve_provider_for_model
from ..config import get_config
from ..console import console
from ..formatting.errors import build_error_panel
from ..formatting.panels import build_response_panel, build_usage_panel
from ..media_input import parse_cli_media_parts
from ..media_saver import get_default_asset_path, save_output_media
from ..prompt_file import PromptFileError, resolve_prompt
from ..service import create_cli_inference_service
from ..storage import RunRecord, SqliteRunStore


def _build_support_snapshot(request: InferenceRequest) -> GenerationSupportSnapshot | None:
    """Build a native capability snapshot for declared generation parameters."""
    if request.generation_config is None:
        return None
    config = request.generation_config
    params = (
        "max_output_tokens",
        "temperature",
        "top_p",
        "top_k",
        "stop_sequences",
        "seed",
        "presence_penalty",
        "frequency_penalty",
    )
    declared = tuple(
        ParameterSupport(name, CapabilitySupport(SupportLevel.NATIVE))
        for name in params
        if getattr(config, name) is not None
    )
    return GenerationSupportSnapshot(request.target, declared)


def run_command(
    prompt: Annotated[
        str | None,
        typer.Argument(help="Texte de l'invite à soumettre au modèle (ou @chemin.md)"),
    ] = None,
    prompt_file: Annotated[
        str | None,
        typer.Option("--prompt-file", "-f", help="Fichier .md/.txt contenant le prompt"),
    ] = None,
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="Identifiant du modèle cible"),
    ] = "gpt-4o",
    system: Annotated[
        str | None,
        typer.Option("--system", "-s", help="Instruction système préalable"),
    ] = None,
    temperature: Annotated[
        float | None,
        typer.Option("--temperature", "-t", help="Température d'échantillonnage (0.0 à 2.0)"),
    ] = None,
    max_tokens: Annotated[
        int | None,
        typer.Option("--max-tokens", help="Nombre maximum de tokens en sortie"),
    ] = None,
    mock: Annotated[
        bool,
        typer.Option("--mock/--live", help="Exécution simulée hors ligne (par défaut: simulation)"),
    ] = True,
    record_content: Annotated[
        bool,
        typer.Option("--record-content", help="Consentir au stockage local du prompt et de la réponse"),
    ] = False,
    image: Annotated[
        list[str] | None,
        typer.Option("--image", "-i", help="Chemin(s) de fichier image ou URL à attacher"),
    ] = None,
    audio: Annotated[
        str | None,
        typer.Option("--audio", "-a", help="Chemin de fichier audio ou URL à attacher"),
    ] = None,
    video: Annotated[
        str | None,
        typer.Option("--video", "-v", help="Chemin de fichier vidéo ou URL à attacher"),
    ] = None,
    output_file: Annotated[
        str | None,
        typer.Option("--output-file", "-o", help="Chemin du fichier où enregistrer la sortie (image, audio, vidéo, texte)"),
    ] = None,
) -> None:
    """Exécuter une inférence textuelle bloquante avec rapport d'usage."""
    try:
        prompt_doc = resolve_prompt(prompt, prompt_file)
    except PromptFileError as exc:
        console.print(build_error_panel("invalid_prompt_file", str(exc)))
        raise typer.Exit(code=2) from None
    if prompt_doc.settings:
        console.print(
            "[yellow]En-tête du fichier prompt ignoré par 'run' "
            "(utilisez 'pyllmkit generate' pour les réglages média).[/yellow]"
        )
    prompt = prompt_doc.text
    cfg = get_config()
    # A CLI invocation is offline by default, even if config.defaults.live is true.
    # Only an explicit --live switch may construct a network-capable adapter.
    if model == "gpt-4o" and cfg.defaults.model:
        model = cfg.defaults.model
    if system is None and cfg.defaults.system_prompt:
        system = cfg.defaults.system_prompt
    if temperature is None and cfg.defaults.temperature is not None:
        temperature = cfg.defaults.temperature
    if max_tokens is None and cfg.defaults.max_tokens is not None:
        max_tokens = cfg.defaults.max_tokens

    catalog = create_reference_catalog()
    service = create_cli_inference_service(catalog, mock=mock)

    gen_config = None
    if temperature is not None or max_tokens is not None:
        gen_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

    messages_list = []
    if system:
        messages_list.append(Message(Role.SYSTEM, Content((TextContent(system.strip()),))))

    try:
        media_parts = parse_cli_media_parts(images=image, audio=audio, video=video)
    except (FileNotFoundError, ValueError) as err:
        console.print(f"[red]Erreur d'attachement multimédia :[/red] {err}")
        raise typer.Exit(code=2) from None

    user_parts = [TextContent(prompt.strip())] + media_parts
    messages_list.append(Message(Role.USER, Content(tuple(user_parts))))

    request = InferenceRequest(
        target=ModelTarget(ModelId(model.strip())),
        messages=tuple(messages_list),
        generation_config=gen_config,
    )

    try:
        snapshot = _build_support_snapshot(request)
        execution = service.invoke(request, support_snapshot=snapshot)
        prov_name = resolve_provider_for_model(catalog, model)

        # Enregistrement silencieux dans l'historique local pour FinOps / Evals / Observabilité
        try:
            store = SqliteRunStore()
            dur_ms = None
            if execution.run.started_at and execution.run.finished_at:
                dur_ms = (
                    execution.run.finished_at - execution.run.started_at
                ).total_seconds() * 1000
            in_tok = None
            out_tok = None
            tot_tok = None
            cached_tok = None
            reas_tok = None
            finish = None
            resp_text = None
            if execution.response:
                resp_text = getattr(execution.response.output, "text", None)
                if execution.response.finish_reason:
                    raw_code = execution.response.finish_reason.code.value
                    finish = raw_code
                if execution.response.usage:
                    in_tok = execution.response.usage.input_tokens
                    out_tok = execution.response.usage.output_tokens
                    tot_tok = execution.response.usage.total_tokens
                    cached_tok = execution.response.usage.cached_input_tokens
                    reas_tok = execution.response.usage.reasoning_tokens
            elif execution.run.failure is not None:
                finish = execution.run.failure.code

            created = (
                execution.run.started_at
                or execution.run.finished_at
                or datetime.now(UTC)
            ).isoformat()

            prov_name = resolve_provider_for_model(catalog, model)

            # Formatage de l'échange complet au standard ChatML / OpenAI JSONL pour Fine-Tuning
            def _format_part_for_storage(part: object) -> dict[str, object]:
                if hasattr(part, "text"):
                    return {"type": "text", "text": getattr(part, "text", "")}
                if hasattr(part, "source"):
                    src = part.source
                    return {
                        "type": getattr(part, "kind", "media"),
                        "source": {"kind": getattr(src, "kind", "uri"), "value": getattr(src, "value", "")},
                    }
                return {"type": getattr(part, "kind", "unknown")}

            messages_payload = []
            for m in request.messages:
                if len(m.content.parts) == 1 and hasattr(m.content.parts[0], "text"):
                    messages_payload.append({"role": m.role.value, "content": getattr(m.content.parts[0], "text", "")})
                else:
                    messages_payload.append({
                        "role": m.role.value,
                        "content": [_format_part_for_storage(p) for p in m.content.parts],
                    })
            if resp_text:
                messages_payload.append({"role": "assistant", "content": resp_text})
            msgs_json = json.dumps(messages_payload, ensure_ascii=False) if record_content else None

            rec = RunRecord(
                run_id=execution.run.run_id.value,
                model_id=model,
                provider=f"{prov_name} (mock)" if mock else prov_name,
                prompt=prompt if record_content else "",
                response_text=resp_text if record_content else None,
                state=execution.run.state.value,
                finish_reason=finish,
                input_tokens=in_tok,
                output_tokens=out_tok,
                duration_ms=dur_ms,
                created_at=created,
                total_tokens=tot_tok,
                cached_tokens=cached_tok,
                reasoning_tokens=reas_tok,
                ttft_ms=None,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system if record_content else None,
                mode="run",
                messages_json=msgs_json,
            )
            store.record_run(rec)
        except Exception:
            pass

        if execution.run.failure is not None:
            panel = build_error_panel(
                execution.run.failure.code,
                None,
                execution.run.run_id.value,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        console.print(build_response_panel(execution, model))
        console.print(build_usage_panel(execution, model_name=model, provider_name=prov_name))

        if execution.response is not None:
            target_to_save: str | None = output_file
            if target_to_save is None:
                out = execution.response.output
                is_media = isinstance(out, (ImageOutput, AudioOutput, VideoOutput)) or (
                    isinstance(out, MultiPartOutput)
                    and any(isinstance(p, (ImageOutput, AudioOutput, VideoOutput)) for p in out.parts)
                )
                if is_media:
                    target_to_save = str(
                        get_default_asset_path(
                            out,
                            execution.run.run_id.value,
                            model,
                        )
                    )

            if target_to_save is not None:
                try:
                    saved_path = save_output_media(execution.response.output, target_to_save)
                    console.print(
                        f"[bold green]Fichier sauvegardé avec succès dans :[/bold green] [cyan]{saved_path}[/cyan]"
                    )
                except Exception as exc:
                    console.print(f"[bold red]Erreur lors de la sauvegarde du fichier :[/bold red] {exc}")
    except (InvocationPortError, InvocationPreconditionError) as exc:
        panel = build_error_panel(exc.code)
        console.print(panel)
        raise typer.Exit(code=1) from None
    except DeploymentResolutionError as exc:
        code = getattr(exc, "code", "no_compatible_deployment")
        panel = build_error_panel(code, str(exc))
        console.print(panel)
        raise typer.Exit(code=1) from None
    except typer.Exit:
        raise
    except Exception as exc:
        panel = build_error_panel("unexpected_error", str(exc))
        console.print(panel)
        raise typer.Exit(code=2) from None
