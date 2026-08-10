"""Populate a small incident snapshot used at image build."""

from __future__ import annotations

from pathlib import Path

from spool.idents import identity
from spool.vfs import create, mkdir, setfacl


def main() -> None:
    alice = identity("alice")
    mkdir(alice, "acme", "/drop", 0o2771, 0o022)
    setfacl(
        alice,
        "acme",
        "/drop",
        "u::rwx,g::rwx,g:review:r-x,m::rwx,o::---",
        default=True,
    )
    create(alice, "acme", "/drop/inv-441.bin", 0o666, 0o022, b"x" * 200)
    erin = identity("erin")
    create(erin, "acme", "/drop/tmp-erin.dat", 0o666, 0o022, b"y" * 80)
    drew = identity("drew")
    mkdir(drew, "globex", "/notices", 0o2771, 0o022)
    create(drew, "globex", "/notices/n1", 0o666, 0o022, b"n" * 200)
    create(drew, "globex", "/notices/n2", 0o666, 0o022, b"n" * 200)


if __name__ == "__main__":
    main()
