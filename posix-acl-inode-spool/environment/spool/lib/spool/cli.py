from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from spool.errors import VfsError
from spool.idents import identity
from spool.vfs import (
    chmod,
    create,
    getfacl,
    link,
    mkdir,
    quota_cmd,
    read,
    rename,
    setfacl,
    stat,
    unlink,
)


def _ok() -> int:
    sys.stdout.write(json.dumps({"ok": True}, separators=(",", ":")) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spoolctl")
    parser.add_argument("--identity", required=True)
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--umask", default="0022")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_mkdir = sub.add_parser("mkdir")
    p_mkdir.add_argument("path")
    p_mkdir.add_argument("--mode", default="0777")

    p_create = sub.add_parser("create")
    p_create.add_argument("path")
    p_create.add_argument("--mode", default="0666")
    p_create.add_argument("--file")

    p_read = sub.add_parser("read")
    p_read.add_argument("path")

    p_link = sub.add_parser("link")
    p_link.add_argument("old")
    p_link.add_argument("new")

    p_unlink = sub.add_parser("unlink")
    p_unlink.add_argument("path")

    p_rename = sub.add_parser("rename")
    p_rename.add_argument("old")
    p_rename.add_argument("new")

    p_chmod = sub.add_parser("chmod")
    p_chmod.add_argument("mode")
    p_chmod.add_argument("path")

    p_setfacl = sub.add_parser("setfacl")
    p_setfacl.add_argument("path")
    p_setfacl.add_argument("--entries", required=True)
    p_setfacl.add_argument("--default", action="store_true")

    p_getfacl = sub.add_parser("getfacl")
    p_getfacl.add_argument("path")

    sub.add_parser("quota")

    p_stat = sub.add_parser("stat")
    p_stat.add_argument("path")

    args = parser.parse_args(argv)
    try:
        ident = identity(args.identity)
        umask = int(str(args.umask), 8)
        cmd = args.cmd
        if cmd == "mkdir":
            mkdir(ident, args.tenant, args.path, int(str(args.mode), 8), umask)
            return _ok()
        if cmd == "create":
            data = b""
            if args.file:
                data = Path(args.file).read_bytes()
            create(ident, args.tenant, args.path, int(str(args.mode), 8), umask, data)
            return _ok()
        if cmd == "read":
            sys.stdout.buffer.write(read(ident, args.tenant, args.path))
            return 0
        if cmd == "link":
            link(ident, args.tenant, args.old, args.new)
            return _ok()
        if cmd == "unlink":
            unlink(ident, args.tenant, args.path)
            return _ok()
        if cmd == "rename":
            rename(ident, args.tenant, args.old, args.new)
            return _ok()
        if cmd == "chmod":
            chmod(ident, args.tenant, args.path, int(str(args.mode), 8))
            return _ok()
        if cmd == "setfacl":
            # Broken: --default flag is parsed then ignored at this layer too.
            setfacl(ident, args.tenant, args.path, args.entries, default=False)
            return _ok()
        if cmd == "getfacl":
            sys.stdout.write(json.dumps(getfacl(ident, args.tenant, args.path), separators=(",", ":")) + "\n")
            return 0
        if cmd == "quota":
            sys.stdout.write(json.dumps(quota_cmd(ident, args.tenant), separators=(",", ":")) + "\n")
            return 0
        if cmd == "stat":
            sys.stdout.write(json.dumps(stat(ident, args.tenant, args.path), separators=(",", ":")) + "\n")
            return 0
        raise VfsError("EINVAL")
    except VfsError as exc:
        sys.stderr.write(exc.to_json() + "\n")
        return 1
    except KeyError as exc:
        sys.stderr.write(json.dumps({"error": "EINVAL", "code": "UNKNOWN_ID"}) + "\n")
        return 1
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(json.dumps({"error": "EINVAL", "message": str(exc)}) + "\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
