"""CLI-L2 Catalog & Inspection tests (CLI-AC-005..010)."""

from typer.testing import CliRunner

from pyllmkit.adapters.cli.main import app

runner = CliRunner()


def test_cli_providers_list() -> None:
    """CLI-AC-005: providers list shows table with all 6 providers."""
    result = runner.invoke(app, ["providers", "list"])
    assert result.exit_code == 0
    assert "OpenAI" in result.output
    assert "Anthropic" in result.output
    assert "Ollama" in result.output
    assert "Google" in result.output
    assert "Gemini" in result.output
    assert "xAI" in result.output
    assert "Mistral" in result.output


def test_cli_providers_inspect_valid() -> None:
    """CLI-AC-006: providers inspect displays details without showing raw secrets."""
    result = runner.invoke(app, ["providers", "inspect", "openai"])
    assert result.exit_code == 0
    assert "OpenAI" in result.output
    assert "https://api.openai.com/v1/responses" in result.output
    assert "OPENAI_API_KEY" in result.output


def test_cli_providers_inspect_unknown() -> None:
    """providers inspect rejects unknown provider with safe error."""
    result = runner.invoke(app, ["providers", "inspect", "unknown-vendor"])
    assert result.exit_code == 1
    assert "Fournisseur inconnu" in result.output


def test_cli_models_list() -> None:
    """CLI-AC-007: models list displays declared models."""
    result = runner.invoke(app, ["models", "list"])
    assert result.exit_code == 0
    assert "gpt-4o" in result.output
    assert "llama3.2" in result.output
    assert "claude-3-5-sonnet" in result.output


def test_cli_models_list_filter_family() -> None:
    """models list filters by family."""
    result = runner.invoke(app, ["models", "list", "--family", "meta"])
    assert result.exit_code == 0
    assert "llama3.2" in result.output
    assert "gpt-4o" not in result.output


def test_cli_models_list_empty_filter() -> None:
    """models list handles empty filter result gracefully."""
    result = runner.invoke(app, ["models", "list", "--family", "non-existent"])
    assert result.exit_code == 0
    assert "Aucun modèle déclaré" in result.output


def test_cli_deployments_list() -> None:
    """CLI-AC-008: deployments list displays active deployments."""
    result = runner.invoke(app, ["deployments", "list"])
    assert result.exit_code == 0
    assert "dep-gpt-4o" in result.output
    assert "dep-llama3.2" in result.output
    assert "available" in result.output


def test_cli_deployments_list_filter_provider() -> None:
    """deployments list filters by provider identifier."""
    result = runner.invoke(app, ["deployments", "list", "--provider", "openai"])
    assert result.exit_code == 0
    assert "openai" in result.output


def test_cli_deployments_list_empty_filter() -> None:
    """deployments list handles empty filter result gracefully."""
    result = runner.invoke(app, ["deployments", "list", "--provider", "non-existent"])
    assert result.exit_code == 0
    assert "Aucun déploiement actif" in result.output


def test_cli_resolve_success() -> None:
    """CLI-AC-009: resolve selects unique matching deployment."""
    result = runner.invoke(app, ["resolve", "--model", "gpt-4o"])
    assert result.exit_code == 0
    assert "dep-gpt-4o" in result.output
    assert "Déploiement retenu" in result.output


def test_cli_resolve_rejection() -> None:
    """CLI-AC-010: resolve displays candidate rejection reasons on mismatch."""
    result = runner.invoke(app, ["resolve", "--model", "gpt-4o", "--provider", "anthropic"])
    assert result.exit_code == 1
    assert "PROVIDER_MISMATCH" in result.output


def test_cli_resolve_unknown_model() -> None:
    """resolve rejects unknown model."""
    result = runner.invoke(app, ["resolve", "--model", "non-existent-xyz"])
    assert result.exit_code == 1
    assert "Échec de résolution" in result.output


