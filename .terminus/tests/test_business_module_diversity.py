"""Regression tests for business-module portfolio diversity."""

from __future__ import annotations

import sys
from pathlib import Path

CONTROL_PLANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE))

import validate_business_module_diversity as gate  # noqa: E402


def program(name: str, *, variant: int = 0, structural_variant: bool = False) -> str:
    extra = ""
    if structural_variant:
        extra = f'''\nASSESS-{variant}.\n    IF WS-VALUE > {variant}\n        COMPUTE WS-VALUE = WS-VALUE - {variant}\n    ELSE\n        COMPUTE WS-VALUE = WS-VALUE + {variant}\n    END-IF.\n'''
    return f'''>SOURCE FORMAT FREE
IDENTIFICATION DIVISION.
PROGRAM-ID. {name.upper()}.
DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-INPUT PIC X(256).
01 WS-A PIC X(32).
01 WS-B PIC X(32).
01 WS-VALUE PIC S9(9) VALUE 0.
01 WS-FLAG PIC X VALUE "Y".
   88 VALID-FLAG VALUE "Y".
PROCEDURE DIVISION.
MAIN.
    ACCEPT WS-INPUT
    PERFORM PARSE-INPUT
    PERFORM CHECK-INPUT
    PERFORM DECIDE-RESULT
    STOP RUN.
PARSE-INPUT.
    UNSTRING WS-INPUT DELIMITED BY "|" INTO WS-A WS-B.
CHECK-INPUT.
    IF WS-A = SPACES
        MOVE "N" TO WS-FLAG
    END-IF.
DECIDE-RESULT.
    EVALUATE TRUE
        WHEN VALID-FLAG
            COMPUTE WS-VALUE = {variant} + 1
        WHEN OTHER
            COMPUTE WS-VALUE = 0
    END-EVALUATE.
{extra}'''


def test_program_id_only_clones_fail(tmp_path: Path) -> None:
    directory = tmp_path / "cobol"
    directory.mkdir()
    body = program("PAY00", variant=5)
    for idx in range(8):
        (directory / f"pay{idx}.cob").write_text(
            body.replace("PROGRAM-ID. PAY00.", f"PROGRAM-ID. PAY{idx}.")
        )
    errors = gate.validate_directory(directory)
    assert any("logic-equivalent" in error for error in errors)


def test_overwhelming_structural_template_reuse_fails(tmp_path: Path) -> None:
    directory = tmp_path / "cobol"
    directory.mkdir()
    # Values differ enough to avoid exact canonical clones, but the control/paragraph
    # architecture remains copied. Eight of ten crosses the default 75% limit.
    for idx in range(8):
        (directory / f"pay{idx}.cob").write_text(program(f"PAY{idx}", variant=idx + 1))
    for idx in range(8, 10):
        (directory / f"pay{idx}.cob").write_text(
            program(f"PAY{idx}", variant=idx + 1, structural_variant=True)
        )
    errors = gate.validate_directory(directory)
    assert any("paragraph/control-flow signature" in error for error in errors)


def test_structurally_diverse_portfolio_passes(tmp_path: Path) -> None:
    directory = tmp_path / "cobol"
    directory.mkdir()
    for idx in range(10):
        text = program(f"PAY{idx}", variant=idx + 1, structural_variant=True)
        # Give every pair a genuinely different control-flow signature, not a renamed
        # paragraph: the number of domain decision blocks changes across the portfolio.
        additions = []
        for branch in range(idx % 5):
            additions.append(
                f'''DOMAIN-{idx}-{branch}.\n    IF WS-VALUE > {branch}\n        PERFORM ASSESS-{idx}\n    END-IF.\n'''
            )
        text += "\n" + "".join(additions)
        (directory / f"pay{idx}.cob").write_text(text)
    assert gate.validate_directory(directory) == []
