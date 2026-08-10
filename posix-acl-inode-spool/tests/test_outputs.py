"""Behavioral checks for the userspace spool VFS."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

APP = Path(os.environ.get("SPOOL_ARTIFACT", "/app/spool"))
BIN = APP / "bin" / "spoolctl"
CONTRACT = APP / "docs" / "vfs-contract.md"
OPS = APP / "ops"


def _reset(home: Path) -> None:
    if home.exists():
        shutil.rmtree(home)
    home.mkdir(parents=True)
    shutil.copytree(OPS, home / "ops")
    (home / "var").mkdir()


def _run(
    home: Path,
    args: list[str],
    *,
    identity: str = "alice",
    tenant: str = "acme",
    umask: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(BIN), "--identity", identity, "--tenant", tenant]
    if umask is not None:
        cmd.extend(["--umask", umask])
    cmd.extend(args)
    env = os.environ.copy()
    env["SPOOL_ROOT"] = str(home)
    env["PYTHONPATH"] = str(APP / "lib")
    cp = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    if check and cp.returncode != 0:
        raise AssertionError(
            f"spoolctl {args} rc={cp.returncode}\nstdout={cp.stdout}\nstderr={cp.stderr}"
        )
    return cp


def _json_out(cp: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(cp.stdout)

def _err(cp: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(cp.stderr.strip().splitlines()[-1])


@pytest.fixture
def home(tmp_path: Path) -> Path:
    dest = tmp_path / "spool"
    _reset(dest)
    return dest


def test_p2p_spoolctl_present() -> None:
    """The operator binary shipped with the spool tree is present and runnable."""
    assert BIN.is_file()
    if os.name != "nt":
        assert bool(BIN.stat().st_mode & stat.S_IXUSR)


def test_p2p_contract_and_catalogs_present() -> None:
    """Contract, tenant limits, and identity catalog remain in the submitted tree."""
    assert CONTRACT.is_file()
    tenants = json.loads((OPS / "tenants.json").read_text(encoding="utf-8"))
    idents = json.loads((OPS / "identities.json").read_text(encoding="utf-8"))
    assert "acme" in tenants and "globex" in tenants
    assert {"alice", "bob", "cara", "root"} <= set(idents)


def test_p2p_owner_roundtrip(home: Path) -> None:
    """An owner can mkdir, create, read, and stat a private file."""
    _run(home, ["mkdir", "/inbox", "--mode", "0755"])
    payload = home / "ops" / "payload.bin"
    payload.write_bytes(b"hello-spool")
    _run(home, ["create", "/inbox/note.txt", "--mode", "0644", "--file", str(payload)])
    cp = _run(home, ["read", "/inbox/note.txt"])
    assert cp.stdout == "hello-spool"
    st = _json_out(_run(home, ["stat", "/inbox/note.txt"]))
    assert st["type"] == "file"
    assert st["size"] == 11
    assert st["blksize"] == 512


def test_p2p_quota_object_shape(home: Path) -> None:
    """quota stdout is a JSON object with the contracted keys."""
    q = _json_out(_run(home, ["quota"]))
    for key in (
        "tenant",
        "block_size",
        "inodes_used",
        "inodes_hard",
        "blocks_used",
        "blocks_hard",
    ):
        assert key in q
    assert q["tenant"] == "acme"
    assert q["block_size"] == 512


def test_f2p_default_acl_inherited_by_file(home: Path) -> None:
    """New files copy the parent default ACL so named review can read 0660 objects."""
    _run(home, ["mkdir", "/drop", "--mode", "03771"], identity="root", umask="0000")
    _run(
        home,
        [
            "setfacl",
            "/drop",
            "--default",
            "--entries",
            "u::rwx,g::rwx,g:review:r-x,m::rwx,o::---",
        ],
        identity="root",
    )
    blob = home / "ops" / "inv.bin"
    blob.write_bytes(b"invoice-bytes")
    _run(home, ["create", "/drop/inv.bin", "--mode", "0660", "--file", str(blob)])
    facl = _json_out(_run(home, ["getfacl", "/drop/inv.bin"]))
    named = [e for e in facl["entries"] if e["tag"] == "group" and e["qualifier"] == "review"]
    assert named and named[0]["perms"][0] == "r"
    cp = _run(home, ["read", "/drop/inv.bin"], identity="cara", check=False)
    assert cp.returncode == 0
    assert "invoice-bytes" in cp.stdout


def test_f2p_default_acl_copied_to_new_directory(home: Path) -> None:
    """New directories receive both an access ACL and a copied default ACL."""
    _run(home, ["mkdir", "/drop", "--mode", "03771"], identity="root", umask="0000")
    _run(
        home,
        [
            "setfacl",
            "/drop",
            "--default",
            "--entries",
            "u::rwx,g::r-x,g:review:r-x,m::r-x,o::---",
        ],
        identity="root",
    )
    _run(home, ["mkdir", "/drop/batch", "--mode", "0777"])
    facl = _json_out(_run(home, ["getfacl", "/drop/batch"]))
    assert facl["default_entries"]
    tags = {(e["tag"], e["qualifier"]) for e in facl["default_entries"]}
    assert ("group", "review") in tags


def test_f2p_umask_skipped_when_default_acl_present(home: Path) -> None:
    """Create mode is intersected with the default ACL; umask is not subtracted."""
    _run(home, ["mkdir", "/drop", "--mode", "0777"], identity="root", umask="0000")
    _run(
        home,
        [
            "setfacl",
            "/drop",
            "--default",
            "--entries",
            "u::rwx,g::rwx,m::rwx,o::rwx",
        ],
        identity="root",
    )
    empty = home / "ops" / "empty.bin"
    empty.write_bytes(b"z")
    _run(
        home,
        ["create", "/drop/wide.bin", "--mode", "0666", "--file", str(empty)],
        umask="0022",
    )
    st = _json_out(_run(home, ["stat", "/drop/wide.bin"]))
    mode = int(st["mode"], 8)
    assert mode & 0o020 == 0o020


def test_p2p_umask_applies_without_default_acl(home: Path) -> None:
    """Without a default ACL, umask still strips group/other write from 0666."""
    _run(home, ["mkdir", "/plain", "--mode", "0777"], identity="root", umask="0000")
    empty = home / "ops" / "e.bin"
    empty.write_bytes(b"z")
    _run(
        home,
        ["create", "/plain/narrow.bin", "--mode", "0666", "--file", str(empty)],
        umask="0022",
    )
    st = _json_out(_run(home, ["stat", "/plain/narrow.bin"]))
    mode = int(st["mode"], 8)
    assert mode & 0o777 == 0o644


def test_f2p_sticky_blocks_non_owner_unlink(home: Path) -> None:
    """Sticky directories reject unlink by a peer who is not the file or dir owner."""
    _run(home, ["mkdir", "/drop", "--mode", "03771"], identity="root", umask="0000")
    blob = home / "ops" / "erin.bin"
    blob.write_bytes(b"erin-temp")
    _run(home, ["create", "/drop/tmp-erin.dat", "--mode", "0644", "--file", str(blob)], identity="erin")
    cp = _run(home, ["unlink", "/drop/tmp-erin.dat"], identity="bob", check=False)
    assert cp.returncode != 0
    assert _err(cp)["error"] == "EACCES"
    _run(home, ["read", "/drop/tmp-erin.dat"], identity="erin")


def test_p2p_sticky_allows_file_owner_and_dir_owner(home: Path) -> None:
    """File owner and directory owner may still unlink from a sticky drop box."""
    _run(home, ["mkdir", "/drop", "--mode", "03771"], identity="alice", umask="0000")
    blob = home / "ops" / "a.bin"
    blob.write_bytes(b"aa")
    _run(home, ["create", "/drop/mine.dat", "--mode", "0644", "--file", str(blob)], identity="bob")
    _run(home, ["unlink", "/drop/mine.dat"], identity="bob")
    blob.write_bytes(b"bb")
    _run(home, ["create", "/drop/theirs.dat", "--mode", "0644", "--file", str(blob)], identity="bob")
    _run(home, ["unlink", "/drop/theirs.dat"], identity="alice")


def test_f2p_setgid_forces_directory_group(home: Path) -> None:
    """Children of a setgid directory inherit that directory's group, not the creator primary gid."""
    _run(home, ["mkdir", "/sg", "--mode", "02777"], identity="root", umask="0000")
    blob = home / "ops" / "c.bin"
    blob.write_bytes(b"cc")
    _run(home, ["create", "/sg/from-cara.bin", "--mode", "0644", "--file", str(blob)], identity="cara")
    st = _json_out(_run(home, ["stat", "/sg/from-cara.bin"], identity="cara"))
    assert st["gid"] == 2100
    _run(home, ["mkdir", "/sg/sub", "--mode", "0777"], identity="cara")
    sub = _json_out(_run(home, ["stat", "/sg/sub"], identity="cara"))
    assert sub["gid"] == 2100
    assert int(sub["mode"], 8) & 0o2000 == 0o2000


