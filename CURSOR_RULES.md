# Terminus Edition 3 Cursor rules

The authoritative task-creation standard is [TERMINUS_3_AI_INSTRUCTIONS.md](TERMINUS_3_AI_INSTRUCTIONS.md). Cursor must read it completely before changing a task.

The local Harbor helpers are [terminus3.ps1](terminus3.ps1) and [terminus3.sh](terminus3.sh).

## Rules loaded from the repository workspace

When the parent `TerminalBench` repository is open, these rules apply to files under `Terminus-Edition-3/**`:

| Rule | Focus |
|---|---|
| [terminus-edition-3-core.mdc](../.cursor/rules/terminus-edition-3-core.mdc) | Design quality, workspace discipline, layout, instructions, evidence, and human writing |
| [terminus-edition-3-task-toml.mdc](../.cursor/rules/terminus-edition-3-task-toml.mdc) | Metadata schema, taxonomy, artifacts, difficulty, compose, network, and resources |
| [terminus-edition-3-verifier.mdc](../.cursor/rules/terminus-edition-3-verifier.mdc) | Docker, oracle, separate verifier, semantic tests, anti-cheating, rubrics, and release gates |
| [terminus-edition-3-general.mdc](../.cursor/rules/terminus-edition-3-general.mdc) | Always-on Edition 3 guardrails when the parent repository is the workspace |
| [terraform-edition-2-to-3.mdc](../.cursor/rules/terraform-edition-2-to-3.mdc) | Conditional conversion queue and task-specific Terraform designs |

## Rules loaded from the Edition 3 workspace

When `Terminus-Edition-3` itself is open as the Cursor workspace, the always-on [terminus-edition-3-general.mdc](.cursor/rules/terminus-edition-3-general.mdc) requires the same authority and companion rules. This file and the Terraform migration rule are mirrored under the parent repository's `.cursor/rules/` directory, so either workspace entry point receives the same guidance.

Terraform migrations also use [terraform-edition-2-to-3.mdc](.cursor/rules/terraform-edition-2-to-3.mdc). It contains the guarded source inventory and a distinct Edition 3 plan for every Edition 2 Terraform candidate. The migration rule is conditional and should be attached when working in a `terraform-*` task or referenced directly in the Cursor conversation.

Never copy `.cursor/` rules into a task directory, agent image, or submission ZIP.
