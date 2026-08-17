# TASK_WRITING_PROFILE — tenant-catalog-logical-cdc-plane

```text
DATASET_POLICY_VERSION: 1.2
DATASET_REGISTRY_SHA256: 05ece08c27414d265a2a238928e4c664295434620ffe957c8e88b5050c54645a
SEED_CATALOG_SHA256: e205f858f8391fd88d3e26665d2f585a69cd691321b9275644e631bb949f0942
CALIBRATION_PAIR_ID: hwpair-ca6491d16e6d8718338e
WRITER_CALIBRATION_ID: hwcal-writer-f0e77961b392116411f6
REVIEWER_CALIBRATION_ID: hwcal-reviewer-8c90efa2d3d88feadea3
WRITER_SAMPLE_IDS: HC-016,HC-030,HC-010,HC-024,HC-020,HC-005,CP-002,CP-001,AT-004
REVIEWER_SAMPLE_IDS: HC-017,HC-007,HC-026,HC-009,HC-013,HC-008,CP-004,CP-005,CP-006,AT-006,AT-003,HP-003,HP-002,HN-001,HN-002
WRITER_REVIEWER_SAMPLE_OVERLAP: []
EXTERNAL_DATASET_COVERAGE: DEGRADED (local seed calibration only; external HF pulls not required for this producer pass)
HUMAN_INFORMATION_SELECTION: lead with operational disagreement after bounce; point to contract/oncall evidence; keep repair language implementation-neutral
CONSTRAINT_PRESERVATION: keep Go plane, WAL protocol, warehouse untouched, CLI fail-closed usage, and contract-bound report schemas
ANTI_TEMPLATE: no empathy filler, no fake customer story, no module-level diagnosis
```

Source pair: `.terminus/contracts/tenant-catalog-logical-cdc-plane/calibration-pair.json`
