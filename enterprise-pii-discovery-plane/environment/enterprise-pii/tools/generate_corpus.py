#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

DEPARTMENTS = ("hr", "finance", "legal", "support", "sales", "engineering", "vendor")
REGIONS = ("na", "eu", "apac")
FIRST_NAMES = ("Avery", "Blake", "Casey", "Devon", "Emery", "Frankie", "Harper", "Indigo", "Jordan", "Kai", "Logan", "Morgan")
LAST_NAMES = ("Arbor", "Beacon", "Cedar", "Delta", "Elm", "Fable", "Grove", "Harbor", "Ivory", "Juniper", "Keystone", "Lumen")
STREETS = ("Atlas Street", "Binary Road", "Circuit Avenue", "Data Lane", "Engine Boulevard", "Fresco Street")
FORMATS = ("csv", "json", "ndjson", "xml", "properties", "email", "text", "zip")


@dataclass(frozen=True)
class Persona:
    index: int
    employee_id: str
    department: str
    region: str
    full_name: str
    email: str
    phone: str
    ssn: str
    card: str
    iban: str
    passport: str
    tax_id: str
    dob: str
    address: str
    clean_note: str


def digits(seed: str, count: int) -> str:
    output = ""
    round_number = 0
    while len(output) < count:
        digest = hashlib.sha256(f"{seed}:{round_number}".encode()).digest()
        output += "".join(str(byte % 10) for byte in digest)
        round_number += 1
    return output[:count]


def luhn(prefix: str, length: int = 16) -> str:
    body = (prefix + digits(prefix, length))[: length - 1]
    for check in range(10):
        value = body + str(check)
        total = 0
        double_digit = False
        for character in reversed(value):
            digit = int(character)
            if double_digit:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
            double_digit = not double_digit
        if total % 10 == 0:
            return value
    raise AssertionError("check digit not found")


def iban(country: str, account: str) -> str:
    provisional = country + "00" + account
    rearranged = account + country + "00"
    numeric = "".join(str(ord(character) - 55) if character.isalpha() else character for character in rearranged)
    check = 98 - int(numeric) % 97
    return provisional[:2] + f"{check:02d}" + provisional[4:]


