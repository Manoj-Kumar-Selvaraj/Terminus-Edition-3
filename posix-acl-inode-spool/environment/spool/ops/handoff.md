Night shift, drop-box cell.

Acme's `/drop` is supposed to be a shared intake: setgid staff, sticky, default ACL so review can read new blobs. This morning cara (review only) cannot open files alice dropped after we "fixed" inheritance last week. bob deleted erin's invoice while cleaning his own temp names. globex quota tripped after three 200-byte notices. One rename from acme's intake showed up under globex's tree during a path typo drill.

I left the last operator trace in the log dir. Don't remount this as a real filesystem and don't blow away the identity/tenant catalogs. Drive it with spoolctl. If you reset `/var`, bootstrap still has to honor the catalogs.
