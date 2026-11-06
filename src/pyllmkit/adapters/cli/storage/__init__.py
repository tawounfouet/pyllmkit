"""CLI storage adapters."""

from .sqlite_store import RunRecord, SqliteRunStore

__all__ = ["RunRecord", "SqliteRunStore"]
