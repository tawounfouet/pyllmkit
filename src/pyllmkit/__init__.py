"""PyLLMKit: provider-agnostic LLM domain primitives (bootstrap)."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pyllmkit")
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = ["__version__"]
