The native supervisor under /app/guardian leaks worker trees after a change to its process-watching code. It also starts some dependents too early, schedules duplicate restarts after reload, and cannot always reopen its journal after an interrupted write. Repair the C++ service rather than replacing it with systemd, a script, or another language.

- Follow /app/guardian/docs/runtime-contract.md for the manifest, control socket, process lifecycle, journal, and security rules. Build with /app/guardian/bin/build-guardian, and keep runtime state under /app/guardian/run.
- Manage unit lifecycle through the required Linux wait path using pidfds and the companion event and timer fds.
- Take a single-owner lock on the state directory. A second guardian must fail without changing the first instance.
- Validate the whole manifest before taking runtime ownership or creating the control socket.
- Supervise the real processes from the supplied manifest. Start dependents only after their providers are ready.
- Preserve dependency and restart state across a valid reload. An invalid reload must leave the running state unchanged and must not schedule duplicate restarts.
- During a unit stop or full shutdown, stop dependents before providers. Send TERM to the process group, wait for the grace period, then use KILL for anything still alive.
- If a unit spends its restart budget, block any dependent that requires it.
- Recover the last committed journal prefix when only the tail is torn. Corruption in committed history must fail closed.
- Serve control requests through the Unix socket and enforce peer credentials.
- Keep the full /app/guardian tree buildable in the separate verifier, including the native sources and the worker fixture named by the contract.
