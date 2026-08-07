# Freight triage — layout

Companion to `/app/environment/docs/requirements.md`. Paths and how to drive
the suite locally; schemas and protocol rules are in that document.

## Layout

```
/app/environment/native      C++17 ledger engine        -> build/freightctl
/app/environment/intake      Java 17 intake HTTP API    -> build/classes
/app/environment/reconcile   Go reconciler              -> build/reconcile
/app/environment/data        normative registries, manifests, intake events
/app/environment/docs        requirements.md and this file
/app/bin                     run-freight-suite and thin CLI wrappers
/app/output                  generated artifacts
```

## Building by hand

```
make -C /app/environment/native -j"$(nproc)"
/app/environment/intake/build.sh
(cd /app/environment/reconcile && go build -o build/reconcile ./cmd/reconcile)
```

## Running stages individually

```
freightctl ledger --root /app --out /app/output/ledger-snapshot.json
freightctl inspect --manifest /app/environment/data/manifests/manifest-000.json
freightctl selftest --out /app/output/selftest-cpp.json

freight-intake replay --root /app --out /app/output/intake-journal.json
freight-intake serve --port 8088          # manual poking with curl
freight-intake selftest --out /app/output/selftest-java.json

freight-reconcile run --root /app
freight-reconcile selftest --out /app/output/selftest-go.json
```

## Whole pipeline

```
run-freight-suite --root /app
run-freight-suite --root /app --skip-build     # reuse existing binaries
```

## Field reports from the freight desk

* Dock supervisors say tonnage on single slot lanes is being over committed and
  the slot numbers printed on the audit sheet start at zero, which no dock uses.
* Night shift in Kathmandu (+05:45) and Chicago (-05:00) report their holds land
  in the wrong six hour window.
* Finance reports held tonnage looks doubled for manifests that were held once.
* The audit sheet has an unstable column order and imports as one column on
  Linux tooling.
* The reconciler flags seal digest mismatches on manifests that were never
  touched, and the recomputed ledger and journal digests never match the ones
  the producers publish.
* One of the shared algorithm families disagrees between languages; the selftest
  reports name the algorithm.

Toolchain is offline. There is no package manager access and no network.