def test_resolve_provider_for_model() -> None:
    """Test resolution of provider identifier for cloud, local Ollama and discovered models."""
    from pyllmkit.adapters.cli.catalog import create_reference_catalog, resolve_provider_for_model

    catalog = create_reference_catalog()
    assert resolve_provider_for_model(catalog, "gpt-4o") == "openai"
    assert resolve_provider_for_model(catalog, "claude-3-5-sonnet") == "anthropic"
    assert resolve_provider_for_model(catalog, "llama3.2") == "ollama"
    assert resolve_provider_for_model(catalog, "mistral:7b-instruct-v0.3-q2_K") == "ollama"
    assert resolve_provider_for_model(catalog, "unknown-fallback-model") == "openai"


def test_cli_models_list_pricing() -> None:
    """models list with --pricing shows context window and pricing columns."""
    result = runner.invoke(app, ["models", "list", "--pricing"])
    assert result.exit_code == 0
    assert "Catalogue des modèles logiques (Spécifications & Tarifs)" in result.output
    assert "Contexte" in result.output
    assert "In / 1M" in result.output
    assert "Out / 1M" in result.output


def test_cli_models_inspect_valid() -> None:
    """models inspect shows full technical specifications and pricing panel."""
    result = runner.invoke(app, ["models", "inspect", "claude-haiku-4-5"])
    assert result.exit_code == 0
    assert "Claude Haiku 4.5" in result.output
    assert "Fenêtre Contexte :" in result.output
    assert "$1.00" in result.output
    assert "$5.00" in result.output


def test_cli_models_inspect_unknown() -> None:
    """models inspect rejects unknown model."""
    result = runner.invoke(app, ["models", "inspect", "unknown-imaginary-model"])
    assert result.exit_code == 1
    assert "Spécifications introuvables" in result.output


def test_model_specs_helpers_and_formatting() -> None:
    """Test get_model_spec lookups, format_tokens, and panels formatting edge cases."""
    from unittest.mock import MagicMock

    from pyllmkit.adapters.cli.formatting.panels import (
        build_model_inspect_panel,
        build_response_panel,
        build_usage_panel,
    )
    from pyllmkit.adapters.cli.formatting.tables import _format_tokens, build_models_table
    from pyllmkit.adapters.cli.model_specs import ModelPricing, ModelSpec, get_model_spec

    # Token formatting
    assert _format_tokens(500) == "500"
    assert _format_tokens(128_000) == "128K"
    assert _format_tokens(1_000_000) == "1M"
    assert _format_tokens(1_500_000) == "1.5M"

    # get_model_spec edge cases
    assert get_model_spec("") is None
    assert get_model_spec("gpt-6-astra") is not None
    assert get_model_spec("gpt-6-astra-preview-custom") is not None
    assert get_model_spec("gpt-6-astracustomsuffix") is not None
    assert get_model_spec("unknown-nonexistent-1234") is None

    # build_models_table empty with show_pricing
    table = build_models_table([], show_pricing=True)
    assert table is not None

    # build_model_inspect_panel minimal
    minimal_spec = ModelSpec(
        id="test-min",
        name="Test Min",
        family="test",
        provider="test",
        context_window=1000,
        max_output_tokens=500,
        modalities_in=(),
        modalities_out=(),
        pricing=ModelPricing(0.0, 0.0, cache_read=None, cache_write=None),
        features=(),
        description="",
    )
    panel = build_model_inspect_panel(minimal_spec)
    assert panel is not None

    # build_response_panel when response is None
    mock_run = MagicMock()
    mock_run.run_id.value = "test-run-empty"
    mock_run.state.value = "completed"
    mock_run.started_at = None
    mock_run.finished_at = None
    empty_exec = MagicMock()
    empty_exec.run = mock_run
    empty_exec.response = None
    resp_panel = build_response_panel(empty_exec, "test")
    assert resp_panel is not None

    # build_usage_panel when tokens are None
    usage_panel = build_usage_panel(empty_exec)
    assert usage_panel is not None


