"""P7-AC-009..016: offline connection security and explicit adapter registration."""

import asyncio
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest

from pyllmkit.adapters.inference import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    AdapterRegistryError,
    AsyncFakeInferenceAdapter,
    CredentialRef,
    CredentialResolutionError,
    EnvCredentialResolver,
    FakeInferenceAdapter,
    ProviderConnectionConfig,
    ProviderProfile,
    RegisteredAsyncInferencePort,
    RegisteredInferencePort,
    SecretValue,
    SecurityConfigurationError,
    normalize_http_failure,
)
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import (
    AsyncInferenceService,
    InferenceService,
    InvocationPreconditionError,
)
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import (
    DeploymentId,
    DeploymentTarget,
    InferenceRequest,
    InferenceRunState,
)
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import ProviderId
from pyllmkit.protocols import CredentialResolverPort, InferencePort

NOW = datetime(2026, 11, 6, tzinfo=UTC)


def _fixture(
    *,
    runtime: str = "ollama",
    provider: ProviderId | None = None,
    deployment_id: str = "local-deployment",
) -> tuple[InMemoryCatalog, DeploymentId, InferenceRequest]:
    catalog = InMemoryCatalog()
    modalities = ModalitySet(
        frozenset((Modality("text"),)),
        frozenset((Modality("text"),)),
    )
    model_id = ModelId("model")
    dep_id = DeploymentId(deployment_id)
    catalog.models.register(Model(
        model_id, ModelIdentity(ModelFamily("models")), modalities=modalities,
    ))
    if provider is not None:
        from pyllmkit.domain.providers import InferenceProvider

        catalog.providers.register(InferenceProvider(
            provider, "pilot", modalities=modalities,
        ))
    catalog.deployments.register(Deployment(
        dep_id, model_id, provider, DeploymentStatus.AVAILABLE,
        modalities=modalities, runtime=runtime,
    ))
    request = InferenceRequest(
        DeploymentTarget(dep_id),
        (Message(Role.USER, Content((TextContent("private payload"),))),),
    )
    return catalog, dep_id, request


def _service(
    catalog: InMemoryCatalog,
    deployment_id: DeploymentId,
    registry: AdapterRegistry,
) -> InferenceService:
    return InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredInferencePort(registry),
        {deployment_id: "verified-alias"},
        clock=lambda: NOW,
    )


def _registration(
    fake: FakeInferenceAdapter,
    key: AdapterKey | None = None,
) -> AdapterRegistration:
    return AdapterRegistration(
        key or AdapterKey(runtime="ollama"),
        ProviderConnectionConfig.ollama_local(),
        sync_factory=lambda _config: fake,
    )


def test_p7_ac009_provider_catalog_does_not_auto_register_adapter() -> None:
    catalog, dep_id, request = _fixture()
    registered = AdapterRegistry()
    assert registered.list_keys() == ()
    # A descriptive AVAILABLE deployment is not an executable provider.
    result = _service(catalog, dep_id, registered).invoke(request)
    assert result.run.state is InferenceRunState.FAILED
    assert result.run.failure is not None
    assert result.run.failure.code == "adapter_not_registered"


def test_p7_ac010_duplicate_and_exact_keys_are_rejected_or_deterministic() -> None:
    c, dep_id, req = _fixture()
    registry = AdapterRegistry()
    fake = FakeInferenceAdapter("synthetic")
    declaration = _registration(fake)
    registry.register(declaration)
    with pytest.raises(AdapterRegistryError, match="adapter_already_registered"):
        registry.register(declaration)
    result = _service(c, dep_id, registry).invoke(req)
    assert result.run.state is InferenceRunState.COMPLETED
    assert result.response is not None
    assert result.response.output.text == "synthetic"
    assert len(fake.calls) == 1
    assert registry.list_keys() == (AdapterKey(runtime="ollama"),)
    assert isinstance(RegisteredInferencePort(registry), InferencePort)


