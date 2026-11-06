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


def test_sqlite_run_store_finops_evals_metadata(tmp_path: Path) -> None:
    """Verify enriched FinOps, Evals and streaming metadata persistence and retrieval."""
    db_file = tmp_path / "finops_history.db"
    store = SqliteRunStore(db_file)

    record = RunRecord(
        run_id="run_finops_123",
        model_id="gpt-4o",
        provider="openai",
        prompt="Exécute un audit de coût",
        response_text="Audit complété",
        state="completed",
        finish_reason="stop",
        input_tokens=100,
        output_tokens=50,
        duration_ms=250.5,
        created_at="2026-11-06T18:30:00Z",
        total_tokens=150,
        cached_tokens=40,
        reasoning_tokens=10,
        ttft_ms=75.2,
        temperature=0.2,
        max_tokens=200,
        system_prompt="Tu es un auditeur FinOps.",
        mode="stream",
    )
    store.record_run(record)

    fetched = store.get_run("run_finops_123")
    assert fetched is not None
    assert fetched.run_id == "run_finops_123"
    assert fetched.cached_tokens == 40
    assert fetched.reasoning_tokens == 10
    assert fetched.total_tokens == 150
    assert fetched.ttft_ms == 75.2
    assert fetched.temperature == 0.2
    assert fetched.max_tokens == 200
    assert fetched.system_prompt == "Tu es un auditeur FinOps."
    assert fetched.mode == "stream"


def test_cli_stream_records_to_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stream command automatically persists run with mode='stream'."""
    db_file = tmp_path / "stream_history.db"
    monkeypatch.setenv("PYLLMKIT_HISTORY_DB", str(db_file))

    res = runner.invoke(
        app,
        ["stream", "Bonjour stream", "--temperature", "0.5", "--max-tokens", "100"],
    )
    assert res.exit_code == 0

    store = SqliteRunStore(db_file)
    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0].mode == "stream"
    assert runs[0].temperature == 0.5
    assert runs[0].max_tokens == 100


def test_cli_runs_inspect_json_and_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify runs inspect --json and runs export command for Fine-Tuning ChatML."""
    db_file = tmp_path / "export_history.db"
    monkeypatch.setenv("PYLLMKIT_HISTORY_DB", str(db_file))

    # Run one inference with system prompt
    res_run = runner.invoke(
        app,
        ["run", "Quelle heure est-il ?", "--system", "Tu es une horloge suisse."],
    )
    assert res_run.exit_code == 0

    store = SqliteRunStore(db_file)
    runs = store.list_runs()
    assert len(runs) == 1
    run_id = runs[0].run_id

    # Test inspect --json
    res_json = runner.invoke(app, ["runs", "inspect", run_id, "--json"])
    assert res_json.exit_code == 0
    assert '"run_id":' in res_json.output
    assert '"role": "system"' in res_json.output
    assert '"role": "user"' in res_json.output
    assert '"role": "assistant"' in res_json.output

    # Test export to stdout
    res_exp_stdout = runner.invoke(app, ["runs", "export"])
    assert res_exp_stdout.exit_code == 0
    assert '{"messages":' in res_exp_stdout.output

    # Test export to file
    out_file = tmp_path / "dataset.jsonl"
    res_exp_file = runner.invoke(app, ["runs", "export", "-o", str(out_file)])
    assert res_exp_file.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert '{"messages":' in content
    assert "Tu es une horloge suisse." in content


def test_cli_finish_reason_normalization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that a completed run with UNKNOWN finish reason is normalized to stop in panel and database."""
    from unittest.mock import MagicMock

    from pyllmkit.domain.inference import (
        FinishReason,
        FinishReasonCode,
        InferenceResponse,
        InferenceRunId,
        TextOutput,
    )

    db_file = tmp_path / "norm_history.db"
    monkeypatch.setenv("PYLLMKIT_HISTORY_DB", str(db_file))

    mock_service = MagicMock()
    mock_run = MagicMock()
    mock_run.run_id.value = "norm-run-123"
    mock_run.state.value = "completed"
    mock_run.failure = None
    mock_run.started_at = None
    mock_run.finished_at = None

    mock_resp = InferenceResponse(
        run_id=InferenceRunId("norm-run-123"),
        output=TextOutput("Réponse test"),
        finish_reason=FinishReason(FinishReasonCode.UNKNOWN),
    )
    mock_exec = MagicMock()
    mock_exec.run = mock_run
    mock_exec.response = mock_resp
    mock_service.invoke.return_value = mock_exec

    monkeypatch.setattr(
        "pyllmkit.adapters.cli.commands.run.create_cli_inference_service",
        lambda _cat, mock=True: mock_service,
    )

    res = runner.invoke(app, ["run", "Test normalisation"])
    assert res.exit_code == 0
    assert "Finish Reason : stop" in res.output

    store = SqliteRunStore(db_file)
    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0].finish_reason == "stop"



