# SPEC_ALIGNMENT — terraform-aws-ec2-fenced-fleet-rollout

## Q1 Spec Gap Repairer

```text
STATUS: REPAIR_APPLIED
GAPS:
- GAP_ID: G1
  GRADED_BEHAVIOR: Report schema, IMDSv2, and least-privilege IAM Sids are graded and live in the binding fleet contract.
  CURRENT_DISCOVERABILITY: PARTIAL (instruction named /app/docs without the contract file or IAM/IMDS families)
  NATURAL_ARTIFACT: instruction.md
  REPAIR_TEXT: Named /app/docs/fenced-fleet-contract.md; added IMDSv2 and least-privilege IAM to the work-request families; pointed the report at the contract schema.
  TEST_DETAIL_LEAKAGE_CHECK: PASS
INSTRUCTION_REQUIREMENT_COMPLETENESS: SUFFICIENT
INSTRUCTION_SHAPE: PASS (two short paragraphs)
INSTRUCTION_DOC_BOUNDARY: CLEAN
CURRENT_STATE_EVIDENCE: PASS (/app/evidence plus contract)
JIRA_SLACK_HANDOFF: PASS
REVERSE_OUTLINE_RISK: LOW
UPDATE_COVERAGE_NOTE: Graded operator/Terraform/controller behaviors remain discoverable from instruction.md plus /app/docs/fenced-fleet-contract.md and /app/docs/iam-statements.md.
```

## Q2 Verifier Coverage Repairer

```text
STATUS: COVERED
REQUIREMENT_MATRIX:
- R_OPERATOR: F2P READY + digest rerun
- R_TF_LT: F2P AMI/IMDSv2 + instance profile
- R_TF_POLICY: F2P IAM Sids, ALB SG, encrypted EBS
- R_PROVENANCE: F2P provenance/slots + no public IPs
- R_ROLLOUT: F2P pilot/wave, fail_pilot, fail_wave, lost-reply resume
- R_FENCE: F2P stale owner + target-release change
- R_PLACE: F2P subnet reorder, invalid manifest, public IPAM subnet, odd fleet, key reorder
- R_JOURNAL: F2P torn tail + interior corruption
- R_DRIFT_IMPORT: F2P report_only drift + legacy Slot/moved
- R_TOKEN: F2P canonical attachment token
- R_ANTICHEAT: F2P forged READY cannot survive
- R_PRESERVE: P2P sources + baked IPAM
EMPIRICAL_NOTE: Harbor oracle=1 jobs/fleet-rebuild-4; NOP=0 jobs/fleet-nop-2 (25 F2P fail / 3 P2P pass). Identity-version F2P tighten is in tests/test_outputs.py. No new tests in this alignment pass.
```

## Q3 Spec Ambiguity Repairer

```text
STATUS: CLARIFIED
CLARIFICATIONS:
- A1: instruction now says the listed families must hold on the same READY result (not independently optional).
- A2: ipam-catalog.md bake paths corrected from /app/sql to /app/docs/sql, matching the image COPY of docs/.
NOTES: Event names, error strings, and report fields stay in the binding contract rather than the work request.
```

SPEC_ALIGNMENT: ALIGNED