def test_p7_ac011_sync_async_adapter_factories_are_lazy() -> None:
    catalog, dep_id, request = _fixture()
    calls: list[ProviderConnectionConfig] = []
    fake = FakeInferenceAdapter("sync")
    async_fake = AsyncFakeInferenceAdapter("async")

    def sync_factory(config: ProviderConnectionConfig) -> FakeInferenceAdapter:
        calls.append(config)
        return fake

    def async_factory(config: ProviderConnectionConfig) -> AsyncFakeInferenceAdapter:
        calls.append(config)
        return async_fake

    registry = AdapterRegistry()
    connection = ProviderConnectionConfig.ollama_local()
    registry.register(AdapterRegistration(
        AdapterKey(runtime="ollama"), connection, sync_factory, async_factory,
    ))
    assert calls == []
    sync = _service(catalog, dep_id, registry).invoke(request)
    assert sync.response is not None
    assert sync.response.output.text == "sync"
    async_service = AsyncInferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredAsyncInferencePort(registry),
        {dep_id: "verified-alias"}, clock=lambda: NOW,
    )
    asynchronous = asyncio.run(async_service.ainvoke(request))
    assert asynchronous.response is not None
    assert asynchronous.response.output.text == "async"
    assert calls == [connection, connection]
    assert fake.calls[0].context.deployment_id == dep_id
    assert async_fake.calls[0].context.deployment_id == dep_id


def test_p7_ac012_explicit_credential_reference_no_secret_in_repr() -> None:
    ref = CredentialRef("openai-primary")
    resolver = EnvCredentialResolver({ref: "OPENAI_API_KEY"}, environ={
        "OPENAI_API_KEY": "secret-demo-DO-NOT-LOG",
    })
    assert isinstance(resolver, CredentialResolverPort)
    value = resolver.resolve(ref)
    assert type(value) is SecretValue
    assert value.reveal() == "secret-demo-DO-NOT-LOG"
    for printed in (repr(ref), repr(value), str(value), repr(resolver)):
        assert "secret-demo-DO-NOT-LOG" not in printed
    assert "<redacted>" in repr(value)
    assert "<redacted>" in str(value)
    assert "OPENAI_API_KEY" not in repr(resolver)
    assert SecretValue("a") is not SecretValue("b")
    with pytest.raises(CredentialResolutionError, match="credential_reference_unknown"):
        resolver.resolve(CredentialRef("other"))
    missing = EnvCredentialResolver({ref: "OPENAI_API_KEY"}, environ={})
    with pytest.raises(CredentialResolutionError, match="credential_unavailable"):
        missing.resolve(ref)


@pytest.mark.parametrize("value", ("", " ", "../wrong", "ABC\nX", "x" * 81, 123))
def test_p7_ac012_invalid_credential_references_fail_closed(value: object) -> None:
    with pytest.raises(SecurityConfigurationError, match="invalid_credential_reference"):
        CredentialRef(value)  # type: ignore[arg-type]


def test_p7_ac013_exact_cloud_destinations_and_no_redirects() -> None:
    key = CredentialRef("cloud")
    openai = ProviderConnectionConfig.openai(key)
    anthropic = ProviderConnectionConfig.anthropic(key)
    assert openai.profile is ProviderProfile.OPENAI
    assert anthropic.profile is ProviderProfile.ANTHROPIC
    assert openai.verify_tls and not openai.follow_redirects
    assert anthropic.verify_tls and not anthropic.follow_redirects
    assert "api.openai.com" not in repr(openai)
    assert "api.anthropic.com" not in repr(anthropic)
    with pytest.raises(FrozenInstanceError):
        openai.verify_tls = False  # type: ignore[misc]


@pytest.mark.parametrize("url", (
    "http://api.openai.com/v1/responses",
    "https://api.openai.com.evil.test/v1/responses",
    "https://api.openai.com@127.0.0.1/v1/responses",
    "https://api.openai.com:444/v1/responses",
    "https://api.openai.com/v1/responses?x=1",
    "https://api.openai.com/v1/embeddings",
    "https://169.254.169.254/v1/responses",
    "https://api.openai.com/v1/responses#fragment",
    "https://api.openai.com/v1/responses/../responses",
))
def test_p7_ac013_untrusted_cloud_urls_refused(url: str) -> None:
    with pytest.raises(SecurityConfigurationError, match="endpoint_not_approved") as exc:
        ProviderConnectionConfig(ProviderProfile.OPENAI, url, CredentialRef("primary"))
    assert url not in str(exc.value)


