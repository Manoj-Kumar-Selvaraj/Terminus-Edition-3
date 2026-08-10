#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "solution" / "fixed"))
sys.path.insert(0, str(ROOT / "environment" / "equiv"))

from unpack import pack_comp3  # noqa: E402


def main() -> None:
    rec1 = bytearray()
    rec1 += b"SKU-00000001"
    rec1 += pack_comp3("1234.56", 9, 2, True)
    rec1 += pack_comp3("12.500", 8, 3, True)
    rec1 += b"A"
    rec1 += pack_comp3("25", 5, 0, False)
    rec1 += b"01"
    rec1 += b"W001"
    rec1 += b"012"
    rec1 += b"A10   "
    rec1 += pack_comp3("5", 5, 0, True)

    rec2 = bytearray()
    rec2 += b"SKU-00000002"
    rec2 += pack_comp3("-42.10", 9, 2, True)
    rec2 += pack_comp3("8.000", 8, 3, True)
    rec2 += b"I"
    rec2 += pack_comp3("10", 5, 0, False)
    rec2 += b"00"

    out = ROOT / "environment" / "equiv" / "samples" / "sku-public.dat"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(rec1) + bytes(rec2))
    print(out, out.stat().st_size, len(rec1), len(rec2))


if __name__ == "__main__":
    main()
