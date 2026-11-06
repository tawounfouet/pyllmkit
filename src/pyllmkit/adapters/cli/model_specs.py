"""Known model specifications, context windows, capabilities, and pricing per 1M tokens."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Default path to packaged catalog
_DEFAULT_CATALOG_PATH = Path(__file__).parent / "data" / "models_catalog.json"


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Pricing in USD per 1M tokens (or per minute for realtime voice)."""

    input_cost: float
    output_cost: float
    cache_read: float | None = None
    cache_write: float | None = None
    cache_write_12h: float | None = None
    unit: str = "1M tokens"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """Rich technical characteristics and operational limits for a model."""

    id: str
    name: str
    family: str
    provider: str
    context_window: int
    max_output_tokens: int
    modalities_in: tuple[str, ...]
    modalities_out: tuple[str, ...]
    pricing: ModelPricing
    features: tuple[str, ...] = ()
    description: str = ""
    source_url: str = ""
    last_verified: str = ""
    pricing_modalities: tuple[tuple[str, dict[str, float | None]], ...] = ()


def _parse_spec_dict(mid: str, raw: dict[str, Any]) -> ModelSpec:
    """Parse raw dictionary entry into immutable ModelSpec."""
    raw_p = raw.get("pricing", {})
    pricing = ModelPricing(
        input_cost=float(raw_p.get("input_cost", 0.0)),
        output_cost=float(raw_p.get("output_cost", 0.0)),
        cache_read=float(raw_p["cache_read"]) if raw_p.get("cache_read") is not None else None,
        cache_write=float(raw_p["cache_write"]) if raw_p.get("cache_write") is not None else None,
        cache_write_12h=float(raw_p["cache_write_12h"]) if raw_p.get("cache_write_12h") is not None else None,
        unit=str(raw_p.get("unit", "1M tokens")),
    )
    raw_pm = raw.get("pricing_modalities", {})
    pricing_modalities = tuple(
        (mod, dict(costs)) for mod, costs in raw_pm.items()
    ) if isinstance(raw_pm, dict) else ()
    return ModelSpec(
        id=str(raw.get("id", mid)),
        name=str(raw.get("name", mid)),
        family=str(raw.get("family", "unknown")),
        provider=str(raw.get("provider", "unknown")),
        context_window=int(raw.get("context_window", 128_000)),
        max_output_tokens=int(raw.get("max_output_tokens", 8_192)),
        modalities_in=tuple(raw.get("modalities_in", ("text",))),
        modalities_out=tuple(raw.get("modalities_out", ("text",))),
        pricing=pricing,
        features=tuple(raw.get("features", ())),
        description=str(raw.get("description", "")),
        source_url=str(raw.get("source_url", "")),
        last_verified=str(raw.get("last_verified", "")),
        pricing_modalities=pricing_modalities,
    )


