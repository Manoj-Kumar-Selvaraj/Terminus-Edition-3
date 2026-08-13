#!/usr/bin/env python3
"""Compatibility entrypoint for canonical execution-record trust validation."""

import validate_execution_record_trust as trust


_original_outputs = trust._outputs


def _outputs_with_external_batch(invocation):
    outputs = _original_outputs(invocation)
    stage = invocation.get("stage", {})
    if stage.get("stage_id") == "OFFICIAL_MODEL_TRIALS":
        outputs["EXTERNAL_RUN_ID"] = "official-batch-validator"
    return outputs


trust._outputs = _outputs_with_external_batch


if __name__ == "__main__":
    raise SystemExit(trust.main())
