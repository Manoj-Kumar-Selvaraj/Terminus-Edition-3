# Service guardian runtime contract

The guardian is a foreground Linux service supervisor. It is started as `guardian run <manifest> <state-directory>`. The state directory contains `control.sock`, `guardian.lock`, `events.bin`, unit logs, and worker-owned fixture state. A second guardian for the same directory must fail without disturbing the first.

## Manifest

The manifest is UTF-8 text. Blank lines and lines beginning with `#` are ignored. A unit begins with `unit <name>` and ends with `end`. Names contain lowercase ASCII letters, digits, and hyphens and are unique. Directives inside a unit are:

```
exec <absolute-path>
arg <one argument without control characters>
depends <unit-name>
restart <never|on-failure>
restart-limit <integer from 0 through 9>
stop-grace-ms <integer from 50 through 5000>
```

Each unit has one `exec` and one each of the restart, restart-limit, and stop-grace directives. `arg` and `depends` may repeat. Dependencies must exist and the graph must be acyclic. Unknown directives, duplicate singleton directives, relative executables, and malformed values reject the complete manifest.

## Worker readiness and process ownership

The child receives `GUARDIAN_READY_FD` naming a writable descriptor. Closing it without writing is startup failure. The first byte marks the unit ready; dependents may be spawned only after all dependencies are ready. The guardian is a Linux child subreaper and owns each unit's process group. It observes the main child through a pidfd registered in the epoll loop. An exec error is a start failure rather than a running service.

Stopping a unit first sends `SIGTERM` to its whole process group. Once its grace expires, any surviving group member receives `SIGKILL`. Shutdown stops dependents before providers and does not return until adopted descendants have been reaped. A successful main process exit is not restarted. An unsuccessful exit consumes one restart from that unit's budget. Once the configured number is exhausted, the unit is `failed` and its dependents are stopped and `blocked`.

## Reload

`RELOAD` parses and validates the whole manifest before changing live state. A rejected reload returns an error and changes nothing. Unchanged units retain their pid, readiness, restart count, and journal history. Removing a unit stops its dependent closure first. A changed unit is replaced only after its dependencies are ready. Reload does not reset a restart budget.

## Control socket

`guardianctl <socket> <command>` sends one request over a Unix `SOCK_SEQPACKET` socket and prints the single response. The socket is mode `0666`, but the server accepts only peers with the guardian's effective uid. Commands are `STATUS`, `START <unit>`, `STOP <unit>`, `RELOAD`, `EVENTS`, and `SHUTDOWN`.

`STATUS` returns one line per unit, sorted by name:

`UNIT|name=<name>|state=<stopped|starting|ready|stopping|failed|blocked>|pid=<pid-or-0>|restarts=<count>`

Mutation success is `OK|command=<command>`. Rejections are `ERR|code=<reason>`. `EVENTS` returns committed events in sequence order, one line per record:

`EVENT|sequence=<number>|type=<type>|unit=<name-or-guardian>|pid=<pid-or-0>|detail=<token>`

## Journal

`events.bin` is an append-only native journal. Every record has a magic/version marker, sequence, type, unit, pid, detail, and checksum. Committed records start at sequence 1 with no gaps. The record is durable before a success response is sent. At startup, a checksum failure, incomplete final record, or bytes after the last valid record are treated as a torn tail: truncate back to the valid committed prefix and continue at the next sequence. Corruption inside the committed prefix fails startup rather than discarding history.

The public event types are `guardian-start`, `unit-starting`, `unit-ready`, `unit-exit`, `unit-restart`, `unit-stopping`, `unit-stopped`, `unit-failed`, `unit-blocked`, `reload-accepted`, `reload-rejected`, and `guardian-stop`.

## Worker fixture

`guardian-worker` is part of the submitted native source and exists for runtime checks. It accepts `--name`, `--ready-file`, `--ready-gate-file`, `--term-file`, `--spawn-child-file`, `--exit-code`, and `--crash-count-file` options. A ready gate delays readiness until that path exists. It writes its pid to the ready file immediately before signaling readiness. With a spawn-child file it creates a same-process-group descendant and records that pid; during termination the parent remains until that descendant is gone. On `SIGTERM` it writes the term file. A crash-count file causes the requested number of early unsuccessful exits before steady operation.
