#!/usr/bin/env bash
set -euo pipefail
EOD_ROOT="${EOD_ROOT:-/app/eod}"
export EOD_ROOT
source "$EOD_ROOT/lib/common.sh"
source "$EOD_ROOT/lib/financial.sh"
source "$EOD_ROOT/lib/population.sh"
source "$EOD_ROOT/lib/accounting.sh"
source "$EOD_ROOT/lib/capacity.sh"
source "$EOD_ROOT/lib/integrity.sh"
source "$EOD_ROOT/lib/restart.sh"
source "$EOD_ROOT/lib/reconcile.sh"
source "$EOD_ROOT/lib/publish.sh"
source "$EOD_ROOT/lib/close.sh"
source "$EOD_ROOT/lib/control.sh"
source "$EOD_ROOT/lib/operations.sh"
source "$EOD_ROOT/lib/lifecycle.sh"

main() {
    require_database
    compile_all_programs
    local cycle_id; cycle_id="$(select_cycle)"
    [[ -n "$cycle_id" ]] || { echo "no EOD cycle selected" >&2; return 2; }
    mkdir -p "$OUT_DIR"
    run_cycle_control "$cycle_id" || true
    if [[ ! -f "$OUT_DIR/reconciliation.json" ]]; then
        collect_reconciliation_metrics "$cycle_id"
        write_reconciliation_json "$cycle_id" HELD
    fi
    write_operational_artifacts "$cycle_id"
    printf 'cycle=%s state=%s reconciliation=%s completion=%s\n' \
      "$cycle_id" "$(cycle_field "$cycle_id" state)" \
      "$(cycle_field "$cycle_id" reconciliation_status)" \
      "$(cycle_field "$cycle_id" completion_status)"
}
main "$@"
