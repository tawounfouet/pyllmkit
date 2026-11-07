"""M1 versioned catalogue and provider discovery regression tests, hermetic."""

from __future__ import annotations

import copy
import json
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.discovery import (
    _fetch_discovery_json,
    load_discovered_models,
    save_discovered_models,
    sync_configured_providers,
)
from pyllmkit.adapters.cli.discovery_snapshot_v2 import (
    ENDPOINTS,
    load_discovery_snapshot,
    parse_discovery_snapshot,
    snapshot_path,
    update_discovery_snapshot,
)
from pyllmkit.adapters.cli.main import app
from pyllmkit.adapters.cli.media_catalog_v2 import (
    CATALOG_PATH,
    MEDIA_TASKS,
    diff_media_catalog,
    effective_lifecycle,
    load_media_catalog,
    merge_media_catalog,
    parse_media_catalog,
    reconcile_observed_ids,
)
from pyllmkit.adapters.inference.media_lifecycle import MediaLifecycle

runner = CliRunner()


def _document() -> dict[str, object]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def test_checked_catalog_schema_and_routes_are_distinct() -> None:
    catalog = load_media_catalog()
    assert catalog.schema_version == 2
    assert len(catalog.models) == 23
    assert len({(m.api_provider, m.public_model_id) for m in catalog.models}) == 23
    assert all(m.model_owner and m.api_provider and m.billing_provider for m in catalog.models)
    assert all(m.availability == "catalog_only" for m in catalog.models)
    assert all(m.source_url.startswith("https://") for m in catalog.models)
    assert all(m.verified_at is not None for m in catalog.models)


def test_declared_task_taxonomy_does_not_invent_support() -> None:
    assert {
        "text_to_image", "image_edit", "text_to_video", "image_to_video",
        "text_to_speech", "speech_to_speech", "text_to_music", "text_to_sfx",
    } == MEDIA_TASKS
    catalog = load_media_catalog()
    assert catalog.list(task="text_to_image")
    assert catalog.list(task="text_to_video")
    assert catalog.list(task="text_to_speech")
    assert catalog.list(task="text_to_music") == ()
    assert catalog.list(task="image_edit") == ()
    with pytest.raises(ValueError, match="unsupported_media_task"):
        catalog.list(task="telepathy")


def test_native_provider_and_billing_identities_are_not_assumed_from_name() -> None:
    catalogue = load_media_catalog()
    model = catalogue.find("gpt-image-2", provider="openai")
    assert model is not None
    assert model.model_owner == "openai"
    assert model.billing_provider == "openai"
    assert model.native_model_id == "gpt-image-2"
    assert catalogue.find("veo-2", provider="google").native_model_id == "veo-2.0-generate-001"  # type: ignore[union-attr]


def test_explicit_provider_is_required_for_ambiguous_id_and_alias() -> None:
    data = _document()
    left = copy.deepcopy(data["models"][0])
    right = copy.deepcopy(left)
    left["public_model_id"] = "same-name"
    left["aliases"] = ["old-name"]
    right["api_provider"] = "second-provider"
    right["billing_provider"] = "second-provider"
    right["public_model_id"] = "same-name"
    right["aliases"] = ["old-name"]
    data["models"] = [left, right]
    catalog = parse_media_catalog(data)
    with pytest.raises(ValueError, match="ambiguous_model_identifier"):
        catalog.find("same-name")
    assert catalog.find("same-name", provider="openai") is not None
    assert catalog.find("old-name", provider="second-provider") is not None


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("schema_version", 1, "unsupported_media_catalog_schema"),
        ("updated_at", "november seven", "invalid_catalog_date"),
        ("revision", "", "invalid_catalog_revision"),
        ("models", {}, "invalid_catalog_entries"),
    ],
)
def test_versioned_catalog_rejects_invalid_header(field: str, value: object, error: str) -> None:
    data = _document()
    data[field] = value
    with pytest.raises(ValueError, match=error):
        parse_media_catalog(data)


