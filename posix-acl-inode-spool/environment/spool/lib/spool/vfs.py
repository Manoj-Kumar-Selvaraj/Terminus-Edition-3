from __future__ import annotations

from typing import Any

from spool import quota, store
from spool.acl import (
    acl_to_mode,
    check_access,
    copy_acl,
    dump_entries,
    intersect_mode,
    mode_to_acl,
    parse_entries,
)
from spool.errors import VfsError
from spool.idents import gid_to_name, load_tenants, uid_to_name
from spool.paths import resolve, split_parts, tenant_prefix
from spool.store import connect


def _open(root=None):
    return connect(root)


def _root_ino(conn) -> int:
    return 1


def walk(conn, full: str, caller: dict[str, Any], *, follow_last_x: bool = True) -> list[dict[str, Any]]:
    parts = split_parts(full)
    ino = _root_ino(conn)
    chain = [store.get_inode(conn, ino)]
    chain[0]["name"] = ""
    chain[0]["parent"] = None
    for i, name in enumerate(parts):
        node = chain[-1]
        if node["type"] != "dir":
            raise VfsError("ENOTDIR", path=full)
        # Broken: skip execute checks on intermediate components.
        child = store.lookup_child(conn, int(node["ino"]), name)
        if child is None:
            raise VfsError("ENOENT", path=full)
        rec = store.get_inode(conn, child)
        rec["name"] = name
        rec["parent"] = int(node["ino"])
        chain.append(rec)
        _ = i, follow_last_x, caller
    return chain


def _special(mode: int) -> int:
    return int(mode) & 0o7000


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
    chain = walk(conn, parent_full, caller)
    parent = chain[-1]
    return full, parent, name


def _apply_create_mode(parent: dict[str, Any], requested: int, umask: int, typ: str) -> tuple[int, dict | None, dict | None]:
    # Broken: ignore default ACL; always apply umask; ignore setgid gid/bit.
    mode = requested & ~umask
    if typ == "dir":
        mode &= 0o7777
    else:
        mode &= 0o7777
    return mode, None, None


def mkdir(identity: dict[str, Any], tenant: str, path: str, mode: int, umask: int, root=None) -> dict[str, Any]:
    conn = _open(root)
    try:
        full, parent, name = _parent_and_name(conn, tenant, path, identity)
        if store.lookup_child(conn, int(parent["ino"]), name) is not None:
            raise VfsError("EEXIST", path=path)
        check_access(parent, identity, "wx")
        new_mode, acc, dfl = _apply_create_mode(parent, mode, umask, "dir")
        gid = int(identity["gid"])
        # Broken: directories do not consume inode quota.
        quota.charge(conn, tenant, 0, quota.dir_blocks())
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
        full, parent, name = _parent_and_name(conn, tenant, path, identity)
        if store.lookup_child(conn, int(parent["ino"]), name) is not None:
            raise VfsError("EEXIST", path=path)
        check_access(parent, identity, "wx")
        new_mode, acc, dfl = _apply_create_mode(parent, mode, umask, "file")
        gid = int(identity["gid"])
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
        full = resolve(tenant, path)
        chain = walk(conn, full, identity)
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
        src_full = resolve(tenant, old)
        src_chain = walk(conn, src_full, identity)
        src = src_chain[-1]
        if src["type"] != "file":
            raise VfsError("EPERM", path=old)
        dest_full, parent, name = _parent_and_name(conn, tenant, new, identity)
        if store.lookup_child(conn, int(parent["ino"]), name) is not None:
            raise VfsError("EEXIST", path=new)
        # Broken: skip write check on destination directory.
        # Broken: hard link charges another inode.
        quota.charge(conn, tenant, 1, 0)
        store.add_dentry(conn, int(parent["ino"]), name, int(src["ino"]))
        store.update_inode(conn, int(src["ino"]), nlink=int(src["nlink"]) + 1)
        conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _sticky_allows(directory: dict[str, Any], node: dict[str, Any], caller: dict[str, Any]) -> bool:
    # Broken: sticky is ignored.
    return True