def test_f2p_quota_counts_512_byte_blocks(home: Path) -> None:
    """A 200-byte file consumes one 512-byte block plus the parent directory block."""
    tenants = json.loads((home / "ops" / "tenants.json").read_text(encoding="utf-8"))
    hard = int(tenants["acme"]["blocks_hard"])
    _run(home, ["mkdir", "/q", "--mode", "0775"], identity="alice", umask="0000")
    blob = home / "ops" / "tiny.bin"
    blob.write_bytes(b"n" * 200)
    _run(home, ["create", "/q/n1", "--mode", "0644", "--file", str(blob)])
    q = _json_out(_run(home, ["quota"]))
    assert q["blocks_used"] == 2
    assert q["inodes_used"] == 2
    assert q["blocks_used"] < hard


def test_p2p_empty_file_uses_zero_blocks(home: Path) -> None:
    """A zero-length file spends an inode and no data blocks."""
    _run(home, ["mkdir", "/z", "--mode", "0755"], identity="alice")
    before = _json_out(_run(home, ["quota"]))
    _run(home, ["create", "/z/empty", "--mode", "0644"])
    after = _json_out(_run(home, ["quota"]))
    assert after["inodes_used"] == before["inodes_used"] + 1
    assert after["blocks_used"] == before["blocks_used"]
    st = _json_out(_run(home, ["stat", "/z/empty"]))
    assert st["blocks"] == 0


