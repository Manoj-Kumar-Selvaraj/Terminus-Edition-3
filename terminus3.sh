#!/usr/bin/env bash
# Terminus Edition 3 — local stb/harbor helper.
# Hand-written CLI wrapper. Not a task generator.
#
# Usage:
#   ./terminus3.sh <command> [task] [extra stb args...]
#
# Task may be a folder name under this directory, a relative path, or absolute.
# If omitted where required, you will be prompted / shown the task list.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# uv tool installs land here; keep them reachable in non-login shells.
export PATH="${HOME}/.local/bin:/root/.local/bin:${PATH}"

STB_BIN="${STB_BIN:-stb}"
# Absolute jobs dir avoids pathlib resolve() FileNotFoundError when harbor's
# process cwd disappears mid-trial (common with compose teardown on /mnt/*).
JOBS_DIR="${JOBS_DIR:-$ROOT/jobs}"
mkdir -p "$JOBS_DIR"

# Stable cwd for harbor itself; trial paths stay absolute via -o/--jobs-dir.
STABLE_CWD="${STABLE_CWD:-/tmp/terminus3-cwd}"
mkdir -p "$STABLE_CWD"

run_harbor() {
  # Usage: run_harbor <stb-args...>
  # Execute harbor with a durable cwd. Callers must pass -o/--jobs-dir themselves
  # (or rely on the wrappers below).
  ( cd "$STABLE_CWD" && "$STB_BIN" "$@" )
}

die() { echo "error: $*" >&2; exit 1; }
need_stb() {
  if ! command -v "$STB_BIN" >/dev/null 2>&1; then
    die "stb not found on PATH.
Install with:
  $0 install
Or set STB_BIN to the full path of the stb binary."
  fi
}

list_tasks() {
  find "$ROOT" -mindepth 1 -maxdepth 1 -type d ! -name '.*' -printf '%f\n' 2>/dev/null \
    | while read -r name; do
        [[ -f "$ROOT/$name/task.toml" ]] && echo "$name"
      done \
    | sort
}

resolve_task() {
  local raw="${1:-}"
  if [[ -z "$raw" ]]; then
    die "task required.
Known tasks:
$(list_tasks | sed 's/^/  /')
Usage: $0 <command> <task>"
  fi

  local cand=""
  if [[ -d "$raw" && -f "$raw/task.toml" ]]; then
    cand="$(cd "$raw" && pwd)"
  elif [[ -d "$ROOT/$raw" && -f "$ROOT/$raw/task.toml" ]]; then
    cand="$ROOT/$raw"
  elif [[ -f "$raw/task.toml" ]]; then
    cand="$(cd "$raw" && pwd)"
  else
    die "not a Terminus task folder: $raw
Expected a directory containing task.toml.
Known tasks:
$(list_tasks | sed 's/^/  /')"
  fi
  printf '%s\n' "$cand"
}

usage() {
  cat <<'EOF'
Terminus Edition 3 — stb/harbor helper

Usage:
  ./terminus3.sh <command> [task] [extra args...]

Setup / auth
  install              Install/upgrade snorkelai-stb via uv
  login                stb login
  keys-refresh         stb keys refresh
  keys-show            stb keys show
  version              Show stb version

Task discovery
  list                 List local Edition-3 tasks
  path <task>          Print absolute task path

Validation
  oracle <task>        stb harbor run -a oracle -p <task>
  nop <task>           stb harbor run -a nop -p <task>
  check <task>         stb harbor check <task>  (LLMaJ; needs IS_SANDBOX=1 if root)
  check-llm <task>     stb harbor check <task> -m claude-sonnet-4-6
  validate <task>      oracle + nop + check (sequential)

Debug
  env <task>           stb harbor tasks start-env -p <task> -i

Difficulty measurement
  diff-gpt <task>      GPT-5.5 ×5   (-m @openai/gpt-5.5 -k 5)
  diff-claude <task>   Claude Opus 4.8 ×5 (-m @anthropic/claude-opus-4-8 -k 5)
  difficulty <task>    Run both difficulty suites sequentially

Convenience
  all-oracle           Run oracle on every local task
  all-check            Run harbor check on every local task
  help                 Show this help

Extra args after <task> are forwarded to stb.
Examples:
  ./terminus3.sh oracle ansible-ci-control-plane
  ./terminus3.sh check freight-triage-polyglot-ledger-recovery
  ./terminus3.sh diff-gpt ansible-ci-control-plane -- --some-stb-flag
  ./terminus3.sh validate terraform-aws-eks-weekend-fleet-cutover-plan

Environment:
  STB_BIN   Override stb binary (default: stb)
EOF
}

cmd_install() {
  if ! command -v uv >/dev/null 2>&1; then
    die "uv not found. Install uv first: https://docs.astral.sh/uv/"
  fi
  echo "==> Installing snorkelai-stb with uv"
  uv tool install snorkelai-stb \
    --find-links https://snorkel-python-wheels.s3.us-west-2.amazonaws.com/stb/index.html \
    --python ">=3.12" \
    --force
  echo "==> Done. Ensure ~/.local/bin (or uv tool bin dir) is on PATH."
  command -v stb && stb --version || true
}

cmd_oracle() {
  need_stb
  local task; task="$(resolve_task "${1:?task required}")"
  shift || true
  echo "==> oracle: $task"
  echo "    jobs-dir: $JOBS_DIR"
  run_harbor harbor run -a oracle -p "$task" -o "$JOBS_DIR" "$@"
}

