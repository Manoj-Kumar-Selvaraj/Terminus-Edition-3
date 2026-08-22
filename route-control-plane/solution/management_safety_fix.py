#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/app/routecp")


def inject_once(path: pathlib.Path, needle: str, replacement: str) -> None:
    text = path.read_text()
    if replacement in text:
        return
    if needle not in text:
        raise RuntimeError(f"expected management-safety anchor not found in {path}")
    path.write_text(text.replace(needle, replacement, 1))


controlplane = root / "internal" / "controlplane" / "controlplane.go"
rollback_anchor = """    if err := validateDesired(candidate, c.nodes); err != nil { return Transaction{}, err }\n    oldDesired := c.desired\n"""
rollback_replacement = """    if err := validateDesired(candidate, c.nodes); err != nil { return Transaction{}, err }\n    if _, _, err := c.managementSafety(candidate); err != nil { return Transaction{}, err }\n    oldDesired := c.desired\n"""
inject_once(controlplane, rollback_anchor, rollback_replacement)


drift = root / "internal" / "controlplane" / "drift.go"
reconcile_anchor = """    if existing, ok := c.idempotency[key]; ok {\n        result.Applied = true\n        result.TransactionID = existing\n        return result, nil\n    }\n    before := cloneObserved(observed)\n"""
reconcile_replacement = """    if existing, ok := c.idempotency[key]; ok {\n        result.Applied = true\n        result.TransactionID = existing\n        return result, nil\n    }\n    if _, _, err := c.managementSafety(c.desired); err != nil { return ReconcileResult{}, err }\n    before := cloneObserved(observed)\n"""
inject_once(drift, reconcile_anchor, reconcile_replacement)


rollout = root / "internal" / "controlplane" / "rollout.go"
rollout_anchor = """    if req.Revision != c.desired.Revision { return Rollout{}, fmt.Errorf(\"%w: rollout revision %d is not current %d\", ErrConflict, req.Revision, c.desired.Revision) }\n    if req.WaveSize < 1 { req.WaveSize = 5 }\n"""
rollout_replacement = """    if req.Revision != c.desired.Revision { return Rollout{}, fmt.Errorf(\"%w: rollout revision %d is not current %d\", ErrConflict, req.Revision, c.desired.Revision) }\n    if _, _, err := c.managementSafety(c.desired); err != nil { return Rollout{}, err }\n    if req.WaveSize < 1 { req.WaveSize = 5 }\n"""
inject_once(rollout, rollout_anchor, rollout_replacement)

print("routecp management-safety reference guards installed")
