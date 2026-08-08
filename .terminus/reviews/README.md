# Terminus Structured Review Evidence

Store semantic review evidence here, outside every task package.

## Current v3 layout

```text
.terminus/reviews/
  <task>/
    <task-commit-prefix>/
      <unique-review-id>.packet.json
      <unique-review-id>.json
      pre-llmaj-aggregate.json
      disagreement-scan.json
      adjudication-<id>.json
```

New semantic reviews use unique execution IDs. Do not overwrite an older result merely to reuse a fixed role filename.

## Packet/result contract

A current ready semantic result must:

- satisfy `agents/schemas/review_result.schema.json` v3;
- reference its exact generated `*.packet.json` through `context_packet`;
- match the packet on review ID, task, task commit, role, protocol/prompt/role policy versions, control-plane commit and role-contract hash;
- be filed under a directory whose prefix matches `task_commit`;
- use the exact output path recorded by the packet;
- put role-specific fields under `role_output`.

Packets satisfy `context_packet.schema.json` v3. Current Cursor isolation is normally `PROCEDURAL`: the packet records an operating evidence boundary, not filesystem ACL isolation.

## Historical evidence

Legacy reports that predate schema v3 remain immutable historical evidence. Do not rewrite them to make them look current and do not require every historical report to validate against every future schema. A legacy report cannot support a current ready semantic gate; rerun the role under the current packet/result contract.

## Freshness enforcement

`.terminus/validate_review_freshness.py` validates current ready evidence against:

- Git-derived current task commit;
- exact gate-cited review path;
- v3 packet/result schema and cross-binding;
- current protocol/role policy and role-contract hash;
- allowed ready verdict, confidence and evidence sufficiency;
- Comprehensive Reviewer 100% checklist coverage;
- Pre-LLMaJ aggregate current commit/panel policy, explicit PASS and no open findings/conflicts;
- the complete mandatory `SUBMISSION_READY` gate set.

`--allow-stale` is local triage only. CI never uses it.

## Deterministic evidence

Oracle, NOP, Ruff, Harbor, model trials and packaging are not semantic review files. Their ready session rows cite current run/job/artifact/package evidence instead.

## Immutability and safety

- Never store secrets or raw credentials.
- Do not store unnecessary full chat transcripts.
- Producers do not write acceptance PASS reviews for their own output.
- Reruns create new review IDs.
- Review/control-plane files remain outside task directories and never enter a submission ZIP.

## Pre-LLMaJ aggregate

`pre-llmaj-aggregate.json` references the frozen current reviewer results and records at minimum task, task commit, panel policy version, explicit verdict, open findings and policy conflicts. Aggregate PASS is accepted only when the freshness validator confirms those invariants.
