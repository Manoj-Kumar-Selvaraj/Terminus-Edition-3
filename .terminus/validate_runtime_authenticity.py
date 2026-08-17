#!/usr/bin/env python3
"""Validate production-authenticity evidence for stateful large-system tasks.

This gate complements validate_task_complexity.py. The complexity gate proves scale,
causal coupling and test-map honesty; this gate rejects toy business logic, toy seed
state and synthetic operational presentation.

State-volume and current-state evidence are conditional under the governing policy:
current-state/incident artifacts are required only when the task asserts inherited
current-state facts, and a strict data-volume floor may be replaced by an explicit
controller-approved domain-specific exemption when business-record seeding would be
unrealistic for the system being modeled.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRICT_PROFILE = "large_system_strict"

SYNTHETIC_README_PHRASES = (
    "cut-down",
    "used to reproduce a",
    "benchmark fixture",
    "benchmark task",
    "this package is a",
)

COBOL_FEATURE_PATTERNS = {
    "PERFORM": re.compile(r"(?im)^\s*PERFORM\b"),
    "EVALUATE": re.compile(r"(?im)^\s*EVALUATE\b"),
    "88_LEVEL": re.compile(r"(?im)^\s*88\s+\S+"),
    "COMPUTE": re.compile(r"(?im)^\s*COMPUTE\b"),
    "UNSTRING": re.compile(r"(?im)^\s*UNSTRING\b"),
    "FUNCTION": re.compile(r"(?i)\bFUNCTION\s+[A-Z0-9-]+"),
    "INSPECT": re.compile(r"(?im)^\s*INSPECT\b"),
    "STRING": re.compile(r"(?im)^\s*STRING\b"),
    "SEARCH": re.compile(r"(?im)^\s*SEARCH\b"),
    "OCCURS": re.compile(r"(?i)\bOCCURS\b"),
}

DIVISION_OR_SECTION = {
    "IDENTIFICATION DIVISION.",
    "ENVIRONMENT DIVISION.",
    "DATA DIVISION.",
    "PROCEDURE DIVISION.",
    "WORKING-STORAGE SECTION.",
    "FILE SECTION.",
    "LINKAGE SECTION.",
}


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path, name: str) -> dict:
    if not path.is_file():
        die(f"missing {name}: {path.relative_to(ROOT)}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"invalid {name}: {exc}")
    if not isinstance(data, dict):
        die(f"{name} must be an object")
    return data


def cobol_substantive_lines(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*>") or stripped.startswith("*"):
            continue
        count += 1
    return count


def cobol_metrics(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    decisions = 0
    paragraphs = 0
    for line in text.splitlines():
        upper = line.strip().upper()
        if re.match(r"^(IF|EVALUATE|WHEN|PERFORM|COMPUTE|INSPECT|SEARCH)\b", upper):
            decisions += 1
        if re.fullmatch(r"[A-Z0-9][A-Z0-9-]+\.", upper) and upper not in DIVISION_OR_SECTION:
            paragraphs += 1
    features = {name for name, pattern in COBOL_FEATURE_PATTERNS.items() if pattern.search(text)}
    return {
        "loc": cobol_substantive_lines(text),
        "decisions": decisions,
        "paragraphs": paragraphs,
        "features": features,
    }


def validate_cobol(task_dir: Path, cfg: dict, errors: list[str]) -> dict[str, object]:
    directory = task_dir / str(cfg.get("directory", "environment/eod/cobol"))
    if not directory.is_dir():
        errors.append(f"COBOL authenticity directory missing: {directory.relative_to(task_dir)}")
        return {}
    programs = sorted([*directory.glob("*.cob"), *directory.glob("*.cbl")])
    minimum_programs = int(cfg.get("min_programs", 1))
    min_loc = int(cfg.get("min_substantive_lines_per_program", 1))
    min_decisions = int(cfg.get("min_decision_points_per_program", 1))
    min_paragraphs = int(cfg.get("min_paragraphs_per_program", 1))
    min_features = int(cfg.get("min_portfolio_syntax_features", 1))
    if len(programs) < minimum_programs:
        errors.append(f"COBOL program count {len(programs)} is below required {minimum_programs}")
    portfolio_features: set[str] = set()
    detail: dict[str, dict[str, object]] = {}
    for program in programs:
        metrics = cobol_metrics(program)
        detail[program.name] = metrics
        portfolio_features.update(metrics["features"])
        if int(metrics["loc"]) < min_loc:
            errors.append(
                f"{program.relative_to(task_dir)} has only {metrics['loc']} substantive lines; "
                f"minimum is {min_loc}. Thin wrapper/micro-program logic is not production-authentic."
            )
        if int(metrics["decisions"]) < min_decisions:
            errors.append(
                f"{program.relative_to(task_dir)} has only {metrics['decisions']} decision/processing points; "
                f"minimum is {min_decisions}. A large file around one IF/EVALUATE does not count."
            )
        if int(metrics["paragraphs"]) < min_paragraphs:
            errors.append(
                f"{program.relative_to(task_dir)} has only {metrics['paragraphs']} procedure paragraphs; "
                f"minimum is {min_paragraphs}."
            )
        if int(metrics["loc"]) >= min_loc and int(metrics["decisions"]) / max(int(metrics["loc"]), 1) < 0.06:
            errors.append(
                f"{program.relative_to(task_dir)} has low executable decision density; "
                "inspect for LOC padding around trivial business logic."
            )
    if len(portfolio_features) < min_features:
        errors.append(
            f"COBOL portfolio uses only {len(portfolio_features)} substantive syntax families "
            f"({', '.join(sorted(portfolio_features))}); require at least {min_features}"
        )
    return {
        "program_count": len(programs),
        "portfolio_features": sorted(portfolio_features),
        "programs": detail,
    }


def validate_incident_evidence(
    task_dir: Path,
    cfg: dict,
    instruction: str,
    readme: str,
    errors: list[str],
) -> dict[str, object]:
    evidence = cfg.get("incident_evidence", [])
    if not isinstance(evidence, list) or len(evidence) < 2:
        errors.append("production_authenticity.incident_evidence must name at least two solver-visible artifacts")
        evidence = []
    suffixes: set[str] = set()
    existing: list[str] = []
    for rel in evidence:
        path = task_dir / str(rel)
        if not path.is_file():
            errors.append(f"incident evidence missing: {rel}")
            continue
        existing.append(str(rel))
        suffixes.add(path.suffix.lower())
        if path.stat().st_size < 80:
            errors.append(f"incident evidence is too small to be meaningful: {rel}")
    if evidence and ".log" not in suffixes:
        errors.append("operational incident profile requires at least one solver-visible .log artifact")
    if evidence and len(suffixes) < 2:
        errors.append(
            "incident evidence must include more than one artifact type "
            "(for example log + handoff/state note)"
        )
    instruction_paths = cfg.get("instruction_evidence_paths", [])
    if not isinstance(instruction_paths, list) or not instruction_paths:
        errors.append("production_authenticity.instruction_evidence_paths must be declared")
        instruction_paths = []
    for path in instruction_paths:
        if str(path) not in instruction:
            errors.append(f"instruction does not point the maintainer to incident evidence path {path}")
    lower_readme = readme.lower()
    for phrase in SYNTHETIC_README_PHRASES:
        if phrase in lower_readme:
            errors.append(
                f"README contains benchmark/fixture framing {phrase!r}; "
                "production profile must orient to the inherited system"
            )
    return {"evidence_files": existing, "evidence_types": sorted(suffixes)}


def validate_stateful_dataset_exemption(cfg: dict, errors: list[str]) -> dict[str, str]:
    exemption = cfg.get("stateful_dataset_exemption")
    if not isinstance(exemption, dict) or exemption.get("approved") is not True:
        errors.append(
            "strict production profile without a stateful_dataset requires an explicit approved stateful_dataset_exemption"
        )
        return {}
    approved_by = str(exemption.get("approved_by", "")).strip()
    reason = str(exemption.get("reason", "")).strip()
    if not approved_by or not reason:
        errors.append("stateful_dataset_exemption requires approved_by and a domain-specific reason")
        return {}
    if len(reason) < 80:
        errors.append("stateful_dataset_exemption reason is too short to establish a domain-specific rationale")
        return {}
    return {"approved_by": approved_by, "reason": reason}


def _query_scalar(con: sqlite3.Connection, sql: str) -> int:
    row = con.execute(sql).fetchone()
    return int(row[0] if row and row[0] is not None else 0)


def _validate_record_bounds(cfg: dict, strict: bool, errors: list[str]) -> tuple[int, int]:
    min_records = int(cfg.get("min_records", 0))
    max_records = int(cfg.get("max_records", 0))
    if strict and min_records < 10000:
        errors.append(
            f"strict stateful production profile min_records={min_records}; require at least 10000"
        )
    if strict and (max_records < min_records or max_records > 20000):
        errors.append(
            f"strict stateful production profile max_records={max_records}; require min<=max<=20000"
        )
    return min_records, max_records


def _generic_variance_metrics(
    con: sqlite3.Connection,
    cfg: dict,
    errors: list[str],
) -> tuple[dict[str, int], dict[str, tuple[int, int | None]]]:
    raw = cfg.get("variance_queries")
    if not isinstance(raw, dict) or not raw:
        return {}, {}
    metrics: dict[str, int] = {}
    checks: dict[str, tuple[int, int | None]] = {}
    for name, specification in raw.items():
        metric_name = str(name)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", metric_name):
            errors.append(f"invalid stateful variance metric name: {metric_name!r}")
            continue
        if not isinstance(specification, dict):
            errors.append(f"variance query {metric_name!r} must be an object")
            continue
        sql = str(specification.get("sql", "")).strip()
        if not sql:
            errors.append(f"variance query {metric_name!r} has no SQL")
            continue
        if ";" in sql.rstrip(";"):
            errors.append(f"variance query {metric_name!r} must contain one read-only scalar statement")
            continue
        if not re.match(r"(?is)^\s*(SELECT|WITH)\b", sql):
            errors.append(f"variance query {metric_name!r} must be a SELECT/WITH scalar query")
            continue
        try:
            metrics[metric_name] = _query_scalar(con, sql)
        except sqlite3.Error as exc:
            errors.append(f"variance query {metric_name!r} failed: {exc}")
            continue
        minimum = int(specification.get("min", 1))
        maximum_raw = specification.get("max")
        maximum = None if maximum_raw is None else int(maximum_raw)
        checks[metric_name] = (minimum, maximum)
    return metrics, checks


def _legacy_payment_metrics(
    con: sqlite3.Connection,
    table: str,
    cfg: dict,
) -> tuple[dict[str, int], dict[str, tuple[int, int | None]]]:
    metrics = {
        "cycles": _query_scalar(con, f"SELECT COUNT(DISTINCT cycle_id) FROM {table}"),
        "payers": _query_scalar(con, f"SELECT COUNT(DISTINCT payer_account) FROM {table}"),
        "amounts": _query_scalar(con, f"SELECT COUNT(DISTINCT amount_cents) FROM {table}"),
        "purposes": _query_scalar(con, f"SELECT COUNT(DISTINCT purpose) FROM {table}"),
        "currencies": _query_scalar(con, f"SELECT COUNT(DISTINCT currency) FROM {table}"),
        "routes": _query_scalar(
            con,
            f"SELECT COUNT(DISTINCT CASE WHEN beneficiary_account IS NULL "
            f"THEN 'EXTERNAL' ELSE 'INTERNAL' END) FROM {table}",
        ),
        "account_statuses": _query_scalar(con, "SELECT COUNT(DISTINCT status) FROM accounts"),
    }
    checks = {
        "cycles": (int(cfg.get("min_distinct_cycles", 1)), None),
        "payers": (int(cfg.get("min_distinct_payers", 1)), None),
        "amounts": (int(cfg.get("min_distinct_amounts", 1)), None),
        "purposes": (int(cfg.get("min_distinct_purposes", 1)), None),
        "currencies": (int(cfg.get("min_distinct_currencies", 1)), None),
        "routes": (int(cfg.get("min_route_variants", 1)), None),
        "account_statuses": (int(cfg.get("min_account_statuses", 1)), None),
    }
    return metrics, checks


def validate_seed_dataset(
    task_dir: Path,
    cfg: dict,
    strict: bool,
    errors: list[str],
) -> dict[str, int]:
    schema_rel = str(cfg.get("schema", ""))
    seed_rel = str(cfg.get("seed", ""))
    schema_path = task_dir / schema_rel
    seed_path = task_dir / seed_rel
    if not schema_path.is_file():
        errors.append(f"seed profile schema missing: {schema_rel}")
        return {}
    if not seed_path.is_file():
        errors.append(f"seed profile seed missing: {seed_rel}")
        return {}
    seed_text = seed_path.read_text(encoding="utf-8")
    if re.search(r"\brandom\s*\(", seed_text, flags=re.IGNORECASE):
        errors.append(
            "seed.sql uses SQLite random(); production seed variance must be deterministic/reproducible"
        )
    table = str(cfg.get("primary_table", "payments"))
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
        errors.append(f"invalid primary seed table name: {table!r}")
        return {}
    min_records, max_records = _validate_record_bounds(cfg, strict, errors)
    con = sqlite3.connect(":memory:")
    metrics: dict[str, int] = {}
    checks: dict[str, tuple[int, int | None]] = {}
    try:
        con.executescript(schema_path.read_text(encoding="utf-8"))
        con.executescript(seed_text)
        metrics["records"] = _query_scalar(con, f'SELECT COUNT(*) FROM "{table}"')
        checks["records"] = (min_records, max_records)
        generic_metrics, generic_checks = _generic_variance_metrics(con, cfg, errors)
        if generic_checks:
            metrics.update(generic_metrics)
            checks.update(generic_checks)
        else:
            legacy_metrics, legacy_checks = _legacy_payment_metrics(con, table, cfg)
            metrics.update(legacy_metrics)
            checks.update(legacy_checks)
        total_rows = 0
        for (name,) in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ):
            total_rows += _query_scalar(con, f'SELECT COUNT(*) FROM "{name}"')
        metrics["database_rows"] = total_rows
    except sqlite3.Error as exc:
        errors.append(f"schema+seed cannot build a deterministic database: {exc}")
        return {}
    finally:
        con.close()
    for key, (minimum, maximum) in checks.items():
        actual = metrics.get(key, 0)
        if actual < minimum:
            errors.append(f"seed {key}={actual} is below required {minimum}")
        if maximum is not None and actual > maximum:
            errors.append(f"seed {key}={actual} exceeds allowed {maximum}")
    return metrics


def validate(task_name: str) -> int:
    task_dir = ROOT / task_name
    if not (task_dir / "task.toml").is_file():
        die(f"task not found: {task_name}")
    manifest = load_json(
        ROOT / ".terminus" / "designs" / f"{task_name}.json",
        "design manifest",
    )
    profile = str(manifest.get("profile", ""))
    strict = profile == STRICT_PROFILE
    companion = ROOT / ".terminus" / "designs" / f"{task_name}-production.json"
    if companion.is_file():
        cfg = load_json(companion, "production-authenticity manifest").get(
            "production_authenticity"
        )
    else:
        cfg = manifest.get("production_authenticity")
    if cfg is None:
        if strict and str(manifest.get("task_kind", "")).lower() in {
            "software",
            "database",
            "operations",
        }:
            print(
                "ERROR: strict stateful/operational task has no production_authenticity profile",
                file=sys.stderr,
            )
            return 1
        print("production_authenticity=not-declared; no runtime-authenticity policy applies")
        return 0
    if not isinstance(cfg, dict):
        die("production_authenticity must be a JSON object")
    errors: list[str] = []
    instruction_path = task_dir / "instruction.md"
    readme_path = task_dir / "README.md"
    instruction = instruction_path.read_text(encoding="utf-8") if instruction_path.is_file() else ""
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""

    current_state_required = cfg.get("current_state_evidence_required", True)
    if not isinstance(current_state_required, bool):
        errors.append("production_authenticity.current_state_evidence_required must be boolean")
        current_state_required = True
    if current_state_required:
        incident = validate_incident_evidence(task_dir, cfg, instruction, readme, errors)
    else:
        incident = {"evidence_files": [], "evidence_types": []}
        if cfg.get("incident_evidence") or cfg.get("instruction_evidence_paths"):
            errors.append(
                "current_state_evidence_required=false cannot also declare incident evidence paths"
            )
        lower_readme = readme.lower()
        for phrase in SYNTHETIC_README_PHRASES:
            if phrase in lower_readme:
                errors.append(
                    f"README contains benchmark/fixture framing {phrase!r}; production profile must orient to the inherited system"
                )

    cobol: dict[str, object] = {}
    if "cobol_depth" in cfg:
        cobol_cfg = cfg.get("cobol_depth")
        if isinstance(cobol_cfg, dict):
            cobol = validate_cobol(task_dir, cobol_cfg, errors)
        else:
            errors.append("production_authenticity.cobol_depth must be an object when declared")

    dataset_cfg = cfg.get("stateful_dataset", {})
    dataset = (
        validate_seed_dataset(task_dir, dataset_cfg, strict, errors)
        if isinstance(dataset_cfg, dict) and dataset_cfg
        else {}
    )
    exemption: dict[str, str] = {}
    if strict and not dataset:
        exemption = validate_stateful_dataset_exemption(cfg, errors)

    print(f"task={task_name} profile={profile} strict={str(strict).lower()}")
    print(f"current_state_evidence_required={str(current_state_required).lower()}")
    if dataset:
        print("seed=" + " ".join(f"{key}={value}" for key, value in sorted(dataset.items())))
    elif exemption:
        print(f"stateful_dataset_exemption=approved by={exemption['approved_by']}")
    if cobol:
        print(
            f"cobol_programs={cobol.get('program_count', 0)} "
            f"syntax_features={','.join(cobol.get('portfolio_features', []))}"
        )
        for name, metrics in sorted(cobol.get("programs", {}).items()):
            print(
                f"  {name}: loc={metrics['loc']} decisions={metrics['decisions']} "
                f"paragraphs={metrics['paragraphs']}"
            )
    print(
        f"incident_evidence={len(incident.get('evidence_files', []))} "
        f"types={','.join(incident.get('evidence_types', []))}"
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            f"production-authenticity gate: FAIL ({len(errors)} finding(s))",
            file=sys.stderr,
        )
        return 1
    print("production-authenticity gate: PASS")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_runtime_authenticity.py TASK", file=sys.stderr)
        return 2
    return validate(sys.argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
