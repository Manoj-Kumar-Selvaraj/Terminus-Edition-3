from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Pic:
    name: str
    kind: str
    length: int
    scale: int
    signed: bool
    comp3: bool
    redefines: str | None = None


@dataclass
class Odo:
    name: str
    depending_on: str
    minimum: int
    maximum: int
    fields: list[Pic] = field(default_factory=list)


@dataclass
class Layout:
    layout_id: str
    fields: list[Pic | Odo]


def parse_pic(token: str) -> tuple[str, int, int, bool]:
    signed = token.startswith("S")
    body = token[1:] if signed else token
    if body == "X":
        return "x", 1, 0, False
    if body.startswith("X("):
        return "x", int(body[2:-1]), 0, False
    if body == "9":
        return "9", 1, 0, signed
    if not body.startswith("9"):
        raise ValueError(token)
    if "V" in body:
        left, right = body.split("V", 1)
        left_n = int(left[2:-1]) if left.startswith("9(") else left.count("9")
        right_n = int(right[2:-1]) if right.startswith("9(") else right.count("9")
        return "9", left_n + right_n, right_n, signed
    digits = int(body[2:-1]) if body.startswith("9(") else body.count("9")
    return "9", digits, 0, signed


def load_layout(path: str) -> Layout:
    layout_id = "UNKNOWN"
    fields: list[Pic | Odo] = []
    current_odo: Odo | None = None
    pending_redefines: str | None = None
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts[0] == "LAYOUT":
            layout_id = parts[1]
            continue
        if parts[0] == "REDEFINES":
            pending_redefines = parts[2]
            continue
        if parts[0] == "ODO":
            current_odo = Odo(parts[1], parts[2], int(parts[3]), int(parts[4]))
            continue
        if parts[0] == "END-ODO":
            assert current_odo is not None
            fields.append(current_odo)
            current_odo = None
            continue
        if parts[0] == "END":
            break
        if parts[0] != "FIELD":
            raise ValueError(line)
        name = parts[1]
        pic_token = parts[3]
        comp3 = len(parts) > 4 and parts[4] == "COMP-3"
        kind, length, scale, signed = parse_pic(pic_token)
        pic = Pic(name, kind, length, scale, signed, comp3, pending_redefines)
        pending_redefines = None
        if current_odo is not None:
            current_odo.fields.append(pic)
        else:
            fields.append(pic)
    return Layout(layout_id, fields)
