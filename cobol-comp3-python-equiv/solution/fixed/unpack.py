from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from src.layout import Layout, Odo, Pic


def comp3_len(digits: int) -> int:
    return (digits + 2) // 2


def unpack_comp3(data: bytes, digits: int, scale: int, signed: bool) -> str:
    need = comp3_len(digits)
    if len(data) != need:
        raise ValueError("comp3 length")
    nibbles: list[int] = []
    for byte in data:
        nibbles.append((byte >> 4) & 0xF)
        nibbles.append(byte & 0xF)
    sign = nibbles[-1]
    digits_n = nibbles[:-1]
    if len(digits_n) < digits:
        digits_n = [0] * (digits - len(digits_n)) + digits_n
    else:
        digits_n = digits_n[-digits:]
    if any(nibble > 9 for nibble in digits_n):
        raise ValueError("comp3 digit")
    if sign == 0xD:
        negative = True
    elif sign in (0xC, 0xF):
        negative = False
    else:
        raise ValueError("comp3 sign")
    integer = 0
    for nibble in digits_n:
        integer = integer * 10 + nibble
    if negative:
        integer = -integer
    value = Decimal(integer).scaleb(-scale)
    if scale == 0:
        return str(int(value))
    quant = Decimal(10) ** -scale
    text = format(value.quantize(quant), "f")
    if "." in text:
        whole, frac = text.split(".", 1)
        frac = frac[:scale].ljust(scale, "0")
        return f"{whole}.{frac}"
    return f"{text}." + ("0" * scale)


def pack_comp3(value: str | int | Decimal, digits: int, scale: int, signed: bool) -> bytes:
    quant = Decimal(10) ** -scale
    number = Decimal(str(value)).quantize(quant)
    negative = number < 0
    scaled = int((abs(number) * (Decimal(10) ** scale)).to_integral_value(rounding=ROUND_DOWN))
    render = f"{scaled:0{digits}d}"
    if len(render) > digits:
        raise ValueError("overflow")
    if signed:
        sign = 0xD if negative else 0xC
    else:
        if negative:
            raise ValueError("unsigned negative")
        sign = 0xF
    nibbles = [int(ch) for ch in render]
    total = comp3_len(digits) * 2
    pad = total - 1 - len(nibbles)
    nibbles = [0] * pad + nibbles + [sign]
    out = bytearray()
    for index in range(0, len(nibbles), 2):
        out.append((nibbles[index] << 4) | nibbles[index + 1])
    return bytes(out)


def field_size(pic: Pic) -> int:
    if pic.comp3:
        return comp3_len(pic.length)
    return pic.length


def unpack_record(layout: Layout, blob: bytes, offset: int) -> tuple[dict, int, str | None]:
    cursor = offset
    fields: dict = {}
    starts: dict[str, int] = {}
    try:
        for item in layout.fields:
            if isinstance(item, Pic):
                size = field_size(item)
                if item.redefines:
                    start = starts[item.redefines]
                    chunk = blob[start : start + size]
                else:
                    if cursor + size > len(blob):
                        raise ValueError("truncated")
                    starts[item.name] = cursor
                    chunk = blob[cursor : cursor + size]
                    cursor += size
                if item.comp3:
                    fields[item.name] = unpack_comp3(chunk, item.length, item.scale, item.signed)
                elif item.kind == "x":
                    fields[item.name] = chunk.decode("ascii")
                else:
                    fields[item.name] = int(chunk.decode("ascii"))
            else:
                count = int(fields[item.depending_on])
                if count < item.minimum or count > item.maximum:
                    raise ValueError("odo count")
                entries = []
                for _ in range(count):
                    entry = {}
                    for pic in item.fields:
                        size = field_size(pic)
                        if cursor + size > len(blob):
                            raise ValueError("truncated odo")
                        chunk = blob[cursor : cursor + size]
                        cursor += size
                        if pic.comp3:
                            entry[pic.name] = unpack_comp3(
                                chunk, pic.length, pic.scale, pic.signed
                            )
                        elif pic.kind == "x":
                            entry[pic.name] = chunk.decode("ascii")
                        else:
                            entry[pic.name] = int(chunk.decode("ascii"))
                    entries.append(entry)
                fields[item.name] = entries
        return fields, cursor - offset, None
    except Exception as exc:  # noqa: BLE001
        return fields, max(cursor - offset, 0), str(exc)
