The SKU tape unpacker under `/app/equiv` still pretty-prints hex instead of evaluating packed catalog records. Shift notes `/app/equiv/ops/handoff.md` and `/app/equiv/log/unpack-incident.log`. Binding rules and report schema are `/app/equiv/docs/record-layout.md`.

Drive `/app/equiv/bin/equiv-eval` against `/app/equiv/programs` and `/app/equiv/samples`. Write `/app/equiv/out/equivalence-report.json`. Signed COMP-3 (nibbles C/D/F), REDEFINES, and OCCURS DEPENDING ON must match the layout contract, including record byte lengths. Stay offline — do not call a model API.
