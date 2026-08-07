"""Shared live-database fixtures for the wire release desk verifier."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

APP = Path("/app/wire")
CLI = APP / "bin" / "wirectl"


def cli_environment() -> dict[str, str]:
    """Return connection defaults while honoring Harbor-provided overrides."""
    environment = os.environ.copy()
    environment.setdefault("WIRE_DB", "wire@127.0.0.1:5432")
    environment.setdefault("WIRE_DB_USER", "wire_app")
    environment.setdefault("WIRE_DB_PASSWORD", "wire_local")
    return environment


def connection() -> psycopg.Connection:
    """Open a verifier connection to the task's PostgreSQL sidecar."""
    return psycopg.connect(
        host=os.environ.get("WIRE_DB_HOST", "127.0.0.1"),
        dbname="wire",
        user="wire_app",
        password="wire_local",
        autocommit=True,
    )


def run_cli(*args: object, timeout: float = 20) -> subprocess.CompletedProcess[str]:
    """Run one public terminal command with captured line-oriented output."""
    return subprocess.run(
        [str(CLI), *(str(arg) for arg in args)],
        cwd=APP,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        env=cli_environment(),
    )


def scalar(query: str, params: tuple[object, ...] = ()) -> object:
    """Return the first column from a single-row database query."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
    assert row is not None
    return row[0]


@pytest.fixture(scope="session", autouse=True)
def built_application() -> Iterator[None]:
    """Wait for PostgreSQL and rebuild the submitted COBOL sources once."""
    deadline = time.monotonic() + 90
    while True:
        try:
            with connection() as conn:
                conn.execute("SELECT 1")
            break
        except psycopg.OperationalError:
            if time.monotonic() >= deadline:
                pytest.fail("PostgreSQL sidecar did not become ready")
            time.sleep(1)

    with connection() as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    database_environment = os.environ.copy()
    database_environment.setdefault(
        "PGHOST", os.environ.get("WIRE_DB_HOST", "127.0.0.1")
    )
    database_environment.setdefault("PGDATABASE", "wire")
    database_environment.setdefault("PGUSER", "wire_app")
    database_environment.setdefault("PGPASSWORD", "wire_local")
    migration = subprocess.run(
        [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            str(APP / "db" / "schema.sql"),
        ],
        cwd=APP,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
        env=database_environment,
    )
    if migration.returncode != 0:
        pytest.fail(
            f"database migration failed:\n{migration.stdout}\n{migration.stderr}"
        )

    result = subprocess.run(
        [str(APP / "bin" / "build-wire")],
        cwd=APP,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"COBOL build failed:\n{result.stdout}\n{result.stderr}")
    yield


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    """Give every test an independent operational database state."""
    with connection() as conn:
        conn.execute(
            "TRUNCATE audit_event, request_record, ledger_entry, wire_request"
        )
        conn.execute("UPDATE audit_counter SET next_value = 1")
        conn.execute(
            "UPDATE wire_account SET balance_cents = CASE account_id "
            "WHEN 'ACC-D1' THEN 1000000 "
            "WHEN 'ACC-D2' THEN 500000 "
            "WHEN 'ACC-C1' THEN 100000 "
            "WHEN 'ACC-C2' THEN 0 "
            "WHEN 'ACC-FZ' THEN 800000 "
            "WHEN 'ACC-LOW' THEN 250 "
            "ELSE balance_cents END, "
            "frozen = (account_id = 'ACC-FZ')"
        )
        conn.execute("UPDATE wire_operator SET active = true")
    yield
