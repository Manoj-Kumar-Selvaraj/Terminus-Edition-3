# Business Module Diversity Gate

Policy version: `1.0`

This policy is an extension of `PRODUCTION_AUTHENTICITY.md` for large tasks with many callable business-language modules.

A portfolio is not production-authentic merely because every file is long. Creators must not copy one thick program template across many modules and vary only program names, field names, literals, fixture IDs, paragraph labels, comments or whitespace.

## Creator rule

When a task has many COBOL or equivalent business modules:

- each module must own a distinct domain responsibility;
- shared conventions are fine, but the actual processing topology must vary where the responsibility varies;
- validation, state classification, calculations, exception handling and business branches must be relevant to that module rather than decorative boilerplate;
- renaming paragraphs does not make copied control flow independent;
- a module that could be replaced by another module after changing constants/names is a clone risk and must be redesigned.

Run `.terminus/validate_business_module_diversity.py <task>` before freezing the candidate.

## Reviewer rule

Task Architect, Originality & Authenticity Reviewer, Difficulty Reviewer, Human Quality Reviewer and Comprehensive Reviewer must look for portfolio-level templating in addition to per-file depth. A task should be revised when apparent codebase scale is materially produced by copies of one control-flow skeleton instead of independent domain logic.

The automated detector blocks exact logic clones and overwhelming reuse of the same paragraph-count/control-flow signature. Passing automation does not waive reviewer judgment about semantic templating.
