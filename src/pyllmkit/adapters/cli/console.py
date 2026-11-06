"""Rich console singletons for PyLLMKit CLI."""

from rich.console import Console

# Singleton consoles for standard output and standard error
console = Console()
err_console = Console(stderr=True)