def test_cli_models_sync_mocked_statuses(monkeypatch) -> None:
    """Test sync display with success, skipped, and error rows."""
    from pyllmkit.adapters.cli.commands import models as models_cmd

    def fake_sync(*args, **kwargs):
        return 1, {
            "openai": {"status": "success", "count": 1, "message": "1 synced", "path": "/path/mock.json"},
            "anthropic": {"status": "skipped", "message": "skipped key missing"},
            "google": {"status": "error", "message": "auth error"},
        }

    monkeypatch.setattr(models_cmd, "sync_configured_providers", fake_sync)
    result = runner.invoke(app, ["models", "sync"])
    assert result.exit_code == 0
    assert "Résultat de synchronisation des modèles" in result.output
    assert "skipped key missing" in result.output
    assert "auth error" in result.output
    assert "1 synced" in result.output


def test_all_model_specs_integrity() -> None:
    """Validate all catalog model specifications and their inspection formatting."""
    from pyllmkit.adapters.cli.formatting.panels import build_model_inspect_panel
    from pyllmkit.adapters.cli.model_specs import MODEL_SPECS, get_model_spec

    assert len(MODEL_SPECS) > 30
    for spec_id, spec in MODEL_SPECS.items():
        resolved = get_model_spec(spec_id)
        assert resolved is spec
        panel = build_model_inspect_panel(spec)
        assert panel is not None