def test_p7_ac014_ollama_loopback_requires_opt_in_only() -> None:
    local = ProviderConnectionConfig.ollama_local()
    ipv6 = ProviderConnectionConfig.ollama_local(port=11435, ipv6=True)
    assert local.profile is ProviderProfile.OLLAMA
    assert ipv6.profile is ProviderProfile.OLLAMA
    assert local.allow_local and not local.follow_redirects
    assert "127.0.0.1" not in repr(local)
    assert "[::1]" not in repr(ipv6)
    with pytest.raises(SecurityConfigurationError, match="local_opt_in_required"):
        replace(local, allow_local=False)


@pytest.mark.parametrize("url", (
    "http://localhost:11434/api/chat",
    "http://127.0.0.2:11434/api/chat",
    "http://169.254.169.254:11434/api/chat",
    "http://192.168.1.2:11434/api/chat",
    "http://127.0.0.1:11434/api/chat?dest=bad",
    "http://user:pwd@127.0.0.1:11434/api/chat",
    "http://127.0.0.1:11434/api/generate",
    "http://[::ffff:127.0.0.1]:11434/api/chat",
    "http://127.0.0.1:65536/api/chat",
    "http://[::1/api/chat",
    "https://127.0.0.1:11434/api/chat",
    " http://127.0.0.1:11434/api/chat",
    "http://127.0.0.1:11434/api/chat\n",
))
def test_p7_ac014_ollama_adversarial_destinations_rejected(url: str) -> None:
    with pytest.raises(SecurityConfigurationError, match="endpoint_not_approved"):
        ProviderConnectionConfig(ProviderProfile.OLLAMA, url, allow_local=True)


def test_p7_ac015_security_invariants_validate_no_network_needed() -> None:
    base = ProviderConnectionConfig.ollama_local()
    for change, code in (
        ({"verify_tls": False}, "tls_verification_required"),
        ({"follow_redirects": True}, "redirects_forbidden"),
        ({"timeout_seconds": 0.0}, "timeout_invalid"),
        ({"timeout_seconds": float("nan")}, "timeout_invalid"),
        ({"timeout_seconds": 121.0}, "timeout_invalid"),
        ({"timeout_seconds": 1}, "timeout_invalid"),
        ({"credential_ref": CredentialRef("not-allowed")}, "ollama_auth_not_implemented"),
    ):
        with pytest.raises(SecurityConfigurationError, match=code):
            replace(base, **change)
    with pytest.raises(SecurityConfigurationError, match="credential_reference_required"):
        ProviderConnectionConfig(ProviderProfile.OPENAI, "https://api.openai.com/v1/responses")
    with pytest.raises(SecurityConfigurationError, match="local_authorization_invalid"):
        replace(ProviderConnectionConfig.openai(CredentialRef("ok")), allow_local=True)
    for port in (0, 65536, -1, True, "11434"):
        with pytest.raises(SecurityConfigurationError):
            ProviderConnectionConfig.ollama_local(port=port)  # type: ignore[arg-type]


@pytest.mark.parametrize("status,code", (
    (400, "invalid_request"),
    (401, "authentication_failed"),
    (403, "permission_denied"),
    (404, "model_not_found"),
    (408, "provider_timeout"),
    (422, "invalid_request"),
    (429, "rate_limited"),
    (500, "provider_overloaded"),
    (503, "provider_overloaded"),
    (504, "provider_timeout"),
    (302, "provider_protocol_error"),
    (200, "provider_protocol_error"),
))
def test_p7_ac016_http_status_mapping_never_includes_body(
    status: int, code: str,
) -> None:
    error = normalize_http_failure(status)
    assert error.code == code
    assert str(error) == code
    assert "SECRET" not in repr(error)


