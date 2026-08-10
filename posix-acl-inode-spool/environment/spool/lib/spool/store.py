from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from spool.errors import VfsError
from spool.idents import load_tenants, spool_root

SCHEMA = """
CREATE TABLE IF NOT EXISTS inodes (
    ino INTEGER PRIMARY KEY,
    type TEXT NOT NULL,
    mode INTEGER NOT NULL,
    uid INTEGER NOT NULL,
    gid INTEGER NOT NULL,
    size INTEGER NOT NULL,
    nlink INTEGER NOT NULL,
    acl_access TEXT,
    acl_default TEXT
);
CREATE TABLE IF NOT EXISTS dentries (
    dir_ino INTEGER NOT NULL,
    name TEXT NOT NULL,
    child_ino INTEGER NOT NULL,
    PRIMARY KEY (dir_ino, name)
);
CREATE TABLE IF NOT EXISTS blobs (
    ino INTEGER PRIMARY KEY,
    data BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS quota (
    tenant TEXT PRIMARY KEY,
    inodes_used INTEGER NOT NULL,
    blocks_used INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def db_path(root: Path | None = None) -> Path:
    base = root or spool_root()
    var = base / "var"
    var.mkdir(parents=True, exist_ok=True)
    return var / "spool.db"


def connect(root: Path | None = None) -> sqlite3.Connection:
    path = db_path(root)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    ensure_bootstrap(conn, root)
    return conn


def ensure_bootstrap(conn: sqlite3.Connection, root: Path | None = None) -> None:
    row = conn.execute("SELECT value FROM meta WHERE key='booted'").fetchone()
    if row:
        return
    conn.execute("INSERT INTO meta(key, value) VALUES('clock', '1000')")
    conn.execute("INSERT INTO meta(key, value) VALUES('booted', '1')")
    root_ino = _alloc_ino(conn)
    _insert_inode(conn, root_ino, "dir", 0o755, 0, 0, 4096, 2, None, None)
    t_ino = _alloc_ino(conn)
    _insert_inode(conn, t_ino, "dir", 0o755, 0, 0, 4096, 2, None, None)
    conn.execute(
        "INSERT INTO dentries(dir_ino, name, child_ino) VALUES(?, 't', ?)",
        (root_ino, t_ino),
    )
    tenants = load_tenants(root)
    for name, spec in tenants.items():
        mode = int(str(spec["root_mode"]), 8)
        tdir = _alloc_ino(conn)
        _insert_inode(
            conn,
            tdir,
            "dir",
            mode,
            int(spec["uid"]),
            int(spec["gid"]),
            4096,
            2,
            None,
            None,
        )
        conn.execute(
            "INSERT INTO dentries(dir_ino, name, child_ino) VALUES(?, ?, ?)",
            (t_ino, name, tdir),
        )
        conn.execute(
            "INSERT INTO quota(tenant, inodes_used, blocks_used) VALUES(?, 0, 0)",
            (name,),
        )
    conn.commit()


def tick(conn: sqlite3.Connection) -> int:
    cur = int(conn.execute("SELECT value FROM meta WHERE key='clock'").fetchone()[0])
    cur += 1
    conn.execute("UPDATE meta SET value=? WHERE key='clock'", (str(cur),))
    return cur


def _alloc_ino(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COALESCE(MAX(ino), 0) + 1 AS n FROM inodes").fetchone()
    return int(row["n"])


def _insert_inode(
    conn: sqlite3.Connection,
    ino: int,
    typ: str,
    mode: int,
    uid: int,
    gid: int,
    size: int,
    nlink: int,
    acl_access: str | None,
    acl_default: str | None,
) -> None:
    conn.execute(
        """INSERT INTO inodes(ino, type, mode, uid, gid, size, nlink, acl_access, acl_default)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (ino, typ, mode, uid, gid, size, nlink, acl_access, acl_default),
    )


