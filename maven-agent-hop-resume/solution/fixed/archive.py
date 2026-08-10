from __future__ import annotations

from engine.paths import ARCHIVE, SECRET_SUFFIXES


def secret_keys(env: dict) -> list[str]:
    return [key for key in env if key.endswith(SECRET_SUFFIXES)]


def write_archive(run_id: str, env: dict, library: dict, lines: list[str]) -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    path = ARCHIVE / f"{run_id}.log"
    redact = bool(library.get("redact_secrets"))
    blocked = set(secret_keys(env)) if redact else set()
    env_lines = []
    for key, value in sorted(env.items()):
        shown = "***" if key in blocked else value
        env_lines.append(f"  {key}={shown}")
    payload = [
        f"run={run_id}",
        f"library={library.get('name')}@{library.get('version')}",
        "env:",
        *env_lines,
        "events:",
        *lines,
        "",
    ]
    path.write_text("\n".join(payload), encoding="utf-8")