def test_build_usage_panel_with_tokens() -> None:
    """Test build_usage_panel with explicit token counts and duration."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    from pyllmkit.adapters.cli.formatting.panels import build_usage_panel

    mock_run = MagicMock()
    mock_run.run_id.value = "test-run-123"
    mock_run.state.value = "completed"
    mock_run.started_at = datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc)
    mock_run.finished_at = datetime(2026, 11, 6, 12, 0, 1, 500000, tzinfo=timezone.utc)

    mock_resp = MagicMock()
    mock_resp.finish_reason.code.value = "stop"
    mock_resp.usage.input_tokens = 42
    mock_resp.usage.output_tokens = 84

    mock_exec = MagicMock()
    mock_exec.run = mock_run
    mock_exec.response = mock_resp

    panel = build_usage_panel(mock_exec)
    assert panel is not None
    assert "42 / 84" in panel.renderable


def test_resolve_provider_candidates_and_discovered(monkeypatch) -> None:
    """Test resolve_provider_for_model candidate search and discovered cache fallback."""
    from pyllmkit.adapters.cli import catalog as cat_mod
    from pyllmkit.adapters.cli.catalog import create_reference_catalog, resolve_provider_for_model
    from pyllmkit.domain.capabilities import CapabilitySet
    from pyllmkit.domain.deployments import Deployment, DeploymentStatus
    from pyllmkit.domain.inference import DeploymentId
    from pyllmkit.domain.modalities import Modality, ModalitySet
    from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity

    catalog = create_reference_catalog()

    # Candidate search with different dep-id pattern
    custom_mid = ModelId("custom-model-abc")
    catalog.models.register(
        Model(
            custom_mid,
            ModelIdentity(ModelFamily("custom")),
            capabilities=CapabilitySet(()),
            modalities=ModalitySet(frozenset({Modality("text")}), frozenset({Modality("text")})),
        )
    )
    custom_dep = Deployment(
        DeploymentId("custom-dep-xyz"),
        custom_mid,
        provider_id=None,
        status=DeploymentStatus.AVAILABLE,
        runtime="ollama",
    )
    catalog.deployments.register(custom_dep)
    assert resolve_provider_for_model(catalog, "custom-model-abc") == "ollama"

    # Discovered models fallback
    monkeypatch.setattr(
        cat_mod,
        "load_discovered_models",
        lambda: [{"id": "discovered-fallback-x", "provider": "xai"}],
    )
    assert resolve_provider_for_model(catalog, "discovered-fallback-x") == "xai"


def test_build_models_table_with_unregistered_spec_pricing() -> None:
    """Test build_models_table with show_pricing=True on a model with no known spec."""
    from pyllmkit.adapters.cli.formatting.tables import build_models_table
    from pyllmkit.domain.capabilities import CapabilitySet
    from pyllmkit.domain.modalities import Modality, ModalitySet
    from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity

    unknown_model = Model(
        ModelId("completely-unknown-ai-model"),
        ModelIdentity(ModelFamily("unknown")),
        capabilities=CapabilitySet(()),
        modalities=ModalitySet(frozenset({Modality("text")}), frozenset({Modality("text")})),
    )
    table = build_models_table([unknown_model], show_pricing=True)
    assert table is not None


def test_cli_models_sync_no_saved_path(monkeypatch) -> None:
    """Test models sync message when no models discovered or saved."""
    from pyllmkit.adapters.cli.commands import models as models_cmd

    monkeypatch.setattr(
        models_cmd,
        "sync_configured_providers",
        lambda *args, **kwargs: (0, {"openai": {"status": "skipped", "message": "nothing"}}),
    )
    result = runner.invoke(app, ["models", "sync"])
    assert result.exit_code == 0
    assert "Aucun modèle supplémentaire n'a été découvert" in result.output


def test_create_reference_catalog_discovered_branches(monkeypatch) -> None:
    """Test create_reference_catalog skips empty ids and registers unknown providers."""
    from pyllmkit.adapters.cli import catalog as cat_mod
    from pyllmkit.domain.providers import ProviderId

    monkeypatch.setattr(
        cat_mod,
        "load_discovered_models",
        lambda: [
            {"id": ""},  # Should be skipped (line 120)
            {"id": "new-model-xyz", "provider": "brand-new-provider-123"},  # Should register provider (line 143)
        ],
    )
    catalog = cat_mod.create_reference_catalog()
    assert catalog.providers.get(ProviderId("brand-new-provider-123")) is not None


def test_load_catalog_specs_and_local_overrides(tmp_path, monkeypatch) -> None:
    """Test loading specs from custom path, handling corrupt json, and local overrides."""
    import json
    from pyllmkit.adapters.cli.model_specs import load_catalog_specs

    # 1. Corrupt json
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json", encoding="utf-8")
    assert load_catalog_specs(custom_path=bad_file, include_local_override=False) == {}

    # 2. Custom valid json
    good_file = tmp_path / "good.json"
    good_file.write_text(
        json.dumps({
            "custom-ai": {
                "id": "custom-ai",
                "name": "Custom AI",
                "pricing": {"input_cost": 1.0, "output_cost": 2.0},
            }
        }),
        encoding="utf-8",
    )
    loaded = load_catalog_specs(custom_path=good_file, include_local_override=False)
    assert "custom-ai" in loaded
    assert loaded["custom-ai"].name == "Custom AI"

    # 3. Local override candidate
    local_dir = tmp_path / ".pyllmkit"
    local_dir.mkdir()
    override_file = local_dir / "models_catalog.json"
    override_file.write_text(
        json.dumps({
            "override-model": {
                "id": "override-model",
                "name": "Overridden Name",
                "pricing": {"input_cost": 0.5, "output_cost": 1.5},
            }
        }),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    merged = load_catalog_specs(custom_path=good_file, include_local_override=True)
    assert "custom-ai" in merged
    assert "override-model" in merged
    assert merged["override-model"].name == "Overridden Name"

    # 4. Local override with corrupt content
    override_file.write_text("{corrupt json", encoding="utf-8")
    fallback = load_catalog_specs(custom_path=good_file, include_local_override=True)
    assert "custom-ai" in fallback


def test_compute_run_cost_comprehensive() -> None:
    """Test compute_run_cost across all pricing tiers, cache discounts, and edge cases."""
    from pyllmkit.adapters.cli.model_specs import compute_run_cost

    # Invalid / unknown cases
    assert compute_run_cost(None, 10, 10) == (None, "-")
    assert compute_run_cost("unknown-nonexistent-model", 10, 10) == (None, "-")
    assert compute_run_cost("gpt-4o", None, None) == (None, "-")

    # Local / Free
    cost_val, cost_lbl = compute_run_cost("llama3.2", 100, 100)
    assert cost_val == 0.0
    assert "local/gratuit" in cost_lbl

    cost_val, cost_lbl = compute_run_cost("crouton-alpha-free", 100, 100)
    assert cost_val == 0.0
    assert "local/gratuit" in cost_lbl

    # Total == 0
    assert compute_run_cost("gpt-4o", 0, 0) == (0.0, "$0.000000")

    # Micro cost (< 0.0001)
    val, lbl = compute_run_cost("gpt-4o-mini", 10, 5)
    assert val is not None and val < 0.0001
    assert " in + " in lbl

    # Low cost (< 0.01)
    val, lbl = compute_run_cost("gpt-4o-mini", 5000, 2000)
    assert val is not None and 0.0001 <= val < 0.01
    assert " in + " in lbl

    # Standard cost (>= 0.01)
    val, lbl = compute_run_cost("gpt-4o", 10000, 5000)
    assert val is not None and val >= 0.01
    assert " in + " in lbl

    # Cached tokens discount
    val_cached, lbl_cached = compute_run_cost("gpt-4o", 10000, 5000, cached_tokens=5000)
    assert val_cached is not None and val_cached < val
    assert " in + " in lbl_cached


def test_build_usage_panel_with_cache_and_reasoning() -> None:
    """Test build_usage_panel with cached tokens and reasoning tokens."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    from pyllmkit.adapters.cli.formatting.panels import build_usage_panel

    mock_run = MagicMock()
    mock_run.run_id.value = "run-cache-1"
    mock_run.state.value = "completed"
    mock_run.started_at = datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc)
    mock_run.finished_at = datetime(2026, 11, 6, 12, 0, 2, tzinfo=timezone.utc)

    mock_resp = MagicMock()
    mock_resp.finish_reason.code.value = "stop"
    mock_resp.usage.input_tokens = 1000
    mock_resp.usage.output_tokens = 500
    mock_resp.usage.cached_input_tokens = 400
    mock_resp.usage.reasoning_tokens = 150

    mock_exec = MagicMock()
    mock_exec.run = mock_run
    mock_exec.response = mock_resp

    panel = build_usage_panel(mock_exec, model_name="gpt-4o", provider_name="openai")
    rendered = str(panel.renderable)
    assert "1000 / 500" in rendered
    assert "total: 1500" in rendered
    assert "dont 400 en cache" in rendered
    assert "dont 150 reasoning" in rendered
    assert "tok/s" in rendered
    assert "Coût estimé" in rendered


