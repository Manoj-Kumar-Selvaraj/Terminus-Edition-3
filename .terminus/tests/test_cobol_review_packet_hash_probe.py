from __future__ import annotations

import sys
from pathlib import Path

T = Path(__file__).resolve().parents[1]
ROOT = T.parent
if str(T) not in sys.path:
    sys.path.insert(0, str(T))

from review_contract import review_scope_hash, role_contract_hash  # noqa: E402


def test_emit_cobol_review_packet_hashes() -> None:
    q4 = role_contract_hash(ROOT, "Spec-Test Contract Reviewer")
    q6 = role_contract_hash(ROOT, "Production Logic Auditor")
    scope = review_scope_hash(ROOT, "cobol-comp3-python-equiv", "Production Logic Auditor")
    raise AssertionError(f"COBOL_PACKET_HASHES Q4={q4} Q6={q6} Q6_SCOPE={scope}")
