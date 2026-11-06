"""CLI-L3 Run command tests (CLI-AC-011..015)."""

from typer.testing import CliRunner

from pyllmkit.adapters.cli.main import app

runner = CliRunner()


def test_cli_run_default_model() -> None:
    """CLI-AC-011: run executes prompt on default model and displays panels."""
    result = runner.invoke(app, ["run", "Bonjour PyLLMKit"])
    assert result.exit_code == 0
    assert "Réponse du modèle" in result.output
    assert "Statistiques d'exécution" in result.output
    assert "gpt-4o" in result.output
    assert "completed" in result.output


def test_cli_run_custom_model_and_system() -> None:
    """CLI-AC-012: run supports custom model and system instruction."""
    result = runner.invoke(
        app,
        [
            "run",
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


def test_cli_run_generation_parameters() -> None:
    """CLI-AC-013: run accepts generation configuration options."""
    result = runner.invoke(
        app,
        [
            "run",
            "Bonjour",
            "--temperature",
            "0.7",
            "--max-tokens",
            "120",
        ],
    )
    assert result.exit_code == 0
    assert "completed" in result.output


def test_cli_run_unknown_model_failure() -> None:
    """CLI-AC-014: run rejects unknown model target with exit code 1."""
    result = runner.invoke(app, ["run", "Bonjour", "--model", "unknown-model-xyz"])
    assert result.exit_code == 1
    assert "Erreur PyLLMKit" in result.output
    assert "no_compatible_deployment" in result.output

