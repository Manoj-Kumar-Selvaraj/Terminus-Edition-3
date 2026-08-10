from __future__ import annotations

from typing import Any

from spool import quota, store
from spool.acl import (
    acl_to_mode,
    check_access,
    copy_acl,
    dump_entries,
    intersect_mode,
    parse_entries,
)
from spool.errors import VfsError
from spool.idents import gid_to_name, load_tenants, uid_to_name
from spool.paths import resolve, split_parts, tenant_prefix
from spool.store import connect


def _open(root=None):
    return connect(root)


def walk(conn, full: str, caller: dict[str, Any]) -> list[dict[str, Any]]:
    parts = split_parts(full)
    ino = 1
    chain = [store.get_inode(conn, ino)]
    chain[0]["name"] = ""
    chain[0]["parent"] = None
    for name in parts:
        node = chain[-1]
        if node["type"] != "dir":
            raise VfsError("ENOTDIR", path=full)
        check_access(node, caller, "x")
        child = store.lookup_child(conn, int(node["ino"]), name)
        if child is None:
            raise VfsError("ENOENT", path=full)
        rec = store.get_inode(conn, child)
        rec["name"] = name
        rec["parent"] = int(node["ino"])
        chain.append(rec)
    return chain


def _fmt_mode(typ: str, mode: int) -> str:
    if typ == "dir":
        return f"04{(mode & 0o7777):05o}"
    return f"010{(mode & 0o7777):04o}"


def _parent_and_name(conn, tenant: str, cli_path: str, caller: dict[str, Any]):
    full = resolve(tenant, cli_path)
    prefix = tenant_prefix(tenant)
    if full == prefix:
        raise VfsError("EPERM", path=cli_path)
    parent_full, name = full.rsplit("/", 1)
    if parent_full == "":
        parent_full = "/"
    parent = walk(conn, parent_full, caller)[-1]
    return full, parent, name


def _create_attrs(parent: dict[str, Any], caller: dict[str, Any], requested: int, umask: int, typ: str):
    setgid = bool(int(parent["mode"]) & 0o2000)
    gid = int(parent["gid"]) if setgid else int(caller["gid"])
    special = 0o2000 if (typ == "dir" and setgid) else 0
    default = copy_acl(parent.get("acl_default"))
    if default:
        acc = intersect_mode(default, requested)
        dfl = copy_acl(default) if typ == "dir" else None
        mode = acl_to_mode(acc, special)
        return mode, acc, dfl, gid
    mode = (requested & ~umask & 0o7777) | special
    return mode, None, None, gid


def _sticky_allows(directory: dict[str, Any], node: dict[str, Any], caller: dict[str, Any]) -> bool:
    if int(caller["uid"]) == 0:
        return True
    if not (int(directory["mode"]) & 0o1000):
        return True
    uid = int(caller["uid"])
    return uid == int(node["uid"]) or uid == int(directory["uid"])


def mkdir(identity: dict[str, Any], tenant: str, path: str, mode: int, umask: int, root=None) -> dict[str, Any]:
    conn = _open(root)
    try:
        _full, parent, name = _parent_and_name(conn, tenant, path, identity)
        if store.lookup_child(conn, int(parent["ino"]), name) is not None:
            raise VfsError("EEXIST", path=path)
        check_access(parent, identity, "wx")
        new_mode, acc, dfl, gid = _create_attrs(parent, identity, mode, umask, "dir")
        quota.charge(conn, tenant, 1, quota.dir_blocks())
        ino = store.new_inode(conn, "dir", new_mode, int(identity["uid"]), gid, 4096, 2, acc, dfl)
        store.add_dentry(conn, int(parent["ino"]), name, ino)
        conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create(
    identity: dict[str, Any],
    tenant: str,
    path: str,
    mode: int,
    umask: int,
    data: bytes,
    root=None,
) -> dict[str, Any]:
    conn = _open(root)
    try:
        _full, parent, name = _parent_and_name(conn, tenant, path, identity)
        if store.lookup_child(conn, int(parent["ino"]), name) is not None:
            raise VfsError("EEXIST", path=path)
        check_access(parent, identity, "wx")
        new_mode, acc, dfl, gid = _create_attrs(parent, identity, mode, umask, "file")
        blocks = quota.file_blocks(len(data))
        quota.charge(conn, tenant, 1, blocks)
        ino = store.new_inode(conn, "file", new_mode, int(identity["uid"]), gid, len(data), 1, acc, dfl)
        store.put_blob(conn, ino, data)
        store.add_dentry(conn, int(parent["ino"]), name, ino)
        conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def read(identity: dict[str, Any], tenant: str, path: str, root=None) -> bytes:
    conn = _open(root)
    try:
        chain = walk(conn, resolve(tenant, path), identity)
        node = chain[-1]
        if node["type"] != "file":
            raise VfsError("EISDIR", path=path)
        check_access(node, identity, "r")
        return store.get_blob(conn, int(node["ino"]))
    finally:
        conn.close()


