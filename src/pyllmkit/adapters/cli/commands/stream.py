"""Typer command for streaming text inference (stream)."""

import asyncio
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
    GenerationConfig,
    GenerationSupportSnapshot,
    InferenceRequest,
    ModelTarget,
    ParameterSupport,
)
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.models import ModelId
from pyllmkit.domain.registry.selection import DeploymentResolutionError

from ..catalog import create_reference_catalog, resolve_provider_for_model
from ..config import get_config
from ..console import console
from ..formatting.errors import build_error_panel
from ..formatting.live_stream import aconsume_and_render_stream
from ..formatting.panels import build_stream_usage_panel
from ..media_input import parse_cli_media_parts
from ..service import create_cli_async_streaming_service
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


def stream_command(
    prompt: Annotated[
        str,
        typer.Argument(help="Texte de l'invite à soumettre au flux"),
    ],
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
        typer.Option("--record-content", help="Consentir au stockage local du prompt et du flux"),
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
) -> None:
    """Consommer une inférence en direct avec affichage incrémental (streaming)."""
    cfg = get_config()
    # Explicit --live is the only way to enable billable streaming.
    if model == "gpt-4o" and cfg.defaults.model:
        model = cfg.defaults.model
    if system is None and cfg.defaults.system_prompt:
        system = cfg.defaults.system_prompt
    if temperature is None and cfg.defaults.temperature is not None:
        temperature = cfg.defaults.temperature
    if max_tokens is None and cfg.defaults.max_tokens is not None:
        max_tokens = cfg.defaults.max_tokens

    catalog = create_reference_catalog()
    service = create_cli_async_streaming_service(catalog, mock=mock)

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
        session = service.open_astream(request, support_snapshot=snapshot)
        summary = asyncio.run(aconsume_and_render_stream(session, model, console))

        # Enregistrement dans l'historique local pour FinOps / Evals / Observabilité
        try:
            store = SqliteRunStore()
            deployment = (
                catalog.deployments.get(session.prepared.resolution.deployment.id)
                if session and session.prepared and session.prepared.resolution
                else None
            )
            prov_name = resolve_provider_for_model(catalog, model, deployment=deployment)
            in_tok = summary.usage.input_tokens if summary.usage else None
            out_tok = summary.usage.output_tokens if summary.usage else None
            tot_tok = summary.usage.total_tokens if summary.usage else None
            cached_tok = summary.usage.cached_input_tokens if summary.usage else None
            reas_tok = summary.usage.reasoning_tokens if summary.usage else None

            # Formatage ChatML / OpenAI JSONL pour Fine-Tuning
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
            if summary.text:
                messages_payload.append({"role": "assistant", "content": summary.text})
            msgs_json = json.dumps(messages_payload, ensure_ascii=False) if record_content else None

            rec = RunRecord(
                run_id=session.run_id.value,
                model_id=model,
                provider=f"{prov_name} (mock)" if mock else prov_name,
                prompt=prompt if record_content else "",
                response_text=summary.text if record_content else None,
                state="completed" if summary.exit_code == 0 else "failed",
                finish_reason=summary.finish_reason,
                input_tokens=in_tok,
                output_tokens=out_tok,
                duration_ms=summary.duration_ms,
                created_at=datetime.now(UTC).isoformat(),
                total_tokens=tot_tok,
                cached_tokens=cached_tok,
                reasoning_tokens=reas_tok,
                ttft_ms=summary.ttft_ms,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system if record_content else None,
                mode="stream",
                messages_json=msgs_json,
            )
            store.record_run(rec)
        except Exception:
            pass

        if summary.exit_code == 0:
            usage_panel = build_stream_usage_panel(
                run_id=session.run_id.value,
                duration_ms=summary.duration_ms,
                finish_reason=summary.finish_reason or "unknown",
                in_tokens=in_tok,
                out_tokens=out_tok,
                cached_tokens=cached_tok,
                reasoning_tokens=reas_tok,
                ttft_ms=summary.ttft_ms,
                model_name=model,
                provider_name=prov_name,
                exit_code=summary.exit_code,
                modalities=[p.kind for p in user_parts],
            )
            console.print(usage_panel)

        if summary.exit_code != 0:
            raise typer.Exit(code=summary.exit_code)

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