def test_f2p_hard_link_shares_inode_quota(home: Path) -> None:
    """A hard link increments nlink without charging another inode or block."""
    _run(home, ["mkdir", "/h", "--mode", "0755"], identity="alice")
    blob = home / "ops" / "h.bin"
    blob.write_bytes(b"x" * 100)
    _run(home, ["create", "/h/a", "--mode", "0644", "--file", str(blob)])
    mid = _json_out(_run(home, ["quota"]))
    _run(home, ["link", "/h/a", "/h/b"])
    after = _json_out(_run(home, ["quota"]))
    assert after["inodes_used"] == mid["inodes_used"]
    assert after["blocks_used"] == mid["blocks_used"]
    sa = _json_out(_run(home, ["stat", "/h/a"]))
    sb = _json_out(_run(home, ["stat", "/h/b"]))
    assert sa["ino"] == sb["ino"]
    assert sa["nlink"] == 2 == sb["nlink"]


def test_f2p_unlink_last_link_frees_quota(home: Path) -> None:
    """Quota is released only when the last name of an inode is removed."""
    _run(home, ["mkdir", "/h", "--mode", "0755"], identity="alice")
    blob = home / "ops" / "h2.bin"
    blob.write_bytes(b"x" * 100)
    _run(home, ["create", "/h/a", "--mode", "0644", "--file", str(blob)])
    _run(home, ["link", "/h/a", "/h/b"])
    linked = _json_out(_run(home, ["quota"]))
    _run(home, ["unlink", "/h/a"])
    still = _json_out(_run(home, ["quota"]))
    assert still["inodes_used"] == linked["inodes_used"]
    _run(home, ["unlink", "/h/b"])
    gone = _json_out(_run(home, ["quota"]))
    assert gone["inodes_used"] == linked["inodes_used"] - 1
    assert gone["blocks_used"] == linked["blocks_used"] - 1


def test_f2p_rename_stays_in_tenant(home: Path) -> None:
    """A rename that normalizes outside the tenant prefix is rejected with TENANT_ESCAPE."""
    _run(home, ["mkdir", "/drop", "--mode", "0755"], identity="alice")
    blob = home / "ops" / "esc.bin"
    blob.write_bytes(b"secret")
    _run(home, ["create", "/drop/inv.bin", "--mode", "0644", "--file", str(blob)])
    cp = _run(
        home,
        ["rename", "/drop/inv.bin", "/drop/../../globex/stray.bin"],
        check=False,
    )
    assert cp.returncode != 0
    err = _err(cp)
    assert err["error"] == "EPERM"
    assert err.get("code") == "TENANT_ESCAPE"
    g = _run(
        home,
        ["stat", "/stray.bin"],
        identity="drew",
        tenant="globex",
        check=False,
    )
    assert g.returncode != 0


