"""Domain errors; no provider SDK dependencies."""


class PyLLMKitError(Exception):
    """Base class for PyLLMKit errors."""


class DomainValidationError(PyLLMKitError, ValueError):
    """A domain invariant was violated by input data."""