def test_duplicate_route_and_alias_conflict_rejected() -> None:
    data = _document()
    original = copy.deepcopy(data["models"][0])
    data["models"].append(original)
    with pytest.raises(ValueError, match="duplicate_provider_model"):
        parse_media_catalog(data)
    data = _document()
    copy_model = copy.deepcopy(data["models"][0])
    copy_model["public_model_id"] = "another-image"
    copy_model["native_model_id"] = "another-image"
    copy_model["aliases"] = [data["models"][0]["public_model_id"]]
    data["models"].append(copy_model)
    with pytest.raises(ValueError, match="ambiguous_provider_alias"):
        parse_media_catalog(data)


def test_malformed_price_source_or_unverified_capability_is_rejected() -> None:
    data = _document()
    item = data["models"][0]
    item["source_url"] = "file:///etc/passwd"
    with pytest.raises(ValueError, match="invalid_media_provenance"):
        parse_media_catalog(data)
    item["source_url"] = "https://example.org/model"
    item["capabilities"]["tasks"] = ["text_to_music", "bad_task"]
    with pytest.raises(ValueError, match="unsupported_capability_value"):
        parse_media_catalog(data)
    item["capabilities"]["tasks"] = ["text_to_image"]
    item["capabilities"]["api_async"] = "yes"
    with pytest.raises(ValueError, match="invalid_capability_boolean"):
        parse_media_catalog(data)


def test_retirement_policy_overrides_observed_provider_listing() -> None:
    model = load_media_catalog().find("dall-e-3", provider="openai")
    assert model is not None
    assert effective_lifecycle(model) is MediaLifecycle.RETIRED
    records = reconcile_observed_ids(load_media_catalog(), {"openai": {"dall-e-3"}})
    match = next(r for r in records if r["model"] == "dall-e-3")
    assert match["comparison"] == "observed"
    assert match["lifecycle"] == "retired"


def test_deprecation_date_rolls_forward_even_if_catalog_is_older() -> None:
    model = load_media_catalog().find("gpt-4o-mini-tts", provider="openai")
    assert model is not None
    assert effective_lifecycle(model, on_date=date(2027, 1, 5)) is MediaLifecycle.DEPRECATED
    assert effective_lifecycle(model, on_date=date(2027, 1, 6)) is MediaLifecycle.RETIRED


def test_model_diff_deterministic_and_non_destructive() -> None:
    data = _document()
    older = copy.deepcopy(data)
    older["revision"] = "m1.previous"
    older["models"] = older["models"][:-1]
    old = parse_media_catalog(older)
    new = parse_media_catalog(data)
    diff = diff_media_catalog(old, new)
    assert len(diff["added"]) == 1
    assert diff["removed"] == ()
    assert diff["changed"] == ()


def test_discovery_snapshot_provider_scoped_and_private(tmp_path: Path) -> None:
    target = tmp_path / "discovered_models_v2.json"
    t = datetime(2026, 11, 7, 13, 0, tzinfo=UTC)
    saved = update_discovery_snapshot(
        target, {"openai": ["shared", "gpt-image-2"], "google": ["shared"]},
        observed_at=t,
    )
    assert saved.revision == 2
    reloaded = load_discovery_snapshot(target)
    assert reloaded.observed_ids() == {
        "openai": {"shared", "gpt-image-2"}, "google": {"shared"},
    }
    assert reloaded.observations[0].complete is False
    assert reloaded.observations[0].endpoint == ENDPOINTS["google"]
    assert "sk-" not in target.read_text(encoding="utf-8")
    assert target.stat().st_mode & 0o777 == 0o600


def test_discovery_does_not_tombstone_missing_ids_and_preserves_unsynced_provider(
    tmp_path: Path,
) -> None:
    target = tmp_path / "discovered_models_v2.json"
    update_discovery_snapshot(target, {
        "openai": ["first", "second"], "google": ["gemini-3.1-flash-image"],
    })
    saved = update_discovery_snapshot(target, {"openai": ["first"]})
    assert saved.observed_ids()["google"] == {"gemini-3.1-flash-image"}
    assert saved.observed_ids()["openai"] == {"first"}
    assert all(not obs.complete for obs in saved.observations)
    # Missing from incomplete API listing never means provider retirement.
    rows = reconcile_observed_ids(load_media_catalog(), saved.observed_ids())
    assert next(x for x in rows if x["model"] == "gpt-image-2")["comparison"] == "catalog_only"


