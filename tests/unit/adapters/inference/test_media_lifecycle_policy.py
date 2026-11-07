"""M0: offline lifecycle cutoffs and no-paid-traffic policy regression tests."""

from datetime import date
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.main import app
from pyllmkit.adapters.inference.media_lifecycle import (
    MediaLifecycle,
    media_model_policy,
    require_live_media_model,
)
from pyllmkit.application.inference import InvocationPortError


@pytest.mark.parametrize(
    "model",
    ["dall-e-2", "dall-e-3", "imagen-3", "veo-2", "gemini-2.5-flash-image"],
)
def test_retired_model_cannot_be_used_live(model: str) -> None:
    with pytest.raises(InvocationPortError, match="model_retired"):
        require_live_media_model(model, on_date=date(2026, 11, 7))


@pytest.mark.parametrize(
    ("model", "kind"),
    [
        ("dall-e-3", "image"),
        ("imagen-3", "image"),
        ("gemini-2.5-flash-image", "image"),
        ("veo-2", "video"),
    ],
)
def test_cli_retired_model_fails_before_secrets_and_network(model: str, kind: str) -> None:
    with (
        patch("socket.getaddrinfo", side_effect=AssertionError("unexpected DNS")),
        patch("urllib.request.urlopen", side_effect=AssertionError("unexpected network")),
        patch("urllib.request.build_opener", side_effect=AssertionError("unexpected network")),
    ):
        result = CliRunner().invoke(
            app, ["generate", kind, "A simple test", "--model", model, "--live"],
        )
    assert result.exit_code == 1
    assert "model_retired" in result.stdout


def test_unverified_marketing_alias_is_blocked_for_live_only() -> None:
    model = "gemini-nano-banana-2.1"
    assert media_model_policy(model).state is MediaLifecycle.UNVERIFIED
    with pytest.raises(InvocationPortError, match="model_unverified"):
        require_live_media_model(model)
    result = CliRunner().invoke(
        app, ["generate", "image", "A tree", "--model", model, "--live"],
    )
    assert result.exit_code == 1 and "model_unverified" in result.stdout


def test_scheduled_shutdown_becomes_hard_refusal_on_cutoff() -> None:
    assert media_model_policy(
        "gpt-image-1-mini", on_date=date(2026, 11, 30),
    ).state is MediaLifecycle.DEPRECATED
    assert media_model_policy(
        "gpt-image-1-mini", on_date=date(2026, 12, 1),
    ).state is MediaLifecycle.RETIRED
    assert media_model_policy(
        "gpt-4o-mini-tts", on_date=date(2027, 1, 5),
    ).state is MediaLifecycle.DEPRECATED
    with pytest.raises(InvocationPortError, match="model_retired"):
        require_live_media_model(
            "gpt-4o-mini-tts", on_date=date(2027, 1, 6),
        )


def test_unknown_id_does_not_invent_a_replacement() -> None:
    info = media_model_policy("custom-company-media-model")
    assert info.state is MediaLifecycle.UNKNOWN
    assert info.replacement is None
    require_live_media_model("custom-company-media-model")


def test_models_inspect_exposes_source_and_retirement_status() -> None:
    result = CliRunner().invoke(app, ["models", "inspect", "dall-e-3"])
    assert result.exit_code == 0
    assert "retired" in result.stdout
    assert "2026-05-12" in result.stdout


def test_offline_legacy_mock_remains_available(tmp_path: object) -> None:
    # Legacy model references are still helpful for deterministic demos.
    result = CliRunner().invoke(app, ["generate", "image", "A cat", "-m", "dall-e-3"])
    assert result.exit_code == 0
    assert "Image générée" in result.stdout


def test_lifecycle_listing_never_needs_network() -> None:
    with patch("socket.getaddrinfo", side_effect=AssertionError("unexpected DNS")):
        result = CliRunner().invoke(app, ["models", "lifecycle"], env={"COLUMNS": "240"})
    assert result.exit_code == 0
    assert "dall-e-3" in result.stdout
    assert "2027-01-06" in result.stdout
    assert "gemini-3.1-flash-image" in result.stdout


def test_legacy_pricing_not_exposed_as_current_rate() -> None:
    from pyllmkit.adapters.cli.model_specs import compute_run_cost, format_pricing_provenance

    assert compute_run_cost("dall-e-3", None, None, output_media_units=2) == (None, "-")
    assert compute_run_cost("veo-2", None, None, output_media_seconds=6.0) == (None, "-")
    assert "retiré" in format_pricing_provenance("veo-2").lower()
