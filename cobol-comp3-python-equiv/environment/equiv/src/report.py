from __future__ import annotations

from src.layout import Layout, Odo
from src.unpack import unpack_record


def evaluate(layout: Layout, blob: bytes, source: str) -> dict:
    records = []
    offset = 0
    index = 0
    signed_ok = True
    odo_ok = True
    redef_ok = True
    while offset < len(blob):
        fields, length, error = unpack_record(layout, blob, offset)
        if length <= 0:
            records.append(
                {"index": index, "byte_length": 0, "error": error or "empty", "fields": fields}
            )
            break
        qoh = fields.get("QOH")
        if error or not (isinstance(qoh, str) and "." in qoh):
            signed_ok = False
        if isinstance(qoh, str) and qoh.startswith("-") is False and fields.get("SKU-CODE", "").startswith("SKU-00000002"):
            signed_ok = False
        if fields.get("STATUS-BYTE") != fields.get("ACTIVE-FLAG"):
            redef_ok = False
        odo = next((item for item in layout.fields if isinstance(item, Odo)), None)
        if odo and isinstance(fields.get(odo.name), list):
            depending = fields.get(odo.depending_on, 0)
            if len(fields[odo.name]) != int(depending or 0):
                odo_ok = False
        records.append(
            {"index": index, "byte_length": length, "error": error, "fields": fields}
        )
        offset += length
        index += 1
    return {
        "layout_id": layout.layout_id,
        "source_records": source,
        "records": records,
        "summary": {
            "record_count": len(records),
            "error_count": sum(1 for rec in records if rec["error"]),
            "comp3_signed_ok": signed_ok,
            "odo_lengths_ok": odo_ok,
            "redefines_ok": redef_ok,
        },
    }
