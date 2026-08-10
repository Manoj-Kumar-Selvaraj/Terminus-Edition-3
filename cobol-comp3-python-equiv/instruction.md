The SKU tape unpacker under `/app/equiv` still pretty-prints hex instead of evaluating packed catalog records. We need signed COMP-3 (nibbles C/D/F), REDEFINES, and OCCURS DEPENDING ON so the Python side matches `/app/equiv/docs/record-layout.md`.

Drive it with `/app/equiv/bin/equiv-eval`. Public programs are `/app/equiv/programs` and samples are `/app/equiv/samples`. Write `/app/equiv/out/equivalence-report.json` using the schema in the layout doc. Stay offline — do not call a model API.
