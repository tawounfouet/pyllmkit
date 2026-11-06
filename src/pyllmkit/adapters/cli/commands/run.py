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
from ..formatting.panels import build_response_panel, build_usage_panel
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
        str,
        typer.Argument(help="Texte de l'invite à soumettre au modèle"),
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
    store_content: Annotated[
        bool,
        typer.Option(
            "--store-content",
            help="Consentement explicite pour conserver prompts, instruction et réponse en SQLite",
        ),
    ] = False,
) -> None:
    """Exécuter une inférence textuelle bloquante avec rapport d'usage."""
    cfg = get_config()
    # Live must be requested with --live on this invocation, never inherited from config.
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
    messages_list.append(Message(Role.USER, Content((TextContent(prompt.strip()),))))

    request = InferenceRequest(
        target=ModelTarget(ModelId(model.strip())),
        messages=tuple(messages_list),
        generation_config=gen_config,
    )

    try:
        snapshot = _build_support_snapshot(request)
        execution = service.invoke(request, support_snapshot=snapshot)

        # Enregistrement silencieux dans l'historique local pour FinOps / Evals / Observabilité
        try:
            store = SqliteRunStore(store_content=store_content)
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
                resp_text = execution.response.output.text
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
            messages_payload = [
                {
                    "role": m.role.value,
                    "content": getattr(m.content.parts[0], "text", "") if m.content.parts else "",
                }
                for m in request.messages
            ]
            if resp_text:
                messages_payload.append({"role": "assistant", "content": resp_text})
            msgs_json = json.dumps(messages_payload, ensure_ascii=False)

            rec = RunRecord(
                run_id=execution.run.run_id.value,
                model_id=model,
                provider=f"{prov_name} (mock)" if mock else prov_name,
                prompt=prompt,
                response_text=resp_text,
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
                system_prompt=system,
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