def get_inode(conn: sqlite3.Connection, ino: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM inodes WHERE ino=?", (ino,)).fetchone()
    if row is None:
        raise VfsError("ENOENT")
    rec = dict(row)
    if rec["acl_access"]:
        rec["acl_access"] = json.loads(rec["acl_access"])
    if rec["acl_default"]:
        rec["acl_default"] = json.loads(rec["acl_default"])
    return rec


def update_inode(conn: sqlite3.Connection, ino: int, **fields: Any) -> None:
    if "acl_access" in fields and not isinstance(fields["acl_access"], (str, type(None))):
        fields["acl_access"] = json.dumps(fields["acl_access"], separators=(",", ":"))
    if "acl_default" in fields and not isinstance(fields["acl_default"], (str, type(None))):
        fields["acl_default"] = json.dumps(fields["acl_default"], separators=(",", ":"))
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE inodes SET {sets} WHERE ino=?", (*fields.values(), ino))


def lookup_child(conn: sqlite3.Connection, dir_ino: int, name: str) -> int | None:
    row = conn.execute(
        "SELECT child_ino FROM dentries WHERE dir_ino=? AND name=?",
        (dir_ino, name),
    ).fetchone()
    return int(row["child_ino"]) if row else None


def add_dentry(conn: sqlite3.Connection, dir_ino: int, name: str, child_ino: int) -> None:
    conn.execute(
        "INSERT INTO dentries(dir_ino, name, child_ino) VALUES(?,?,?)",
        (dir_ino, name, child_ino),
    )


def del_dentry(conn: sqlite3.Connection, dir_ino: int, name: str) -> None:
    conn.execute("DELETE FROM dentries WHERE dir_ino=? AND name=?", (dir_ino, name))


def children(conn: sqlite3.Connection, dir_ino: int) -> list[tuple[str, int]]:
    rows = conn.execute(
        "SELECT name, child_ino FROM dentries WHERE dir_ino=? ORDER BY name",
        (dir_ino,),
    ).fetchall()
    return [(str(r["name"]), int(r["child_ino"])) for r in rows]


def put_blob(conn: sqlite3.Connection, ino: int, data: bytes) -> None:
    conn.execute("INSERT OR REPLACE INTO blobs(ino, data) VALUES(?, ?)", (ino, data))


def get_blob(conn: sqlite3.Connection, ino: int) -> bytes:
    row = conn.execute("SELECT data FROM blobs WHERE ino=?", (ino,)).fetchone()
    return bytes(row["data"]) if row else b""


def delete_blob(conn: sqlite3.Connection, ino: int) -> None:
    conn.execute("DELETE FROM blobs WHERE ino=?", (ino,))


def new_inode(
    conn: sqlite3.Connection,
    typ: str,
    mode: int,
    uid: int,
    gid: int,
    size: int,
    nlink: int,
    acl_access: dict[str, Any] | None,
    acl_default: dict[str, Any] | None,
) -> int:
    ino = _alloc_ino(conn)
    acc = json.dumps(acl_access, separators=(",", ":")) if acl_access else None
    dfl = json.dumps(acl_default, separators=(",", ":")) if acl_default else None
    _insert_inode(conn, ino, typ, mode, uid, gid, size, nlink, acc, dfl)
    return ino


def delete_inode(conn: sqlite3.Connection, ino: int) -> None:
    delete_blob(conn, ino)
    conn.execute("DELETE FROM inodes WHERE ino=?", (ino,))


def quota_row(conn: sqlite3.Connection, tenant: str) -> dict[str, int]:
    row = conn.execute(
        "SELECT inodes_used, blocks_used FROM quota WHERE tenant=?", (tenant,)
    ).fetchone()
    if row is None:
        raise VfsError("EINVAL", path=tenant)
    return {"inodes_used": int(row["inodes_used"]), "blocks_used": int(row["blocks_used"])}


def set_quota(conn: sqlite3.Connection, tenant: str, inodes_used: int, blocks_used: int) -> None:
    conn.execute(
        "UPDATE quota SET inodes_used=?, blocks_used=? WHERE tenant=?",
        (inodes_used, blocks_used, tenant),
    )