@pytest.mark.parametrize("status", (0, 1000, 200.0, "429", True, None))
def test_p7_ac016_bad_http_status_rejected(status: object) -> None:
    with pytest.raises(ValueError, match="invalid_http_status"):
        normalize_http_failure(status)  # type: ignore[arg-type]


def test_registry_requires_exact_runtime_and_provider_combination() -> None:
    registry = AdapterRegistry()
    fake = FakeInferenceAdapter()
    registration = AdapterRegistration(
        AdapterKey(ProviderId("openai"), runtime="external"),
        ProviderConnectionConfig.openai(CredentialRef("openai")),
        sync_factory=lambda _config: fake,
    )
    registry.register(registration)
    expected = _fixture(runtime="external", provider=ProviderId("openai"))
    catalog, dep_id, req = expected
    assert _service(catalog, dep_id, registry).invoke(req).response is not None
    # No fallback to 'openai' only, or another runtime.
    other, other_id, other_req = _fixture(
        runtime="alternate", provider=ProviderId("openai")
    )
    rejected = _service(other, other_id, registry).invoke(other_req)
    assert rejected.run.failure is not None
    assert rejected.run.failure.code == "adapter_not_registered"
    assert len(fake.calls) == 1


def test_registration_factory_missing_invalid_and_failure_sanitized() -> None:
    conn = ProviderConnectionConfig.ollama_local()
    key = AdapterKey(runtime="ollama")
    with pytest.raises(AdapterRegistryError, match="adapter_factory_missing"):
        AdapterRegistration(key, conn)
    with pytest.raises(AdapterRegistryError, match="adapter_factory_invalid"):
        AdapterRegistration(key, conn, sync_factory="not_callable")
    with pytest.raises(AdapterRegistryError, match="adapter_profile_mismatch"):
        AdapterRegistration(AdapterKey(runtime="vllm"), conn, sync_factory=lambda _: FakeInferenceAdapter())
    with pytest.raises(AdapterRegistryError, match="adapter_profile_mismatch"):
        AdapterRegistration(
            AdapterKey(runtime="cloud"),
            ProviderConnectionConfig.openai(CredentialRef("cloud")),
            sync_factory=lambda _: FakeInferenceAdapter(),
        )
    registry = AdapterRegistry()
    with pytest.raises(AdapterRegistryError, match="registration_invalid"):
        registry.register("not_a_registration")  # type: ignore[arg-type]
    with pytest.raises(AdapterRegistryError, match="adapter_key_empty"):
        AdapterKey()
    with pytest.raises(AdapterRegistryError, match="adapter_key_invalid"):
        AdapterKey(runtime="http://bad")


def test_factory_side_effects_not_executed_at_registration_and_raw_errors_redacted() -> None:
    fake_errors = "https://private.token.example/api credential=SECRET"
    registry = AdapterRegistry()

    def bad_factory(_config: ProviderConnectionConfig) -> FakeInferenceAdapter:
        raise RuntimeError(fake_errors)

    registry.register(AdapterRegistration(
        AdapterKey(runtime="ollama"),
        ProviderConnectionConfig.ollama_local(),
        sync_factory=bad_factory,
    ))
    catalog, dep_id, req = _fixture()
    result = _service(catalog, dep_id, registry).invoke(req)
    assert result.run.failure is not None
    assert result.run.failure.code == "adapter_initialization_failed"
    assert fake_errors not in repr(result)
    assert fake_errors not in str(result.run.failure)
    deployment = catalog.deployments.get(dep_id)
    assert deployment is not None
    with pytest.raises(AdapterRegistryError, match="adapter_initialization_failed"):
        registry.resolve_sync(deployment)