def persona(index: int) -> Persona:
    department = DEPARTMENTS[index % len(DEPARTMENTS)]
    region = REGIONS[(index // len(DEPARTMENTS)) % len(REGIONS)]
    first = FIRST_NAMES[index % len(FIRST_NAMES)]
    last = LAST_NAMES[(index * 5 + 3) % len(LAST_NAMES)]
    serial = digits(f"ssn:{index}", 4)
    group = f"{index % 98 + 1:02d}"
    area = f"{index % 665 + 1:03d}"
    account = "WEST" + digits(f"iban:{index}", 14)
    birthday = date(1960, 1, 1) + timedelta(days=(index * 97) % 16000)
    return Persona(
        index=index,
        employee_id=f"SYN-{index:06d}",
        department=department,
        region=region,
        full_name=f"{first} {last}",
        email=f"synthetic.{index:06d}@example.invalid",
        phone=f"+1 202 555 {index % 10000:04d}" if region == "na" else f"+44 20 7946 {index % 10000:04d}",
        ssn=f"{area}-{group}-{serial}",
        card=luhn("4" + digits(f"card:{index}", 5)),
        iban=iban("GB", account),
        passport=f"P{digits(f'passport:{index}', 8)}",
        tax_id=f"TIN-{digits(f'tax:{index}', 9)}",
        dob=birthday.isoformat(),
        address=f"{index % 9999 + 1} {STREETS[index % len(STREETS)]}",
        clean_note=f"Synthetic control record {index}; no external identity is represented.",
    )


def exposed(person: Persona) -> dict[str, str]:
    mode = person.index % 12
    row = {
        "record_id": person.employee_id,
        "department": person.department,
        "region": person.region,
        "note": person.clean_note,
    }
    if mode == 0:
        row.update(email=person.email, full_name=person.full_name)
    elif mode == 1:
        row.update(phone=person.phone, address=person.address)
    elif mode == 2:
        row.update(ssn_label="social security number", ssn=person.ssn)
    elif mode == 3:
        row.update(card_label="payment card", card=person.card)
    elif mode == 4:
        row.update(iban_label="iban", iban=person.iban)
    elif mode == 5:
        row.update(passport_label="passport", passport=person.passport)
    elif mode == 6:
        row.update(tax_label="tax identification", tax_id=person.tax_id)
    elif mode == 7:
        row.update(dob_label="date of birth", dob=person.dob)
    elif mode == 8:
        row.update(address_label="mailing address", address=person.address)
    elif mode == 9:
        row.update(contact_name=person.full_name, email=person.email)
    elif mode == 10:
        row.update(invalid_card=person.card[:-1] + str((int(person.card[-1]) + 1) % 10), example="placeholder sample")
    else:
        row.update(control="clean", project=f"PROJECT-{person.index % 300:03d}")
    return row


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    keys = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text(json.dumps({"records": rows}, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def write_ndjson(path: Path, rows: list[dict[str, str]], malformed: bool) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for offset, row in enumerate(rows):
            output.write(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
            if malformed and offset == len(rows) // 2:
                output.write('{"synthetic_malformed":\n')


def write_xml(path: Path, rows: list[dict[str, str]]) -> None:
    def escape(value: str) -> str:
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    lines = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>", "<synthetic-records>"]
    for row in rows:
        lines.append(f"  <record id=\"{escape(row['record_id'])}\">")
        for key in sorted(row):
            if key != "record_id":
                lines.append(f"    <{key}>{escape(row[key])}</{key}>")
        lines.append("  </record>")
    lines.append("</synthetic-records>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_properties(path: Path, rows: list[dict[str, str]]) -> None:
    lines: list[str] = []
    for row in rows:
        prefix = row["record_id"].lower().replace("-", ".")
        for key in sorted(row):
            value = row[key].replace("\\", "\\\\").replace("\n", "\\n").replace("=", "\\=")
            lines.append(f"{prefix}.{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_email(path: Path, rows: list[dict[str, str]]) -> None:
    body = "\n".join("; ".join(f"{key}: {row[key]}" for key in sorted(row)) for row in rows)
    message = (
        "From: synthetic-sender@example.invalid\n"
        "To: synthetic-receiver@example.invalid\n"
        "Subject: Generated corporate records\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "Content-Transfer-Encoding: 8bit\n\n"
        + body
        + "\n"
    )
    path.write_text(message, encoding="utf-8")


def write_text(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text("\n".join(" | ".join(f"{key}={row[key]}" for key in sorted(row)) for row in rows) + "\n", encoding="utf-8")


def write_zip(path: Path, rows: list[dict[str, str]]) -> None:
    payload = "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows) + "\n"
    email = "From: archive@example.invalid\nTo: review@example.invalid\nSubject: Synthetic archive\n\n" + payload
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        info = zipfile.ZipInfo("records/records.ndjson", date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, payload.encode())
        info = zipfile.ZipInfo("mail/summary.eml", date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, email.encode())


WRITERS = {
    "csv": write_csv,
    "json": write_json,
    "xml": write_xml,
    "properties": write_properties,
    "email": write_email,
    "text": write_text,
    "zip": write_zip,
}


def extension(format_name: str) -> str:
    return {"email": "eml", "text": "txt"}.get(format_name, format_name)


def build(output: Path, count: int) -> None:
    if count != 12000:
        raise SystemExit("this corpus contract requires exactly 12000 records")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for index in range(count):
        person = persona(index)
        format_name = FORMATS[index % len(FORMATS)]
        grouped.setdefault((person.department, person.region, format_name), []).append(exposed(person))
    files: list[dict[str, object]] = []
    for (department, region, format_name), rows in sorted(grouped.items()):
        directory = output / department / region
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"synthetic-records.{extension(format_name)}"
        if format_name == "ndjson":
            write_ndjson(path, rows, malformed=(department == "support" and region == "na"))
        else:
            WRITERS[format_name](path, rows)
        body = path.read_bytes()
        files.append({"path": path.relative_to(output).as_posix(), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
    manifest = {
        "schema": "enterprise-pii-synthetic-corpus/v1",
        "records": count,
        "synthetic_only": True,
        "seed": "enterprise-pii-corpus-v1",
        "departments": list(DEPARTMENTS),
        "regions": list(REGIONS),
        "formats": list(FORMATS),
        "files": files,
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    manifest["digest"] = hashlib.sha256(canonical.encode()).hexdigest()
    (output / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic enterprise records")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--records", type=int, default=12000)
    arguments = parser.parse_args()
    build(arguments.output, arguments.records)


if __name__ == "__main__":
    main()