# Incident timeline (noisy)

- 09:40 UTC — Jenkins shadow still primary writer in runtime inspect.
- 10:12 UTC — Alias shift to generation 2 returned transport error after control plane commit.
- 10:18 UTC — Resume of batch `B-441` re-entered `intake` and duplicated partner notify.
- 10:25 UTC — Poison item `I-poison` landed in ledger despite validate failures.
- 10:31 UTC — Second owner attempted the same batch lock while first execution was `RETRY_PENDING`.

Operator notes elsewhere under `/app/evidence` are incomplete; trust the contract and runtime inspect over console lore.
