# Resource reference

All resources are real Terraform managed resources. Paths are absolute Linux paths. Where a mode is supplied, equivalent octal spellings represent the same mode. Resource IDs are stable external-object identities and do not change when mutable properties change.

| Resource | External identity | Required configuration | Managed behavior |
|---|---|---|---|
| `ansibleops_file` | file path | `path` | Regular file existence plus optional mode/owner/group. |
| `ansibleops_directory` | directory path | `path` | Directory existence plus optional mode/owner/group. |
| `ansibleops_copy` | destination path | `source`, `source_digest`, `destination` | Copy source content and optional metadata; observe destination digest. |
| `ansibleops_template` | destination path | `source`, `source_digest`, `destination` | Render a Jinja template using optional string variables and manage the destination digest. |
| `ansibleops_line` | path + stable name | `name`, `path`, `line` | Manage one named line contract, optionally using `regexp` and `create`. |
| `ansibleops_block` | path + stable name | `name`, `path`, `block` | Manage one named marker-delimited block. |
| `ansibleops_symlink` | link path | `path`, `target` | Ensure a symlink points to the requested target. |
| `ansibleops_user` | user name | `name` | Manage local user attributes and supplementary groups. |
| `ansibleops_group` | group name | `name` | Manage a local group and optional gid. |
| `ansibleops_cron` | user + stable name | `name`, `job` | Manage one named crontab entry. |

## Content resources

`source_digest` is caller-supplied desired-state input for copy and template resources. Typical Terraform configurations set it with `filesha256(...)`. A digest change is a configuration change and must drive one update. `destination_digest` is observed/computed state and is refreshed from the installed destination.

Template `variables` are semantically unordered. Equivalent maps must generate stable task payloads and state regardless of insertion order.

`ansibleops_line` uses `name` only as stable Terraform/provider identity; the line/regexp contract controls the managed text. Delete removes only the matching managed line. `ansibleops_block` defaults its marker to `# {mark} ANSIBLEOPS <name>` so separately named blocks in the same file remain independently owned.

## Cron defaults

`ansibleops_cron.user` defaults to `root`. Omitted `minute`, `hour`, `day`, `month`, and `weekday` values are semantically `*`. Explicit wildcards and omitted values therefore represent the same schedule. Delete removes only the named Ansible cron entry for that user.

## Observation

Filesystem reads distinguish regular files, directories and symlinks; symlink reads use `lstat`/`readlink`. User/group reads use the local account databases. Cron reads inspect the user's crontab spool and do not depend on a running cron daemon.
