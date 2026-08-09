# Business-module diversity control-plane change

This branch adds a portfolio-level production-authenticity check for copied thick COBOL/business-language modules. Per-file LOC and decision thresholds remain required, but a large-system task is also rejected when multiple programs are logic-equivalent after identity/noise normalization or when an overwhelming share of the portfolio reuses the same paragraph-count/control-flow signature.

The detector intentionally ignores paragraph names for the structural comparison so renaming `DECIDE-RESULT` does not evade the check. The current payment EOD task is used as the live declared-profile integration target in CI.
