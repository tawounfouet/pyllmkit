"""Dynamic model discovery and catalog synchronization for PyLLMKit CLI."""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .config import find_config_file, get_config

PROVIDER_FAMILY_MAP = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google",
    "mistral": "mistral",
    "xai": "xai",
    "ollama": "meta",
}


def get_discovered_models_path(local: bool = False) -> Path:
    """Resolve destination path for discovered models JSON cache."""
    if local:
        local_cfg = find_config_file()
        base_dir = local_cfg.parent if local_cfg else Path.cwd()
        return (base_dir / ".pyllmkit" / "discovered_models.json").resolve()

    local_cfg = find_config_file()
    if local_cfg:
        return (local_cfg.parent / ".pyllmkit" / "discovered_models.json").resolve()

    return Path("~/.config/pyllmkit/discovered_models.json").expanduser().resolve()


def load_discovered_models(path: Path | None = None) -> list[dict[str, str]]:
    """Load previously discovered models from JSON cache file."""
    target = path or get_discovered_models_path()
    if not target.is_file():
        return []
    try:
        content = target.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, list):
            return [m for m in data if isinstance(m, dict) and "id" in m]
    except Exception:
        pass
    return []


def save_discovered_models(
    models: list[dict[str, str]],
    target_path: Path | None = None,
) -> Path:
    """Save or merge discovered models into JSON cache file."""
    target = target_path or get_discovered_models_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    existing = load_discovered_models(target)
    by_id = {m["id"]: m for m in existing}
    for m in models:
        by_id[m["id"]] = m

    merged = sorted(by_id.values(), key=lambda x: (x.get("provider", ""), x.get("id", "")))
    target.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def fetch_provider_models(
    provider: str,
    api_key: str | None = None,
    timeout: float = 10.0,
) -> list[str]:
    """Query provider HTTP API to discover all available models for the given credentials."""
    prov = provider.lower().strip()
    headers: dict[str, str] = {"User-Agent": "PyLLMKit/0.3.1"}

    if prov == "openai":
        if not api_key:
            raise ValueError("Clé d'API OpenAI requise pour interroger le catalogue")
        url = "https://api.openai.com/v1/models"
        headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            return sorted(item["id"] for item in items if isinstance(item, dict) and "id" in item)

    elif prov == "anthropic":
        if not api_key:
            raise ValueError("Clé d'API Anthropic requise pour interroger le catalogue")
        url = "https://api.anthropic.com/v1/models"
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            return sorted(item["id"] for item in items if isinstance(item, dict) and "id" in item)

    elif prov in ("google", "gemini"):
        if not api_key:
            raise ValueError("Clé d'API Gemini requise pour interroger le catalogue")
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("models", [])
            results = []
            for item in items:
                name = item.get("name", "")
                if name.startswith("models/"):
                    name = name[len("models/"):]
                if name:
                    results.append(name)
            return sorted(results)

    elif prov == "mistral":
        if not api_key:
            raise ValueError("Clé d'API Mistral requise pour interroger le catalogue")
        url = "https://api.mistral.ai/v1/models"
        headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            return sorted(item["id"] for item in items if isinstance(item, dict) and "id" in item)

    elif prov == "xai":
        if not api_key:
            raise ValueError("Clé d'API xAI requise pour interroger le catalogue")
        url = "https://api.x.ai/v1/models"
        headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            return sorted(item["id"] for item in items if isinstance(item, dict) and "id" in item)

    elif prov == "ollama":
        url = "http://localhost:11434/api/tags"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("models", [])
            results = []
            for item in items:
                name = item.get("name", "")
                if not name:
                    continue
                if name.endswith(":latest"):
                    name = name[:-7]
                if name and name not in results:
                    results.append(name)
            return sorted(results)

    else:
        raise ValueError(f"Fournisseur non supporté pour la synchronisation : {prov}")


def sync_configured_providers(
    target_provider: str | None = None,
    local: bool = False,
    timeout: float = 10.0,
) -> tuple[int, dict[str, dict[str, Any]]]:
    """Discover models across configured providers and persist to JSON cache."""
    cfg = get_config()
    providers_to_sync = (
        [target_provider.lower().strip()]
        if target_provider
        else ["openai", "anthropic", "google", "mistral", "xai", "ollama"]
    )

    results: dict[str, dict[str, Any]] = {}
    discovered_records: list[dict[str, str]] = []

    for prov in providers_to_sync:
        canonical_env = (
            "GEMINI_API_KEY" if prov in ("google", "gemini")
            else f"{prov.upper()}_API_KEY"
        )
        api_key = cfg.api_keys.get(prov)
        if not api_key or "..." in api_key:
            api_key = os.environ.get(canonical_env)

        if prov != "ollama" and (not api_key or "..." in api_key):
            results[prov] = {
                "status": "skipped",
                "message": "Ignoré (clé API absente ou non renseignée)",
                "count": 0,
            }
            continue

        try:
            model_ids = fetch_provider_models(prov, api_key=api_key, timeout=timeout)
            family = PROVIDER_FAMILY_MAP.get(prov, prov)
            runtime = "ollama" if prov == "ollama" else "cloud"

            for mid in model_ids:
                discovered_records.append({
                    "id": mid,
                    "family": family,
                    "provider": prov,
                    "runtime": runtime,
                    "region": "local" if prov == "ollama" else "global",
                })

            results[prov] = {
                "status": "success",
                "message": f"{len(model_ids)} modèle(s) synchronisé(s)",
                "count": len(model_ids),
                "models": model_ids,
            }
        except Exception as exc:
            results[prov] = {
                "status": "error",
                "message": f"Échec ({exc})",
                "count": 0,
            }

    saved_path = None
    if discovered_records:
        saved_path = save_discovered_models(
            discovered_records,
            target_path=get_discovered_models_path(local=local),
        )

    total_synced = len(discovered_records)
    for _p, res in results.items():
        if saved_path:
            res["path"] = str(saved_path)

    return total_synced, results
