"""SQLite-backed workspace state, lock leases, idempotency, and audit."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .clock import Clock


class StoreError(Exception):
    def __init__(self, status: int, message: str, event: str = "state_rejected") -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.event = event


class Store:
    def __init__(self, db_path: Path, clock: Clock, lease_ttl_ticks: int = 10) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        self.lease_ttl_ticks = int(lease_ttl_ticks)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._init_schema()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS workspace_state (
              workspace TEXT PRIMARY KEY,
              state_json TEXT,
              md5 TEXT,
              serial INTEGER NOT NULL DEFAULT 0,
              lineage TEXT
            );
            CREATE TABLE IF NOT EXISTS locks (
              workspace TEXT PRIMARY KEY,
              lock_id TEXT NOT NULL,
              lock_info TEXT NOT NULL,
              owner TEXT NOT NULL,
              expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency (
              idem_key TEXT PRIMARY KEY,
              workspace TEXT NOT NULL,
              body_md5 TEXT NOT NULL,
              serial INTEGER NOT NULL,
              response_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (
              seq INTEGER PRIMARY KEY AUTOINCREMENT,
              tick INTEGER NOT NULL,
              workspace TEXT NOT NULL,
              event TEXT NOT NULL,
              detail_json TEXT NOT NULL
            );
            """
        )

    def _audit(self, workspace: str, event: str, detail: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO audit(tick, workspace, event, detail_json) VALUES (?, ?, ?, ?)",
            (self.clock.now(), workspace, event, json.dumps(detail, sort_keys=True)),
        )

    def export_audit(self) -> dict[str, Any]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT seq, tick, workspace, event, detail_json FROM audit ORDER BY seq ASC"
            ).fetchall()
        events = []
        for row in rows:
            events.append(
                {
                    "seq": int(row["seq"]),
                    "tick": int(row["tick"]),
                    "workspace": row["workspace"],
                    "event": row["event"],
                    "detail": json.loads(row["detail_json"]),
                }
            )
        return {"schema_version": 1, "events": events}

    def get_state(self, workspace: str) -> tuple[str | None, str | None]:
        with self._lock:
            row = self._conn.execute(
                "SELECT state_json, md5 FROM workspace_state WHERE workspace = ?",
                (workspace,),
            ).fetchone()
        if row is None or row["state_json"] is None:
            return None, None
        return row["state_json"], row["md5"]

    def _active_lock(self, workspace: str) -> sqlite3.Row | None:
        row = self._conn.execute(
            "SELECT * FROM locks WHERE workspace = ?", (workspace,)
        ).fetchone()
        if row is None:
            return None
        if int(row["expires_at"]) <= self.clock.now():
            self._conn.execute("DELETE FROM locks WHERE workspace = ?", (workspace,))
            self._audit(
                workspace,
                "lease_reclaimed",
                {"lock_id": row["lock_id"], "owner": row["owner"], "reason": "expired"},
            )
            return None
        return row

    def lock(self, workspace: str, lock_info: dict[str, Any]) -> dict[str, Any]:
        lock_id = str(lock_info.get("ID") or "").strip()
        if not lock_id:
            raise StoreError(400, "lock info missing ID", event="lock_rejected")
        owner = str(lock_info.get("Who") or lock_id)
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                active = self._active_lock(workspace)
                if active is not None and active["lock_id"] != lock_id:
                    self._audit(
                        workspace,
                        "lock_rejected",
                        {
                            "holder": active["owner"],
                            "lock_id": active["lock_id"],
                            "requester": owner,
                        },
                    )
                    self._conn.execute("COMMIT")
                    raise StoreError(
                        423,
                        f"active lock held by {active['owner']}",
                        event="lock_rejected",
                    )
                expires = self.clock.now() + self.lease_ttl_ticks
                self._conn.execute(
                    """
                    INSERT INTO locks(workspace, lock_id, lock_info, owner, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(workspace) DO UPDATE SET
                      lock_id=excluded.lock_id,
                      lock_info=excluded.lock_info,
                      owner=excluded.owner,
                      expires_at=excluded.expires_at
                    """,
                    (workspace, lock_id, json.dumps(lock_info, sort_keys=True), owner, expires),
                )
                self._audit(
                    workspace,
                    "lock_acquired",
                    {"lock_id": lock_id, "owner": owner, "expires_at": expires},
                )
                self._conn.execute("COMMIT")
            except StoreError:
                raise
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
        return lock_info

    def unlock(self, workspace: str, lock_info: dict[str, Any]) -> None:
        lock_id = str(lock_info.get("ID") or "").strip()
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                active = self._active_lock(workspace)
                if active is None:
                    self._conn.execute("COMMIT")
                    return
                if active["lock_id"] != lock_id:
                    self._audit(
                        workspace,
                        "lock_rejected",
                        {
                            "reason": "unlock_token_mismatch",
                            "holder": active["owner"],
                            "provided": lock_id,
                        },
                    )
                    self._conn.execute("COMMIT")
                    raise StoreError(409, "unlock lock id mismatch", event="lock_rejected")
                self._conn.execute("DELETE FROM locks WHERE workspace = ?", (workspace,))
                self._audit(
                    workspace,
                    "lock_released",
                    {"lock_id": lock_id, "owner": active["owner"]},
                )
                self._conn.execute("COMMIT")
            except StoreError:
                raise
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def put_state(
        self,
        workspace: str,
        body: str,
        lock_id: str | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        body_md5 = hashlib.md5(body.encode("utf-8")).hexdigest()
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise StoreError(400, f"invalid state json: {exc}") from exc
        serial = int(payload.get("serial", 0))
        lineage = str(payload.get("lineage") or "")

        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                if idempotency_key:
                    prior = self._conn.execute(
                        "SELECT * FROM idempotency WHERE idem_key = ?",
                        (idempotency_key,),
                    ).fetchone()
                    if prior is not None:
                        if prior["body_md5"] != body_md5 or prior["workspace"] != workspace:
                            self._audit(
                                workspace,
                                "state_rejected",
                                {"reason": "idempotency_conflict", "key": idempotency_key},
                            )
                            self._conn.execute("COMMIT")
                            raise StoreError(409, "idempotency key conflict")
                        response = json.loads(prior["response_json"])
                        self._conn.execute("COMMIT")
                        return response

                active = self._active_lock(workspace)
                if active is None or not lock_id or active["lock_id"] != lock_id:
                    holder = active["owner"] if active else None
                    self._audit(
                        workspace,
                        "state_rejected",
                        {
                            "reason": "lock_token_fence",
                            "provided": lock_id,
                            "holder": holder,
                        },
                    )
                    self._conn.execute("COMMIT")
                    raise StoreError(409, "lock token required for state write")

                row = self._conn.execute(
                    "SELECT * FROM workspace_state WHERE workspace = ?",
                    (workspace,),
                ).fetchone()
                if row is None or row["state_json"] is None:
                    if not lineage:
                        self._audit(
                            workspace,
                            "state_rejected",
                            {"reason": "missing_lineage"},
                        )
                        self._conn.execute("COMMIT")
                        raise StoreError(400, "state lineage required")
                else:
                    if row["md5"] == body_md5 and int(row["serial"]) == serial:
                        response = {
                            "status": "committed",
                            "workspace": workspace,
                            "serial": serial,
                            "lineage": lineage,
                            "md5": body_md5,
                            "idempotent_replay": True,
                        }
                        if idempotency_key:
                            self._conn.execute(
                                """
                                INSERT OR IGNORE INTO idempotency(
                                  idem_key, workspace, body_md5, serial, response_json
                                ) VALUES (?, ?, ?, ?, ?)
                                """,
                                (
                                    idempotency_key,
                                    workspace,
                                    body_md5,
                                    serial,
                                    json.dumps(response, sort_keys=True),
                                ),
                            )
                        self._conn.execute("COMMIT")
                        return response
                    if lineage != str(row["lineage"] or ""):
                        self._audit(
                            workspace,
                            "state_rejected",
                            {
                                "reason": "lineage_mismatch",
                                "stored": row["lineage"],
                                "provided": lineage,
                            },
                        )
                        self._conn.execute("COMMIT")
                        raise StoreError(409, "saved plan is stale for current state lineage")
                    expected = int(row["serial"]) + 1
                    if serial != expected:
                        self._audit(
                            workspace,
                            "state_rejected",
                            {
                                "reason": "serial_mismatch",
                                "stored": int(row["serial"]),
                                "provided": serial,
                                "expected": expected,
                            },
                        )
                        self._conn.execute("COMMIT")
                        raise StoreError(409, "saved plan is stale for current state serial")

                self._conn.execute(
                    """
                    INSERT INTO workspace_state(workspace, state_json, md5, serial, lineage)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(workspace) DO UPDATE SET
                      state_json=excluded.state_json,
                      md5=excluded.md5,
                      serial=excluded.serial,
                      lineage=excluded.lineage
                    """,
                    (workspace, body, body_md5, serial, lineage),
                )
                response = {
                    "status": "committed",
                    "workspace": workspace,
                    "serial": serial,
                    "lineage": lineage,
                    "md5": body_md5,
                }
                if idempotency_key:
                    self._conn.execute(
                        """
                        INSERT INTO idempotency(idem_key, workspace, body_md5, serial, response_json)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            idempotency_key,
                            workspace,
                            body_md5,
                            serial,
                            json.dumps(response, sort_keys=True),
                        ),
                    )
                self._audit(
                    workspace,
                    "state_committed",
                    {
                        "serial": serial,
                        "lineage": lineage,
                        "md5": body_md5,
                        "idempotency_key": idempotency_key,
                        "lock_id": lock_id,
                    },
                )
                self._conn.execute("COMMIT")
                return response
            except StoreError:
                raise
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
