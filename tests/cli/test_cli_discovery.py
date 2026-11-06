"""Tests for dynamic model discovery and catalog synchronization."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from pyllmkit.adapters.cli.catalog import create_reference_catalog
from pyllmkit.adapters.cli.config import CliConfig
from pyllmkit.adapters.cli.discovery import (
    fetch_provider_models,
    load_discovered_models,
    save_discovered_models,
    sync_configured_providers,
)
from pyllmkit.adapters.cli.main import app
from pyllmkit.domain.models import ModelId

runner = CliRunner()


def test_load_save_discovered_models(tmp_path: Path) -> None:
    cache_file = tmp_path / "discovered.json"
    assert load_discovered_models(cache_file) == []

    models = [
        {"id": "custom-model-1", "family": "openai", "provider": "openai"},
        {"id": "custom-model-2", "family": "anthropic", "provider": "anthropic"},
    ]
    saved = save_discovered_models(models, target_path=cache_file)
    assert saved == cache_file
    assert cache_file.is_file()

    loaded = load_discovered_models(cache_file)
    assert len(loaded) == 2
    assert loaded[0]["id"] in ("custom-model-1", "custom-model-2")


def test_fetch_provider_models_openai() -> None:
    fake_response = {
        "data": [
            {"id": "gpt-4o-custom"},
            {"id": "gpt-3.5-custom"},
        ]
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        models = fetch_provider_models("openai", api_key="sk-test")
        assert models == ["gpt-3.5-custom", "gpt-4o-custom"]


def test_fetch_provider_models_anthropic() -> None:
    fake_response = {
        "data": [
            {"id": "claude-3-5-sonnet-20241022"},
        ]
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        models = fetch_provider_models("anthropic", api_key="sk-ant-test")
        assert models == ["claude-3-5-sonnet-20241022"]


def test_fetch_provider_models_google() -> None:
    fake_response = {
        "models": [
            {"name": "models/gemini-custom-pro"},
        ]
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        models = fetch_provider_models("google", api_key="AIzaTest")
        assert models == ["gemini-custom-pro"]


def test_fetch_provider_models_ollama() -> None:
    fake_response = {
        "models": [
            {"name": "deepseek-coder:latest"},
        ]
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        models = fetch_provider_models("ollama")
        assert models == ["deepseek-coder"]


def test_sync_configured_providers(tmp_path: Path, monkeypatch) -> None:
    mock_cfg = CliConfig(api_keys={"openai": "sk-test"})
    monkeypatch.setattr("pyllmkit.adapters.cli.discovery.get_config", lambda: mock_cfg)
    monkeypatch.setattr(
        "pyllmkit.adapters.cli.discovery.get_discovered_models_path",
        lambda local=False: tmp_path / "discovered.json",
    )

    fake_openai = {"data": [{"id": "gpt-4o-synced"}]}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(fake_openai).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        total, results = sync_configured_providers(target_provider="openai")
        assert total == 1
        assert results["openai"]["status"] == "success"
        assert "gpt-4o-synced" in results["openai"]["models"]


def test_catalog_ingests_discovered_models(tmp_path: Path, monkeypatch) -> None:
    cache_file = tmp_path / "discovered.json"
    cache_file.write_text(
        json.dumps([{"id": "dynamic-model-x", "family": "custom", "provider": "openai"}]),
        encoding="utf-8",
    )
    monkeypatch.setattr("pyllmkit.adapters.cli.catalog.load_discovered_models", lambda: [
        {"id": "dynamic-model-x", "family": "custom", "provider": "openai"}
    ])

    catalog = create_reference_catalog()
    assert catalog.models.get(ModelId("dynamic-model-x")) is not None


def test_cli_models_sync_command(tmp_path: Path, monkeypatch) -> None:
    mock_cfg = CliConfig(api_keys={"openai": "sk-test"})
    monkeypatch.setattr("pyllmkit.adapters.cli.discovery.get_config", lambda: mock_cfg)
    monkeypatch.setattr(
        "pyllmkit.adapters.cli.discovery.get_discovered_models_path",
        lambda local=False: tmp_path / "discovered.json",
    )

    fake_resp = {"data": [{"id": "gpt-4o-discovered"}]}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(fake_resp).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = runner.invoke(app, ["models", "sync", "--provider", "openai"])
        assert result.exit_code == 0
        assert "Résultat de synchronisation" in result.output
        assert "modèle(s) synchronisé(s)" in result.output
