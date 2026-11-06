"""CLI programmatic walkthrough: inspection, execution, and local history.

Demonstrates programmatic execution of PyLLMKit's Typer/Rich CLI interface,
operating in hermetic offline simulation mode without requiring live network access
or external credentials.
"""

import tempfile
from pathlib import Path

from typer.testing import CliRunner

from pyllmkit.adapters.cli.main import app

runner = CliRunner()


def main() -> None:
    print("=== PyLLMKit CLI Programmatic Walkthrough ===\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        import os
        db_path = Path(tmp_dir) / "walkthrough_history.db"
        os.environ["PYLLMKIT_HISTORY_DB"] = str(db_path)

        # 1. Version and Help
        print("[1] Vérification de la version")
        res = runner.invoke(app, ["--version"])
        print(res.output.strip())

        # 2. Providers Inspection
        print("\n[2] Inspection des fournisseurs")
        res = runner.invoke(app, ["providers", "list"])
        print(res.output.strip())

        print("\n[3] Inspection détaillée d'un fournisseur (OpenAI)")
        res = runner.invoke(app, ["providers", "inspect", "openai"])
        print(res.output.strip())

        # 4. Models & Resolution
        print("\n[4] Résolution de déploiement pour 'gpt-4o'")
        res = runner.invoke(app, ["resolve", "--model", "gpt-4o"])
        print(res.output.strip())

        # 5. Blocking Inference (Run)
        print("\n[5] Exécution d'une inférence simulée (mode offline)")
        res = runner.invoke(app, ["run", "Pourquoi le ciel est-il bleu ?", "--model", "gpt-4o"])
        print(res.output.strip())

        # 6. Streaming Inference (Stream)
        print("\n[6] Exécution d'un flux continu (streaming)")
        res = runner.invoke(app, ["stream", "Raconte une histoire courte", "--model", "claude-3-5-sonnet"])
        print(res.output.strip())

        # 7. Runs History Inspection
        print("\n[7] Consultation de l'historique local")
        res = runner.invoke(app, ["runs", "list"])
        print(res.output.strip())

    print("\n=== Walkthrough completed successfully ===")


if __name__ == "__main__":
    main()
