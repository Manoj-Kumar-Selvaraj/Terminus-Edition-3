from __future__ import annotations

from src.layout import Layout, Odo, Pic


def unpack_comp3(data: bytes, digits: int, scale: int, signed: bool) -> str:
    # Starter: pretty-print hex and ignore packed sign/scale.
    return data.hex()


def field_size(pic: Pic) -> int:
    if pic.comp3:
        return (pic.length + 2) // 2
    return pic.length


def unpack_record(layout: Layout, blob: bytes, offset: int) -> tuple[dict, int, str | None]:
    cursor = offset
    fields: dict = {}
    try:
        for item in layout.fields:
            if isinstance(item, Pic):
                size = field_size(item)
                chunk = blob[cursor : cursor + size]
                cursor += size
                if item.comp3:
                    fields[item.name] = unpack_comp3(chunk, item.length, item.scale, item.signed)
                elif item.kind == "x":
                    fields[item.name] = chunk.decode("ascii")
                else:
                    fields[item.name] = int(chunk.decode("ascii"))
            else:
                count = item.maximum
                entries = []
                for _ in range(count):
                    entry = {}
                    for pic in item.fields:
                        size = field_size(pic)
                        chunk = blob[cursor : cursor + size]
                        cursor += size
                        if pic.comp3:
                            entry[pic.name] = unpack_comp3(
                                chunk, pic.length, pic.scale, pic.signed
                            )
                        elif pic.kind == "x":
                            entry[pic.name] = chunk.decode("ascii")
                        else:
                            entry[pic.name] = int(chunk.decode("ascii") or "0")
                    entries.append(entry)
                fields[item.name] = entries
        return fields, cursor - offset, None
    except Exception as exc:  # noqa: BLE001
        return fields, max(cursor - offset, 0), str(exc)
