#!/usr/bin/env python3
"""Shared provenance and schema helpers for Terminus semantic reviews."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

ROLE_POLICY_VERSIONS = {
    "Task Architect": "1.0",
    "Verifier Engineer": "1.0",
    "Originality & Authenticity Reviewer": "1.0",
    "Difficulty Reviewer": "1.0",
    "Compliance Auditor": "1.0",
    "Instruction Reviewer": "1.0",
    "Engineering Documentation Reviewer": "1.0",
    "Human Quality Reviewer": "1.0",
    "Comprehensive Reviewer": "1.0",
    "Trajectory Analyst": "1.0",
    "Adjudicator": "1.0",
    "Q4 Closure Adjudicator": "1.0",
    "Spec-Test Contract Reviewer": "1.1",
    "Production Logic Auditor": "1.1",
    "Model Perspective Difficulty Simulator": "1.0",
}

ROLE_PROMPT_HEADINGS = {
    "Task Architect": "Task Architect",
    "Verifier Engineer": "Verifier Engineer",
    "Originality & Authenticity Reviewer": "Originality & Authenticity Reviewer",
    "Difficulty Reviewer": "Difficulty Reviewer",
    "Compliance Auditor": "Compliance Auditor",
    "Instruction Reviewer": "Instruction Reviewer",
    "Engineering Documentation Reviewer": "Engineering Documentation Reviewer",
    "Human Quality Reviewer": "Human Quality Reviewer",
    "Comprehensive Reviewer": "Comprehensive Reviewer",
    "Trajectory Analyst": "Trajectory Analyst",
    "Adjudicator": "Adjudicator",
    "Q4 Closure Adjudicator": "Q4 Closure Adjudicator",
    "Spec-Test Contract Reviewer": "Q4 — Spec-Test Contract Reviewer",
    "Production Logic Auditor": "Q6 — Production Logic Auditor",
    "Model Perspective Difficulty Simulator": "Q8 — Model Perspective Difficulty Simulator",
}

QUALITY_REVIEW_ROLES = {
    "Spec-Test Contract Reviewer",
    "Production Logic Auditor",
    "Model Perspective Difficulty Simulator",
}

SCOPE_REUSABLE_ROLES = {"Production Logic Auditor"}

WRITING_ROLES = {
    "Instruction Reviewer",
    "Engineering Documentation Reviewer",
    "Human Quality Reviewer",
}

TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
}


def git(root: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    return result.returncode, result.stdout.strip()


def declared_version(path: Path, label: str) -> str:
    if not path.is_file():
        return ""
    match = re.search(rf"{re.escape(label)}: `([^`]+)`", path.read_text(encoding="utf-8"))
    return match.group(1) if match else ""


def policy_versions(root: Path) -> dict[str, str]:
    t = root / ".terminus"
    return {
        "agent_system": declared_version(t / "AGENT_SYSTEM.md", "Agent-system policy version"),
        "protocol": declared_version(t / "agents" / "PROTOCOL.md", "Policy version"),
        "prompts": declared_version(t / "agents" / "PROMPTS.md", "Prompt policy version"),
        "panel": declared_version(t / "reviewers" / "PRE_LLMAJ.md", "Panel policy version"),
        "comprehensive": declared_version(
            t / "agents" / "COMPREHENSIVE_REVIEWER.md", "Reviewer policy version"
        ),
        "session_schema": declared_version(t / "sessions" / "TEMPLATE.md", "Session schema version"),
        "operating": declared_version(t / "CURSOR_OPERATING.md", "Operating policy version"),
        "invocation": declared_version(t / "agents" / "INVOKE.md", "Invocation policy version"),
        "quality_registry": declared_version(
            t / "agents" / "QUALITY_AGENT_REGISTRY.md", "Quality-agent registry version"
        ),
        "quality_prompts": declared_version(
            t / "agents" / "QUALITY_AGENT_PROMPTS.md", "Quality-agent prompt policy version"
        ),
    }


def markdown_section(text: str, heading: str) -> str:
    """Return one level-2 Markdown section including its heading."""
    pattern = re.compile(rf"(?ms)^## {re.escape(heading)}\s*$.*?(?=^## |\Z)")
    match = pattern.search(text)
    return match.group(0).strip() if match else ""


def role_contract_inputs(root: Path, role: str) -> list[Path]:
    t = root / ".terminus"
    inputs = [
        root / "TERMINUS_3_AI_INSTRUCTIONS.md",
        t / "agents" / "PROTOCOL.md",
        t / "agents" / "PROMPTS.md",
        t / "agents" / "PRODUCTION_AUTHENTICITY.md",
    ]
    if role in QUALITY_REVIEW_ROLES:
        inputs.extend(
            [
                t / "agents" / "QUALITY_AGENT_REGISTRY.md",
                t / "agents" / "QUALITY_AGENT_PROMPTS.md",
            ]
        )
    if role == "Q4 Closure Adjudicator":
        inputs.append(t / "agents" / "Q4_CLOSURE_POLICY.md")
    if role == "Comprehensive Reviewer":
        inputs.extend(
            [
                t / "agents" / "COMPREHENSIVE_REVIEWER.md",
                t / "reviewers" / "REVIEWER_CHECKLIST.md",
                t / "reviewers" / "reviewer_criteria.json",
            ]
        )
    if role in WRITING_ROLES:
        inputs.extend(
            [
                t / "reviewers" / "HUMAN_WRITING_CALIBRATION.md",
                t / "reviewers" / "WRITING_EXAMPLE_BANK.md",
            ]
        )
    if role == "Originality & Authenticity Reviewer":
        inputs.append(t / "GOLDEN_TASKS.md")
    return inputs


def role_contract_hash(root: Path, role: str) -> str:
    """Hash exactly the policy/calibration inputs that govern one reviewer role."""
    t = root / ".terminus"
    prompt_path = t / "agents" / "PROMPTS.md"
    quality_prompt_path = t / "agents" / "QUALITY_AGENT_PROMPTS.md"
    prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    quality_prompt_text = (
        quality_prompt_path.read_text(encoding="utf-8") if quality_prompt_path.is_file() else ""
    )
    heading = ROLE_PROMPT_HEADINGS.get(role, role)
    role_prompt = markdown_section(prompt_text, heading)
    quality_role_prompt = markdown_section(quality_prompt_text, heading)

    h = hashlib.sha256()
    h.update(f"role={role}\nrole_policy={ROLE_POLICY_VERSIONS.get(role, '')}\n".encode())
    for path in role_contract_inputs(root, role):
        h.update(f"\n--- {path.relative_to(root)} ---\n".encode())
        if path == prompt_path:
            h.update(role_prompt.encode("utf-8"))
        elif path == quality_prompt_path:
            h.update(quality_role_prompt.encode("utf-8"))
        elif path.is_file():
            h.update(path.read_bytes())
        else:
            h.update(b"<missing>")
    return h.hexdigest()


def control_plane_commit(root: Path) -> str:
    code, out = git(root, "rev-parse", "HEAD")
    return out if code == 0 else ""


def current_task_commit(root: Path, task: str) -> str:
    code, out = git(root, "log", "-1", "--format=%H", "--", task)
    return out if code == 0 else ""


def task_tree_dirty(root: Path, task: str) -> bool:
    code, out = git(root, "status", "--porcelain", "--", task)
    return code == 0 and bool(out)


def review_scope_paths(root: Path, task: str, role: str) -> list[Path]:
    """Return the conservative task evidence surface eligible for scoped reuse."""
    if role not in SCOPE_REUSABLE_ROLES:
        return []
    root = root.resolve()
    task_root = (root / task).resolve()
    paths: list[Path] = []
    task_toml = task_root / "task.toml"
    if task_toml.is_file():
        paths.append(task_toml)
    environment = task_root / "environment"
    if environment.is_dir():
        for candidate in environment.rglob("*"):
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            try:
                resolved.relative_to(task_root)
            except ValueError as exc:
                raise ValueError(f"scope path escapes task root: {candidate}") from exc
            paths.append(resolved)
    return sorted(set(paths), key=lambda path: path.relative_to(root).as_posix())


def review_scope_hash(root: Path, task: str, role: str) -> str:
    """Hash the role-specific task evidence surface; empty means exact-commit-only."""
    paths = review_scope_paths(root, task, role)
    if not paths:
        return ""
    root = root.resolve()
    h = hashlib.sha256()
    h.update(f"scope-v1\nrole={role}\ntask={task}\n".encode("utf-8"))
    for path in paths:
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        h.update(f"\n--- {rel} {len(data)} ---\n".encode("utf-8"))
        h.update(data)
    return h.hexdigest()


def governing_policy_dirty(root: Path, role: str) -> bool:
    paths = [str(path.relative_to(root)) for path in role_contract_inputs(root, role) if path.exists()]
    if not paths:
        return False
    code, out = git(root, "status", "--porcelain", "--", *paths)
    return code == 0 and bool(out)


def validate_schema(value: object, schema: dict, path: str, out: list[str]) -> None:
    """Validate the JSON-Schema subset used by the control-plane schemas."""
    expected = schema.get("type")
    if expected:
        py_type = TYPE_MAP.get(expected)
        if py_type is None:
            out.append(f"{path}: unsupported schema type {expected!r}")
            return
        if expected == "integer" and isinstance(value, bool):
            out.append(f"{path}: expected integer, found bool")
            return
        if not isinstance(value, py_type):
            out.append(f"{path}: expected {expected}, found {type(value).__name__}")
            return

    if "const" in schema and value != schema["const"]:
        out.append(f"{path}: expected constant {schema['const']!r}, found {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: {value!r} is not one of {schema['enum']}")
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        out.append(f"{path}: shorter than minLength {schema['minLength']}")

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                out.append(f"{path}: missing required field {key!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    out.append(f"{path}: undeclared field {key!r}")
        for key, subschema in properties.items():
            if key in value:
                validate_schema(value[key], subschema, f"{path}.{key}", out)

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            out.append(f"{path}: fewer than minItems {schema['minItems']}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_schema(item, item_schema, f"{path}[{index}]", out)

    for subschema in schema.get("allOf", []):
        condition = subschema.get("if")
        if condition is not None:
            probe: list[str] = []
            validate_schema(value, condition, path, probe)
            if probe:
                continue
            validate_schema(value, subschema.get("then", {}), path, out)
        else:
            validate_schema(value, subschema, path, out)
