# Oracle solution

`solve.sh` installs the fixed Java worker sources and rebuilds the plane:

```bash
/solution/fixed/worker/src/main/java/com/example/pii/WorkerMain.java
/solution/fixed/worker/src/main/java/com/example/pii/ScannerEngine.java
/solution/fixed/worker/src/main/java/com/example/pii/policy/ScanPolicy.java
/solution/fixed/worker/src/main/java/com/example/pii/text/UnicodeChunker.java
```

Copied into `/app/enterprise-pii/worker/src/main/java/com/example/pii/` (mirroring package layout), then `/app/enterprise-pii/scripts/build.sh` runs.

Policy digest for the shipped `config/policy.json` is `50f9892748a268044a4df998f128c523643f457847340ed599de6294fb317dfc` (Go `CanonicalPolicyDigest`).