def test_build_model_inspect_panel_flagship_and_realtime() -> None:
    """Test inspect panel rendering for 12h prompt cache and multimodal realtime models."""
    from pyllmkit.adapters.cli.formatting.panels import build_model_inspect_panel
    from pyllmkit.adapters.cli.model_specs import get_model_spec

    # 12h cache write (gpt-6-astra)
    spec_astra = get_model_spec("gpt-6-astra")
    assert spec_astra is not None
    p_astra = build_model_inspect_panel(spec_astra)
    rendered_astra = str(p_astra.renderable)
    assert "Cache Write (30m)" in rendered_astra
    assert "Cache Write (12h)" in rendered_astra
    assert "$25.00" in rendered_astra

    # Realtime multimodal breakdown (gpt-realtime-2.1)
    spec_rt = get_model_spec("gpt-realtime-2.1")
    assert spec_rt is not None
    p_rt = build_model_inspect_panel(spec_rt)
    rendered_rt = str(p_rt.renderable)
    assert "Tarification multimodale détaillée" in rendered_rt
    assert "Audio" in rendered_rt
    assert "$32.00" in rendered_rt
    assert "Text" in rendered_rt
    assert "Image" in rendered_rt


def test_build_response_and_stream_panels() -> None:
    """Test build_response_panel and build_stream_usage_panel."""
    from unittest.mock import MagicMock

    from pyllmkit.adapters.cli.formatting.panels import (
        build_response_panel,
        build_stream_usage_panel,
    )

    # 1. build_response_panel with None response
    mock_exec_none = MagicMock()
    mock_exec_none.response = None
    p_none = build_response_panel(mock_exec_none, "gpt-4o")
    assert "Aucune réponse générée" in str(p_none.renderable)

    # 2. build_response_panel with text response
    mock_exec_text = MagicMock()
    mock_exec_text.response.output.text = "Bonjour le monde"
    p_text = build_response_panel(mock_exec_text, "gpt-4o")
    assert "Bonjour le monde" in str(p_text.renderable)

    # 3. build_stream_usage_panel success with TTFT & cost
    p_stream = build_stream_usage_panel(
        run_id="stream-123",
        duration_ms=1500.0,
        finish_reason="stop",
        in_tokens=50,
        out_tokens=100,
        cached_tokens=10,
        reasoning_tokens=20,
        ttft_ms=250.0,
        model_name="gpt-4o",
        provider_name="openai",
        exit_code=0,
    )
    rendered_stream = str(p_stream.renderable)
    assert "stream-123" in rendered_stream
    assert "completed" in rendered_stream
    assert "TTFT: 250.0 ms" in rendered_stream
    assert "tok/s" in rendered_stream
    assert "Coût estimé" in rendered_stream

    # 4. build_stream_usage_panel failure
    p_stream_fail = build_stream_usage_panel(
        run_id="stream-fail",
        duration_ms=500.0,
        finish_reason="length",
        in_tokens=None,
        out_tokens=None,
        exit_code=1,
    )
    assert "failed (exit 1)" in str(p_stream_fail.renderable)


