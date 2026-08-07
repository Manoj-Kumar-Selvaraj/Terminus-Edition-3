# Linux service guardian

This is a native Linux process-supervision task. The starter is a sizeable C++ service manager rather than a simulator: it forks and execs real workers, uses Linux event descriptors, owns process groups, exposes a Unix-domain control plane, and keeps a crash-recoverable binary journal.

The hard part is the interaction between readiness, dependency ordering, reload, restart accounting, descendant cleanup, and journal recovery. Fixing only the visible parent process leaves adopted grandchildren behind; rebuilding state during reload can silently grant a crashing service a fresh restart budget.

The verifier rebuilds the submitted source and drives live process trees. It checks socket credentials, pidfd-backed lifecycle events, dependency ordering, restart exhaustion, reload rejection, torn-journal recovery, singleton locking, and shutdown cleanup. The canonical GCC image is used for both compilation and verification.