def test_f2p_named_acl_mask_limits_access(home: Path) -> None:
    """Named ACL entries are intersected with the mask before granting access."""
    _run(home, ["mkdir", "/priv", "--mode", "0755"], identity="alice")
    blob = home / "ops" / "m.bin"
    blob.write_bytes(b"masked")
    _run(home, ["create", "/priv/doc", "--mode", "0600", "--file", str(blob)])
    _run(
        home,
        [
            "setfacl",
            "/priv/doc",
            "--entries",
            "u::rw-,u:cara:r--,g::---,m::---,o::---",
        ],
    )
    cp = _run(home, ["read", "/priv/doc"], identity="cara", check=False)
    assert cp.returncode != 0
    assert _err(cp)["error"] == "EACCES"


def test_f2p_chmod_updates_acl_mask(home: Path) -> None:
    """chmod on an ACL inode rewrites the mask from the new group-class bits."""
    _run(home, ["mkdir", "/priv", "--mode", "0755"], identity="alice")
    blob = home / "ops" / "cmode.bin"
    blob.write_bytes(b"m")
    _run(home, ["create", "/priv/doc", "--mode", "0660", "--file", str(blob)])
    _run(
        home,
        [
            "setfacl",
            "/priv/doc",
            "--entries",
            "u::rw-,u:bob:rw-,g::r--,m::rw-,o::---",
        ],
    )
    _run(home, ["chmod", "0640", "/priv/doc"])
    facl = _json_out(_run(home, ["getfacl", "/priv/doc"]))
    mask = [e for e in facl["entries"] if e["tag"] == "mask"]
    assert mask and mask[0]["perms"] == "r--"


