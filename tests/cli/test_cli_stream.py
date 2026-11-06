"""CLI-L4 Stream command tests (CLI-AC-016..020)."""

from typer.testing import CliRunner

from pyllmkit.adapters.cli.main import app

runner = CliRunner()


def test_cli_stream_default_model() -> None:
    """CLI-AC-016: stream executes prompt and streams deltas in real-time."""
    result = runner.invoke(app, ["stream", "Bonjour en streaming"])
    assert result.exit_code == 0
    assert "Réponse complète" in result.output
    assert "flux continu" in result.output
    assert "gpt-4o" in result.output


def test_cli_stream_custom_model_and_system() -> None:
    """CLI-AC-017: stream supports custom model and system instruction."""
    result = runner.invoke(
        app,
        [
            "stream",
            "Bonjour",
            "--model",
            "claude-3-5-sonnet",
            "--system",
            "Tu es un assistant de test.",
        ],
    )
    assert result.exit_code == 0
    assert "claude-3-5-sonnet" in result.output
    assert "anthropic" in result.output


def test_cli_stream_generation_parameters() -> None:
    """CLI-AC-018: stream accepts generation parameters."""
    result = runner.invoke(
        app,
        [
            "stream",
            "Bonjour",
            "--temperature",
            "0.5",
            "--max-tokens",
            "64",
        ],
    )
    assert result.exit_code == 0
    assert "Réponse complète" in result.output


def test_cli_stream_unknown_model_failure() -> None:
    """CLI-AC-019: stream rejects unknown model with exit code 1."""
    result = runner.invoke(app, ["stream", "Bonjour", "--model", "non-existent-stream-model"])
    assert result.exit_code == 1
    assert "Erreur PyLLMKit" in result.output
    assert "no_compatible_deployment" in result.output


def test_consume_and_render_stream_events() -> None:
    """CLI-AC-020: test stream rendering handles failure, cancel and sigint."""
    from rich.console import Console
    from pyllmkit.adapters.cli.formatting.live_stream import consume_and_render_stream
    from pyllmkit.domain.inference import InferenceRunId
    from pyllmkit.domain.streaming import ResponseCancelled, ResponseFailed, TextDelta

    console = Console(record=True, width=100)
    run_id = InferenceRunId("1234567890abcdef1234567890abcdef")

    # Failure event test
    class MockFailureSession:
        def __iter__(self):
            yield TextDelta(run_id=run_id, sequence=0, delta="Début...")
            yield ResponseFailed(run_id=run_id, sequence=1, reason_code="timeout_error")

        def cancel(self):
            pass

    exit_code = consume_and_render_stream(MockFailureSession(), "test-model", console)
    assert exit_code == 1

    # Cancellation event test
    class MockCancelSession:
        def __iter__(self):
            yield TextDelta(run_id=run_id, sequence=0, delta="Début...")
            yield ResponseCancelled(run_id=run_id, sequence=1, reason_code="user_cancelled")

        def cancel(self):
            pass

    exit_code = consume_and_render_stream(MockCancelSession(), "test-model", console)
    assert exit_code == 130

    # KeyboardInterrupt test
    class MockSigintSession:
        cancelled = False

        def __iter__(self):
            raise KeyboardInterrupt()

        def cancel(self):
            self.cancelled = True

    sig_session = MockSigintSession()
    exit_code = consume_and_render_stream(sig_session, "test-model", console)
    assert exit_code == 130
    assert sig_session.cancelled is True
