"""Live stream rendering using Rich."""

import asyncio
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from pyllmkit.application.inference.streaming import AsyncStreamingSession, StreamingSession
from pyllmkit.domain.streaming import (
    ResponseCancelled,
    ResponseCompleted,
    ResponseFailed,
    TextDelta,
)


def consume_and_render_stream(
    session: StreamingSession | Any,
    model_name: str,
    console: Console,
) -> int:
    """Consume events from synchronous StreamingSession and render deltas in real-time."""
    accumulated_text = ""
    exit_code = 0

    with Live(
        Panel(Text("..."), title=f"Flux de réponse [{model_name}]", border_style="cyan"),
        console=console,
        refresh_per_second=15,
    ) as live:
        try:
            for event in session:
                if isinstance(event, TextDelta):
                    accumulated_text += event.delta
                    live.update(
                        Panel(
                            Text(accumulated_text),
                            title=f"Flux de réponse [{model_name}]",
                            border_style="green",
                        )
                    )
                elif isinstance(event, ResponseFailed):
                    live.update(
                        Panel(
                            Text(f"Échec du flux : {event.reason_code}"),
                            title="Erreur de flux",
                            border_style="red",
                        )
                    )
                    exit_code = 1
                    break
                elif isinstance(event, ResponseCancelled):
                    live.update(
                        Panel(
                            Text(f"Flux interrompu ({event.reason_code})"),
                            title="Interruption",
                            border_style="yellow",
                        )
                    )
                    exit_code = 130
                    break
                elif isinstance(event, ResponseCompleted):
                    live.update(
                        Panel(
                            Text(accumulated_text),
                            title=f"Réponse complète [{model_name}]",
                            border_style="green",
                        )
                    )
        except KeyboardInterrupt:
            session.cancel()
            live.update(
                Panel(
                    Text(accumulated_text + "\n[Interrompu par l'utilisateur]"),
                    title="Interruption (Ctrl+C)",
                    border_style="yellow",
                )
            )
            return 130

    return exit_code


async def aconsume_and_render_stream(
    session: AsyncStreamingSession | Any,
    model_name: str,
    console: Console,
) -> int:
    """Consume events from AsyncStreamingSession and render deltas in real-time."""
    accumulated_text = ""
    exit_code = 0

    with Live(
        Panel(Text("..."), title=f"Flux de réponse [{model_name}]", border_style="cyan"),
        console=console,
        refresh_per_second=15,
    ) as live:
        try:
            async for event in session:
                if isinstance(event, TextDelta):
                    accumulated_text += event.delta
                    live.update(
                        Panel(
                            Text(accumulated_text),
                            title=f"Flux de réponse [{model_name}]",
                            border_style="green",
                        )
                    )
                elif isinstance(event, ResponseFailed):
                    live.update(
                        Panel(
                            Text(f"Échec du flux : {event.reason_code}"),
                            title="Erreur de flux",
                            border_style="red",
                        )
                    )
                    exit_code = 1
                    break
                elif isinstance(event, ResponseCancelled):
                    live.update(
                        Panel(
                            Text(f"Flux interrompu ({event.reason_code})"),
                            title="Interruption",
                            border_style="yellow",
                        )
                    )
                    exit_code = 130
                    break
                elif isinstance(event, ResponseCompleted):
                    live.update(
                        Panel(
                            Text(accumulated_text),
                            title=f"Réponse complète [{model_name}]",
                            border_style="green",
                        )
                    )
        except (KeyboardInterrupt, asyncio.CancelledError):
            session.cancel()
            live.update(
                Panel(
                    Text(accumulated_text + "\n[Interrompu par l'utilisateur]"),
                    title="Interruption (Ctrl+C)",
                    border_style="yellow",
                )
            )
            return 130

    return exit_code
