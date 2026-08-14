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
    encoded_digits = nibbles[:-1]
    pad_count = len(encoded_digits) - digits
    if pad_count not in (0, 1):
        raise ValueError("comp3 length")
    if pad_count and any(nibble != 0 for nibble in encoded_digits[:pad_count]):
        raise ValueError("comp3 pad")

    digits_n = encoded_digits[pad_count:]
    if len(digits_n) != digits or any(nibble > 9 for nibble in digits_n):
        raise ValueError("comp3 digit")

    if signed:
        if sign == 0xD:
            negative = True
        elif sign == 0xC:
            negative = False
        else:
            raise ValueError("comp3 signed sign")
    else:
        if sign != 0xF:
            raise ValueError("comp3 unsigned sign")
        negative = False

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
    scaled = int(
        (abs(number) * (Decimal(10) ** scale)).to_integral_value(rounding=ROUND_DOWN)
    )
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


def _decode_pic(pic: Pic, chunk: bytes) -> object:
    if pic.comp3:
        return unpack_comp3(chunk, pic.length, pic.scale, pic.signed)
    if pic.kind == "x":
        return chunk.decode("ascii")
    return int(chunk.decode("ascii"))


def unpack_record(layout: Layout, blob: bytes, offset: int) -> tuple[dict, int, str | None]:
    cursor = offset
    fields: dict = {}
    starts: dict[str, int] = {}
    first_error: str | None = None

    for item in layout.fields:
        if isinstance(item, Pic):
            size = field_size(item)
            if item.redefines:
                start = starts.get(item.redefines)
                if start is None:
                    return fields, 0, first_error or "redefines target"
                chunk = blob[start : start + size]
                if len(chunk) != size:
                    return fields, 0, first_error or "truncated redefines"
            else:
                if cursor + size > len(blob):
                    return fields, 0, first_error or "truncated"
                starts[item.name] = cursor
                chunk = blob[cursor : cursor + size]
                cursor += size

            try:
                fields[item.name] = _decode_pic(item, chunk)
            except (UnicodeDecodeError, ValueError) as exc:
                if first_error is None:
                    first_error = str(exc)
            continue

        depending = fields.get(item.depending_on)
        if depending is None:
            return fields, 0, first_error or "odo depending-on"
        try:
            count = int(depending)
        except (TypeError, ValueError):
            return fields, 0, first_error or "odo depending-on"
        if count < item.minimum or count > item.maximum:
            return fields, cursor - offset, first_error or "odo count"

        entries = []
        for _ in range(count):
            entry = {}
            for pic in item.fields:
                size = field_size(pic)
                if cursor + size > len(blob):
                    return fields, 0, first_error or "truncated odo"
                chunk = blob[cursor : cursor + size]
                cursor += size
                try:
                    entry[pic.name] = _decode_pic(pic, chunk)
                except (UnicodeDecodeError, ValueError) as exc:
                    if first_error is None:
                        first_error = str(exc)
            entries.append(entry)
        fields[item.name] = entries

    return fields, cursor - offset, first_error