def link(identity: dict[str, Any], tenant: str, old: str, new: str, root=None) -> dict[str, Any]:
    conn = _open(root)
    try:
        src = walk(conn, resolve(tenant, old), identity)[-1]
        if src["type"] != "file":
            raise VfsError("EPERM", path=old)
        _full, parent, name = _parent_and_name(conn, tenant, new, identity)
        if store.lookup_child(conn, int(parent["ino"]), name) is not None:
            raise VfsError("EEXIST", path=new)
        check_access(parent, identity, "wx")
        store.add_dentry(conn, int(parent["ino"]), name, int(src["ino"]))
        store.update_inode(conn, int(src["ino"]), nlink=int(src["nlink"]) + 1)
        conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _free_node(conn, tenant: str, node: dict[str, Any]) -> None:
    if node["type"] == "dir":
        quota.charge(conn, tenant, -1, -quota.dir_blocks())
        store.delete_inode(conn, int(node["ino"]))
        return
    nlink = int(node["nlink"]) - 1
    if nlink <= 0:
        quota.charge(conn, tenant, -1, -quota.file_blocks(int(node["size"])))
        store.delete_inode(conn, int(node["ino"]))
    else:
        store.update_inode(conn, int(node["ino"]), nlink=nlink)


def unlink(identity: dict[str, Any], tenant: str, path: str, root=None) -> dict[str, Any]:
    conn = _open(root)
    try:
        _full, parent, name = _parent_and_name(conn, tenant, path, identity)
        child_ino = store.lookup_child(conn, int(parent["ino"]), name)
        if child_ino is None:
            raise VfsError("ENOENT", path=path)
        node = store.get_inode(conn, child_ino)
        check_access(parent, identity, "wx")
        if not _sticky_allows(parent, node, identity):
            raise VfsError("EACCES", path=path)
        if node["type"] == "dir" and store.children(conn, child_ino):
            raise VfsError("ENOTEMPTY", path=path)
        store.del_dentry(conn, int(parent["ino"]), name)
        _free_node(conn, tenant, node)
        conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def rename(identity: dict[str, Any], tenant: str, old: str, new: str, root=None) -> dict[str, Any]:
    conn = _open(root)
    try:
        _sf, src_parent, src_name = _parent_and_name(conn, tenant, old, identity)
        _df, dst_parent, dst_name = _parent_and_name(conn, tenant, new, identity)
        src_ino = store.lookup_child(conn, int(src_parent["ino"]), src_name)
        if src_ino is None:
            raise VfsError("ENOENT", path=old)
        src = store.get_inode(conn, src_ino)
        check_access(src_parent, identity, "wx")
        check_access(dst_parent, identity, "wx")
        if not _sticky_allows(src_parent, src, identity):
            raise VfsError("EACCES", path=old)
        dest_ino = store.lookup_child(conn, int(dst_parent["ino"]), dst_name)
        if dest_ino is not None:
            dest = store.get_inode(conn, dest_ino)
            if not _sticky_allows(dst_parent, dest, identity):
                raise VfsError("EACCES", path=new)
            if dest["type"] == "dir" and store.children(conn, dest_ino):
                raise VfsError("ENOTEMPTY", path=new)
            store.del_dentry(conn, int(dst_parent["ino"]), dst_name)
            _free_node(conn, tenant, dest)
        store.del_dentry(conn, int(src_parent["ino"]), src_name)
        store.add_dentry(conn, int(dst_parent["ino"]), dst_name, src_ino)
        conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def chmod(identity: dict[str, Any], tenant: str, path: str, mode: int, root=None) -> dict[str, Any]:
    conn = _open(root)
    try:
        node = walk(conn, resolve(tenant, path), identity)[-1]
        if int(identity["uid"]) != 0 and int(identity["uid"]) != int(node["uid"]):
            raise VfsError("EPERM", path=path)
        new_mode = mode & 0o7777
        acc = copy_acl(node.get("acl_access"))
        if acc:
            acc["user"] = (new_mode >> 6) & 7
            acc["other"] = new_mode & 7
            if acc.get("mask") is not None:
                acc["mask"] = (new_mode >> 3) & 7
            else:
                acc["group"] = (new_mode >> 3) & 7
            store.update_inode(
                conn,
                int(node["ino"]),
                mode=acl_to_mode(acc, new_mode & 0o7000),
                acl_access=acc,
            )
        else:
            store.update_inode(conn, int(node["ino"]), mode=new_mode)
        conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def setfacl(
    identity: dict[str, Any],
    tenant: str,
    path: str,
    spec: str,
    default: bool,
    root=None,
) -> dict[str, Any]:
    conn = _open(root)
    try:
        node = walk(conn, resolve(tenant, path), identity)[-1]
        if int(identity["uid"]) != 0 and int(identity["uid"]) != int(node["uid"]):
            raise VfsError("EPERM", path=path)
        acl = parse_entries(spec, tenant)
        if default:
            if node["type"] != "dir":
                raise VfsError("EINVAL", path=path)
            store.update_inode(conn, int(node["ino"]), acl_default=acl)
        else:
            mode = acl_to_mode(acl, int(node["mode"]) & 0o7000)
            store.update_inode(conn, int(node["ino"]), acl_access=acl, mode=mode)
        conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def getfacl(identity: dict[str, Any], tenant: str, path: str, root=None) -> dict[str, Any]:
    conn = _open(root)
    try:
        node = walk(conn, resolve(tenant, path), identity)[-1]
        uid_n = uid_to_name
        gid_n = lambda g: gid_to_name(g, tenant)
        entries = dump_entries(node.get("acl_access"), int(node["mode"]), uid_n, gid_n)
        default_entries = []
        if node.get("acl_default"):
            default_entries = dump_entries(node.get("acl_default"), int(node["mode"]), uid_n, gid_n)
        return {
            "path": path,
            "owner": uid_to_name(int(node["uid"])),
            "group": gid_to_name(int(node["gid"]), tenant),
            "entries": entries,
            "default_entries": default_entries,
        }
    finally:
        conn.close()


def stat(identity: dict[str, Any], tenant: str, path: str, root=None) -> dict[str, Any]:
    conn = _open(root)
    try:
        node = walk(conn, resolve(tenant, path), identity)[-1]
        size = int(node["size"])
        blocks = quota.dir_blocks() if node["type"] == "dir" else quota.file_blocks(size)
        return {
            "path": path,
            "ino": int(node["ino"]),
            "type": node["type"],
            "mode": _fmt_mode(node["type"], int(node["mode"])),
            "nlink": int(node["nlink"]),
            "uid": int(node["uid"]),
            "gid": int(node["gid"]),
            "size": size,
            "blocks": blocks,
            "blksize": quota.BLOCK,
        }
    finally:
        conn.close()


def quota_cmd(identity: dict[str, Any], tenant: str, root=None) -> dict[str, Any]:
    if tenant not in load_tenants():
        raise VfsError("EINVAL", path=tenant)
    conn = _open(root)
    try:
        _ = identity
        return quota.report(conn, tenant)
    finally:
        conn.close()
