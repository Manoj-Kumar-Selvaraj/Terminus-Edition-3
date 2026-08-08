#!/usr/bin/env bash
set -euo pipefail

EOD_ROOT="${EOD_ROOT:-/app/eod}"
DB="${DB:-$EOD_ROOT/state/payment_eod.db}"
OUT_DIR="${OUT_DIR:-$EOD_ROOT/out}"
COBOL_DIR="${COBOL_DIR:-$EOD_ROOT/cobol}"
PROGRAM_BIN_DIR="${PROGRAM_BIN_DIR:-$EOD_ROOT/.bin}"
SQLITE_BIN="${SQLITE_BIN:-sqlite3}"

mkdir -p "$(dirname "$DB")" "$OUT_DIR" "$PROGRAM_BIN_DIR"

sql_escape() {
    local value="${1-}"
    value=${value//\'/\'\'}
    printf "%s" "$value"
}

db_exec() {
    local statement="$1"
    "$SQLITE_BIN" "$DB" "PRAGMA foreign_keys=ON; $statement"
}

db_scalar() {
    local statement="$1"
    "$SQLITE_BIN" -noheader "$DB" "PRAGMA foreign_keys=ON; $statement" | head -n 1
}

db_rows() {
    local statement="$1"
    "$SQLITE_BIN" -noheader -separator '|' "$DB" "PRAGMA foreign_keys=ON; $statement"
}

db_csv() {
    local statement="$1"
    "$SQLITE_BIN" -header -csv "$DB" "PRAGMA foreign_keys=ON; $statement"
}

safe_int() {
    local value="${1:-0}"
    if [[ "$value" =~ ^-?[0-9]+$ ]]; then
        printf "%s" "$value"
    else
        printf "0"
    fi
}

compile_program() {
    local program="$1"
    local source="$COBOL_DIR/${program}.cob"
    local output="$PROGRAM_BIN_DIR/$program"
    [[ -f "$source" ]] || {
        echo "missing COBOL program: $source" >&2
        return 1
    }
    cobc -x -free -I "$COBOL_DIR/copybooks" -o "$output" "$source"
}

compile_all_programs() {
    local program
    for program in \
        paydup \
        payelig \
        paymoney \
        paycap \
        payroute \
        payrsv \
        payclr \
        payledger \
        payrecon \
        payclose \
        paystate \
        payhist \
        paypub \
        payguard
    do
        compile_program "$program"
    done
}

cobol_call() {
    local program="$1"
    local input="${2-}"
    local output
    output="$(printf '%s\n' "$input" | "$PROGRAM_BIN_DIR/$program")"
    output="${output//$'\r'/}"
    output="${output//$'\n'/}"
    printf "%s" "$output" | sed -E 's/[[:space:]]+$//'
}

normalize_numeric_output() {
    local value="${1:-0}"
    value="${value//[[:space:]]/}"
    value="${value#-}"
    value="$(printf "%s" "$value" | sed -E 's/^0+([0-9])/\1/')"
    [[ -n "$value" ]] || value=0
    printf "%s" "$value"
}

select_cycle() {
    local cycle
    cycle="$(db_scalar "
        SELECT cycle_id
        FROM cycles
        WHERE completion_status <> 'COMPLETED'
        ORDER BY business_date, cycle_id
        LIMIT 1;
    ")"
    if [[ -z "$cycle" ]]; then
        cycle="$(db_scalar "
            SELECT cycle_id
            FROM cycles
            ORDER BY business_date DESC, cycle_id DESC
            LIMIT 1;
        ")"
    fi
    [[ -n "$cycle" ]] || {
        echo "no payment cycle available" >&2
        return 1
    }
    printf "%s" "$cycle"
}

cycle_field() {
    local cycle_id="$1"
    local column="$2"
    db_scalar "SELECT $column FROM cycles WHERE cycle_id='$(sql_escape "$cycle_id")';"
}

remove_gated_outputs() {
    rm -f "$OUT_DIR/customer_response.csv"
}

audit_event() {
    local cycle_id="$1"
    local payment_id="${2:-NULL}"
    local event_type="$3"
    local event_key="$4"
    local detail="${5:-}"
    local pid_sql="NULL"
    if [[ "$payment_id" =~ ^[0-9]+$ ]]; then
        pid_sql="$payment_id"
    fi
    db_exec "
        INSERT INTO audit_events(
            cycle_id,payment_id,event_type,event_key,event_detail,recorded_at
        ) VALUES(
            '$(sql_escape "$cycle_id")',
            $pid_sql,
            '$(sql_escape "$event_type")',
            '$(sql_escape "$event_key")',
            '$(sql_escape "$detail")',
            datetime('now')
        )
        ON CONFLICT(event_key) DO NOTHING;
    "
}

checkpoint() {
    local cycle_id="$1"
    local payment_id="${2:-NULL}"
    local stage="$3"
    local status="$4"
    local key="$5"
    local pid_sql="NULL"
    if [[ "$payment_id" =~ ^[0-9]+$ ]]; then
        pid_sql="$payment_id"
    fi
    db_exec "
        INSERT INTO work_checkpoints(
            cycle_id,payment_id,stage,status,checkpoint_key,recorded_at
        ) VALUES(
            '$(sql_escape "$cycle_id")',
            $pid_sql,
            '$(sql_escape "$stage")',
            '$(sql_escape "$status")',
            '$(sql_escape "$key")',
            datetime('now')
        )
        ON CONFLICT(checkpoint_key) DO UPDATE SET
            status=excluded.status,
            recorded_at=excluded.recorded_at;
    "
}

mark_cycle_processing() {
    local cycle_id="$1"
    db_exec "
        UPDATE cycles
        SET state='PROCESSING',
            started_at=COALESCE(started_at,datetime('now'))
        WHERE cycle_id='$(sql_escape "$cycle_id")'
          AND completion_status <> 'COMPLETED';
    "
    checkpoint "$cycle_id" NULL "CONTROL" "STARTED" "$cycle_id:CONTROL"
}

ensure_prerequisite_row() {
    local cycle_id="$1"
    db_exec "
        INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete)
        VALUES('$(sql_escape "$cycle_id")',0,0,0)
        ON CONFLICT(cycle_id) DO NOTHING;
    "
}

payment_ids_for_cycle() {
    local cycle_id="$1"
    db_rows "
        SELECT payment_id
        FROM payments
        WHERE cycle_id='$(sql_escape "$cycle_id")'
        ORDER BY received_seq,payment_id;
    "
}

payment_row() {
    local payment_id="$1"
    db_rows "
        SELECT
            payment_id,
            cycle_id,
            source_ref,
            payer_account,
            beneficiary_ref,
            COALESCE(beneficiary_account,''),
            amount_cents,
            fee_cents,
            tax_cents,
            currency,
            purpose
        FROM payments
        WHERE payment_id=$payment_id;
    "
}

require_database() {
    [[ -f "$DB" ]] || {
        echo "database not found: $DB" >&2
        return 1
    }
    db_scalar "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='cycles';" | grep -q '^1$'
}
