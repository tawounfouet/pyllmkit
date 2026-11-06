"""SQLite storage adapter for CLI execution history."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


def _to_int(val: object) -> int | None:
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        try:
            return int(val)
        except ValueError:
            return None
    return None


def _to_float(val: object) -> float | None:
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return None
    return None


@dataclass(frozen=True, slots=True)
class RunRecord:
    """Historical execution record."""

    run_id: str
    model_id: str
    provider: str
    prompt: str
    response_text: str | None
    state: str
    finish_reason: str | None
    input_tokens: int | None
    output_tokens: int | None
    duration_ms: float | None
    created_at: str
    total_tokens: int | None = None
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None
    ttft_ms: float | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    system_prompt: str | None = None
    mode: str = "run"
    messages_json: str | None = None

    def to_chatml_messages(self) -> list[dict[str, str]]:
        """Return the conversation as standard ChatML messages list."""
        if self.messages_json:
            try:
                import json

                parsed = json.loads(self.messages_json)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        msgs: list[dict[str, str]] = []
        if self.system_prompt:
            msgs.append({"role": "system", "content": self.system_prompt})
        msgs.append({"role": "user", "content": self.prompt})
        if self.response_text:
            msgs.append({"role": "assistant", "content": self.response_text})
        return msgs

    def as_dict(self) -> dict[str, object]:
        """Serialize run record to dictionary."""
        return {
            "run_id": self.run_id,
            "model_id": self.model_id,
            "provider": self.provider,
            "mode": self.mode,
            "state": self.state,
            "finish_reason": self.finish_reason,
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "response_text": self.response_text,
            "duration_ms": self.duration_ms,
            "ttft_ms": self.ttft_ms,
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
                "total": self.total_tokens,
                "cached": self.cached_tokens,
                "reasoning": self.reasoning_tokens,
            },
            "parameters": {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
            "created_at": self.created_at,
            "messages": self.to_chatml_messages(),
        }


class SqliteRunStore:
    """Zero-dependency execution history store using Python's built-in sqlite3."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            env_path = os.environ.get("PYLLMKIT_HISTORY_DB")
            if env_path:
                db_path = Path(env_path)
            else:
                try:
                    from ..config import get_config

                    cfg = get_config()
                    if cfg.storage.history_db:
                        db_path = cfg.storage.history_db
                except Exception:
                    pass

            if db_path is None:
                config_dir = Path.home() / ".config" / "pyllmkit"
                config_dir.mkdir(parents=True, exist_ok=True)
                db_path = config_dir / "history.db"
        self._db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        try:
            with closing(self._get_connection()) as conn:
                with conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS runs (
                            run_id TEXT PRIMARY KEY,
                            model_id TEXT NOT NULL,
                            provider TEXT NOT NULL,
                            prompt TEXT NOT NULL,
                            response_text TEXT,
                            state TEXT NOT NULL,
                            finish_reason TEXT,
                            input_tokens INTEGER,
                            output_tokens INTEGER,
                            duration_ms REAL,
                            created_at TEXT NOT NULL,
                            total_tokens INTEGER,
                            cached_tokens INTEGER,
                            reasoning_tokens INTEGER,
                            ttft_ms REAL,
                            temperature REAL,
                            max_tokens INTEGER,
                            system_prompt TEXT,
                            mode TEXT NOT NULL DEFAULT 'run',
                            messages_json TEXT
                        )
                        """
                    )
                    # Migration de schéma pour tables existantes
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA table_info(runs)")
                    existing_cols = {col[1] for col in cursor.fetchall()}
                    additions = [
                        ("total_tokens", "INTEGER"),
                        ("cached_tokens", "INTEGER"),
                        ("reasoning_tokens", "INTEGER"),
                        ("ttft_ms", "REAL"),
                        ("temperature", "REAL"),
                        ("max_tokens", "INTEGER"),
                        ("system_prompt", "TEXT"),
                        ("mode", "TEXT NOT NULL DEFAULT 'run'"),
                        ("messages_json", "TEXT"),
                    ]
                    for col_name, col_type in additions:
                        if col_name not in existing_cols:
                            conn.execute(f"ALTER TABLE runs ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            # En lecture seule ou environnement restreint, continuer sans migrer
            pass

    def record_run(self, record: RunRecord) -> None:
        """Persist or update an execution record."""
        with closing(self._get_connection()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO runs (
                        run_id, model_id, provider, prompt, response_text,
                        state, finish_reason, input_tokens, output_tokens,
                        duration_ms, created_at, total_tokens, cached_tokens,
                        reasoning_tokens, ttft_ms, temperature, max_tokens,
                        system_prompt, mode, messages_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.run_id,
                        record.model_id,
                        record.provider,
                        record.prompt,
                        record.response_text,
                        record.state,
                        record.finish_reason,
                        record.input_tokens,
                        record.output_tokens,
                        record.duration_ms,
                        record.created_at,
                        record.total_tokens,
                        record.cached_tokens,
                        record.reasoning_tokens,
                        record.ttft_ms,
                        record.temperature,
                        record.max_tokens,
                        record.system_prompt,
                        record.mode,
                        record.messages_json,
                    ),
                )

    @staticmethod
    def _row_to_record(col_names: list[str], row: tuple[object, ...]) -> RunRecord:
        d = dict(zip(col_names, row, strict=False))
        resp = d.get("response_text")
        finish = d.get("finish_reason")
        in_tok = d.get("input_tokens")
        out_tok = d.get("output_tokens")
        dur = d.get("duration_ms")
        tot = d.get("total_tokens")
        cached = d.get("cached_tokens")
        reas = d.get("reasoning_tokens")
        ttft = d.get("ttft_ms")
        temp = d.get("temperature")
        max_t = d.get("max_tokens")
        sys_p = d.get("system_prompt")
        msgs = d.get("messages_json")
        return RunRecord(
            run_id=str(d.get("run_id", "")),
            model_id=str(d.get("model_id", "")),
            provider=str(d.get("provider", "")),
            prompt=str(d.get("prompt", "")),
            response_text=str(resp) if resp is not None else None,
            state=str(d.get("state", "unknown")),
            finish_reason=str(finish) if finish is not None else None,
            input_tokens=_to_int(in_tok),
            output_tokens=_to_int(out_tok),
            duration_ms=_to_float(dur),
            created_at=str(d.get("created_at", "")),
            total_tokens=_to_int(tot),
            cached_tokens=_to_int(cached),
            reasoning_tokens=_to_int(reas),
            ttft_ms=_to_float(ttft),
            temperature=_to_float(temp),
            max_tokens=_to_int(max_t),
            system_prompt=str(sys_p) if sys_p is not None else None,
            mode=str(d.get("mode") or "run"),
            messages_json=str(msgs) if msgs is not None else None,
        )

    def list_runs(self, limit: int = 20) -> list[RunRecord]:
        """Retrieve recent execution records in reverse chronological order."""
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,))
            if cursor.description is None:
                return []
            col_names = [col[0] for col in cursor.description]
            return [self._row_to_record(col_names, row) for row in cursor.fetchall()]

    def get_run(self, run_id: str) -> RunRecord | None:
        """Retrieve a specific run by its identifier."""
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            if cursor.description is None:
                return None
            row = cursor.fetchone()
            if row is None:
                return None
            col_names = [col[0] for col in cursor.description]
            return self._row_to_record(col_names, row)
