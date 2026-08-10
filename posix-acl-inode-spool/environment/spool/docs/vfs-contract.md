# Upload spool VFS contract

Userspace inode store. No kernel mounts. Operator binary is `/app/spool/bin/spoolctl`. Durable state is SQLite plus blobs under `/app/spool/var`. Identity catalog is `/app/spool/ops/identities.json`. Tenant limits are `/app/spool/ops/tenants.json`.

## Identity and paths

`--identity NAME` loads uid, primary gid, and supplemental groups from the catalog. uid `0` is privileged and skips access, sticky, and ACL checks. `--tenant ID` selects that tenant's tree. `--umask OCTAL` defaults to `0022`.

CLI paths are absolute inside the tenant (`/drop/a`). On disk they live under `/t/<tenant>/...`. Resolve by joining the tenant prefix with the CLI path, then normalizing `.` and `..`. If the normalized full path is not the tenant prefix and does not stay under it, fail with `{"error":"EPERM","code":"TENANT_ESCAPE"}`. A leading `/..` that would leave `/` is the same failure. Tenants share one inode table.

## Commands

```
spoolctl --identity NAME --tenant ID [--umask OCTAL] mkdir PATH [--mode OCTAL]
spoolctl --identity NAME --tenant ID [--umask OCTAL] create PATH [--mode OCTAL] [--file FILE]
spoolctl --identity NAME --tenant ID read PATH
spoolctl --identity NAME --tenant ID link OLD NEW
spoolctl --identity NAME --tenant ID unlink PATH
spoolctl --identity NAME --tenant ID rename OLD NEW
spoolctl --identity NAME --tenant ID chmod MODE PATH
spoolctl --identity NAME --tenant ID setfacl [--default] --entries SPEC PATH
spoolctl --identity NAME --tenant ID getfacl PATH
spoolctl --identity NAME --tenant ID quota
spoolctl --identity NAME --tenant ID stat PATH
```

`MODE` for chmod is an octal integer including special bits (`2` setgid, `1` sticky, `4` setuid). `mkdir` default mode `0777`, `create` default mode `0666`, both before umask or ACL intersection. `create --file` copies those bytes; omit `--file` for a zero-length file. `read` writes file bytes to stdout. Success for `mkdir`, `create`, `link`, `unlink`, `rename`, `chmod`, `setfacl` prints `{"ok":true}` and exit `0`. Failures print one JSON object on stderr, nothing required on stdout, exit `1`.

Error `error` values: `EACCES`, `EPERM`, `ENOENT`, `EEXIST`, `ENOSPC`, `EINVAL`, `ENOTEMPTY`, `EISDIR`, `ENOTDIR`.

## Permission walk

Every ancestor except the last component needs execute. `mkdir` / `create` / `link` dest / `unlink` / `rename` need write+execute on the directory that gains or loses the name. `read` needs read on the file. `stat` / `getfacl` need only search on ancestors. `chmod` and `setfacl` require the caller is the owner or privileged.

Access ACL evaluation (POSIX 1003.1e):

1. Owner uid matches: use `user::` only.
2. Else a named user entry matches uid: use that entry AND the mask.
3. Else owning group (primary or supplemental) or any named group matches: the group class applies. Grant only if some matching group entry includes the bits AND the mask includes them. Do not fall through to `other::`.
4. Else use `other::`.

If there is no extended ACL, use classic owner/group/other mode bits. Group match uses primary gid plus supplemental groups.

## Sticky, setgid, umask, default ACL

If a directory has sticky (`01000`), unlink or rename of an entry requires the caller is privileged, the file owner, or the directory owner.

If a directory has setgid (`02000`), new children take that directory's gid, not the creator's primary gid. New subdirectories also receive the setgid bit.

If the parent has a default ACL, ignore umask. Copy the default ACL to the child's access ACL, then intersect `user::`, mask (or `group::` when no mask), and `other::` with the requested mode's owner/group/other bits. New directories also copy the parent's default ACL as their own default ACL. If the parent has no default ACL, apply umask to the requested mode and store classic mode bits only.

`setfacl --entries` replaces the access ACL. `setfacl --default --entries` replaces the default ACL (directories only). SPEC is comma-separated `u::rwx`, `u:NAME:rw-`, `g::r-x`, `g:NAME:r-x`, `m::rwx`, `o::---`. Names map through the identity catalog (users) or tenant group catalog. Setting any named user or named group entry requires a mask entry. `chmod` on an inode that has an access ACL updates `user::`, `other::`, and the mask (group class) from the new mode; named entries stay.

## Quota and links

Block size is `512`. A regular file uses `ceil(size/512)` blocks, or `0` when size is `0`. A directory uses `1` inode and `1` block. Hard links add a directory entry and increment `nlink` only; they do not add inode or block usage. Unlink frees inode and block quota only when `nlink` reaches `0`. Crossing a tenant `inodes_hard` or `blocks_hard` fails with `ENOSPC` and must not create the object. `quota` reports current stored usage.

Timestamps are a monotonic integer clock in the store, not wall time.

## JSON schemas

`stat` stdout:

```
{"path":str,"ino":int,"type":"file"|"dir","mode":str,"nlink":int,"uid":int,"gid":int,"size":int,"blocks":int,"blksize":512}
```

`mode` is a 7-digit zero-padded octal string including the type nibble (`0402771` directory, `0100644` file).

`getfacl` stdout:

```
{"path":str,"owner":str,"group":str,"entries":[Entry],"default_entries":[Entry]}
```

`Entry` is `{"tag":"user"|"group"|"mask"|"other","qualifier":str,"perms":str}`. `perms` is a 3-char `rwx` mask using `-` for off. Order: `user` with empty qualifier, named users sorted by qualifier, `group` with empty qualifier, named groups sorted by qualifier, `mask` if present, `other`. `default_entries` uses the same rules and is `[]` when the inode has no default ACL. Owner and group fields are catalog names; unknown ids render as the decimal id string.

`quota` stdout:

```
{"tenant":str,"block_size":512,"inodes_used":int,"inodes_hard":int,"blocks_used":int,"blocks_hard":int}
```
