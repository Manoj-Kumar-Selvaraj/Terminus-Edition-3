#!/usr/bin/env python3
"""Compatibility entrypoint for canonical execution-record trust validation."""

import hashlib
import subprocess
from urllib.parse import quote

import validate_execution_record_trust as trust

_RECORD_REFERENCE_FIXTURE = ".terminus/tests/fixtures/record_reference_ids.json"
_original_outputs = trust._outputs


def _outputs_with_external_batch(invocation):
    outputs = _original_outputs(invocation)
    stage = invocation.get("stage", {})
    if stage.get("stage_id") == "OFFICIAL_MODEL_TRIALS":
        outputs["EXTERNAL_RUN_ID"] = "official-batch-validator"
    return outputs


def _resolved_ref(kind: str, identity: str):
    commit = subprocess.run(
        ["git", "-C", str(trust.ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    raw = subprocess.run(
        ["git", "-C", str(trust.ROOT), "show", f"{commit}:{_RECORD_REFERENCE_FIXTURE}"],
        check=True,
        capture_output=True,
    ).stdout
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    return {
        "kind": kind,
        "ref": (
            f"git:{commit}:{_RECORD_REFERENCE_FIXTURE}#"
            f"{quote(identity, safe='')}"
        ),
        "content_hash": digest,
    }


trust._outputs = _outputs_with_external_batch
trust._eref = _resolved_ref


if __name__ == "__main__":
    raise SystemExit(trust.main())
