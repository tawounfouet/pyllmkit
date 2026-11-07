"""Dynamic model discovery and catalog synchronization for PyLLMKit CLI."""

import json
import os
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


_MAX_DISCOVERY_BYTES = 1_048_576


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Do not follow a provider redirect with credentials or metadata."""

    def redirect_request(
        self, req: urllib.request.Request, fp: object, code: int,
        msg: str, headers: object, newurl: str,
    ) -> None:
        return None


def _open_discovery_request(
    request: urllib.request.Request, timeout: float,
):
    """Use fixed endpoints, no environment proxies, no redirects."""
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirectHandler(),
    )
    return opener.open(request, timeout=timeout)


def _fetch_discovery_json(
    url: str, headers: dict[str, str], timeout: float,
) -> dict[str, Any]:
    """Fetch only fixed provider URLs and read bounded JSON data."""
    if type(timeout) not in (float, int) or not 0 < timeout <= 120:
        raise ValueError("invalid_discovery_timeout")
    if not (url.startswith("https://") or url == "http://127.0.0.1:11434/api/tags"):
        raise ValueError("invalid_discovery_endpoint")
    req = urllib.request.Request(url, headers=headers)
    with _open_discovery_request(req, float(timeout)) as response:
        content = response.read(_MAX_DISCOVERY_BYTES + 1)
    if len(content) > _MAX_DISCOVERY_BYTES:
        raise ValueError("discovery_payload_too_large")
    data = json.loads(content.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid_discovery_payload")
    return data


def fetch_provider_models(
    provider: str,
    api_key: str | None = None,
    timeout: float = 10.0,
) -> list[str]:
    """Query the configured provider's fixed models endpoint, without redirect."""
    prov = provider.lower().strip()
    headers: dict[str, str] = {"User-Agent": "PyLLMKit/0.3.1"}

    if prov == "openai":
        if not api_key:
            raise ValueError("discovery_credential_required")
        url = "https://api.openai.com/v1/models"
        headers["Authorization"] = f"Bearer {api_key}"
        data = _fetch_discovery_json(url, headers, timeout)
        items = data.get("data", [])
        return sorted(item["id"] for item in items if isinstance(item, dict) and "id" in item)

    if prov == "anthropic":
        if not api_key:
            raise ValueError("discovery_credential_required")
        url = "https://api.anthropic.com/v1/models"
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        data = _fetch_discovery_json(url, headers, timeout)
        items = data.get("data", [])
        return sorted(item["id"] for item in items if isinstance(item, dict) and "id" in item)

    if prov in ("google", "gemini"):
        if not api_key:
            raise ValueError("discovery_credential_required")
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        headers["x-goog-api-key"] = api_key
        data = _fetch_discovery_json(url, headers, timeout)
        items = data.get("models", [])
        results = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            if name.startswith("models/"):
                name = name[len("models/"):]
            if name:
                results.append(name)
        return sorted(results)

    if prov == "mistral":
        if not api_key:
            raise ValueError("discovery_credential_required")
        url = "https://api.mistral.ai/v1/models"
        headers["Authorization"] = f"Bearer {api_key}"
        data = _fetch_discovery_json(url, headers, timeout)
        items = data.get("data", [])
        return sorted(item["id"] for item in items if isinstance(item, dict) and "id" in item)

    if prov == "xai":
        if not api_key:
            raise ValueError("discovery_credential_required")
        url = "https://api.x.ai/v1/models"
        headers["Authorization"] = f"Bearer {api_key}"
        data = _fetch_discovery_json(url, headers, timeout)
        items = data.get("data", [])
        return sorted(item["id"] for item in items if isinstance(item, dict) and "id" in item)

    if prov == "ollama":
        url = "http://127.0.0.1:11434/api/tags"
        data = _fetch_discovery_json(url, headers, timeout)
        items = data.get("models", [])
        results = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            if not name:
                continue
            if name.endswith(":latest"):
                name = name[:-7]
            if name and name not in results:
                results.append(name)
        return sorted(results)

    raise ValueError("unsupported_discovery_provider")


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
        except Exception:
            results[prov] = {
                "status": "error",
                "message": "Échec (discovery_request_failed)",
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
