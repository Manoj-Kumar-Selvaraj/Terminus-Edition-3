"""Regression tests for production-authenticity gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CONTROL_PLANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE))

import validate_runtime_authenticity as gate  # noqa: E402

TASK = "demo-production-task"


def cobol_program(name: str, *, thin: bool = False) -> str:
    if thin:
        return f'''>SOURCE FORMAT FREE
IDENTIFICATION DIVISION.
PROGRAM-ID. {name.upper()}.
DATA DIVISION.
WORKING-STORAGE SECTION.
01 IN-LINE PIC X(80).
PROCEDURE DIVISION.
MAIN.
    ACCEPT IN-LINE
    IF IN-LINE = "Y"
        DISPLAY "OK"
    ELSE
        DISPLAY "NO"
    END-IF
    STOP RUN.
'''
    paragraphs = []
    for idx in range(1, 10):
        paragraphs.append(f'''STEP-{idx}.
    PERFORM VALIDATE-{idx}
    IF WS-FLAG = "Y"
        COMPUTE WS-VALUE = WS-VALUE + {idx}
    ELSE
        COMPUTE WS-VALUE = WS-VALUE - {idx}
    END-IF.
VALIDATE-{idx}.
    EVALUATE WS-FLAG
        WHEN "Y"
            CONTINUE
        WHEN "N"
            CONTINUE
        WHEN OTHER
            MOVE "N" TO WS-FLAG
    END-EVALUATE.''')
    return f'''>SOURCE FORMAT FREE
IDENTIFICATION DIVISION.
PROGRAM-ID. {name.upper()}.
DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-INPUT PIC X(512).
01 WS-FLAG PIC X VALUE "Y".
   88 FLAG-ON VALUE "Y".
01 WS-VALUE PIC S9(9) VALUE 0.
01 WS-A PIC X(20).
01 WS-B PIC X(20).
01 WS-C PIC X(20).
PROCEDURE DIVISION.
MAIN.
    ACCEPT WS-INPUT
    UNSTRING WS-INPUT DELIMITED BY "|" INTO WS-A WS-B WS-C
    PERFORM STEP-1
    PERFORM STEP-2
    PERFORM STEP-3
    DISPLAY FUNCTION TRIM(WS-A)
    STOP RUN.
{"".join(paragraphs)}
'''


def seed_sql(count: int = 10050) -> str:
    return f'''
BEGIN;
WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<{count})
INSERT INTO cycles(cycle_id,business_date,source,run_id,state,reconciliation_status,completion_status)
SELECT printf('C%05d',x), '2026-01-01', 'SRC', printf('R%05d',x), 'COMPLETED','BALANCED','COMPLETED' FROM n;
WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<1000)
INSERT INTO accounts(account_id,status,balance_cents,currency)
SELECT printf('A%05d',x), CASE x%3 WHEN 0 THEN 'ACTIVE' WHEN 1 THEN 'BLOCKED' ELSE 'CLOSED' END,
       100000 + x*17, CASE x%3 WHEN 0 THEN 'INR' WHEN 1 THEN 'USD' ELSE 'EUR' END FROM n;
WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<{count})
INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,amount_cents,fee_cents,tax_cents,currency,purpose,received_seq)
SELECT x, printf('C%05d',x), printf('SRC-%05d',x), printf('A%05d',1 + (x*17)%1000), printf('B-%05d',x),
       CASE WHEN x%2=0 THEN printf('A%05d',1 + (x*19)%1000) ELSE NULL END,
       1000 + ((x*7919)%900000), x%37, x%13,
       CASE x%3 WHEN 0 THEN 'INR' WHEN 1 THEN 'USD' ELSE 'EUR' END,
       CASE x%5 WHEN 0 THEN 'PAYROLL' WHEN 1 THEN 'VENDOR' WHEN 2 THEN 'REFUND' WHEN 3 THEN 'TREASURY' ELSE 'TRANSFER' END, x FROM n;
COMMIT;
'''


def schema_sql() -> str:
    return '''
PRAGMA foreign_keys=ON;
CREATE TABLE cycles(cycle_id TEXT PRIMARY KEY,business_date TEXT,source TEXT,run_id TEXT,state TEXT,reconciliation_status TEXT,completion_status TEXT);
CREATE TABLE accounts(account_id TEXT PRIMARY KEY,status TEXT,balance_cents INTEGER,currency TEXT);
CREATE TABLE payments(payment_id INTEGER PRIMARY KEY,cycle_id TEXT,source_ref TEXT,payer_account TEXT,beneficiary_ref TEXT,beneficiary_account TEXT,amount_cents INTEGER,fee_cents INTEGER,tax_cents INTEGER,currency TEXT,purpose TEXT,received_seq INTEGER);
'''


def design() -> dict:
    return {"schema_version":"1.0","profile":"large_system_strict","task_kind":"software","task":TASK,"production_authenticity":{"incident_evidence":["environment/eod/log/archive/run.log","environment/eod/ops/handoff.txt"],"instruction_evidence_paths":["/app/eod/log/archive","/app/eod/ops"],"cobol_depth":{"directory":"environment/eod/cobol","min_programs":10,"min_substantive_lines_per_program":70,"min_decision_points_per_program":8,"min_paragraphs_per_program":5,"min_portfolio_syntax_features":6},"stateful_dataset":{"schema":"environment/eod/sql/schema.sql","seed":"environment/eod/sql/seed.sql","primary_table":"payments","min_records":10000,"max_records":20000,"min_distinct_cycles":100,"min_distinct_payers":500,"min_distinct_amounts":1000,"min_distinct_purposes":4,"min_distinct_currencies":3,"min_route_variants":2,"min_account_statuses":3}}}


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    task = root / TASK
    (task / "environment/eod/cobol").mkdir(parents=True)
    (task / "environment/eod/sql").mkdir(parents=True)
    (task / "environment/eod/log/archive").mkdir(parents=True)
    (task / "environment/eod/ops").mkdir(parents=True)
    (root / ".terminus/designs").mkdir(parents=True)
    (task / "task.toml").write_text(f'name = "{TASK}"\n')
    (task / "instruction.md").write_text("The failed run is under /app/eod/log/archive and the handoff is under /app/eod/ops.\n")
    (task / "README.md").write_text("# Settlement service\n\nOperational notes for the inherited settlement batch.\n")
    (task / "environment/eod/log/archive/run.log").write_text("2026-08-08 cycle=C1 stage=posting state=committed\n" * 3)
    (task / "environment/eod/ops/handoff.txt").write_text("Night shift stopped the rerun after durable work appeared to execute again.\n" * 3)
    for idx in range(10):
        (task / "environment/eod/cobol" / f"pay{idx}.cob").write_text(cobol_program(f"PAY{idx}"))
    (task / "environment/eod/sql/schema.sql").write_text(schema_sql())
    (task / "environment/eod/sql/seed.sql").write_text(seed_sql())
    (root / ".terminus/designs" / f"{TASK}.json").write_text(json.dumps(design(), indent=2))
    monkeypatch.setattr(gate, "ROOT", root)
    return root


def test_realistic_production_profile_passes(repo: Path) -> None:
    assert gate.validate(TASK) == 0


def test_thin_cobol_module_fails_even_when_other_modules_are_large(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = repo / TASK / "environment/eod/cobol/pay0.cob"
    path.write_text(cobol_program("PAY0", thin=True))
    assert gate.validate(TASK) == 1
    err = capsys.readouterr().err
    assert "Thin wrapper/micro-program logic" in err or "decision/processing points" in err


def test_toy_seed_dataset_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / TASK / "environment/eod/sql/seed.sql").write_text(seed_sql(25))
    assert gate.validate(TASK) == 1
    assert "seed records=25 is below required 10000" in capsys.readouterr().err


def test_missing_incident_evidence_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / TASK / "environment/eod/log/archive/run.log").unlink()
    assert gate.validate(TASK) == 1
    assert "incident evidence missing" in capsys.readouterr().err


def test_benchmark_fixture_readme_language_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / TASK / "README.md").write_text("This package is a cut-down payment chain used to reproduce a restart problem.\n")
    assert gate.validate(TASK) == 1
    assert "benchmark/fixture framing" in capsys.readouterr().err


def test_instruction_must_point_to_real_incident_evidence(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / TASK / "instruction.md").write_text("Fix the restart logic and keep interfaces stable.\n")
    assert gate.validate(TASK) == 1
    assert "does not point the maintainer to incident evidence path" in capsys.readouterr().err


def test_nondeterministic_seed_random_function_is_rejected(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = repo / TASK / "environment/eod/sql/seed.sql"
    path.write_text(path.read_text() + "\nSELECT random();\n")
    assert gate.validate(TASK) == 1
    assert "uses SQLite random()" in capsys.readouterr().err
