from __future__ import annotations

from engine.paths import ARCHIVE, SECRET_SUFFIXES


def secret_keys(env: dict) -> list[str]:
    return [key for key in env if key.endswith(SECRET_SUFFIXES)]


def write_archive(run_id: str, env: dict, library: dict, lines: list[str]) -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    path = ARCHIVE / f"{run_id}.log"
    # Starter: dump the live environment, including nexus/build secrets.
    payload = [
        f"run={run_id}",
        f"library={library.get('name')}@{library.get('version')}",
        "env:",
        *[f"  {key}={value}" for key, value in sorted(env.items())],
        "events:",
        *lines,
        "",
    ]
    path.write_text("\n".join(payload), encoding="utf-8")
