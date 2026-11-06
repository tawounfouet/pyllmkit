"""CLI configuration tests (JSON/YAML/TOML loading, env injection, defaults)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.config import (
    load_and_apply_config,
    load_config,
    mask_secret,
)
from pyllmkit.adapters.cli.main import app

runner = CliRunner()


def test_mask_secret() -> None:
    assert mask_secret("") == "[non configuré]"
    assert mask_secret("short") == "****"
    assert mask_secret("sk-proj-1234567890abcdef") == "sk-pro...cdef"


def test_load_config_json(tmp_path: Path) -> None:
    cfg_file = tmp_path / "pyllmkit.json"
    cfg_file.write_text(
        """{
        "api_keys": {
            "openai": "sk-proj-test123456789",
            "anthropic": "sk-ant-test987654321"
        },
        "storage": {
            "history_db": "./custom_history.db",
            "export_dir": "./custom_exports"
        },
        "defaults": {
            "model": "gpt-4o-mini",
            "temperature": 0.3,
            "max_tokens": 500,
            "live": true,
            "system_prompt": "Tu es un expert Python."
        }
    }""",
        encoding="utf-8",
    )

    cfg = load_config(cfg_file)
    assert cfg.config_path == cfg_file.resolve()
    assert cfg.api_keys["openai"] == "sk-proj-test123456789"
    assert cfg.api_keys["anthropic"] == "sk-ant-test987654321"
    assert cfg.storage.history_db is not None
    assert cfg.storage.export_dir is not None
    assert cfg.defaults.model == "gpt-4o-mini"
    assert cfg.defaults.temperature == 0.3
    assert cfg.defaults.max_tokens == 500
    assert cfg.defaults.live is True
    assert cfg.defaults.system_prompt == "Tu es un expert Python."


def test_load_and_apply_config_injects_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("PYLLMKIT_HISTORY_DB", raising=False)

    cfg_file = tmp_path / "test_cfg.json"
    cfg_file.write_text(
        """{
        "api_keys": {
            "openai": "sk-proj-injected-key",
            "anthropic": "sk-ant-injected-key"
        },
        "storage": {
            "history_db": "./injected_history.db"
        }
    }""",
        encoding="utf-8",
    )

    load_and_apply_config(cfg_file)

    import os

    assert os.environ.get("OPENAI_API_KEY") == "sk-proj-injected-key"
    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-injected-key"
    assert os.environ.get("PYLLMKIT_HISTORY_DB") is not None


def test_cli_config_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target_config = tmp_path / "generated_config.json"

    # 1. config init
    res_init = runner.invoke(app, ["config", "init", "--path", str(target_config)])
    assert res_init.exit_code == 0
    assert target_config.exists()
    assert "Fichier de configuration généré avec succès" in res_init.output

    # 2. config init without force fails if exists
    res_init_fail = runner.invoke(app, ["config", "init", "--path", str(target_config)])
    assert res_init_fail.exit_code == 1
    assert "existe déjà" in res_init_fail.output

    # 3. config show
    monkeypatch.setenv("PYLLMKIT_CONFIG", str(target_config))
    res_show = runner.invoke(app, ["config", "show"])
    assert res_show.exit_code == 0
    assert target_config.name in res_show.output
    assert "OPENAI_API_KEY" in res_show.output
    assert "Base de données SQLite" in res_show.output

    # 4. config path
    res_path = runner.invoke(app, ["config", "path"])
    assert res_path.exit_code == 0
    assert target_config.name in res_path.output


def test_cli_config_yaml_init(tmp_path: Path) -> None:
    yaml_config = tmp_path / "config.yaml"
    res_init = runner.invoke(app, ["config", "init", "--path", str(yaml_config), "--format", "yaml"])
    assert res_init.exit_code == 0
    assert yaml_config.exists()
    content = yaml_config.read_text(encoding="utf-8")
    assert "api_keys:" in content
    assert "storage:" in content


def test_cli_config_local_init_and_gitignore(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("node_modules/\n.venv/\n", encoding="utf-8")

    res = runner.invoke(app, ["config", "init", "--local", "--format", "yaml"])
    assert res.exit_code == 0
    assert (tmp_path / ".pyllmkit.yaml").exists()

    git_content = gitignore.read_text(encoding="utf-8")
    assert ".pyllmkit*" in git_content
    assert ".pyllmkit/" in git_content


def test_cli_config_cascading_merging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    global_dir = tmp_path / "global_home" / ".config" / "pyllmkit"
    global_dir.mkdir(parents=True)
    global_file = global_dir / "config.yaml"
    global_file.write_text(
        """api_keys:
  openai: "sk-proj-global-openai"
defaults:
  model: "gpt-4o"
  temperature: 0.2
""",
        encoding="utf-8",
    )

    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    local_file = project_dir / ".pyllmkit.yaml"
    local_file.write_text(
        """api_keys:
  anthropic: "sk-ant-local-anthropic"
storage:
  history_db: ".pyllmkit/history.db"
defaults:
  model: "claude-3-5-sonnet"
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("HOME", str(tmp_path / "global_home"))
    monkeypatch.delenv("PYLLMKIT_CONFIG", raising=False)
    monkeypatch.chdir(project_dir)

    cfg = load_config()
    assert cfg.config_path == local_file.resolve()
    assert cfg.global_config_path == global_file.resolve()
    # Merged API keys: inherited global openai + local anthropic
    assert cfg.api_keys["openai"] == "sk-proj-global-openai"
    assert cfg.api_keys["anthropic"] == "sk-ant-local-anthropic"
    # Local model override wins
    assert cfg.defaults.model == "claude-3-5-sonnet"
    # Inherited global temperature
    assert cfg.defaults.temperature == 0.2
    # Relative storage path resolved relative to project
    assert cfg.storage.history_db == (project_dir / ".pyllmkit/history.db").resolve()

