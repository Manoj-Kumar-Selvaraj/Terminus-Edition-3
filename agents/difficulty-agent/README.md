# Edition 3 Difficulty Agent

ChatGPT alone cannot run official Terminus Edition 3 difficulty. This pack pairs a **ChatGPT orchestrator prompt** with a **local Harbor runner** (WSL/Linux + Docker + `stb`).

Official difficulty = Harbor trials:

| Suite | Command pattern |
|-------|-----------------|
| GPT-5.5 ×5 | `stb harbor run -m @openai/gpt-5.5 -k 5` |
| Claude Opus 4.8 ×5 | `stb harbor run -m @anthropic/claude-opus-4-8 -k 5` |

Accuracy = **mean pass@1 over all 10 runs**.

## Tier table

| Tier | Mean pass@1 |
|------|-------------|
| `frontier` | &lt; 20% |
| `advanced` | 20% – &lt; 50% |
| `core` | 50% – &lt; 80% |
| `base` | 80% – &lt; 100% |
| reject (too easy) | 100% always-pass |

Infra/flaky/env bugs do not count — fix and re-measure.

## Files

| File | Role |
|------|------|
| `CHATGPT_SYSTEM_PROMPT.md` | Paste into Custom GPT / Project instructions |
| `difficulty_from_zip.sh` | Unpack zip (or copy task dir) → oracle/nop → optional GPT×5 + Opus×5 |
| `README.md` | This guide |

## Day-to-day usage

### 1. Configure ChatGPT

1. Create a Custom GPT or Project.
2. Paste the full contents of `CHATGPT_SYSTEM_PROMPT.md` into Instructions / system prompt.
3. Use it to validate zip layout, emit commands, and interpret reports — **not** to invent difficulty from reading the task alone.

### 2. Auth on the Harbor machine (once)

In WSL/Linux (Docker available). If your default distro is `docker-desktop`, use Ubuntu explicitly:

```bash
wsl -d Ubuntu-22.04

# if needed
./Terminus-Edition-3/terminus3.sh install
stb login
stb keys refresh
```

Do **not** hand-set `OPENAI_API_KEY`.

### 3. Run difficulty from a zip

```bash
cd Terminus-Edition-3/agents/difficulty-agent
chmod +x difficulty_from_zip.sh

# Full suite: oracle + nop + GPT×5 + Opus×5
./difficulty_from_zip.sh /path/to/task.zip

# Gate only (smoke / pre-check)
./difficulty_from_zip.sh /path/to/task.zip --validate-only

# Or point at an unpacked task directory
./difficulty_from_zip.sh ../../event-time-session-window-processor --validate-only
```

Jobs and unpack dirs default to Linux FS under `/tmp` (`/tmp/e3-diff-jobs`, `/tmp/e3-diff-work`) to avoid Windows mount issues.

### 4. Feed results back to ChatGPT

The runner writes `DIFFICULTY_REPORT.md` next to the unpacked task root. Paste that report (or job paths under `/tmp/e3-diff-jobs/...`) into the ChatGPT agent for:

- Recommended `difficulty = "..."` in `task.toml`
- Harden vs soften advice grounded in measured pass rates

## Flat zip layout (required)

At zip root (or one single nested task folder):

- `instruction.md`
- `task.toml`
- `environment/`
- `solution/`
- `tests/`

Reject nested junk packages (`runs/`, rubrics-only, multi-task trees). Prefer validating with `./terminus3.sh validate <task>` before a full difficulty spend.

## Options

```text
--validate-only     oracle + nop only
--skip-difficulty   same as --validate-only
--skip-validate     skip oracle/nop (only if already green)
```

Env overrides: `STB_BIN`, `JOBS_ROOT`, `WORK_ROOT`, `STABLE_CWD`.

## Longer roadmap

1. **This pack** — measure real hardness.
2. Later **task-generation agent** — authors tasks, then **must** call this difficulty flow before claiming a tier.

Do not reverse that order.
