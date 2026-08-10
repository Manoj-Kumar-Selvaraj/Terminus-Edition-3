from __future__ import annotations

from src.layout import Layout, Odo, Pic
from src.unpack import unpack_record


def _looks_packed_value(value: object, scale: int) -> bool:
    if not isinstance(value, str) or not value:
        return False
    # Starter hex dumps are [0-9a-f]+ with even length and no sign/decimal form.
    if all(ch in "0123456789abcdef" for ch in value) and "." not in value and "-" not in value:
        if len(value) >= 2 and len(value) % 2 == 0 and any(ch.isalpha() for ch in value):
            return False
    try:
        if scale == 0:
            int(value)
            return True
        if "." not in value:
            return False
        whole, frac = value.split(".", 1)
        if not frac or len(frac) != scale:
            return False
        int(whole)
        int(frac)
        return True
    except ValueError:
        return False


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
            signed_ok = False
            break

        if error:
            lowered = error.lower()
            if "sign" in lowered or "comp3" in lowered or "digit" in lowered:
                signed_ok = False
            if "odo" in lowered:
                odo_ok = False

        for item in layout.fields:
            if isinstance(item, Pic) and item.comp3:
                if not _looks_packed_value(fields.get(item.name), item.scale):
                    signed_ok = False
            elif isinstance(item, Odo):
                depending = fields.get(item.depending_on)
                entries = fields.get(item.name)
                if not isinstance(entries, list) or depending is None:
                    odo_ok = False
                else:
                    try:
                        if len(entries) != int(depending):
                            odo_ok = False
                    except (TypeError, ValueError):
                        odo_ok = False
                for pic in item.fields:
                    if not pic.comp3:
                        continue
                    for entry in entries or []:
                        if not _looks_packed_value(entry.get(pic.name), pic.scale):
                            signed_ok = False

        if fields.get("STATUS-BYTE") != fields.get("ACTIVE-FLAG"):
            redef_ok = False

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
