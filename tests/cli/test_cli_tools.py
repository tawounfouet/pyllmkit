"""CLI-L5 Tools validation tests (CLI-AC-021..023)."""

import json
from pathlib import Path

from typer.testing import CliRunner

from pyllmkit.adapters.cli.main import app

runner = CliRunner()


def test_cli_tools_validate_valid_tool(tmp_path: Path) -> None:
    """CLI-AC-021: tools validate validates a full tool definition."""
    tool_file = tmp_path / "calculator.json"
    tool_data = {
        "name": "calculator",
        "description": "Effectue des calculs arithmétiques simples",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["add", "sub", "mul", "div"]},
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["operation", "a", "b"],
            "additionalProperties": False,
        },
    }
    tool_file.write_text(json.dumps(tool_data), encoding="utf-8")

    result = runner.invoke(app, ["tools", "validate", str(tool_file)])
    assert result.exit_code == 0
    assert "Outil validé avec succès" in result.output
    assert "calculator" in result.output
    assert "P4-JSON-1" in result.output


def test_cli_tools_validate_raw_schema(tmp_path: Path) -> None:
    """CLI-AC-022: tools validate validates a raw P4-JSON-1 schema."""
    schema_file = tmp_path / "schema.json"
    schema_data = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Terme de recherche"},
        },
        "required": ["query"],
    }
    schema_file.write_text(json.dumps(schema_data), encoding="utf-8")

    result = runner.invoke(app, ["tools", "validate", str(schema_file)])
    assert result.exit_code == 0
    assert "Schéma P4-JSON-1 validé avec succès" in result.output


def test_cli_tools_validate_invalid_schema(tmp_path: Path) -> None:
    """CLI-AC-023: tools validate rejects schema violating P4-JSON-1 profile."""
    bad_file = tmp_path / "bad.json"
    bad_data = {
        "type": "object",
        "$schema": "http://json-schema.org/draft-07/schema#",  # Keyword disallowed in P4-JSON-1
    }
    bad_file.write_text(json.dumps(bad_data), encoding="utf-8")

    result = runner.invoke(app, ["tools", "validate", str(bad_file)])
    assert result.exit_code == 1
    assert "Erreur PyLLMKit" in result.output
    assert "schema_validation_error" in result.output


def test_cli_tools_validate_invalid_json(tmp_path: Path) -> None:
    """tools validate rejects malformed JSON."""
    bad_file = tmp_path / "syntax_error.json"
    bad_file.write_text("{ unquoted_key: 123 ", encoding="utf-8")

    result = runner.invoke(app, ["tools", "validate", str(bad_file)])
    assert result.exit_code == 1
    assert "Syntaxe JSON invalide" in result.output


def test_cli_tools_validate_non_object_root(tmp_path: Path) -> None:
    """tools validate rejects JSON root that is not an object."""
    array_file = tmp_path / "array.json"
    array_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    result = runner.invoke(app, ["tools", "validate", str(array_file)])
    assert result.exit_code == 1
    assert "invalid_format" in result.output


def test_cli_tools_validate_unrecognized_format(tmp_path: Path) -> None:
    """tools validate rejects object lacking name/schema or type."""
    unknown_file = tmp_path / "unknown.json"
    unknown_file.write_text(json.dumps({"some_key": "some_value"}), encoding="utf-8")

    result = runner.invoke(app, ["tools", "validate", str(unknown_file)])
    assert result.exit_code == 1
    assert "unrecognized_tool_format" in result.output
