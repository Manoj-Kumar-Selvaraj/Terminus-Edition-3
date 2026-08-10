from __future__ import annotations

from typing import Any

from spool.errors import VfsError
from spool.idents import name_to_gid, name_to_uid

PERM_CHARS = (("r", 4), ("w", 2), ("x", 1))


def bits_to_str(bits: int) -> str:
    bits = int(bits) & 7
    return "".join(ch if bits & flag else "-" for ch, flag in PERM_CHARS)


def str_to_bits(text: str) -> int:
    if len(text) != 3:
        raise VfsError("EINVAL")
    bits = 0
    expected = ["r", "w", "x"]
    for i, ch in enumerate(text):
        if ch == expected[i]:
            bits |= PERM_CHARS[i][1]
        elif ch != "-":
            raise VfsError("EINVAL")
    return bits


def parse_entries(spec: str, tenant: str) -> dict[str, Any]:
    acl: dict[str, Any] = {
        "user": None,
        "named_users": {},
        "group": None,
        "named_groups": {},
        "mask": None,
        "other": None,
    }
    if not spec.strip():
        raise VfsError("EINVAL")
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        bits_txt = part.split(":")[-1]
        perms = str_to_bits(bits_txt)
        if part.startswith("u::") or part.startswith("user::"):
            acl["user"] = perms
        elif part.startswith("u:") or part.startswith("user:"):
            qual = part.split(":")[1]
            acl["named_users"][str(name_to_uid(qual))] = perms
        elif part.startswith("g::") or part.startswith("group::"):
            acl["group"] = perms
        elif part.startswith("g:") or part.startswith("group:"):
            qual = part.split(":")[1]
            acl["named_groups"][str(name_to_gid(qual, tenant))] = perms
        elif part.startswith("m::") or part.startswith("mask::"):
            acl["mask"] = perms
        elif part.startswith("o::") or part.startswith("other::"):
            acl["other"] = perms
        else:
            raise VfsError("EINVAL")
    if acl["user"] is None or acl["group"] is None or acl["other"] is None:
        raise VfsError("EINVAL")
    if (acl["named_users"] or acl["named_groups"]) and acl["mask"] is None:
        raise VfsError("EINVAL")
    return acl


def mode_to_acl(mode: int) -> dict[str, Any]:
    return {
        "user": (mode >> 6) & 7,
        "named_users": {},
        "group": (mode >> 3) & 7,
        "named_groups": {},
        "mask": None,
        "other": mode & 7,
    }


def acl_to_mode(acl: dict[str, Any], special: int = 0) -> int:
    group_class = acl["mask"] if acl.get("mask") is not None else acl["group"]
    return (special & 0o7000) | ((int(acl["user"]) & 7) << 6) | ((int(group_class) & 7) << 3) | (int(acl["other"]) & 7)


def intersect_mode(acl: dict[str, Any], mode: int) -> dict[str, Any]:
    out = {
        "user": int(acl["user"]) & ((mode >> 6) & 7),
        "named_users": dict(acl.get("named_users") or {}),
        "group": int(acl["group"]),
        "named_groups": dict(acl.get("named_groups") or {}),
        "mask": acl.get("mask"),
        "other": int(acl["other"]) & (mode & 7),
    }
    if out["mask"] is not None:
        out["mask"] = int(out["mask"]) & ((mode >> 3) & 7)
    else:
        out["group"] = int(out["group"]) & ((mode >> 3) & 7)
    return out


def copy_acl(acl: dict[str, Any] | None) -> dict[str, Any] | None:
    if acl is None:
        return None
    return {
        "user": acl["user"],
        "named_users": dict(acl.get("named_users") or {}),
        "group": acl["group"],
        "named_groups": dict(acl.get("named_groups") or {}),
        "mask": acl.get("mask"),
        "other": acl["other"],
    }


def _want(need: str) -> int:
    bits = 0
    if "r" in need:
        bits |= 4
    if "w" in need:
        bits |= 2
    if "x" in need:
        bits |= 1
    return bits


def check_access(inode: dict[str, Any], caller: dict[str, Any], need: str) -> None:
    if int(caller["uid"]) == 0:
        return
    want = _want(need)
    mode = int(inode["mode"])
    acl = inode.get("acl_access")
    if not acl:
        if int(caller["uid"]) == int(inode["uid"]):
            have = (mode >> 6) & 7
        elif int(inode["gid"]) in {int(g) for g in caller["groups"]}:
            have = (mode >> 3) & 7
        else:
            have = mode & 7
        if have & want != want:
            raise VfsError("EACCES")
        return

    uid = int(caller["uid"])
    named_users = {int(k): int(v) for k, v in (acl.get("named_users") or {}).items()}
    mask = acl.get("mask")
    mask_bits = 7 if mask is None else int(mask)

    if uid == int(inode["uid"]):
        have = int(acl["user"])
    elif uid in named_users:
        have = named_users[uid] & mask_bits
    else:
        groups = {int(g) for g in caller["groups"]}
        group_class = False
        have = 0
        if int(inode["gid"]) in groups:
            have |= int(acl["group"])
            group_class = True
        for gid_s, perms in (acl.get("named_groups") or {}).items():
            if int(gid_s) in groups:
                have |= int(perms)
                group_class = True
        if group_class:
            have &= mask_bits
        else:
            have = int(acl["other"])
    if have & want != want:
        raise VfsError("EACCES")


def dump_entries(acl: dict[str, Any] | None, mode: int, uid_name, gid_name) -> list[dict[str, str]]:
    if not acl:
        acl = mode_to_acl(mode)
    entries: list[dict[str, str]] = [
        {"tag": "user", "qualifier": "", "perms": bits_to_str(int(acl["user"]))},
    ]
    named_users = acl.get("named_users") or {}
    for uid_s in sorted(named_users, key=lambda s: uid_name(int(s))):
        entries.append(
            {
                "tag": "user",
                "qualifier": uid_name(int(uid_s)),
                "perms": bits_to_str(int(named_users[uid_s])),
            }
        )
    entries.append({"tag": "group", "qualifier": "", "perms": bits_to_str(int(acl["group"]))})
    named_groups = acl.get("named_groups") or {}
    for gid_s in sorted(named_groups, key=lambda s: gid_name(int(s))):
        entries.append(
            {
                "tag": "group",
                "qualifier": gid_name(int(gid_s)),
                "perms": bits_to_str(int(named_groups[gid_s])),
            }
        )
    if acl.get("mask") is not None:
        entries.append({"tag": "mask", "qualifier": "", "perms": bits_to_str(int(acl["mask"]))})
    entries.append({"tag": "other", "qualifier": "", "perms": bits_to_str(int(acl["other"]))})
    return entries
