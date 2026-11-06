"""Configuration file loader and manager for PyLLMKit CLI.

Supports JSON (built-in), TOML (Python 3.11+ built-in tomllib), and YAML (via built-in parser or optional PyYAML).
Supports hierarchical discovery: Local project configuration takes precedence over global ~/.config/pyllmkit/config.yaml.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

API_KEY_ENV_MAPPINGS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "openai_api_key": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "google": "GEMINI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "gemini_api_key": "GEMINI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "mistral_api_key": "MISTRAL_API_KEY",
    "xai": "XAI_API_KEY",
    "xai_api_key": "XAI_API_KEY",
}


@dataclass
class StorageConfig:
    """Storage location configurations."""

    history_db: Path | None = None
    export_dir: Path | None = None


@dataclass
class DefaultsConfig:
    """Default invocation parameters."""

    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    system_prompt: str | None = None
    live: bool = False


@dataclass
class CliConfig:
    """Global CLI configuration with local override support."""

    config_path: Path | None = None
    global_config_path: Path | None = None
    local_api_keys: dict[str, str] = field(default_factory=dict)
    global_api_keys: dict[str, str] = field(default_factory=dict)
    api_keys: dict[str, str] = field(default_factory=dict)
    storage: StorageConfig = field(default_factory=StorageConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)


_ACTIVE_CONFIG: CliConfig | None = None


def mask_secret(value: str) -> str:
    """Mask secret value for safe terminal display."""
    if not value:
        return "[non configuré]"
    if len(value) <= 8:
        return "****"
    return f"{value[:6]}...{value[-4:]}"


def find_local_config_file(start_dir: Path | None = None) -> Path | None:
    """Find local configuration in start_dir or its parent directories."""
    curr = (start_dir or Path.cwd()).resolve()
    local_names = [
        ".pyllmkit.yaml",
        ".pyllmkit.yml",
        ".pyllmkit.json",
        ".pyllmkit.toml",
        "pyllmkit.yaml",
        "pyllmkit.yml",
        "pyllmkit.json",
        "pyllmkit.toml",
        ".pyllmkit/config.yaml",
        ".pyllmkit/config.json",
    ]
    # Check current directory and parents up to git root or filesystem root
    for d in [curr, *curr.parents]:
        for name in local_names:
            candidate = d / name
            if candidate.is_file():
                return candidate.resolve()
        if (d / ".git").exists():
            break
    return None


def find_global_config_file() -> Path | None:
    """Find user global configuration in ~/.config/pyllmkit/."""
    config_dir = Path.home() / ".config" / "pyllmkit"
    global_names = [
        "config.yaml",
        "config.yml",
        "config.json",
        "config.toml",
    ]
    for name in global_names:
        candidate = config_dir / name
        if candidate.is_file():
            return candidate.resolve()
    return None


def find_config_file(custom_path: Path | str | None = None) -> Path | None:
    """Locate configuration file following discovery hierarchy (Custom -> Env -> Local -> Global)."""
    if custom_path is not None:
        p = Path(custom_path).expanduser().resolve()
        return p if p.is_file() else None

    # 1. Environment variable
    env_config = os.environ.get("PYLLMKIT_CONFIG")
    if env_config:
        p = Path(env_config).expanduser().resolve()
        if p.is_file():
            return p

    # 2. Local project configuration (priority over global)
    local_cfg = find_local_config_file()
    if local_cfg:
        return local_cfg

    # 3. Global user home configuration
    return find_global_config_file()


def ensure_in_gitignore(target_dir: Path) -> bool:
    """Ensure .pyllmkit configuration and artifacts are ignored in target_dir's .gitignore."""
    gitignore = target_dir / ".gitignore"
    if not gitignore.exists():
        for parent in target_dir.parents:
            if (parent / ".git").exists() and (parent / ".gitignore").exists():
                gitignore = parent / ".gitignore"
                break

    if gitignore.exists():
        try:
            content = gitignore.read_text(encoding="utf-8")
            if ".pyllmkit*" not in content and ".pyllmkit" not in content:
                addition = (
                    "\n# PyLLMKit local configuration, SQLite database and exports\n"
                    ".pyllmkit*\n"
                    ".pyllmkit/\n"
                    "*.db\n"
                )
                gitignore.write_text(content.rstrip() + addition + "\n", encoding="utf-8")
                return True
        except Exception:
            pass
    return False


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Lightweight 2-level YAML parser for basic configurations without external dependencies."""
    result: dict[str, Any] = {}
    current_section: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")

        if indent == 0:
            if not val:
                current_section = key
                result[current_section] = {}
            else:
                current_section = None
                result[key] = val
        elif indent > 0 and current_section is not None:
            typed_val: Any = val
            if val.lower() == "true":
                typed_val = True
            elif val.lower() == "false":
                typed_val = False
            else:
                try:
                    typed_val = int(val)
                except ValueError:
                    try:
                        typed_val = float(val)
                    except ValueError:
                        typed_val = val
            result[current_section][key] = typed_val

    return result


def _parse_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    suffix = path.suffix.lower()

    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore[import-untyped]

            data = yaml.safe_load(text)
            return data if isinstance(data, dict) else {}
        except ImportError:
            try:
                return _parse_simple_yaml(text)
            except Exception:
                raise ValueError(
                    f"Le fichier '{path.name}' est en YAML mais PyYAML n'est pas installé. "
                    "Installez-le avec 'pip install pyyaml' ou utilisez un fichier .json."
                ) from None

    if suffix == ".toml":
        try:
            import tomllib

            data = tomllib.loads(text)
            return data if isinstance(data, dict) else {}
        except ImportError:
            raise ValueError("Python >= 3.11 est requis pour le format .toml.") from None

    # Par défaut: JSON
    data = json.loads(text)
    return data if isinstance(data, dict) else {}


def _extract_config_data(raw: dict[str, Any], base_dir: Path | None = None) -> tuple[dict[str, str], StorageConfig, DefaultsConfig]:
    raw_keys = raw.get("api_keys") or raw.get("keys") or {}
    api_keys = {str(k): str(v) for k, v in raw_keys.items() if v is not None} if isinstance(raw_keys, dict) else {}

    storage_dict = raw.get("storage") or {}
    history_db = None
    export_dir = None
    if isinstance(storage_dict, dict):
        if storage_dict.get("history_db"):
            p = Path(str(storage_dict["history_db"])).expanduser()
            if not p.is_absolute() and base_dir is not None:
                history_db = (base_dir / p).resolve()
            else:
                history_db = p.resolve()
        if storage_dict.get("export_dir"):
            p = Path(str(storage_dict["export_dir"])).expanduser()
            if not p.is_absolute() and base_dir is not None:
                export_dir = (base_dir / p).resolve()
            else:
                export_dir = p.resolve()

    defaults_dict = raw.get("defaults") or {}
    defaults = DefaultsConfig()
    if isinstance(defaults_dict, dict):
        defaults.model = str(defaults_dict["model"]) if defaults_dict.get("model") else None
        defaults.temperature = (
            float(defaults_dict["temperature"]) if defaults_dict.get("temperature") is not None else None
        )
        defaults.max_tokens = int(defaults_dict["max_tokens"]) if defaults_dict.get("max_tokens") is not None else None
        defaults.system_prompt = (
            str(defaults_dict["system_prompt"]) if defaults_dict.get("system_prompt") else None
        )
        defaults.live = bool(defaults_dict.get("live", False))

    return api_keys, StorageConfig(history_db=history_db, export_dir=export_dir), defaults


def load_config(custom_path: Path | str | None = None) -> CliConfig:
    """Load configuration with cascading overrides (Custom -> Local -> Global)."""
    # 1. Custom explicit path or PYLLMKIT_CONFIG environment variable
    if custom_path is not None:
        cfg_file = find_config_file(custom_path)
        if cfg_file is None:
            return CliConfig()
        raw = _parse_file(cfg_file)
        keys, storage, defaults = _extract_config_data(raw, base_dir=cfg_file.parent)
        return CliConfig(
            config_path=cfg_file,
            global_config_path=None,
            local_api_keys=keys,
            global_api_keys={},
            api_keys=keys,
            storage=storage,
            defaults=defaults,
        )

    env_config = os.environ.get("PYLLMKIT_CONFIG")
    if env_config is not None:
        if not env_config.strip() or env_config == "/dev/null":
            return CliConfig()
        cfg_file = Path(env_config).expanduser().resolve()
        if not cfg_file.exists():
            return CliConfig()
        raw = _parse_file(cfg_file)
        keys, storage, defaults = _extract_config_data(raw, base_dir=cfg_file.parent)
        return CliConfig(
            config_path=cfg_file,
            global_config_path=None,
            local_api_keys=keys,
            global_api_keys={},
            api_keys=keys,
            storage=storage,
            defaults=defaults,
        )

    # 2. Cascading discovery: Global base, Local project override
    global_file = find_global_config_file()
    local_file = find_local_config_file()

    global_keys: dict[str, str] = {}
    global_storage = StorageConfig()
    global_defaults = DefaultsConfig()

    if global_file is not None:
        try:
            g_raw = _parse_file(global_file)
            global_keys, global_storage, global_defaults = _extract_config_data(g_raw, base_dir=global_file.parent)
        except Exception:
            pass

    if local_file is not None:
        try:
            l_raw = _parse_file(local_file)
            local_keys, local_storage, local_defaults = _extract_config_data(l_raw, base_dir=local_file.parent)
        except Exception as exc:
            raise ValueError(f"Erreur de lecture du fichier de configuration local '{local_file}': {exc}") from exc

        # Merging: Local takes precedence over Global
        merged_keys = {**global_keys, **local_keys}
        merged_storage = StorageConfig(
            history_db=local_storage.history_db or global_storage.history_db,
            export_dir=local_storage.export_dir or global_storage.export_dir,
        )
        merged_defaults = DefaultsConfig(
            model=local_defaults.model or global_defaults.model,
            temperature=local_defaults.temperature if local_defaults.temperature is not None else global_defaults.temperature,
            max_tokens=local_defaults.max_tokens if local_defaults.max_tokens is not None else global_defaults.max_tokens,
            system_prompt=local_defaults.system_prompt or global_defaults.system_prompt,
            live=local_defaults.live or global_defaults.live,
        )
        return CliConfig(
            config_path=local_file,
            global_config_path=global_file,
            local_api_keys=local_keys,
            global_api_keys=global_keys,
            api_keys=merged_keys,
            storage=merged_storage,
            defaults=merged_defaults,
        )

    # If only global exists
    if global_file is not None:
        return CliConfig(
            config_path=global_file,
            global_config_path=global_file,
            local_api_keys={},
            global_api_keys=global_keys,
            api_keys=global_keys,
            storage=global_storage,
            defaults=global_defaults,
        )

    return CliConfig()


def load_and_apply_config(custom_path: Path | str | None = None) -> CliConfig:
    """Load configuration, inject environment variables and configure global active state."""
    global _ACTIVE_CONFIG
    cfg = load_config(custom_path)

    # Inject missing API keys into environment (ignoring template placeholders containing '...')
    for key_alias, key_value in cfg.api_keys.items():
        canonical_env = API_KEY_ENV_MAPPINGS.get(key_alias.lower(), key_alias.upper())
        if not os.environ.get(canonical_env) and key_value and "..." not in key_value:
            os.environ[canonical_env] = key_value

    # Inject history_db if set and not already overridden by PYLLMKIT_HISTORY_DB
    if cfg.storage.history_db and not os.environ.get("PYLLMKIT_HISTORY_DB"):
        os.environ["PYLLMKIT_HISTORY_DB"] = str(cfg.storage.history_db)

    _ACTIVE_CONFIG = cfg
    return cfg


def get_config() -> CliConfig:
    """Return the active global configuration."""
    global _ACTIVE_CONFIG
    if _ACTIVE_CONFIG is None:
        _ACTIVE_CONFIG = load_and_apply_config()
    return _ACTIVE_CONFIG


def generate_template_config(format_type: str = "yaml", local: bool = False) -> str:
    """Generate an annotated template configuration file (global or local)."""
    if local:
        if format_type in ("yaml", "yml"):
            return """# Configuration locale PyLLMKit pour ce projet
