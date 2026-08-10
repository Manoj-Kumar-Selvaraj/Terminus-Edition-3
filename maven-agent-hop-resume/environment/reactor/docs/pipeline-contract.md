# Reactor pipeline contract

Public operator: `/app/reactor/bin/pipe`

| command | meaning |
| --- | --- |
| `run` | start a new run id from the pipeline at `/app/reactor/src/pipeline.json` |
| `resume` | continue `/app/reactor/var/journal.json` after a crash |
| `status` | print the journal as JSON to stdout |

Unknown commands exit 2 without writing journal or archive.

## Topology

- Module graph and build order: `/app/reactor/src/modules.json`. A module may run only after every declared dependency has a durable result in the same stage.
- Sources live under `/app/reactor/src/<module>/`. Fingerprint is SHA-256 of the sorted relative path plus file bytes for every regular file in that tree.
- Shared libraries live under `/app/reactor/libs/<name>-<version>/manifest.json`. The pipeline `library` pin is exact. Loading any other version is a contract break. Record the resolved `{name, version}` on the journal.
- Agent inventory: `/app/reactor/agents/inventory.json`. Each agent has `id` and `labels`.

Stage kinds and required labels:

| kind | required label |
| --- | --- |
| `scm` | `linux` |
| `maven` | `maven` |
| `docker` | `docker` |

Selecting an agent that lacks the required label is forbidden. The stage must fail closed (`failed`), leave no durable module results, and must not hop forward. `resume` discards any recorded stage or module result whose `agent_id` was illegal for that kind.

## Durability and incremental skip

A stage or module result is durable only when all of:

1. `status` is `ok` or `skipped`
2. the executing agent carried the required label
3. required `unstash` names exist in the journal stash map before the stage body runs

`resume` starts at the first non-durable stage and does not rerun earlier durable stages. Inside a maven stage, skip a module when the loaded library `incremental` flag is true, the module fingerprint matches `/app/reactor/var/fingerprints/<module>.sha256`, and every upstream dependency in this stage was also skipped as unchanged. A rebuilt dependency forces downstream modules to rebuild even if their own fingerprint still matches. Rewrite the fingerprint file after a successful rebuild.

Library `incremental=false` disables skip even when fingerprints match.

## Stash

`stash` copies the current module artifact set under that name. `unstash` must precede any stage that declares it. A docker stage without the named stash fails closed.

## Journal

Path: `/app/reactor/var/journal.json`

```json
{
  "run_id": "b-1842",
  "status": "crashed",
  "library": {"name": "platform-lib", "version": "1.4.2"},
  "completed_stages": ["checkout"],
  "resume_from": "test",
  "stages": {
    "compile": {
      "status": "ok",
      "agent_id": "maven-03",
      "agent_labels": ["linux", "maven"],
      "modules_ok": ["common", "core", "web"],
      "skipped_modules": []
    }
  },
  "stash": {
    "reactor-classes": {"modules": ["common", "core", "web"], "created_stage": "compile"}
  }
}
```

`status` is one of `crashed`, `running`, `success`, `failed`. After a successful resume, `status` is `success`, `resume_from` is null, and `completed_stages` lists every pipeline stage in order. `pipe status` prints this object.

## Archive

Each run writes `/app/reactor/var/archive/<run_id>.log`. Values of pipeline `env` keys whose names end with `_TOKEN`, `_PASSWORD`, or `_SECRET` must not appear in that file. When the loaded library sets `redact_secrets` true, those values are replaced with `***`. The journal may name the keys; it must not store the values.

## Crash evidence

`/app/reactor/log/crash.log` records the failed hop. Resume uses the journal plus this log to decide the restart stage; it does not invent a new run id.
