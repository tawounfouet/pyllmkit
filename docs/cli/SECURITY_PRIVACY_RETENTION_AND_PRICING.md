# PyLLMKit CLI: safety, consent, retention and local pricing

> Scope: CLI engineering behavior on the `fix/cli-safety-privacy-discovery-pricing` branch.
> This guide does not certify real-provider networking, production readiness, or live pricing.

## Network safety

- `pyllmkit run PROMPT` and `pyllmkit stream PROMPT` are always offline unless
  `--live` is explicitly provided on that same invocation.
- An explicit `--mock` always uses fake adapters, even when a legacy config file
  sets `defaults.live: true`. That legacy setting is retained for file parsing
  compatibility but **never grants network authorization** to `run` or `stream`.
- Running `--live` may incur provider fees and should be done only with approval,
  credentials, budget boundaries and network safeguards.
- `models sync` is a **separate explicit network operation**. It is not covered
  by the inference `--mock` guard.
- Discovery uses fixed HTTPS URLs for cloud providers and the literal loopback
  `127.0.0.1` for Ollama; it rejects HTTP redirects, disables proxy auto-discovery
  and bounds response JSON size to 1 MiB.
- Gemini discovery sends its key in the `x-goog-api-key` request header, **not**
  the URL query. API errors are reported with a generic code, without raw provider
  exception text or request URLs. Do not log headers or enable debug dumping of
  HTTP requests in other wrappers.

**Limit:** these measures do not attest live DNS resolution, connected peer IP,
TLS pinning, canary spend limits or provider-side execution lifetime. S6 network
and release governance remain separate open requirements.

## History privacy and consent

- By default, after a CLI `run` or `stream`, SQLite stores **metadata only**:
  run ID, model/provider, status, finish reason, token usage, timing and chosen
  numeric generation parameters.
- Default history **does not store** prompt text, system prompt, response text
  or ChatML/JSONL message bodies. Text is still displayed in the terminal
  during the active invocation.
- To consent to persist raw text for one invocation, add
  `--record-content`. This flag is **not inherited from config**, is never
  inferred from the presence of an API key and is required separately on each
  invocation. Example: `pyllmkit run "Public test" --record-content`.
- A newly created SQLite file is created with POSIX mode `0600`; existing
  database permissions are **not** overwritten automatically.
- The consent change is **not retroactive**: previously recorded prompts and
  responses remain in legacy SQLite databases. Locate them with
  `pyllmkit config show` and delete or migrate them intentionally if needed.
- `runs inspect --json` and `runs export` can reproduce opted-in sensitive
  content. Export to a file is written with POSIX `0600`. Avoid copying JSONL
  exports into public repositories, issue bodies, CI logs or shared storage.

## Retention and deletion

History has **no surprise automatic deletion by default**. For installations
requiring time-bound retention, set `PYLLMKIT_HISTORY_RETENTION_DAYS=30` (or
another integer 1..36500). Opening the local store then prunes runs whose
ISO8601 timezone-aware `created_at` is older than that duration. Rows with
invalid/naive timestamps are conservatively retained and require manual review.

Manual deletion is also available:

```bash
pyllmkit runs prune --older-than-days 30 --yes
```

Without `--yes`, the command refuses the irreversible operation. The prune
removes metadata and opted-in raw content together, by run ID. SQLite
deletions do not guarantee secure erasure of old bytes in SQLite free pages,
journal files, snapshots, backups or previous exports. Use storage-level
secure deletion/encryption and a backup-retention policy for sensitive use.

## FinishReason is an observation

`InferenceRun.state=completed` and `FinishReasonCode.UNKNOWN` are
**not** contradictory. The CLI stores and displays `unknown` unmodified;
it no longer silently rewrites `UNKNOWN` into `STOP`. The absence of a
provider-reported finish reason also remains `unknown` in usage panels.

## Pricing and FinOps provenance

The CLI reads a **bundled, local JSON catalog** of model specifications and
pricing. Every displayed estimate is explicitly labelled as derived from
that local catalog, together with the catalog's `last_verified` date when
provided. When the date is missing, it says so; no current provider price
is invented. A local estimate is **not** a provider invoice or a real-time
tariff quote. If the catalog does not recognize a model, the UI reports
N/A rather than fabricating a price.

Some catalog entries provide `source_url` and `last_verified` fields.
These are provenance metadata from the catalog author, **not** a live
reverification at execution time. Local overrides can replace entries.
Recheck official provider pricing and region/currency/contract terms
before using cost estimates for budgeting or reconciliation.

## Operational controls

1. Rotate any real API key accidentally included in debug logs, transcript
   archives or shared configuration files.
2. Prefer environment variables and protected secret stores over committed
   plaintext `api_keys`.
3. Check new and legacy history database ownership and permissions.
4. Do not enable live inference based only on green MockTransport tests.
5. Preserve these controls under regression tests before shipping a CLI release.

Versioning note: these fixes do not change `pyproject.toml`, publish a
package, create a release tag or authorize paid provider calls.


## Supplemental v0.3.0 CLI protections (PR #102)

- `runs export` requires an additional invocation-scoped `--allow-content-export`
  before displaying or writing opted-in ChatML/JSONL content. This is distinct
  from `run --record-content` and `stream --record-content` consent.
- `runs purge-content --yes [--run-id ID]` logically removes previously stored
  prompts, system instructions, responses and message bodies from SQLite while
  preserving non-content run metadata. This is not secure deletion of SQLite
  free pages, WAL files, backups, prior exports or terminal logs.
- Missing model context limits and pricing rates are shown as unknown/N/A,
  never replaced with implied limits or zero USD. Exact zero is retained only
  when present explicitly in a catalog entry. Missing usage inputs prevent
  a total cost estimate.
