"""Typer command for streaming text inference (stream)."""

import asyncio
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

from ..catalog import create_reference_catalog
from ..console import console
from ..formatting.errors import build_error_panel
from ..formatting.live_stream import aconsume_and_render_stream
from ..service import create_cli_async_streaming_service


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
) -> None:
    """Consommer une inférence en direct avec affichage incrémental (streaming)."""
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
    messages_list.append(Message(Role.USER, Content((TextContent(prompt.strip()),))))

    request = InferenceRequest(
        target=ModelTarget(ModelId(model.strip())),
        messages=tuple(messages_list),
        generation_config=gen_config,
    )

    try:
        snapshot = _build_support_snapshot(request)
        session = service.open_astream(request, support_snapshot=snapshot)
        exit_code = asyncio.run(aconsume_and_render_stream(session, model, console))
        if exit_code != 0:
            raise typer.Exit(code=exit_code)

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