cmd_nop() {
  need_stb
  local task; task="$(resolve_task "${1:?task required}")"
  shift || true
  echo "==> nop: $task"
  echo "    jobs-dir: $JOBS_DIR"
  run_harbor harbor run -a nop -p "$task" -o "$JOBS_DIR" "$@"
}

cmd_check() {
  need_stb
  local task; task="$(resolve_task "${1:?task required}")"
  shift || true
  # harbor tasks check was removed; harbor check is the LLMaJ entrypoint.
  if [ "$(id -u)" -eq 0 ] && [ -z "${IS_SANDBOX:-}" ]; then
    export IS_SANDBOX=1
    echo "==> harbor check (IS_SANDBOX=1 for root): $task"
  else
    echo "==> harbor check: $task"
  fi
  "$STB_BIN" harbor check "$task" "$@"
}

cmd_check_llm() {
  need_stb
  local task; task="$(resolve_task "${1:?task required}")"
  shift || true
  if [ "$(id -u)" -eq 0 ] && [ -z "${IS_SANDBOX:-}" ]; then
    export IS_SANDBOX=1
    echo "==> harbor check LLM (IS_SANDBOX=1 for root): $task"
  else
    echo "==> harbor check LLM: $task"
  fi
  # Short alias "sonnet" currently resolves to a bad model id via Claude Code.
  "$STB_BIN" harbor check "$task" -m claude-sonnet-4-6 "$@"
}

cmd_validate() {
  need_stb
  local task_arg="${1:?task required}"
  shift || true
  local task; task="$(resolve_task "$task_arg")"
  echo "==> validate: $task"
  echo "---- oracle ----"
  run_harbor harbor run -a oracle -p "$task" -o "$JOBS_DIR" "$@"
  echo "---- nop ----"
  run_harbor harbor run -a nop -p "$task" -o "$JOBS_DIR" "$@"
  echo "---- check ----"
  if [ "$(id -u)" -eq 0 ] && [ -z "${IS_SANDBOX:-}" ]; then
    export IS_SANDBOX=1
  fi
  "$STB_BIN" harbor check "$task" -m claude-sonnet-4-6
  echo "==> validate finished for $(basename "$task")"
}

cmd_env() {
  need_stb
  local task; task="$(resolve_task "${1:?task required}")"
  shift || true
  echo "==> start-env: $task"
  "$STB_BIN" harbor tasks start-env -p "$task" -i "$@"
}

cmd_diff_gpt() {
  need_stb
  local task; task="$(resolve_task "${1:?task required}")"
  shift || true
  echo "==> difficulty GPT-5.5 x5: $task"
  run_harbor harbor run -m @openai/gpt-5.5 -p "$task" -k 5 -o "$JOBS_DIR" "$@"
}

cmd_diff_claude() {
  need_stb
  local task; task="$(resolve_task "${1:?task required}")"
  shift || true
  echo "==> difficulty Claude Opus 4.8 x5: $task"
  run_harbor harbor run -m @anthropic/claude-opus-4-8 -p "$task" -k 5 -o "$JOBS_DIR" "$@"
}

cmd_difficulty() {
  need_stb
  local task_arg="${1:?task required}"
  shift || true
  local task; task="$(resolve_task "$task_arg")"
  echo "==> full difficulty suite: $task"
  echo "---- GPT-5.5 x5 ----"
  run_harbor harbor run -m @openai/gpt-5.5 -p "$task" -k 5 -o "$JOBS_DIR" "$@"
  echo "---- Claude Opus 4.8 x5 ----"
  run_harbor harbor run -m @anthropic/claude-opus-4-8 -p "$task" -k 5 -o "$JOBS_DIR" "$@"
}

cmd_all_oracle() {
  need_stb
  local t
  while IFS= read -r t; do
    [[ -z "$t" ]] && continue
    echo "======== oracle: $t ========"
    run_harbor harbor run -a oracle -p "$ROOT/$t" -o "$JOBS_DIR" "$@" || echo "FAILED: $t"
  done < <(list_tasks)
}

cmd_all_check() {
  need_stb
  if [ "$(id -u)" -eq 0 ] && [ -z "${IS_SANDBOX:-}" ]; then
    export IS_SANDBOX=1
  fi
  local t
  while IFS= read -r t; do
    [[ -z "$t" ]] && continue
    echo "======== check: $t ========"
    "$STB_BIN" harbor check "$ROOT/$t" -m claude-sonnet-4-6 "$@" || echo "FAILED: $t"
  done < <(list_tasks)
}

main() {
  local cmd="${1:-help}"
  shift || true

  case "$cmd" in
    help|-h|--help) usage ;;
    list|ls) list_tasks ;;
    path)
      resolve_task "${1:?task required}"
      ;;
    install) cmd_install "$@" ;;
    login) need_stb; "$STB_BIN" login "$@" ;;
    keys-refresh) need_stb; "$STB_BIN" keys refresh "$@" ;;
    keys-show) need_stb; "$STB_BIN" keys show "$@" ;;
    version) need_stb; "$STB_BIN" --version "$@" ;;
    oracle) cmd_oracle "$@" ;;
    nop) cmd_nop "$@" ;;
    check) cmd_check "$@" ;;
    check-llm) cmd_check_llm "$@" ;;
    validate) cmd_validate "$@" ;;
    env|start-env) cmd_env "$@" ;;
    diff-gpt|gpt) cmd_diff_gpt "$@" ;;
    diff-claude|claude) cmd_diff_claude "$@" ;;
    difficulty|diff) cmd_difficulty "$@" ;;
    all-oracle) cmd_all_oracle "$@" ;;
    all-check) cmd_all_check "$@" ;;
    *)
      die "unknown command: $cmd
Run: $0 help"
      ;;
  esac
}

main "$@"