def test_provider_keys_sort_stably_and_factories_validate_ports() -> None:
    registry = AdapterRegistry()
    for runtime in ("zeta", "alpha"):
        registry.register(AdapterRegistration(
            AdapterKey(ProviderId("openai"), runtime=runtime),
            ProviderConnectionConfig.openai(CredentialRef("k")),
            sync_factory=lambda _: FakeInferenceAdapter(),
        ))
    assert tuple(k.runtime for k in registry.list_keys()) == ("alpha", "zeta")
    invalid_registry = AdapterRegistry()
    invalid_registry.register(AdapterRegistration(
        AdapterKey(runtime="ollama"),
        ProviderConnectionConfig.ollama_local(),
        sync_factory=lambda _: object(),  # type: ignore[arg-type]
    ))
    catalog, dep_id, _ = _fixture()
    deployment = catalog.deployments.get(dep_id)
    assert deployment is not None
    with pytest.raises(AdapterRegistryError, match="adapter_factory_invalid"):
        invalid_registry.resolve_sync(deployment)


def test_async_missing_factory_does_not_fallback_to_sync() -> None:
    registry = AdapterRegistry()
    registry.register(_registration(FakeInferenceAdapter()))
    catalog, dep_id, request = _fixture()
    deployment = catalog.deployments.get(dep_id)
    assert deployment is not None
    with pytest.raises(AdapterRegistryError, match="async_adapter_unavailable"):
        registry.resolve_async(deployment)
    async_service = AsyncInferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredAsyncInferencePort(registry),
        {dep_id: "verified-alias"},
        clock=lambda: NOW,
    )
    failed = asyncio.run(async_service.ainvoke(request))
    assert failed.run.failure is not None
    assert failed.run.failure.code == "async_adapter_unavailable"


def test_registry_is_separate_from_catalog_and_does_not_autoload_env() -> None:
    ref = CredentialRef("cloud-main")
    mapping = EnvCredentialResolver({ref: "OPENAI_API_KEY"}, environ={})
    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(ProviderId("openai")),
        ProviderConnectionConfig.openai(ref),
        sync_factory=lambda _connection: FakeInferenceAdapter(),
    ))
    # Construction has not attempted secret resolution.
    assert len(registry.list_keys()) == 1
    with pytest.raises(CredentialResolutionError, match="credential_unavailable"):
        mapping.resolve(ref)


def test_unknown_routes_do_not_resolve_or_invoke_adapter() -> None:
    catalog, dep_id, request = _fixture(runtime="vllm")
    fake = FakeInferenceAdapter()
    registry = AdapterRegistry()
    registry.register(_registration(fake))
    result = _service(catalog, dep_id, registry).invoke(request)
    assert result.run.failure is not None
    assert result.run.failure.code == "adapter_not_registered"
    assert fake.calls == []


def test_explicit_endpoint_target_still_rejected_before_registry_factory() -> None:
    from pyllmkit.domain.inference import EndpointId, EndpointTarget

    catalog, dep_id, _ = _fixture()
    called: list[ProviderConnectionConfig] = []
    registry = AdapterRegistry()

    def factory(config: ProviderConnectionConfig) -> FakeInferenceAdapter:
        called.append(config)
        return FakeInferenceAdapter()

    registry.register(AdapterRegistration(
        AdapterKey(runtime="ollama"),
        ProviderConnectionConfig.ollama_local(),
        sync_factory=factory,
    ))
    request = InferenceRequest(
        EndpointTarget(EndpointId("http://169.254.169.254")),
        (Message(Role.USER, Content((TextContent("msg"),))),),
    )
    with pytest.raises(InvocationPreconditionError, match="target_not_routable"):
        _service(catalog, dep_id, registry).invoke(request)
    assert called == []

def test_provider_profile_identity_must_be_explicit_and_consistent() -> None:
    with pytest.raises(AdapterRegistryError, match="adapter_profile_mismatch"):
        AdapterRegistration(
            AdapterKey(ProviderId("anthropic")),
            ProviderConnectionConfig.openai(CredentialRef("k")),
            sync_factory=lambda _: FakeInferenceAdapter(),
        )
    with pytest.raises(AdapterRegistryError, match="adapter_profile_mismatch"):
        AdapterRegistration(
            AdapterKey(ProviderId("openai"), runtime="ollama"),
            ProviderConnectionConfig.ollama_local(),
            sync_factory=lambda _: FakeInferenceAdapter(),
        )
    assert AdapterRegistration(
        AdapterKey(ProviderId("anthropic")),
        ProviderConnectionConfig.anthropic(CredentialRef("a")),
        sync_factory=lambda _: FakeInferenceAdapter(),
    ).key.provider_id == ProviderId("anthropic")


