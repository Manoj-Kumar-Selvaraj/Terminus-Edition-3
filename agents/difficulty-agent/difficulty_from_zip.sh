#!/usr/bin/env bash
# Terminus Edition 3 — run oracle/NOP (+ optional difficulty) from a task zip or folder.
#
# Usage:
#   ./difficulty_from_zip.sh <task.zip|/path/to/task-dir> [--validate-only] [--skip-validate] [--skip-difficulty]
#
# Defaults: oracle + nop + GPT-5.5×5 + Claude Opus 4.8×5.
# Jobs write to Linux FS under /tmp to avoid Windows mount issues.
set -euo pipefail

export PATH="${HOME}/.local/bin:/root/.local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
E3_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STB_BIN="${STB_BIN:-stb}"
STABLE_CWD="${STABLE_CWD:-/tmp/terminus3-cwd}"
JOBS_ROOT="${JOBS_ROOT:-/tmp/e3-diff-jobs}"
WORK_ROOT="${WORK_ROOT:-/tmp/e3-diff-work}"

VALIDATE=1
DIFFICULTY=1
INPUT=""

die() { echo "error: $*" >&2; exit 1; }

usage() {
  cat <<EOF
Usage: $0 <task.zip|task-dir> [options]

Options:
  --validate-only     Run oracle + nop only; skip model difficulty
  --skip-validate     Skip oracle/nop (use when already green)
  --skip-difficulty   Skip GPT×5 / Opus×5 (same as --validate-only)
  -h, --help          Show this help

Environment:
  STB_BIN     stb binary (default: stb)
  JOBS_ROOT   Harbor jobs parent dir (default: /tmp/e3-diff-jobs)
  WORK_ROOT   Unpack parent dir (default: /tmp/e3-diff-work)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --validate-only|--skip-difficulty) DIFFICULTY=0; shift ;;
    --skip-validate) VALIDATE=0; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) die "unknown option: $1" ;;
    *)
      [[ -n "$INPUT" ]] && die "unexpected extra argument: $1"
      INPUT="$1"
      shift
      ;;
  esac
done

[[ -n "$INPUT" ]] || { usage; die "task zip or directory required"; }
command -v "$STB_BIN" >/dev/null 2>&1 || die "stb not found on PATH. Run: $E3_ROOT/terminus3.sh install && stb login"

mkdir -p "$STABLE_CWD" "$JOBS_ROOT" "$WORK_ROOT"

run_harbor() {
  ( cd "$STABLE_CWD" && "$STB_BIN" "$@" )
}

# --- resolve / unpack --------------------------------------------------------