# Prioritaire sur la configuration globale ~/.config/pyllmkit/config.yaml

api_keys:
  # Optionnel: surchargez des clés d'API spécifiques à ce projet ici.
  # Les clés non définies ici héritent automatiquement de ~/.config/pyllmkit/config.yaml
  # openai: "sk-proj-..."

storage:
  # Base SQLite et exports stockés localement dans ce projet (non suivis par git)
  history_db: ".pyllmkit/history.db"
  export_dir: "./exports"

defaults:
  model: "gpt-4o"
  live: false
  temperature: 0.7
  max_tokens: 1500
  system_prompt: "Tu es un assistant IA expert dédié à ce projet."
"""
        return """{
  "api_keys": {},
  "storage": {
    "history_db": ".pyllmkit/history.db",
    "export_dir": "./exports"
  },
  "defaults": {
    "model": "gpt-4o",
    "live": false,
    "temperature": 0.7,
    "max_tokens": 1500,
    "system_prompt": "Tu es un assistant IA expert dédié à ce projet."
  }
}
"""

    if format_type in ("yaml", "yml"):
        return """# Configuration globale PyLLMKit (~/.config/pyllmkit/config.yaml)
# Vos clés d'API et paramètres par défaut pour toute la machine.

api_keys:
  openai: "sk-proj-..."
  anthropic: "sk-ant-..."
  gemini: "AIzaSy..."
  mistral: "..."
  xai: "..."

storage:
  history_db: "~/.config/pyllmkit/history.db"
  export_dir: "./exports"

defaults:
  model: "gpt-4o"
  temperature: 0.7
  max_tokens: 1000
  live: false
  system_prompt: "Tu es un assistant IA concis et précis."
"""

    return """{
  "api_keys": {
    "openai": "sk-proj-...",
    "anthropic": "sk-ant-...",
    "gemini": "AIzaSy...",
    "mistral": "...",
    "xai": "..."
  },
  "storage": {
    "history_db": "~/.config/pyllmkit/history.db",
    "export_dir": "./exports"
  },
  "defaults": {
    "model": "gpt-4o",
    "temperature": 0.7,
    "max_tokens": 1000,
    "live": false,
    "system_prompt": "Tu es un assistant IA concis et précis."
  }
}
"""
