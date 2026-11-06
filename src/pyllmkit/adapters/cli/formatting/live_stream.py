"""Live stream rendering using Rich."""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from pyllmkit.application.inference.streaming import AsyncStreamingSession, StreamingSession
from pyllmkit.domain.inference import Usage
from pyllmkit.domain.streaming import (
    ResponseCancelled,
    ResponseCompleted,
    ResponseFailed,
    TextDelta,
    UsageUpdated,
)


@dataclass(slots=True)
class StreamExecutionSummary:
    """Observed execution summary for a rendered stream."""

    exit_code: int
    text: str
    finish_reason: str | None = None
    usage: Usage | None = None
    duration_ms: float = 0.0
    ttft_ms: float | None = None

    def __int__(self) -> int:
        return self.exit_code

    def __eq__(self, other: object) -> bool:
        if isinstance(other, int):
            return self.exit_code == other
        return super().__eq__(other)


def consume_and_render_stream(
    session: StreamingSession | Any,
    model_name: str,
    console: Console,
) -> StreamExecutionSummary:
    """Consume events from synchronous StreamingSession and render deltas in real-time."""
    accumulated_text = ""
    exit_code = 0
    finish_reason: str | None = None
    last_usage: Usage | None = None
    start_time = time.perf_counter()
    first_token_time: float | None = None

    with Live(
        Panel(Text("..."), title=f"Flux de réponse [{model_name}]", border_style="cyan"),
        console=console,
        refresh_per_second=15,
    ) as live:
        try:
            for event in session:
                if isinstance(event, TextDelta):
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                    accumulated_text += event.delta
                    live.update(
                        Panel(
                            Text(accumulated_text),
                            title=f"Flux de réponse [{model_name}]",
                            border_style="green",
                        )
                    )
                elif isinstance(event, UsageUpdated):
                    last_usage = event.usage
                elif isinstance(event, ResponseFailed):
                    live.update(
                        Panel(
                            Text(f"Échec du flux : {event.reason_code}"),
                            title="Erreur de flux",
                            border_style="red",
                        )
                    )
                    exit_code = 1
                    finish_reason = event.reason_code
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
                    finish_reason = event.reason_code
                    break
                elif isinstance(event, ResponseCompleted):
                    if event.finish_reason is not None:
                        finish_reason = event.finish_reason.code.value
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
            exit_code = 130
            finish_reason = "cancelled"

    dur_ms = (time.perf_counter() - start_time) * 1000
    ttft_ms = (first_token_time - start_time) * 1000 if first_token_time is not None else None
    return StreamExecutionSummary(
        exit_code=exit_code,
        text=accumulated_text,
        finish_reason=finish_reason,
        usage=last_usage,
        duration_ms=dur_ms,
        ttft_ms=ttft_ms,
    )


async def aconsume_and_render_stream(
    session: AsyncStreamingSession | Any,
    model_name: str,
    console: Console,
) -> StreamExecutionSummary:
    """Consume events from AsyncStreamingSession and render deltas in real-time."""
    accumulated_text = ""
    exit_code = 0
    finish_reason: str | None = None
    last_usage: Usage | None = None
    start_time = time.perf_counter()
    first_token_time: float | None = None

    with Live(
        Panel(Text("..."), title=f"Flux de réponse [{model_name}]", border_style="cyan"),
        console=console,
        refresh_per_second=15,
    ) as live:
        try:
            async for event in session:
                if isinstance(event, TextDelta):
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                    accumulated_text += event.delta
                    live.update(
                        Panel(
                            Text(accumulated_text),
                            title=f"Flux de réponse [{model_name}]",
                            border_style="green",
                        )
                    )
                elif isinstance(event, UsageUpdated):
                    last_usage = event.usage
                elif isinstance(event, ResponseFailed):
                    live.update(
                        Panel(
                            Text(f"Échec du flux : {event.reason_code}"),
                            title="Erreur de flux",
                            border_style="red",
                        )
                    )
                    exit_code = 1
                    finish_reason = event.reason_code
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
                    finish_reason = event.reason_code
                    break
                elif isinstance(event, ResponseCompleted):
                    if event.finish_reason is not None:
                        finish_reason = event.finish_reason.code.value
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
            exit_code = 130
            finish_reason = "cancelled"

    dur_ms = (time.perf_counter() - start_time) * 1000
    ttft_ms = (first_token_time - start_time) * 1000 if first_token_time is not None else None
    return StreamExecutionSummary(
        exit_code=exit_code,
        text=accumulated_text,
        finish_reason=finish_reason,
        usage=last_usage,
        duration_ms=dur_ms,
        ttft_ms=ttft_ms,
    )