def test_legacy_discovery_migration_preserves_same_id_from_multiple_providers(
    tmp_path: Path,
) -> None:
    path = tmp_path / "discovered_models.json"
    save_discovered_models([
        {"id": "duplicate", "provider": "openai", "family": "openai"},
        {"id": "duplicate", "provider": "google", "family": "google"},
    ], path)
    entries = load_discovered_models(path)
    assert len(entries) == 2
    assert {x["provider"] for x in entries} == {"openai", "google"}
    assert snapshot_path(path).name == "discovered_models_v2.json"


@pytest.mark.parametrize(
    "bad",
    [
        {"schema_version": 1, "revision": 1, "observations": []},
        {"schema_version": 2, "revision": 0, "observations": []},
        {"schema_version": 2, "revision": 1, "observations": [{
            "provider": "openai", "endpoint": ENDPOINTS["openai"], "model_ids": ["x"],
            "observed_at": "2026-11-07T13:00:00+00:00", "complete": True,
        }]},
    ],
)
def test_discovery_rejects_schema_and_completeness_claims(bad: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        parse_discovery_snapshot(bad)


def test_discovery_endpoint_is_exact_allowlist_not_arbitrary_https() -> None:
    with patch("pyllmkit.adapters.cli.discovery._open_discovery_request") as transport:
        with pytest.raises(ValueError, match="invalid_discovery_endpoint"):
            _fetch_discovery_json("https://attacker.invalid/v1/models", {}, 10)
    transport.assert_not_called()


def test_models_availability_offline_json_does_not_claim_real_access(
    tmp_path: Path,
) -> None:
    with (
        patch("pyllmkit.adapters.cli.commands.models.get_discovered_models_path",
              return_value=tmp_path / "discovered_models.json"),
        patch("socket.getaddrinfo", side_effect=AssertionError("no DNS")),
    ):
        result = runner.invoke(app, [
            "models", "availability", "--provider", "openai", "--model",
            "dall-e-3", "--json",
        ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["account_access_verified"] is False
    assert payload["models"][0]["lifecycle"] == "retired"
    assert payload["models"][0]["observation"] == "catalog_only"


def test_models_diff_offline_cannot_infer_retirement(
    tmp_path: Path,
) -> None:
    target = tmp_path / "discovered_models.json"
    update_discovery_snapshot(snapshot_path(target), {"openai": ["dall-e-3"]})
    with patch("pyllmkit.adapters.cli.commands.models.get_discovered_models_path",
               return_value=target):
        result = runner.invoke(app, ["models", "diff", "--json"])
    assert result.exit_code == 0, result.output
    doc = json.loads(result.stdout)
    assert doc["listing_complete"] is False
    entry = next(x for x in doc["differences"] if x["model"] == "dall-e-3")
    assert entry["comparison"] == "observed"
    assert entry["lifecycle"] == "retired"


def test_cli_versioned_media_list_and_snapshot_diff(tmp_path: Path) -> None:
    result = runner.invoke(app, ["models", "list", "--media"], env={"COLUMNS": "240"})
    assert result.exit_code == 0
    assert "gpt-image-2" in result.stdout
    before = _document()
    before["revision"] = "old"
    before["models"] = before["models"][:-1]
    file = tmp_path / "older.json"
    file.write_text(json.dumps(before), encoding="utf-8")
    result = runner.invoke(app, ["models", "diff", "--against", str(file), "--json"])
    assert result.exit_code == 0, result.output
    assert len(json.loads(result.stdout)["added"]) == 1


def test_sync_emits_private_incomplete_versioned_snapshot(tmp_path: Path, monkeypatch) -> None:
    from pyllmkit.adapters.cli.config import CliConfig

    monkeypatch.setattr(
        "pyllmkit.adapters.cli.discovery.get_config",
        lambda: CliConfig(api_keys={"openai": "sk-synthetic"}),
    )
    monkeypatch.setattr(
        "pyllmkit.adapters.cli.discovery.get_discovered_models_path",
        lambda local=False: tmp_path / "discovered_models.json",
    )
    transport = MagicMock()
    transport.read.return_value = b'{"data":[{"id":"gpt-image-2"}]}'
    transport.__enter__.return_value = transport
    with patch("pyllmkit.adapters.cli.discovery._open_discovery_request",
               return_value=transport):
        total, results = sync_configured_providers(target_provider="openai")
    assert total == 1
    assert results["openai"]["status"] == "success"
    cache = load_discovery_snapshot(tmp_path / "discovered_models_v2.json")
    assert cache.observed_ids()["openai"] == {"gpt-image-2"}
    assert all(not item.complete for item in cache.observations)
    assert "sk-synthetic" not in (tmp_path / "discovered_models_v2.json").read_text()


def test_catalog_extension_never_overwrites_a_verified_existing_route() -> None:
    base = load_media_catalog()
    payload = _document()
    payload["revision"] = "user-extension"
    copy_route = copy.deepcopy(payload["models"][0])
    copy_route["billing_provider"] = "unknown-billing-service"
    payload["models"] = [copy_route]
    extension = parse_media_catalog(payload)
    with pytest.raises(ValueError, match="verified_route_overwrite_forbidden"):
        merge_media_catalog(base, extension)


def test_catalog_extension_with_explicit_aggregator_route_is_accepted() -> None:
    base = load_media_catalog()
    payload = _document()
    payload["revision"] = "test-aggregator"
    item = copy.deepcopy(payload["models"][0])
    item["public_model_id"] = "alternative-photo-model"
    item["native_model_id"] = "vendor-model-v1"
    item["model_owner"] = "creator"
    item["api_provider"] = "fal"
    item["billing_provider"] = "fal"
    item["deployment_channel"] = "aggregator"
    item["aliases"] = ["photo-fast"]
    item["source_url"] = "https://fal.ai/models"
    payload["models"] = [item]
    extension = parse_media_catalog(payload)
    combined = merge_media_catalog(base, extension)
    assert len(combined.models) == 24
    route = combined.find("photo-fast", provider="fal")
    assert route is not None
    assert route.model_owner == "creator"
    assert route.api_provider == "fal"
    assert route.billing_provider == "fal"
    assert route.native_model_id == "vendor-model-v1"
    assert len(base.models) == 23


def test_gemini_alias_sync_uses_canonical_google_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pyllmkit.adapters.cli.config import CliConfig

    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSYNTHETIC")
    monkeypatch.setattr(
        "pyllmkit.adapters.cli.discovery.get_config",
        lambda: CliConfig(api_keys={}),
    )
    monkeypatch.setattr(
        "pyllmkit.adapters.cli.discovery.get_discovered_models_path",
        lambda local=False: tmp_path / "discovered_models.json",
    )
    resp = MagicMock()
    resp.read.return_value = b'{"models":[{"name":"models/gemini-3.1-flash-image"}]}'
    resp.__enter__.return_value = resp
    with patch(
        "pyllmkit.adapters.cli.discovery._open_discovery_request", return_value=resp,
    ):
        total, results = sync_configured_providers(target_provider="gemini")
    assert total == 1
    assert results["gemini"]["status"] == "success"
    saved = load_discovery_snapshot(tmp_path / "discovered_models_v2.json")
    assert saved.observed_ids() == {"google": {"gemini-3.1-flash-image"}}

def test_legacy_registry_never_selects_ambiguous_provider_implicitly() -> None:
    from pyllmkit.adapters.cli.catalog import create_reference_catalog
    from pyllmkit.domain.models import ModelId

    conflicting = [
        {"id": "overlap-model", "provider": "openai", "family": "openai"},
        {"id": "overlap-model", "provider": "google", "family": "google"},
    ]
    with patch("pyllmkit.adapters.cli.catalog.load_discovered_models",
               return_value=conflicting):
        catalog = create_reference_catalog()
    assert catalog.models.get(ModelId("overlap-model")) is None