def test_resolve_provider_fallbacks() -> None:
    """Test resolve_provider_for_model fallbacks."""
    from pyllmkit.adapters.cli.catalog import create_reference_catalog, resolve_provider_for_model

    cat = create_reference_catalog()
    assert resolve_provider_for_model(cat, "completely-unknown-model-xyz") == "openai"
    assert resolve_provider_for_model(cat, "ollama/custom-model") == "ollama"


def test_model_spec_candidate_progressive_resolution() -> None:
    """Test progressive matching of snapshot dates, reasoning suffixes, and iterations."""
    from pyllmkit.adapters.cli.model_specs import compute_run_cost, get_model_spec

    # 1. Grok reasoning / non-reasoning snapshot
    spec_grok_nr = get_model_spec("grok-4.20-0309-non-reasoning")
    assert spec_grok_nr is not None
    assert spec_grok_nr.id == "grok-4.20-0309-non-reasoning"

    spec_grok_r = get_model_spec("grok-4.20-0309-reasoning")
    assert spec_grok_r is not None
    assert spec_grok_r.id == "grok-4.20-0309-reasoning"

    # 2. Date snapshots
    spec_gpt = get_model_spec("gpt-4o-2024-08-06")
    assert spec_gpt is not None
    assert spec_gpt.id == "gpt-4o"

    spec_claude = get_model_spec("claude-3-5-sonnet-20241022")
    assert spec_claude is not None
    assert spec_claude.id == "claude-3-5-sonnet"

    # 3. Iteration / preview
    spec_gemini_ver = get_model_spec("gemini-1.5-flash-002")
    assert spec_gemini_ver is not None
    assert spec_gemini_ver.id == "gemini-1.5-flash"

    spec_gemini_prev = get_model_spec("gemini-2.5-flash-preview")
    assert spec_gemini_prev is not None
    assert spec_gemini_prev.id == "gemini-2.5-flash"

    # 4. Unknown model fallback in usage panels
    from unittest.mock import MagicMock
    from pyllmkit.adapters.cli.formatting.panels import (
        build_stream_usage_panel,
        build_usage_panel,
    )

    mock_run = MagicMock()
    mock_run.run_id.value = "run-unk"
    mock_run.state.value = "completed"
    mock_run.started_at = None
    mock_run.finished_at = None

    mock_resp = MagicMock()
    mock_resp.finish_reason.code.value = "stop"
    mock_resp.usage.input_tokens = 50
    mock_resp.usage.output_tokens = 50
    mock_resp.usage.cached_input_tokens = 0
    mock_resp.usage.reasoning_tokens = 0

    mock_exec = MagicMock()
    mock_exec.run = mock_run
    mock_exec.response = mock_resp

    panel_run = build_usage_panel(mock_exec, model_name="unknown-custom-model")
    assert "N/A (modèle hors catalogue tarifaire)" in str(panel_run.renderable)

    panel_stream = build_stream_usage_panel(
        run_id="stream-unk",
        duration_ms=100.0,
        finish_reason="stop",
        in_tokens=50,
        out_tokens=50,
        model_name="unknown-custom-model",
    )
    assert "N/A (modèle hors catalogue tarifaire)" in str(panel_stream.renderable)



