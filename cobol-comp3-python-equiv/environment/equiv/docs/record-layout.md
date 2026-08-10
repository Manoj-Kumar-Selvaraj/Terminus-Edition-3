# Warehouse SKU tape layout

Public evaluator: `/app/equiv/bin/equiv-eval`

Default inputs:

- layout `/app/equiv/programs/skumast.layout`
- records `/app/equiv/samples/sku-public.dat`
- output `/app/equiv/out/equivalence-report.json`

Flags: `--layout PATH --records PATH --out PATH`. Unknown flags exit 2 without writing output. Offline only.

## Storage rules

COMP-3 (packed decimal):

- Digit count is the number of `9`s in the PIC (include digits after `V`).
- Byte length is `ceil((digits + 1) / 2)`.
- Digits are stored as nibbles, high nibble first, padded on the left with zero nibbles.
- The final nibble is the sign: `C` positive signed, `D` negative signed, `F` unsigned. Other sign nibbles are a record error.
- Digit nibbles must be 0–9.
- Implied decimal: `V` marks the scale. The reported number is `integer_digits * 10^(-scale)` as a decimal string that preserves scale (for example `1234.56`, `-1234.56`, `12.500`).

Display:

- `PIC X(n)` is `n` bytes, left-justified, space padded.
- `PIC 9(n)` display is `n` ASCII digits, right-justified, zero padded. The JSON value is an integer.

REDEFINES: the redefining field occupies the same bytes as the named target. It does not advance the record offset.

OCCURS DEPENDING ON `NAME` from `min` to `max`: read `NAME` first as the actual count. Emit exactly that many occurrences. Record byte length is the fixed prefix plus `count * occurrence_size`. `count` outside `min..max` is a record error. Do not consume the max occurrence span when `count` is smaller.

Records are concatenated with no RDW. After each record, the next record starts at the computed byte length.

## Public sample (first record)

`SKU-CODE` = `SKU-00000001`, `QOH` = `1234.56`, `UNIT-COST` = `12.500`, `STATUS-BYTE` = `A`, `ACTIVE-FLAG` = `A`, `REORDER-PT` = `25`, `BIN-COUNT` = `1`, one bin `W001` / `12` / `A10   ` / `5`.

Second public record is negative `QOH` `-42.10` with `BIN-COUNT` `0`.

## Report schema

`/app/equiv/out/equivalence-report.json`:

```json
{
  "layout_id": "SKU-REC",
  "source_records": "/app/equiv/samples/sku-public.dat",
  "records": [
    {
      "index": 0,
      "byte_length": 44,
      "error": null,
      "fields": {
        "SKU-CODE": "SKU-00000001",
        "QOH": "1234.56",
        "UNIT-COST": "12.500",
        "STATUS-BYTE": "A",
        "ACTIVE-FLAG": "A",
        "REORDER-PT": "25",
        "BIN-COUNT": 1,
        "BIN-ENTRY": [
          {"WHSE": "W001", "AISLE": 12, "SLOT": "A10   ", "QTY-IN-BIN": "5"}
        ]
      }
    }
  ],
  "summary": {
    "record_count": 2,
    "error_count": 0,
    "comp3_signed_ok": true,
    "odo_lengths_ok": true,
    "redefines_ok": true
  }
}
```

`records` stay in tape order. `error` is a string or null. Failed records still include `byte_length` when it can be determined, otherwise `byte_length` is 0. `summary.comp3_signed_ok` is false if any packed field used a wrong sign or dropped the minus. `odo_lengths_ok` is false if any record consumed the max OCCURS span instead of the depending-on count. `redefines_ok` is false if REDEFINES fields were unpacked from a later offset than their target. `QTY-IN-BIN` and other integer COMP-3 values are decimal strings without a trailing `.0` when scale is 0 (`"5"`, `"-3"`).
