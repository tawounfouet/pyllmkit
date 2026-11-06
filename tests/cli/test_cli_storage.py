"""CLI-L5 Storage and History inspection tests (CLI-AC-024..025)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.main import app
from pyllmkit.adapters.cli.storage import RunRecord, SqliteRunStore

runner = CliRunner()


def test_sqlite_run_store_lifecycle(tmp_path: Path) -> None:
    """CLI-AC-024: SqliteRunStore records, lists and retrieves runs."""
    db_file = tmp_path / "test_history.db"
    store = SqliteRunStore(db_file)

    assert store.list_runs() == []

    record = RunRecord(
        run_id="abc12345def67890",
        model_id="gpt-4o",
        provider="openai",
        prompt="Quelle est la capitale de la France ?",
        response_text="Paris",
        state="completed",
        finish_reason="stop",
        input_tokens=10,
        output_tokens=2,
        duration_ms=45.2,
        created_at="2026-11-06T18:00:00Z",
    )
    store.record_run(record)

    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0].run_id == "abc12345def67890"
    assert runs[0].model_id == "gpt-4o"
    assert runs[0].response_text == "Paris"

    fetched = store.get_run("abc12345def67890")
    assert fetched is not None
    assert fetched.run_id == "abc12345def67890"
    assert fetched.duration_ms == 45.2

    assert store.get_run("non_existent") is None


def test_cli_runs_list_and_inspect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI-AC-025: runs list and runs inspect commands."""
    db_file = tmp_path / "env_history.db"
    monkeypatch.setenv("PYLLMKIT_HISTORY_DB", str(db_file))

    # Empty list
    res_empty = runner.invoke(app, ["runs", "list"])
    assert res_empty.exit_code == 0
    assert "Aucune exécution enregistrée" in res_empty.output

    # Run inference which records to DB
    res_run = runner.invoke(app, ["run", "Bonjour pour l'historique"])
    assert res_run.exit_code == 0

    # List shows recorded run
    res_list = runner.invoke(app, ["runs", "list"])
    assert res_list.exit_code == 0
    assert "gpt-4o" in res_list.output
    assert "completed" in res_list.output

    # Inspect the run
    store = SqliteRunStore(db_file)
    runs = store.list_runs()
    assert len(runs) >= 1
    run_id = runs[0].run_id

    res_inspect = runner.invoke(app, ["runs", "inspect", run_id[:8]])
    assert res_inspect.exit_code == 0
    assert run_id in res_inspect.output
    assert "Bonjour pour l'historique" in res_inspect.output
    assert "Réponse" in res_inspect.output


def test_cli_runs_inspect_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """runs inspect rejects non-existent identifier with safe error."""
    db_file = tmp_path / "empty_history.db"
    monkeypatch.setenv("PYLLMKIT_HISTORY_DB", str(db_file))

    res = runner.invoke(app, ["runs", "inspect", "unknown-run-id"])
    assert res.exit_code == 1
    assert "run_not_found" in res.output

