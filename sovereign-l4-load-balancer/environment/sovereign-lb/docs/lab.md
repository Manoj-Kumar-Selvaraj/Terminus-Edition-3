# Loopback lab

The lab starts five deterministic TCP backend behaviors on `127.0.0.1`: echo on port 19001, slow reader on 19002, half-close on 19003, reset on 19004, and PROXY protocol v2 inspection on 19005. It writes bounded event summaries under `/app/sovereign-lb/state/lab`.

Echo returns each received byte. Slow reader consumes fixed-size chunks at a configured interval and then echoes them, exercising bounded client-to-target buffering. Half-close sends a fixed greeting, shuts down its write side, and continues reading until client EOF. Reset configures abortive close. The inspector requires one valid PROXY v2 header, records its family and declared addresses, then echoes remaining payload.

`/app/sovereign-lb/bin/lab start` runs all backends in the foreground. `list` prints the deterministic endpoint map as JSON. No lab command modifies routes, firewall rules, DNS, or non-loopback interfaces.

The fleet fixture contains 24 nodes, eight per zone, with deterministic IDs, control/status ports, session seeds, and state directories. It is inventory input, not thousands of generated runtime records. Operators may run a smaller subset while preserving node and zone identity.