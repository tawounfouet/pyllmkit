# PyLLMKit

**Framework Python agnostique pour intégrer des modèles de langage.** Un domaine typé, des adaptateurs fournisseurs et une CLI pour l'inférence, le catalogue et le suivi d'usage.

**Version :** `v0.3.0` | **Python :** 3.11+ | **Licence :** MIT | **Distribution :** tag Git (pas encore publié sur PyPI)

## Installation

```bash
git clone --branch v0.3.0 https://github.com/tawounfouet/pyllmkit.git
cd pyllmkit
python -m pip install -e ".[cli]"
```

Pour utiliser les adaptateurs HTTP : `python -m pip install -e ".[cli,providers]"`.

## Démarrage rapide

```bash
pyllmkit --version
pyllmkit models list
pyllmkit run "Bonjour" --model gpt-4o --mock
```

Le mode mock fonctionne hors ligne. Les requêtes réseau nécessitent `--live` explicitement.

## Exemple Python

```python
from pyllmkit.domain import Content, Message, Role, TextContent

message = Message(Role.USER, Content((TextContent("Bonjour"),)))
assert message.content.parts[0].text == "Bonjour"
```

## Fonctionnalités

- **Domaine :** Model, Capabilities, Message, Inference, Usage, Tooling, Structured Output et Streaming.
- **Providers :** adaptateurs textuels pour OpenAI, Anthropic, Google Gemini, xAI, Mistral et Ollama.
- **Catalogue :** modèles, déploiements, découverte et résolution déterministe.
- **CLI et suivi :** exécution mock/live, historique SQLite, coûts estimés et export avec consentement explicite.

## Architecture

```text
Applications / agents / RAG
          |
     API Python / CLI
          |
  Application Services
     |          |
 Domain Core   Ports / Adapters
               |-- Providers
               |-- Catalog & Discovery
               |-- Storage & History
```

## Limites

La version 0.3.0 est qualifiée par **tests hors ligne**. **NO-GO pour toute garantie de sécurité provider-live / production** (DNS, TLS, SSRF, budgets et canaris non qualifiés). Les prix du catalogue sont indicatifs. Le tag Git n'est ni une publication PyPI ni une certification d'exploitation.

## Documentation

- [API Inference](docs/api/inference.md), [JSON v1](docs/api/inference-json-v1.md), [Tooling](docs/api/tooling.md), [Streaming](docs/api/streaming.md), [Registry](docs/api/registry-discovery.md)
- [Exemple d'inférence hors ligne](examples/12_full_inference_walkthrough.py), [exemple Tooling](examples/17_full_tooling_walkthrough.py)
- [Changelog](CHANGELOG.md), [qualité M4](docs/quality/M4_GATE_REVIEW.md), [périmètre v0.3.0](docs/milestones/0.3.0/18_V030_TAG_SCOPE_AND_AUTHORIZATION_2026-11-07.md)

## Développement

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```
