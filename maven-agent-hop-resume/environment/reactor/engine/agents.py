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
    # Starter: hop maven work onto the docker pool whenever it exists.
    agents = load_agents()
    if kind == "scm":
        for agent in agents:
            if "linux" in agent["labels"] and "maven" not in agent["labels"] and "docker" not in agent["labels"]:
                return agent
        return agents[0]
    for agent in agents:
        if "docker" in agent["labels"]:
            return agent
    return agents[-1]