def test_adapter_error_codes_are_strictly_allowlisted() -> None:
    for bad in ("raw-secret-from-provider", "error with newline", "Bad_Code", "", "missing"):
        with pytest.raises(ValueError, match="invalid_adapter_error_code"):
            AdapterRegistryError(bad)


def test_registered_ports_refuse_raw_non_prepared_input() -> None:
    sync = RegisteredInferencePort(AdapterRegistry())
    async_port = RegisteredAsyncInferencePort(AdapterRegistry())
    with pytest.raises(TypeError, match="prepared_invocation_required"):
        sync.invoke("raw")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="prepared_invocation_required"):
        asyncio.run(async_port.ainvoke("raw"))  # type: ignore[arg-type]


def test_security_configuration_rejects_bad_sources_and_reference_maps() -> None:
    reference = CredentialRef("primary")
    with pytest.raises(SecurityConfigurationError, match="credential_mapping_invalid"):
        EnvCredentialResolver(None)  # type: ignore[arg-type]
    with pytest.raises(SecurityConfigurationError, match="credential_mapping_invalid"):
        EnvCredentialResolver({"primary": "OPENAI_API_KEY"})  # type: ignore[dict-item]
    with pytest.raises(SecurityConfigurationError, match="credential_mapping_invalid"):
        EnvCredentialResolver({reference: "lowercase"})
    with pytest.raises(SecurityConfigurationError, match="credential_source_invalid"):
        EnvCredentialResolver({reference: "OPENAI_API_KEY"}, environ=17)  # type: ignore[arg-type]
    resolver = EnvCredentialResolver({reference: "OPENAI_API_KEY"}, environ={})
    with pytest.raises(CredentialResolutionError, match="invalid_credential_reference"):
        resolver.resolve("primary")  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ("", None, 5, False))
def test_secret_value_refuses_nonsecret_payload(value: object) -> None:
    with pytest.raises(CredentialResolutionError, match="credential_unavailable"):
        SecretValue(value)  # type: ignore[arg-type]


def test_connection_config_refuses_wrong_types_without_exposing_payloads() -> None:
    from pyllmkit.adapters.inference import SecurityConfigurationError as SecurityError

    with pytest.raises(SecurityError, match="provider_profile_invalid"):
        ProviderConnectionConfig("openai", "https://api.openai.com/v1/responses")  # type: ignore[arg-type]
    for bad in ("", None, True):
        with pytest.raises(SecurityError, match="endpoint_not_approved"):
            ProviderConnectionConfig(ProviderProfile.OPENAI, bad)  # type: ignore[arg-type]
    cloud = ProviderConnectionConfig.openai(CredentialRef("ok"))
    with pytest.raises(SecurityError, match="local_authorization_invalid"):
        replace(cloud, allow_local="yes")
    with pytest.raises(SecurityError, match="credential_reference_invalid"):
        replace(cloud, credential_ref="raw")
    with pytest.raises(SecurityError, match="local_authorization_invalid"):
        replace(cloud, allow_local=True)
    for bad in (False, 0, "false"):
        with pytest.raises(SecurityError, match="tls_verification_required"):
            replace(cloud, verify_tls=bad)
    with pytest.raises(SecurityError, match="redirects_forbidden"):
        replace(cloud, follow_redirects="false")
    with pytest.raises(SecurityError, match="timeout_invalid"):
        replace(cloud, timeout_seconds=True)
    with pytest.raises(SecurityError, match="timeout_invalid"):
        replace(cloud, timeout_seconds=float("inf"))


