"""SQLite storage adapter for CLI execution history."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


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


class SqliteRunStore:
    """Zero-dependency execution history store using Python's built-in sqlite3."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            env_path = os.environ.get("PYLLMKIT_HISTORY_DB")
            if env_path:
                db_path = Path(env_path)
            else:
                config_dir = Path.home() / ".config" / "pyllmkit"
                config_dir.mkdir(parents=True, exist_ok=True)
                db_path = config_dir / "history.db"
        self._db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
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
                        created_at TEXT NOT NULL
                    )
                    """
                )

    def record_run(self, record: RunRecord) -> None:
        """Persist or update an execution record."""
        with closing(self._get_connection()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO runs (
                        run_id, model_id, provider, prompt, response_text,
                        state, finish_reason, input_tokens, output_tokens,
                        duration_ms, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    ),
                )

    def list_runs(self, limit: int = 20) -> list[RunRecord]:
        """Retrieve recent execution records in reverse chronological order."""
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT run_id, model_id, provider, prompt, response_text,
                       state, finish_reason, input_tokens, output_tokens,
                       duration_ms, created_at
                FROM runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                RunRecord(
                    run_id=row[0],
                    model_id=row[1],
                    provider=row[2],
                    prompt=row[3],
                    response_text=row[4],
                    state=row[5],
                    finish_reason=row[6],
                    input_tokens=row[7],
                    output_tokens=row[8],
                    duration_ms=row[9],
                    created_at=row[10],
                )
                for row in rows
            ]

    def get_run(self, run_id: str) -> RunRecord | None:
        """Retrieve a specific run by its identifier."""
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT run_id, model_id, provider, prompt, response_text,
                       state, finish_reason, input_tokens, output_tokens,
                       duration_ms, created_at
                FROM runs
                WHERE run_id = ?
                """,
                (run_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return RunRecord(
                run_id=row[0],
                model_id=row[1],
                provider=row[2],
                prompt=row[3],
                response_text=row[4],
                state=row[5],
                finish_reason=row[6],
                input_tokens=row[7],
                output_tokens=row[8],
                duration_ms=row[9],
                created_at=row[10],
            )
