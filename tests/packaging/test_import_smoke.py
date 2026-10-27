"""Bootstrap import checks, not L1.1 domain behavior tests."""

import importlib
from importlib.metadata import version

import pyllmkit


def test_domain_packages_import_without_provider_sdk() -> None:
    for name in (
        "pyllmkit.domain", "pyllmkit.domain.models",
        "pyllmkit.domain.capabilities", "pyllmkit.domain.modalities",
        "pyllmkit.domain.errors",
    ):
        assert importlib.import_module(name) is not None


def test_version_comes_from_package_metadata() -> None:
    assert pyllmkit.__version__ == version("pyllmkit")