def test_anthropic_strict_destination_and_credential_requirements() -> None:
    valid = ProviderConnectionConfig.anthropic(CredentialRef("primary"))
    with pytest.raises(SecurityConfigurationError, match="endpoint_not_approved"):
        replace(valid, endpoint_url="https://api.anthropic.com:443/v1/messages")
    with pytest.raises(SecurityConfigurationError, match="credential_reference_required"):
        replace(valid, credential_ref=None)
    with pytest.raises(SecurityConfigurationError, match="local_authorization_invalid"):
        replace(valid, allow_local=True)


def test_local_canonical_url_rejects_padded_port_and_nonbool_ipv6() -> None:
    with pytest.raises(SecurityConfigurationError, match="endpoint_not_approved"):
        ProviderConnectionConfig(
            ProviderProfile.OLLAMA,
            "http://127.0.0.1:011434/api/chat",
            allow_local=True,
        )
    with pytest.raises(SecurityConfigurationError, match="endpoint_not_approved"):
        ProviderConnectionConfig.ollama_local(ipv6="true")  # type: ignore[arg-type]


def test_registry_rejects_wrong_registration_key_and_type() -> None:
    from pyllmkit.adapters.inference.registry import AdapterKey as Key

    with pytest.raises(AdapterRegistryError, match="adapter_key_invalid"):
        Key(provider_id="openai")  # type: ignore[arg-type]
    with pytest.raises(AdapterRegistryError, match="deployment_invalid"):
        Key.from_deployment("raw")  # type: ignore[arg-type]
    key = Key(runtime="ollama")
    conn = ProviderConnectionConfig.ollama_local()
    with pytest.raises(AdapterRegistryError, match="adapter_key_invalid"):
        AdapterRegistration("key", conn, sync_factory=lambda _: FakeInferenceAdapter())  # type: ignore[arg-type]
    with pytest.raises(AdapterRegistryError, match="connection_invalid"):
        AdapterRegistration(key, "url", sync_factory=lambda _: FakeInferenceAdapter())  # type: ignore[arg-type]
    with pytest.raises(AdapterRegistryError, match="adapter_factory_invalid"):
        AdapterRegistration(key, conn, async_factory=17)  # type: ignore[arg-type]


def test_sync_adapter_does_not_fallback_to_async_when_missing() -> None:
    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(runtime="ollama"),
        ProviderConnectionConfig.ollama_local(),
        async_factory=lambda _config: AsyncFakeInferenceAdapter(),
    ))
    catalog, dep_id, request = _fixture()
    deployment = catalog.deployments.get(dep_id)
    assert deployment is not None
    with pytest.raises(AdapterRegistryError, match="sync_adapter_unavailable"):
        registry.resolve_sync(deployment)
    result = _service(catalog, dep_id, registry).invoke(request)
    assert result.run.failure is not None
    assert result.run.failure.code == "sync_adapter_unavailable"


def test_async_factory_failure_is_sanitized_and_invalid_port_is_rejected() -> None:
    catalog, dep_id, _ = _fixture()
    deployment = catalog.deployments.get(dep_id)
    assert deployment is not None

    def fails(_config: ProviderConnectionConfig) -> AsyncFakeInferenceAdapter:
        raise RuntimeError("SECRET-ANOTHER-PROVIDER")

    first = AdapterRegistry()
    first.register(AdapterRegistration(
        AdapterKey(runtime="ollama"),
        ProviderConnectionConfig.ollama_local(),
        async_factory=fails,
    ))
    with pytest.raises(AdapterRegistryError, match="adapter_initialization_failed") as exc:
        first.resolve_async(deployment)
    assert "SECRET" not in str(exc.value)

    second = AdapterRegistry()
    second.register(AdapterRegistration(
        AdapterKey(runtime="ollama"),
        ProviderConnectionConfig.ollama_local(),
        async_factory=lambda _config: object(),  # type: ignore[arg-type]
    ))
    with pytest.raises(AdapterRegistryError, match="adapter_factory_invalid"):
        second.resolve_async(deployment)
