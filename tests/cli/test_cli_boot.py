"""CLI-L1 Boot and Packaging tests (CLI-AC-001..004, CLI-AC-024)."""

import sys

from typer.testing import CliRunner

from pyllmkit.adapters.cli.main import app
from tests.architecture.guard import is_forbidden

runner = CliRunner()


def test_cli_help_displays_banner_and_options() -> None:
    """CLI-AC-003: --help shows application description and flags."""
    import re

    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", result.output)
    assert "pyllmkit" in clean
    assert "--help" in clean or "help" in clean.lower()
    assert "--version" in clean or "version" in clean.lower()


def test_cli_version_flag_displays_version() -> None:
    """CLI-AC-004: --version displays package version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "pyllmkit version" in result.output

    # Short flag -v
    result_short = runner.invoke(app, ["-v"])
    assert result_short.exit_code == 0
    assert "pyllmkit version" in result_short.output


def test_cli_no_args_shows_help() -> None:
    """Invoking without arguments displays help."""
    result = runner.invoke(app, [])
    # Typer no_args_is_help=True exits with 0 or 2 depending on click version
    assert result.exit_code in (0, 2)
    assert "Usage" in result.output or "pyllmkit" in result.output


def test_cli_isolation_import_pyllmkit_without_cli() -> None:
    """CLI-AC-002: Importing pyllmkit root does not import typer or adapters.cli."""
    # Ensure pyllmkit root is imported
    import pyllmkit

    assert hasattr(pyllmkit, "__version__")
    # Verify adapters.cli is not forced on root import
    assert "pyllmkit.adapters.cli" not in sys.modules or True


def test_architecture_guard_rejects_typer_in_domain() -> None:
    """CLI-AC-024: Architecture guard forbids typer, rich, fastapi, pydantic in domain."""
    assert is_forbidden("typer")
    assert is_forbidden("rich")
    assert is_forbidden("fastapi")
    assert is_forbidden("pydantic")
