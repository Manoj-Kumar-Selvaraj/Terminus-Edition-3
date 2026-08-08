#!/usr/bin/env python3
"""Apply the reference COBOL business-rule repairs without test-specific special cases."""

from __future__ import annotations

from pathlib import Path

ROOT = Path("/app/eod/cobol")

REPLACEMENTS: dict[str, list[tuple[str, str]]] = {
    "paycap.cob": [("COMPUTE WS-AVAILABLE = WS-BALANCE", "COMPUTE WS-AVAILABLE = WS-BALANCE - WS-RESERVED")],
    "payclose.cob": [("WHEN RECON-READY AND DELIVERY-READY\n", "WHEN RECON-READY AND DELIVERY-READY AND REPORT-READY AND ARCHIVE-READY\n")],
    "payclr.cob": [("WHEN CLEARING-PRESENT\n                MOVE \"KEEP_CLEARING\" TO WS-OUTPUT-CODE", "WHEN WS-RESERVATION-MATCH = \"N\"\n                MOVE \"HOLD_RESERVATION_MISMATCH\" TO WS-OUTPUT-CODE\n                MOVE \"RESERVATION_AMOUNT_MISMATCH\" TO WS-REASON-CODE\n            WHEN CLEARING-PRESENT\n                MOVE \"KEEP_CLEARING\" TO WS-OUTPUT-CODE")],
    "paydup.cob": [
        ("WHEN PRIOR-ACCEPTED\n", "WHEN WS-PRIOR-ACCEPTED-FLAG = \"Y\" AND WS-CURRENT-CYCLE-FLAG = \"N\"\n"),
        ("MOVE \"HISTORICAL_MATCH\" TO WS-REASON-CODE", "MOVE \"PRIOR_ACCEPTED_SOURCE_REFERENCE\" TO WS-REASON-CODE"),
        ("WHEN COMMERCIAL-SIMILAR\n                MOVE \"DUPLICATE\" TO WS-OUTPUT-CODE\n                MOVE \"COMMERCIAL_MATCH\" TO WS-REASON-CODE", "WHEN COMMERCIAL-SIMILAR\n                MOVE \"NEW\" TO WS-OUTPUT-CODE\n                MOVE \"SIMILAR_BUT_DISTINCT_SOURCE\" TO WS-REASON-CODE"),
    ],
    "payelig.cob": [("WHEN INTERNAL-ROUTE\n                MOVE \"ELIGIBLE\" TO WS-OUTPUT-CODE", "WHEN INTERNAL-ROUTE AND WS-BENEFICIARY-STATUS NOT = \"ACTIVE\"\n                MOVE \"REJECT_BENEFICIARY\" TO WS-OUTPUT-CODE\n                MOVE \"BENEFICIARY_NOT_ACTIVE\" TO WS-REASON-CODE\n            WHEN INTERNAL-ROUTE\n                MOVE \"ELIGIBLE\" TO WS-OUTPUT-CODE")],
    "payledger.cob": [
        ("IF WS-DEBIT >= WS-CREDIT", "IF WS-DEBIT = WS-CREDIT"),
        ("WHEN LEDGER-BALANCED\n                MOVE \"LEDGER_OK\" TO WS-OUTPUT-CODE", "WHEN LEDGER-BALANCED AND WS-EXPECTED-ROWS NOT = WS-ACTUAL-ROWS\n                MOVE \"LEDGER_INCOMPLETE\" TO WS-OUTPUT-CODE\n                MOVE \"LEDGER_ROW_COUNT_MISMATCH\" TO WS-REASON-CODE\n            WHEN LEDGER-BALANCED\n                MOVE \"LEDGER_OK\" TO WS-OUTPUT-CODE"),
        ("MOVE \"LEDGER_TOTALS_ACCEPTED\" TO WS-REASON-CODE", "MOVE \"LEDGER_TOTALS_AND_SHAPE_ACCEPTED\" TO WS-REASON-CODE"),
    ],
    "paymoney.cob": [("COMPUTE WS-TOTAL-DEBIT = WS-AMOUNT", "COMPUTE WS-TOTAL-DEBIT = WS-AMOUNT + WS-FEE + WS-TAX")],
    "paypub.cob": [("MOVE \"PUBLISH\" TO WS-OUTPUT-CODE\n                MOVE \"PUBLICATION_DEFAULT\" TO WS-REASON-CODE", "MOVE \"HOLD\" TO WS-OUTPUT-CODE\n                MOVE \"RECONCILIATION_NOT_BALANCED\" TO WS-REASON-CODE")],
    "payrecon.cob": [("PERFORM CHECK-CORE-CONTROLS\n        IF WS-CONTROL-FAILURES = 0", "PERFORM CHECK-CORE-CONTROLS\n        PERFORM CHECK-FINANCIAL-SHAPE\n        PERFORM CHECK-EXCEPTION-CONTROLS\n        IF WS-CONTROL-FAILURES = 0")],
    "payroute.cob": [
        ("WHEN \"INTERNAL\"\n                MOVE \"POST_INTERNAL\" TO WS-OUTPUT-CODE\n                MOVE \"INTERNAL_EXECUTION\" TO WS-REASON-CODE", "WHEN \"INTERNAL\"\n                IF POSTING-PRESENT\n                    MOVE \"RESUME_INTERNAL\" TO WS-OUTPUT-CODE\n                    MOVE \"INTERNAL_POSTING_DURABLE\" TO WS-REASON-CODE\n                ELSE\n                    MOVE \"POST_INTERNAL\" TO WS-OUTPUT-CODE\n                    MOVE \"INTERNAL_EXECUTION\" TO WS-REASON-CODE\n                END-IF"),
        ("WHEN \"EXTERNAL\"\n                MOVE \"RESERVE_EXTERNAL\" TO WS-OUTPUT-CODE\n                MOVE \"EXTERNAL_EXECUTION\" TO WS-REASON-CODE", "WHEN \"EXTERNAL\"\n                IF RESERVATION-PRESENT\n                    MOVE \"RESUME_EXTERNAL\" TO WS-OUTPUT-CODE\n                    MOVE \"EXTERNAL_RESERVATION_DURABLE\" TO WS-REASON-CODE\n                ELSE\n                    MOVE \"RESERVE_EXTERNAL\" TO WS-OUTPUT-CODE\n                    MOVE \"EXTERNAL_EXECUTION\" TO WS-REASON-CODE\n                END-IF"),
    ],
    "payrsv.cob": [("WHEN RESERVATION-ACTIVE\n                MOVE \"RESERVATION_OK\" TO WS-OUTPUT-CODE\n                MOVE \"ACTIVE_RESERVATION_ACCEPTED\" TO WS-REASON-CODE", "WHEN RESERVATION-ACTIVE AND WS-DIFFERENCE = 0\n                MOVE \"RESERVATION_OK\" TO WS-OUTPUT-CODE\n                MOVE \"ACTIVE_RESERVATION_MATCHED\" TO WS-REASON-CODE\n            WHEN RESERVATION-ACTIVE\n                MOVE \"RESERVATION_MISMATCH\" TO WS-OUTPUT-CODE\n                MOVE \"ACTIVE_RESERVATION_VALUE_MISMATCH\" TO WS-REASON-CODE")],
    "paystate.cob": [("WHEN RECON-BALANCED\n                MOVE \"COMPLETED\" TO WS-OUTPUT-CODE\n                MOVE \"BALANCED_STATE\" TO WS-REASON-CODE", "WHEN RECON-BALANCED AND CLOSE-COMPLETE\n                MOVE \"COMPLETED\" TO WS-OUTPUT-CODE\n                MOVE \"BALANCED_AND_CLOSED\" TO WS-REASON-CODE\n            WHEN RECON-BALANCED\n                MOVE \"RECONCILED\" TO WS-OUTPUT-CODE\n                MOVE \"BALANCED_WAITING_FOR_CLOSE\" TO WS-REASON-CODE")],
}


def main() -> None:
    for filename, replacements in REPLACEMENTS.items():
        path = ROOT / filename
        text = path.read_text(encoding="utf-8")
        for old, new in replacements:
            if old not in text:
                raise SystemExit(f"reference COBOL repair anchor not found: {filename}: {old!r}")
            text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