def load_catalog_specs(
    custom_path: Path | str | None = None,
    include_local_override: bool = True,
) -> dict[str, ModelSpec]:
    """Load model specifications from bundled JSON and optional local override."""
    specs: dict[str, ModelSpec] = {}

    # 1. Base bundled catalog
    base_file = Path(custom_path) if custom_path else _DEFAULT_CATALOG_PATH
    if base_file.exists():
        try:
            with open(base_file, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for mid, entry in data.items():
                        if isinstance(entry, dict):
                            specs[mid.lower()] = _parse_spec_dict(mid, entry)
        except Exception:
            pass

    # 2. Local project override (.pyllmkit/models_catalog.json)
    if include_local_override:
        local_candidates = [
            Path.cwd() / ".pyllmkit" / "models_catalog.json",
            Path.cwd() / "models_catalog.json",
        ]
        for candidate in local_candidates:
            if candidate.exists() and candidate.is_file():
                try:
                    with open(candidate, encoding="utf-8") as f:
                        local_data = json.load(f)
                        if isinstance(local_data, dict):
                            for mid, entry in local_data.items():
                                if isinstance(entry, dict):
                                    specs[mid.lower()] = _parse_spec_dict(mid, entry)
                except Exception:
                    pass
                break

    return specs


# Module-level dictionary for backward compatibility and high-performance in-memory lookups
MODEL_SPECS: dict[str, ModelSpec] = load_catalog_specs()


def get_model_spec(model_id: str) -> ModelSpec | None:
    """Retrieve full specification for a model identifier or alias."""
    if not model_id:
        return None
    normalized = model_id.strip().lower()

    if normalized in MODEL_SPECS:
        return MODEL_SPECS[normalized]

    # Résolution progressive des déclinaisons (snapshots datés, suffixes de réflexion, etc.)
    import re
    cleaned = normalized
    candidates = [normalized]

    # Retrait des suffixes de raisonnement (-non-reasoning, -reasoning)
    sub_reasoning = re.sub(r"-(non-)?reasoning$", "", cleaned)
    if sub_reasoning != cleaned:
        candidates.append(sub_reasoning)
        cleaned = sub_reasoning

    # Retrait des dates d'instantanés (-YYYY-MM-DD, -YYYYMMDD, -MMDD)
    sub_date = re.sub(r"-(\d{4}-?\d{2}-?\d{2}|\d{4})$", "", cleaned)
    if sub_date != cleaned:
        candidates.append(sub_date)
        cleaned = sub_date

    # Retrait des déclinaisons de préversion / itération (-preview, -exp, -latest, -001, -002, etc.)
    sub_ver = re.sub(r"-(preview|exp|latest|\d{3})$", "", cleaned)
    if sub_ver != cleaned:
        candidates.append(sub_ver)
        cleaned = sub_ver

    # Retrait de la version mineure (.XX) pour chercher la famille de base (ex: grok-4.20 -> grok-4)
    sub_major = re.sub(r"(\.[0-9]+)+$", "", cleaned)
    if sub_major != cleaned:
        candidates.append(sub_major)

    for cand in candidates:
        if cand in MODEL_SPECS:
            return MODEL_SPECS[cand]

    # Prefix match with separator (e.g. claude-haiku-4-5-20251001 -> claude-haiku-4-5)
    for key, spec in MODEL_SPECS.items():
        if (
            normalized.startswith(f"{key}-")
            or normalized.startswith(f"{key}:")
            or normalized.startswith(f"{key}.")
        ):
            return spec

    # Prefix match without false positives
    for key, spec in MODEL_SPECS.items():
        if normalized.startswith(key):
            return spec

    return None


def pricing_provenance(model_name: str | None) -> str:
    """Local catalog snapshot provenance, never a real-time tariff claim."""
    spec = get_model_spec(model_name) if model_name else None
    if spec is None:
        return "tarif inconnu (aucune vérification en temps réel)"
    date = spec.last_verified or "date de relevé inconnue"
    return f"catalogue local, relevé déclaré {date}, non vérifié en temps réel"


def compute_run_cost(
    model_name: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    cached_tokens: int | None = None,
) -> tuple[float | None, str]:
    """Compute estimated dollar cost for token usage and format human readable string."""
    if not isinstance(model_name, str) or not model_name:
        return None, "-"

    spec = get_model_spec(model_name)
    if spec is None or (input_tokens is None and output_tokens is None):
        return None, "-"

    in_count = int(input_tokens) if isinstance(input_tokens, (int, float)) else 0
    out_count = int(output_tokens) if isinstance(output_tokens, (int, float)) else 0
    cached_count = int(cached_tokens) if isinstance(cached_tokens, (int, float)) else 0

    # Local / Free models (e.g. Ollama, community)
    if spec.pricing.input_cost == 0.0 and spec.pricing.output_cost == 0.0:
        return 0.0, "$0.000000 (local/gratuit)"

    # Cached tokens discount
    if cached_count > 0 and spec.pricing.cache_read is not None:
        uncached_in = max(0, in_count - cached_count)
        cost_in = (uncached_in / 1_000_000) * spec.pricing.input_cost + (
            cached_count / 1_000_000
        ) * spec.pricing.cache_read
    else:
        cost_in = (in_count / 1_000_000) * spec.pricing.input_cost

    cost_out = (out_count / 1_000_000) * spec.pricing.output_cost
    total = cost_in + cost_out

    if total == 0.0:
        return 0.0, "$0.000000"
    if total < 0.0001:
        cost_str = f"${total:.6f} (${cost_in:.6f} in + ${cost_out:.6f} out)"
    elif total < 0.01:
        cost_str = f"${total:.5f} (${cost_in:.5f} in + ${cost_out:.5f} out)"
    else:
        cost_str = f"${total:.4f} (${cost_in:.4f} in + ${cost_out:.4f} out)"

    return total, cost_str
