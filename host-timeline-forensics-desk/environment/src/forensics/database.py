"""PostgreSQL pool, transactions, migration bootstrap, and query helpers."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import get_settings
from .errors import DatabaseUnavailable


class Database:
    def __init__(self, dsn: str | None = None, *, min_size: int = 1, max_size: int = 12):
        self.dsn = dsn or get_settings().database_url
        self.pool = ConnectionPool(
            conninfo=self.dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row, "autocommit": False},
            open=False,
            name="forensic-control-plane",
        )

    def open(self, timeout: float = 15.0) -> None:
        try:
            self.pool.open(wait=True, timeout=timeout)
        except Exception as exc:
            raise DatabaseUnavailable(f"database pool could not open: {exc}") from exc

    def close(self) -> None:
        self.pool.close()

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        try:
            with self.pool.connection() as conn:
                yield conn
        except psycopg.OperationalError as exc:
            raise DatabaseUnavailable(f"database connection failed: {exc}") from exc

    @contextmanager
    def transaction(self, *, isolation: str = "READ COMMITTED") -> Iterator[psycopg.Connection]:
        if isolation not in {"READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"}:
            raise ValueError("unsupported transaction isolation")
        with self.connection() as conn:
            try:
                with conn.transaction():
                    conn.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation}")
                    yield conn
            except psycopg.Error:
                raise

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return list(cur.fetchall()) if cur.description else []

    def one(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone() if cur.description else None

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        with self.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    return cur.rowcount

    def migrate(self, migration_dir: Path | None = None) -> list[int]:
        directory = migration_dir or Path("/app/sql/migrations")
        if not directory.is_dir():
            directory = Path(__file__).resolve().parents[2] / "sql" / "migrations"
        applied: list[int] = []
        with self.transaction(isolation="SERIALIZABLE") as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT clock_timestamp())"
            )
            for path in sorted(directory.glob("[0-9]*.sql")):
                version = int(path.name.split("_", 1)[0])
                exists = conn.execute(
                    "SELECT 1 FROM schema_migrations WHERE version=%s", (version,)
                ).fetchone()
                if exists:
                    continue
                sql = path.read_text(encoding="utf-8")
                conn.execute(sql, prepare=False)
                conn.execute("INSERT INTO schema_migrations(version) VALUES(%s)", (version,))
                applied.append(version)
        return applied


_database: Database | None = None


def get_database() -> Database:
    global _database
    if _database is None:
        _database = Database()
        _database.open()
    return _database