def test_f2p_ancestor_execute_required(home: Path) -> None:
    """Creating through a directory without search fails even if the leaf dir is writable."""
    _run(home, ["mkdir", "/hidden", "--mode", "0755"], identity="root", umask="0000")
    _run(home, ["mkdir", "/hidden/box", "--mode", "0777"], identity="root", umask="0000")
    _run(home, ["chmod", "0000", "/hidden"], identity="root")
    blob = home / "ops" / "x.bin"
    blob.write_bytes(b"x")
    cp = _run(
        home,
        ["create", "/hidden/box/f", "--mode", "0644", "--file", str(blob)],
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "EACCES"


def test_f2p_quota_hard_limit_enospc(home: Path) -> None:
    """Crossing the configured inode hard limit fails with ENOSPC and creates nothing extra."""
    spec = json.loads((home / "ops" / "tenants.json").read_text(encoding="utf-8"))
    spec["acme"]["inodes_hard"] = 2
    (home / "ops" / "tenants.json").write_text(json.dumps(spec), encoding="utf-8")
    _run(home, ["mkdir", "/lim", "--mode", "0755"], identity="alice")
    blob = home / "ops" / "one.bin"
    blob.write_bytes(b"one")
    _run(home, ["create", "/lim/a", "--mode", "0644", "--file", str(blob)])
    cp = _run(home, ["create", "/lim/b", "--mode", "0644", "--file", str(blob)], check=False)
    assert cp.returncode != 0
    assert _err(cp)["error"] == "ENOSPC"
    st = _run(home, ["stat", "/lim/b"], check=False)
    assert st.returncode != 0


def test_p2p_getfacl_entry_order(home: Path) -> None:
    """getfacl lists user, named users, group, named groups, mask, then other."""
    _run(home, ["mkdir", "/acl", "--mode", "0755"], identity="alice")
    blob = home / "ops" / "o.bin"
    blob.write_bytes(b"o")
    _run(home, ["create", "/acl/f", "--mode", "0644", "--file", str(blob)])
    _run(
        home,
        [
            "setfacl",
            "/acl/f",
            "--entries",
            "u::rw-,u:bob:r--,u:cara:rw-,g::r--,g:review:r-x,m::rwx,o::---",
        ],
    )
    facl = _json_out(_run(home, ["getfacl", "/acl/f"]))
    tags = [(e["tag"], e["qualifier"]) for e in facl["entries"]]
    assert tags[0] == ("user", "")
    named_users = [q for t, q in tags if t == "user" and q]
    assert named_users == sorted(named_users)
    assert ("mask", "") in tags
    assert tags[-1] == ("other", "")
    assert facl["owner"] == "alice"
    assert facl["path"] == "/acl/f"


def test_p2p_stat_mode_type_nibble(home: Path) -> None:
    """stat.mode is a 7-digit octal string that includes the file type nibble."""
    _run(home, ["mkdir", "/s", "--mode", "0755"], identity="alice")
    d = _json_out(_run(home, ["stat", "/s"]))
    assert d["mode"].startswith("040")
    assert len(d["mode"]) == 7
    blob = home / "ops" / "s.bin"
    blob.write_bytes(b"s")
    _run(home, ["create", "/s/f", "--mode", "0644", "--file", str(blob)])
    f = _json_out(_run(home, ["stat", "/s/f"]))
    assert f["mode"].startswith("010")
    assert f["uid"] == 1001


def test_f2p_rename_overwrite_respects_sticky(home: Path) -> None:
    """Overwriting a name in a sticky directory requires dest ownership rules."""
    _run(home, ["mkdir", "/drop", "--mode", "03771"], identity="root", umask="0000")
    blob = home / "ops" / "r.bin"
    blob.write_bytes(b"alice")
    _run(home, ["create", "/drop/a", "--mode", "0644", "--file", str(blob)])
    blob.write_bytes(b"erin")
    _run(home, ["create", "/drop/e", "--mode", "0644", "--file", str(blob)], identity="erin")
    cp = _run(home, ["rename", "/drop/a", "/drop/e"], identity="bob", check=False)
    assert cp.returncode != 0
    assert _err(cp)["error"] == "EACCES"


def test_f2p_link_requires_dest_write(home: Path) -> None:
    """Hard-linking into a directory without write permission is denied."""
    _run(home, ["mkdir", "/src", "--mode", "0755"], identity="alice")
    _run(home, ["mkdir", "/dst", "--mode", "0555"], identity="root", umask="0000")
    blob = home / "ops" / "l.bin"
    blob.write_bytes(b"linkme")
    _run(home, ["create", "/src/a", "--mode", "0644", "--file", str(blob)])
    cp = _run(home, ["link", "/src/a", "/dst/b"], check=False)
    assert cp.returncode != 0
    assert _err(cp)["error"] == "EACCES"


def test_f2p_directory_inode_quota(home: Path) -> None:
    """Each directory consumes one inode toward the tenant hard limit."""
    before = _json_out(_run(home, ["quota"]))
    _run(home, ["mkdir", "/counted", "--mode", "0755"], identity="alice")
    after = _json_out(_run(home, ["quota"]))
    assert after["inodes_used"] == before["inodes_used"] + 1
    assert after["blocks_used"] == before["blocks_used"] + 1


def test_f2p_default_setfacl_keeps_access_acl(home: Path) -> None:
    """setfacl --default writes only the default ACL and leaves the access ACL intact."""
    _run(home, ["mkdir", "/drop", "--mode", "0755"], identity="root", umask="0000")
    _run(
        home,
        ["setfacl", "/drop", "--entries", "u::rwx,g::rwx,m::rwx,o::---"],
        identity="root",
    )
    _run(
        home,
        [
            "setfacl",
            "/drop",
            "--default",
            "--entries",
            "u::rwx,g::r-x,g:review:r-x,m::r-x,o::---",
        ],
        identity="root",
    )
    facl = _json_out(_run(home, ["getfacl", "/drop"], identity="root"))
    access_named = [e for e in facl["entries"] if e["tag"] == "group" and e["qualifier"] == "review"]
    default_named = [
        e for e in facl["default_entries"] if e["tag"] == "group" and e["qualifier"] == "review"
    ]
    assert not access_named
    assert default_named


def test_f2p_block_ceil_not_floor(home: Path) -> None:
    """A 513-byte payload occupies two quota blocks, not one."""
    _run(home, ["mkdir", "/b", "--mode", "0755"], identity="alice")
    blob = home / "ops" / "big.bin"
    blob.write_bytes(b"B" * 513)
    before = _json_out(_run(home, ["quota"]))
    _run(home, ["create", "/b/big", "--mode", "0644", "--file", str(blob)])
    after = _json_out(_run(home, ["quota"]))
    assert after["blocks_used"] - before["blocks_used"] == 2
    st = _json_out(_run(home, ["stat", "/b/big"]))
    assert st["blocks"] == 2
