from __future__ import annotations

import json

from engine.paths import AGENTS, KIND_LABEL


def load_agents() -> list[dict]:
    return json.loads(AGENTS.read_text(encoding="utf-8"))["agents"]


def required_label(kind: str) -> str:
    return KIND_LABEL[kind]


def agent_is_legal(agent: dict, kind: str) -> bool:
    return required_label(kind) in agent.get("labels", [])


def select_agent(kind: str) -> dict:
    need = required_label(kind)
    for agent in load_agents():
        if need in agent.get("labels", []):
            return agent
    raise RuntimeError(f"no agent carries required label {need}")