resolve_task_root() {
  local root="$1"
  if [[ -f "$root/instruction.md" && -f "$root/task.toml" && -d "$root/environment" && -d "$root/solution" && -d "$root/tests" ]]; then
    printf '%s\n' "$root"
    return 0
  fi
  # Single nested folder (common when zip wraps one directory)
  local kids=()
  while IFS= read -r -d '' d; do kids+=("$d"); done < <(find "$root" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)
  if [[ ${#kids[@]} -eq 1 ]]; then
    resolve_task_root "${kids[0]}"
    return $?
  fi
  # Search one level for task.toml
  local hit
  hit="$(find "$root" -mindepth 1 -maxdepth 2 -type f -name task.toml 2>/dev/null | head -1 || true)"
  if [[ -n "$hit" ]]; then
    resolve_task_root "$(dirname "$hit")"
    return $?
  fi
  return 1
}

stamp="$(date +%Y%m%d_%H%M%S)"
base_name="$(basename "$INPUT")"
base_name="${base_name%.zip}"
base_name="${base_name//[^a-zA-Z0-9._-]/_}"
UNPACK="$WORK_ROOT/${base_name}_${stamp}"
JOBS="$JOBS_ROOT/${base_name}_${stamp}"
mkdir -p "$UNPACK" "$JOBS"

if [[ -f "$INPUT" ]]; then
  case "$INPUT" in
    *.zip|*.ZIP) ;;
    *) die "input file must be a .zip (or pass a task directory): $INPUT" ;;
  esac
  command -v unzip >/dev/null 2>&1 || die "unzip required"
  echo "==> unpacking zip -> $UNPACK"
  unzip -q "$INPUT" -d "$UNPACK"
elif [[ -d "$INPUT" ]]; then
  echo "==> copying task dir -> $UNPACK"
  # Prefer absolute source
  SRC="$(cd "$INPUT" && pwd)"
  cp -a "$SRC/." "$UNPACK/"
else
  die "not a file or directory: $INPUT"
fi

TASK="$(resolve_task_root "$UNPACK")" || die "could not find flat Harbor task under $UNPACK
Expected instruction.md, task.toml, environment/, solution/, tests/"
TASK="$(cd "$TASK" && pwd)"
echo "==> task root: $TASK"

# Layout warnings
if [[ -d "$TASK/runs" ]]; then
  echo "warn: runs/ present — ignore for difficulty; do not upload runs in submission zips" >&2
fi

REPORT="$TASK/DIFFICULTY_REPORT.md"
{
  echo "# Edition 3 difficulty report"
  echo
  echo "- Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- Task root: \`$TASK\`"
  echo "- Jobs root: \`$JOBS\`"
  echo "- Input: \`$INPUT\`"
  echo
} >"$REPORT"

# Snapshot top-level job dirs currently under JOBS
list_job_dirs() {
  find "$JOBS" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort || true
}

# After a harbor run: summarize rewards under newly created job dir(s)
summarize_new_jobs() {
  local label="$1"
  local before_file="$2"
  local after_list new_dirs
  after_list="$(mktemp)"
  list_job_dirs >"$after_list"
  new_dirs="$(comm -13 "$before_file" "$after_list" || true)"
  rm -f "$after_list"

  LAST_PASS=0
  LAST_FAIL=0
  LAST_JOB=""

  if [[ -z "$new_dirs" ]]; then
    # Fallback: newest mtime dir (GNU find)
    LAST_JOB="$(find "$JOBS" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2- || true)"
    [[ -n "$LAST_JOB" ]] || { echo "$label: (no job dir)"; return 1; }
    new_dirs="$LAST_JOB"
    echo "warn: no new job dir detected; using newest: $LAST_JOB" >&2
  fi

  local job rewards f val
  local pass=0 fail=0
  while IFS= read -r job; do
    [[ -z "$job" ]] && continue
    LAST_JOB="$job"
    echo "$label job: $job"
    rewards="$(find "$job" -type f -name reward.txt 2>/dev/null | sort || true)"
    if [[ -z "$rewards" ]]; then
      echo "  rewards: (none)"
      continue
    fi
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      val="$(tr -d '[:space:]' <"$f" || true)"
      echo "  reward ${f#"$job"/}: $val"
      if [[ "$val" == "1" || "$val" == "1.0" ]]; then
        pass=$((pass + 1))
      else
        fail=$((fail + 1))
      fi
    done <<<"$rewards"
  done <<<"$new_dirs"

  LAST_PASS="$pass"
  LAST_FAIL="$fail"
  {
    echo "## $label"
    echo
    echo "- Job: \`${LAST_JOB}\`"
    echo "- Pass (reward 1): $pass"
    echo "- Non-pass: $fail"
    echo
  } >>"$REPORT"
  echo "$label: pass=$pass fail=$fail"
}

# --- validate ----------------------------------------------------------------

GPT_PASS=""
OPUS_PASS=""
ORACLE_OK=""
NOP_OK=""

if [[ "$VALIDATE" -eq 1 ]]; then
  echo "===== ORACLE ====="
  BEFORE="$(mktemp)"
  list_job_dirs >"$BEFORE"
  run_harbor harbor run -a oracle -p "$TASK" -o "$JOBS" -n 1
  summarize_new_jobs "oracle" "$BEFORE" || true
  rm -f "$BEFORE"
  ORACLE_PASS="${LAST_PASS:-0}"
  if [[ "${ORACLE_PASS:-0}" -ge 1 ]]; then ORACLE_OK=1; else ORACLE_OK=0; fi

  echo "===== NOP ====="
  BEFORE="$(mktemp)"
  list_job_dirs >"$BEFORE"
  run_harbor harbor run -a nop -p "$TASK" -o "$JOBS" -n 1
  summarize_new_jobs "nop" "$BEFORE" || true
  rm -f "$BEFORE"
  NOP_PASS="${LAST_PASS:-0}"
  # NOP should score 0
  if [[ "${NOP_PASS:-0}" -eq 0 ]]; then NOP_OK=1; else NOP_OK=0; fi

  {
    echo "## Gate"
    echo
    echo "- Oracle OK (expect pass≥1): $ORACLE_OK (pass_count=$ORACLE_PASS)"
    echo "- NOP OK (expect pass=0): $NOP_OK (pass_count=$NOP_PASS)"
    echo
  } >>"$REPORT"

  if [[ "$ORACLE_OK" != "1" || "$NOP_OK" != "1" ]]; then
    echo "error: oracle/NOP gate failed — fix task before trusting difficulty." >&2
    echo "Report: $REPORT" >&2
    if [[ "$DIFFICULTY" -eq 1 ]]; then
      die "refusing to run difficulty until oracle=1 and NOP=0 (use --skip-validate to override)"
    fi
  fi
else
  echo "==> skipping oracle/nop (--skip-validate)"
  {
    echo "## Gate"
    echo
    echo "- Skipped (--skip-validate)"
    echo
  } >>"$REPORT"
fi

# --- difficulty --------------------------------------------------------------

tier_for_mean() {
  # arg: mean percent 0-100 as integer or float string
  python3 - "$1" <<'PY'
import sys
m=float(sys.argv[1])
if m >= 100.0 - 1e-9:
    print("reject_too_easy")
elif m >= 80.0:
    print("base")
elif m >= 50.0:
    print("core")
elif m >= 20.0:
    print("advanced")
else:
    print("frontier")
PY
}

if [[ "$DIFFICULTY" -eq 1 ]]; then
  echo "===== DIFFICULTY GPT-5.5 ×5 ====="
  BEFORE="$(mktemp)"
  list_job_dirs >"$BEFORE"
  run_harbor harbor run -m @openai/gpt-5.5 -p "$TASK" -k 5 -o "$JOBS"
  summarize_new_jobs "gpt-5.5" "$BEFORE" || true
  rm -f "$BEFORE"
  GPT_PASS="${LAST_PASS:-0}"
  GPT_TOTAL=$(( GPT_PASS + ${LAST_FAIL:-0} ))
  [[ "$GPT_TOTAL" -eq 0 ]] && GPT_TOTAL=5

  echo "===== DIFFICULTY Claude Opus 4.8 ×5 ====="
  BEFORE="$(mktemp)"
  list_job_dirs >"$BEFORE"
  run_harbor harbor run -m @anthropic/claude-opus-4-8 -p "$TASK" -k 5 -o "$JOBS"
  summarize_new_jobs "opus-4.8" "$BEFORE" || true
  rm -f "$BEFORE"
  OPUS_PASS="${LAST_PASS:-0}"
  OPUS_TOTAL=$(( OPUS_PASS + ${LAST_FAIL:-0} ))
  [[ "$OPUS_TOTAL" -eq 0 ]] && OPUS_TOTAL=5

  TOTAL_PASS=$(( GPT_PASS + OPUS_PASS ))
  TOTAL_N=$(( GPT_TOTAL + OPUS_TOTAL ))
  MEAN_PCT="$(python3 -c "print(round(100.0 * $TOTAL_PASS / max($TOTAL_N,1), 2))")"
  TIER="$(tier_for_mean "$MEAN_PCT")"

  {
    echo "## Difficulty summary"
    echo
    echo "| Suite | Pass | Trials |"
    echo "|-------|------|--------|"
    echo "| GPT-5.5 | $GPT_PASS | $GPT_TOTAL |"
    echo "| Claude Opus 4.8 | $OPUS_PASS | $OPUS_TOTAL |"
    echo "| **Combined** | **$TOTAL_PASS** | **$TOTAL_N** |"
    echo
    echo "- Mean pass@1: **${MEAN_PCT}%**"
    echo "- Recommended \`task.toml\` difficulty: **\`${TIER}\`**"
    if [[ "$TIER" == "reject_too_easy" ]]; then
      echo "- Action: **harden** the task (100% pass is not a valid Edition 3 difficulty)."
    fi
    echo
    echo '```toml'
    if [[ "$TIER" == "reject_too_easy" ]]; then
      echo "# DO NOT SHIP — measured 100%. Harden and re-measure."
      echo '# difficulty = "frontier"  # provisional after hardening'
    else
      echo "difficulty = \"$TIER\""
    fi
    echo '```'
    echo
  } >>"$REPORT"

  echo
  echo "===== SUMMARY ====="
  echo "GPT-5.5:     $GPT_PASS / $GPT_TOTAL"
  echo "Opus 4.8:    $OPUS_PASS / $OPUS_TOTAL"
  echo "Mean pass@1: ${MEAN_PCT}%"
  echo "Tier:        $TIER"
else
  {
    echo "## Difficulty summary"
    echo
    echo "- Skipped (--validate-only / --skip-difficulty)"
    echo
  } >>"$REPORT"
  echo "==> difficulty skipped"
fi

echo
echo "Report written: $REPORT"
echo "Paste that file into ChatGPT (Difficulty Orchestrator) for harden/soften advice."
echo "Task: $TASK"
echo "Jobs: $JOBS"
