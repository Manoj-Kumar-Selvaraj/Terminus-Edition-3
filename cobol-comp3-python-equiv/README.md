# cobol-comp3-python-equiv

Repair a Python unpacker for warehouse SKU tape records: packed COMP-3 with C/D/F signs, REDEFINES, and OCCURS DEPENDING ON. The starter pretty-prints and mishandles signed packed fields plus ODO lengths. No GnuCOBOL runtime is required; the verifier checks decimals and byte lengths against sealed holdouts, malformed packed/ODO cases, and the stable report interface.

## Layout

- `environment/equiv/` — public CLI, layout contract, sample tape, incident notes, broken unpacker
- `solution/` — correct COMP-3 pack/unpack and `solve.sh` which writes the public report
- `tests/` — separate verifier with holdout data plus sign-class, digit, pad, ODO, schema, and failure-boundary checks

Difficulty in `task.toml` is provisional until GPT-5.5 ×5 and Claude Opus 4.8 ×5 are measured.
