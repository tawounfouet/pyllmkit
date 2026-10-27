# PyLLMKit - P1-BOOT scaffold

> Status: **P1-BOOT proposed**. The repository bootstrap is not the L1.1/L1.2 domain implementation, and v0.1.0a1 is not qualified or released.

PyLLMKit is intended to model provider-agnostic LLM primitives before adding provider adapters or live inference.

## Local setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python -m ruff check .
python -m mypy src/pyllmkit
python -m build
```

Python 3.11+ is supported by the proposed baseline. No provider SDK or cloud credentials should be required to use or test the domain core.

## Architecture

```text
Applications -> Facade -> Application Services -> Ports (contracts)
                                   |                  ^
                                   v                  |
                              Domain Core <----- Provider Adapters
                                                        |
                                                   External APIs
```

Arrows above express conceptual calls/implementation roles, **not a definitive module import graph**. `domain` cannot import `providers`, `facade`, or infrastructure SDKs; adapters (future) will depend on domain types and ports.

See `docs/architecture/dependencies.md` for explicit allowed/forbidden code dependencies.

## In scope and not in scope

- In scope now: source layout, packaging baseline, ADR proposals, empty domain packages, import smoke tests, architecture guards, CI skeleton.
- Later in L1.1 and L1.2: `Model`, `ModelIdentity`, `ModelId`, `ModelArtifact`, `Capability`, `CapabilitySet`, `Modality`, `ModalitySet` and related domain tests.
- Later releases: interaction, inference, streaming, tool calling, registries, provider adapters.

## Caveats

- Initial GitHub integration is proposed on a dedicated pull request; merge and CI qualification remain pending.
- License is deliberately not chosen. Decide before public publication.
- Package version `0.1.0a1` is a **target metadata placeholder**, not proof of a built or published release.
- ADRs are **PROPOSED**, not approved.