def unlink(identity: dict[str, Any], tenant: str, path: str, root=None) -> dict[str, Any]:
    conn = _open(root)
    try:
        full, parent, name = _parent_and_name(conn, tenant, path, identity)
        child_ino = store.lookup_child(conn, int(parent["ino"]), name)
        if child_ino is None:
            raise VfsError("ENOENT", path=path)
        node = store.get_inode(conn, child_ino)
        check_access(parent, identity, "wx")
        if not _sticky_allows(parent, node, identity):
            raise VfsError("EACCES", path=path)
        if node["type"] == "dir":
            if store.children(conn, child_ino):
                raise VfsError("ENOTEMPTY", path=path)
        store.del_dentry(conn, int(parent["ino"]), name)
        nlink = int(node["nlink"]) - 1
        # Broken: always free quota on unlink, even when hard links remain.
        if node["type"] == "dir":
            quota.charge(conn, tenant, 0, -quota.dir_blocks())
            store.delete_inode(conn, child_ino)
        else:
            quota.charge(conn, tenant, -1, -quota.file_blocks(int(node["size"])))
            if nlink <= 0:
                store.delete_inode(conn, child_ino)
            else:
                store.update_inode(conn, child_ino, nlink=nlink)
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
        src_full, src_parent, src_name = _parent_and_name(conn, tenant, old, identity)
        dst_full, dst_parent, dst_name = _parent_and_name(conn, tenant, new, identity)
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
            # Broken: no sticky check on overwritten dest.
            if dest["type"] == "dir":
                if store.children(conn, dest_ino):
                    raise VfsError("ENOTEMPTY", path=new)
                quota.charge(conn, tenant, 0, -quota.dir_blocks())
                store.del_dentry(conn, int(dst_parent["ino"]), dst_name)
                store.delete_inode(conn, dest_ino)
            else:
                quota.charge(conn, tenant, -1, -quota.file_blocks(int(dest["size"])))
                store.del_dentry(conn, int(dst_parent["ino"]), dst_name)
                nlink = int(dest["nlink"]) - 1
                if nlink <= 0:
                    store.delete_inode(conn, dest_ino)
                else:
                    store.update_inode(conn, dest_ino, nlink=nlink)
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
        full = resolve(tenant, path)
        chain = walk(conn, full, identity)
        node = chain[-1]
        if int(identity["uid"]) != 0 and int(identity["uid"]) != int(node["uid"]):
            raise VfsError("EPERM", path=path)
        new_mode = mode & 0o7777
        acc = node.get("acl_access")
        if acc:
            # Broken: chmod does not update the ACL mask / user:: / other::.
            store.update_inode(conn, int(node["ino"]), mode=new_mode)
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
        full = resolve(tenant, path)
        chain = walk(conn, full, identity)
        node = chain[-1]
        if int(identity["uid"]) != 0 and int(identity["uid"]) != int(node["uid"]):
            raise VfsError("EPERM", path=path)
        acl = parse_entries(spec, tenant)
        # Broken: --default still writes the access ACL.
        mode = acl_to_mode(acl, _special(int(node["mode"])))
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
        full = resolve(tenant, path)
        chain = walk(conn, full, identity)
        node = chain[-1]
        owner = uid_to_name(int(node["uid"]))
        group = gid_to_name(int(node["gid"]), tenant)
        entries = dump_entries(
            node.get("acl_access"),
            int(node["mode"]),
            tenant,
            uid_to_name,
            lambda g: gid_to_name(g, tenant),
        )
        # Broken: omit default ACL entries.
        return {
            "path": path,
            "owner": owner,
            "group": group,
            "entries": entries,
            "default_entries": [],
        }
    finally:
        conn.close()


def stat(identity: dict[str, Any], tenant: str, path: str, root=None) -> dict[str, Any]:
    conn = _open(root)
    try:
        full = resolve(tenant, path)
        chain = walk(conn, full, identity)
        node = chain[-1]
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


# silence unused import warnings for broken inherit helpers referenced by oracle parity
_ = (copy_acl, intersect_mode, mode_to_acl)
