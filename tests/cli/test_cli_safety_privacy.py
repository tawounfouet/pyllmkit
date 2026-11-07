"""CLI security and provenance regression tests, with zero provider traffic."""

from __future__ import annotations

import os
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.config import CliConfig, DefaultsConfig
from pyllmkit.adapters.cli.discovery import (
    _MAX_DISCOVERY_BYTES,
    _NoRedirectHandler,
    fetch_provider_models,
    sync_configured_providers,
)
from pyllmkit.adapters.cli.main import app
from pyllmkit.adapters.cli.model_specs import format_pricing_provenance
from pyllmkit.adapters.cli.storage import RunRecord, SqliteRunStore

runner = CliRunner()


@pytest.mark.parametrize(
    ("command", "module"),
    [
        ("run", "pyllmkit.adapters.cli.commands.run"),
        ("stream", "pyllmkit.adapters.cli.commands.stream"),
    ],
)
def test_explicit_mock_cannot_be_overridden_by_global_live_setting(
    command: str, module: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With defaults.live=True, explicit --mock must still use only fakes."""
    import importlib

    mod = importlib.import_module(module)
    original = (
        mod.create_cli_inference_service
        if command == "run"
        else mod.create_cli_async_streaming_service
    )
    seen: list[bool] = []

    def inspect_factory(catalog, *, mock=True):
        seen.append(mock)
        assert mock is True, "Explicit --mock must never build live providers"
        return original(catalog, mock=True)

    monkeypatch.setattr(mod, "get_config", lambda: CliConfig(
        defaults=DefaultsConfig(live=True),
    ))
    name = (
        "create_cli_inference_service"
        if command == "run"
        else "create_cli_async_streaming_service"
    )
    monkeypatch.setattr(mod, name, inspect_factory)
    result = runner.invoke(app, [command, "offline-only", "--mock"])
    assert result.exit_code == 0, result.output
    assert seen == [True]


@pytest.mark.parametrize(
    ("command", "module"),
    [
        ("run", "pyllmkit.adapters.cli.commands.run"),
        ("stream", "pyllmkit.adapters.cli.commands.stream"),
    ],
)
def test_only_explicit_live_can_select_live_factory(
    command: str, module: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib

    mod = importlib.import_module(module)
    original = (
        mod.create_cli_inference_service
        if command == "run"
        else mod.create_cli_async_streaming_service
    )
    seen: list[bool] = []

    def inspect_factory(catalog, *, mock=True):
        seen.append(mock)
        # Still execute with an offline fake, never bill a provider.
        return original(catalog, mock=True)

    monkeypatch.setattr(mod, "get_config", lambda: CliConfig(
        defaults=DefaultsConfig(live=True),
    ))
    name = (
        "create_cli_inference_service"
        if command == "run"
        else "create_cli_async_streaming_service"
    )
    monkeypatch.setattr(mod, name, inspect_factory)
    result = runner.invoke(app, [command, "safe-test", "--live"])
    assert result.exit_code == 0, result.output
    assert seen == [False]


@pytest.mark.parametrize("command", ["run", "stream"])
def test_history_default_metadata_only_and_content_requires_consent(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "history.db"
    monkeypatch.setenv("PYLLMKIT_HISTORY_DB", str(path))
    monkeypatch.delenv("PYLLMKIT_HISTORY_RETENTION_DAYS", raising=False)

    no_consent = runner.invoke(app, [
        command, "private-first-prompt", "--system", "private-system-instruction",
    ])
    assert no_consent.exit_code == 0, no_consent.output
    assert "private-first-prompt" not in path.read_bytes().decode(
        "utf-8", errors="ignore",
    )
    entry = SqliteRunStore(path).list_runs()[0]
    assert entry.prompt == ""
    assert entry.system_prompt is None
    assert entry.response_text is None
    assert entry.messages_json is None
    assert entry.model_id == "gpt-4o"

    with_consent = runner.invoke(app, [
        command, "private-second-prompt", "--record-content",
    ])
    assert with_consent.exit_code == 0, with_consent.output
    entries = SqliteRunStore(path).list_runs()
    assert any(r.prompt == "private-second-prompt" and r.response_text for r in entries)


def _record(run_id: str, when: datetime) -> RunRecord:
    return RunRecord(
        run_id=run_id,
        model_id="gpt-4o",
        provider="openai (mock)",
        prompt="private",
        response_text="text",
        state="completed",
        finish_reason="unknown",
        input_tokens=3,
        output_tokens=4,
        duration_ms=1.0,
        created_at=when.isoformat(),
    )


def test_retention_prune_and_explicit_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "retention.db"
    monkeypatch.setenv("PYLLMKIT_HISTORY_DB", str(path))
    monkeypatch.delenv("PYLLMKIT_HISTORY_RETENTION_DAYS", raising=False)
    store = SqliteRunStore(path)
    now = datetime.now(UTC)
    store.record_run(_record("old-one", now - timedelta(days=80)))
    store.record_run(_record("recent-one", now - timedelta(days=1)))
    assert store.prune_older_than_days(30, now=now) == 1
    assert store.get_run("old-one") is None
    assert store.get_run("recent-one") is not None

    store.record_run(_record("old-two", now - timedelta(days=90)))
    refused = runner.invoke(app, ["runs", "prune", "--older-than-days", "30"])
    assert refused.exit_code == 1
    assert store.get_run("old-two") is not None
    approved = runner.invoke(app, [
        "runs", "prune", "--older-than-days", "30", "--yes",
    ])
    assert approved.exit_code == 0, approved.output
    assert store.get_run("old-two") is None
    assert store.get_run("recent-one") is not None


def test_opt_in_auto_retention_environment_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "automatic.db"
    monkeypatch.delenv("PYLLMKIT_HISTORY_RETENTION_DAYS", raising=False)
    store = SqliteRunStore(path)
    store.record_run(_record("expired", datetime.now(UTC) - timedelta(days=60)))
    monkeypatch.setenv("PYLLMKIT_HISTORY_RETENTION_DAYS", "30")
    reopened = SqliteRunStore(path)
    assert reopened.get_run("expired") is None
    monkeypatch.setenv("PYLLMKIT_HISTORY_RETENTION_DAYS", "0")
    with pytest.raises(ValueError, match="invalid_history_retention_days"):
        SqliteRunStore(path)


@pytest.mark.skipif(os.name == "nt", reason="POSIX filesystem permissions")
def test_new_history_database_is_private(tmp_path: Path) -> None:
    path = tmp_path / "private.db"
    SqliteRunStore(path)
    assert path.stat().st_mode & 0o077 == 0


def test_discovery_never_places_gemini_key_in_url() -> None:
    fake_response = MagicMock()
    fake_response.read.return_value = b'{"models":[{"name":"models/gemini-test"}]}'
    fake_response.__enter__.return_value = fake_response
    secret = "synthetic_gemini_private_credential"
    with patch(
        "pyllmkit.adapters.cli.discovery._open_discovery_request",
        return_value=fake_response,
    ) as opened:
        models = fetch_provider_models("google", api_key=secret)
    req = opened.call_args.args[0]
    assert models == ["gemini-test"]
    assert secret not in req.full_url
    assert "key=" not in req.full_url
    assert dict(req.header_items())["X-goog-api-key"] == secret


def test_discovery_disables_ambient_proxies_and_redirects() -> None:
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"data":[]}'
    mock_response.__enter__.return_value = mock_response
    with patch("urllib.request.build_opener") as build:
        build.return_value.open.return_value = mock_response
        assert fetch_provider_models("openai", api_key="synthetic") == []
        handlers = build.call_args.args
        proxy = next(h for h in handlers if isinstance(h, urllib.request.ProxyHandler))
        redirect = next(h for h in handlers if isinstance(h, _NoRedirectHandler))
        assert proxy.proxies == {}
        assert redirect.redirect_request(None, None, 302, "moved", {}, "https://bad") is None


def test_discovery_bounded_response_and_safe_failure_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_response = MagicMock()
    mock_response.read.return_value = b"x" * (_MAX_DISCOVERY_BYTES + 1)
    mock_response.__enter__.return_value = mock_response
    with patch(
        "pyllmkit.adapters.cli.discovery._open_discovery_request",
        return_value=mock_response,
    ):
        with pytest.raises(ValueError, match="discovery_payload_too_large"):
            fetch_provider_models("openai", api_key="synthetic")

    monkeypatch.setattr(
        "pyllmkit.adapters.cli.discovery.get_config",
        lambda: CliConfig(api_keys={"openai": "synthetic"}),
    )
    with patch(
        "pyllmkit.adapters.cli.discovery._open_discovery_request",
        side_effect=RuntimeError("synthetic_sensitive_secret"),
    ):
        count, results = sync_configured_providers(target_provider="openai")
    assert count == 0
    assert results["openai"]["status"] == "error"
    assert "synthetic_sensitive_secret" not in results["openai"]["message"]


def test_pricing_ui_explicitly_labels_local_not_live_source() -> None:
    note = format_pricing_provenance("gpt-4o")
    assert "catalogue local" in note
    assert "non actualisé en temps réel" in note
    assert "facturation" in note
    assert "non renseignée" in format_pricing_provenance("gpt-4o") or "vérifié" in note
    assert "Prix non disponible" in format_pricing_provenance("not-a-real-model")
