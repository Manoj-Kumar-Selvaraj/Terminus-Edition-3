# posix-acl-inode-spool

Userspace multi-tenant upload spool: SQLite inodes, POSIX ACL inheritance, setgid/sticky drop boxes, and block quota. No privileged mounts.

## Why it is hard

The public CLI looks like a thin file tool. Correctness is the interaction of default-ACL creation, umask suppression, sticky unlink, setgid gid inheritance, 512-byte quota (including hard links), and a tenant path fence. Fixing only the visible delete bug still fails quota, inheritance, or rename escape.

## Solution approach

Repair the Python VFS under `/app/spool` so `spoolctl` matches `/app/spool/docs/vfs-contract.md`. The oracle replaces the broken ACL, path, quota, VFS, and CLI modules, then reopens the store through the public binary.

## Verification

Separate verifier image. Tests reset a private `SPOOL_ROOT`, drive `spoolctl`, and check JSON plus live inode/quota effects. Difficulty in `task.toml` is provisional until both model families are measured.

## Layout

- `environment/spool/` — agent-visible tree
- `solution/fixed/` — corrected modules
- `tests/` — pytest + separate Dockerfile
