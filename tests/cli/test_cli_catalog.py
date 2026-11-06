"""CLI-L2 Catalog & Inspection tests (CLI-AC-005..010)."""

from typer.testing import CliRunner

from pyllmkit.adapters.cli.main import app

runner = CliRunner()


def test_cli_providers_list() -> None:
    """CLI-AC-005: providers list shows table with all 6 providers."""
    result = runner.invoke(app, ["providers", "list"])
    assert result.exit_code == 0
    assert "OpenAI" in result.output
    assert "Anthropic" in result.output
    assert "Ollama" in result.output
    assert "Google" in result.output
    assert "Gemini" in result.output
    assert "xAI" in result.output
    assert "Mistral" in result.output


def test_cli_providers_inspect_valid() -> None:
    """CLI-AC-006: providers inspect displays details without showing raw secrets."""
    result = runner.invoke(app, ["providers", "inspect", "openai"])
    assert result.exit_code == 0
    assert "OpenAI" in result.output
    assert "https://api.openai.com/v1/responses" in result.output
    assert "OPENAI_API_KEY" in result.output


def test_cli_providers_inspect_unknown() -> None:
    """providers inspect rejects unknown provider with safe error."""
    result = runner.invoke(app, ["providers", "inspect", "unknown-vendor"])
    assert result.exit_code == 1
    assert "Fournisseur inconnu" in result.output


def test_cli_models_list() -> None:
    """CLI-AC-007: models list displays declared models."""
    result = runner.invoke(app, ["models", "list"])
    assert result.exit_code == 0
    assert "gpt-4o" in result.output
    assert "llama3.2" in result.output
    assert "claude-3-5-sonnet" in result.output


def test_cli_models_list_filter_family() -> None:
    """models list filters by family."""
    result = runner.invoke(app, ["models", "list", "--family", "meta"])
    assert result.exit_code == 0
    assert "llama3.2" in result.output
    assert "gpt-4o" not in result.output


def test_cli_models_list_empty_filter() -> None:
    """models list handles empty filter result gracefully."""
    result = runner.invoke(app, ["models", "list", "--family", "non-existent"])
    assert result.exit_code == 0
    assert "Aucun modèle déclaré" in result.output


def test_cli_deployments_list() -> None:
    """CLI-AC-008: deployments list displays active deployments."""
    result = runner.invoke(app, ["deployments", "list"])
    assert result.exit_code == 0
    assert "dep-gpt-4o" in result.output
    assert "dep-llama3.2" in result.output
    assert "available" in result.output


def test_cli_deployments_list_filter_provider() -> None:
    """deployments list filters by provider identifier."""
    result = runner.invoke(app, ["deployments", "list", "--provider", "openai"])
    assert result.exit_code == 0
    assert "openai" in result.output


def test_cli_deployments_list_empty_filter() -> None:
    """deployments list handles empty filter result gracefully."""
    result = runner.invoke(app, ["deployments", "list", "--provider", "non-existent"])
    assert result.exit_code == 0
    assert "Aucun déploiement actif" in result.output


def test_cli_resolve_success() -> None:
    """CLI-AC-009: resolve selects unique matching deployment."""
    result = runner.invoke(app, ["resolve", "--model", "gpt-4o"])
    assert result.exit_code == 0
    assert "dep-gpt-4o" in result.output
    assert "Déploiement retenu" in result.output


def test_cli_resolve_rejection() -> None:
    """CLI-AC-010: resolve displays candidate rejection reasons on mismatch."""
    result = runner.invoke(app, ["resolve", "--model", "gpt-4o", "--provider", "anthropic"])
    assert result.exit_code == 1
    assert "PROVIDER_MISMATCH" in result.output


def test_cli_resolve_unknown_model() -> None:
    """resolve rejects unknown model."""
    result = runner.invoke(app, ["resolve", "--model", "non-existent-xyz"])
    assert result.exit_code == 1
    assert "Échec de résolution" in result.output
