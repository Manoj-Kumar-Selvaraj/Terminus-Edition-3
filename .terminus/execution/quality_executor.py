"""Packet-bound Terminus Q execution with exactly one Cursor or API backend.

The runner projects only packet-authorized task/control-plane snapshots, hides git
history and previous reviews, performs one fresh backend execution with no fallback,
and independently validates the persisted schema-v3 review before publication.
"""

from __future__ import annotations

import fnmatch
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

Q4_ROLE = "Spec-Test Contract Reviewer"
Q6_ROLE = "Production Logic Auditor"
Q8_ROLE = "Model Perspective Difficulty Simulator"
QUALITY_ROLES = frozenset({Q4_ROLE, Q6_ROLE, Q8_ROLE})
SUPPORTED_EXECUTORS = frozenset({"cursor", "api"})
SUPPORTED_API_PROVIDERS = frozenset({"openai", "anthropic"})
REVIEW_SCHEMA = ".terminus/agents/schemas/review_result.schema.json"
MAX_FILE_BYTES = 2_000_000
MAX_READ_CHARS = 120_000
MAX_LIST_FILES = 800
MAX_GREP_RESULTS = 200
MAX_API_ROUNDS = 80
MAX_API_TOOL_CALLS = 300
Q4_INTERFACE_SUFFIXES = frozenset(
    {".h", ".hh", ".hpp", ".md", ".rst", ".txt", ".proto", ".json", ".yaml", ".yml", ".toml"}
)
Q4_INTERFACE_NAMES = frozenset({"Dockerfile", "Makefile", ".dockerignore"})


class QualityExecutorError(RuntimeError):
    """Fail-closed quality-executor error."""


@dataclass(frozen=True)
class QualitySelection:
    executor: str
    provider: str | None
    model: str


@dataclass(frozen=True)
class Projection:
    root: Path
    packet_path: Path
    review_path: Path
    baseline: Mapping[str, str]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def safe_relative(value: str, *, label: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise QualityExecutorError(f"{label} must be a safe repository-relative path")
    return path


def safe_child(root: Path, relative: Path) -> Path:
    target = (root / relative).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise QualityExecutorError(f"path escapes projected workspace: {relative}") from exc
    return target


def load_packet(root: Path, packet_path: str | Path) -> tuple[Path, dict[str, Any]]:
    root = root.resolve()
    relative = safe_relative(str(packet_path), label="packet path")
    absolute = safe_child(root, relative)
    if not absolute.is_file():
        raise QualityExecutorError(f"packet does not exist: {relative.as_posix()}")
    try:
        packet = json.loads(absolute.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QualityExecutorError(f"packet is invalid JSON: {exc}") from exc
    if not isinstance(packet, dict):
        raise QualityExecutorError("packet must contain one JSON object")

    required = {
        "schema_version",
        "review_id",
        "protocol_policy_version",
        "prompt_policy_version",
        "role_policy_version",
        "control_plane_commit",
        "role_contract_hash",
        "task",
        "task_commit",
        "role",
        "authoritative_rules",
        "evidence_allowed",
        "evidence_excluded",
        "prior_verdicts_visible",
        "output_schema",
        "review_output_path",
    }
    missing = required - set(packet)
    if missing:
        raise QualityExecutorError(f"packet missing fields: {sorted(missing)}")
    if packet["schema_version"] != "3.0":
        raise QualityExecutorError("quality executor requires schema-v3 review packets")
    if packet["role"] not in QUALITY_ROLES:
        raise QualityExecutorError(f"unsupported packet role: {packet['role']!r}")
    task = str(packet["task"])
    if not task or task.startswith(".") or "/" in task or "\\" in task or ".." in task:
        raise QualityExecutorError("packet task must be one safe top-level task directory")
    for field in ("task_commit", "control_plane_commit"):
        if not re.fullmatch(r"[0-9a-fA-F]{40}", str(packet[field])):
            raise QualityExecutorError(f"packet {field} must be a full git SHA")
    if packet["output_schema"] != REVIEW_SCHEMA:
        raise QualityExecutorError("packet must use the canonical schema-v3 review schema")
    if packet["prior_verdicts_visible"] is not False:
        raise QualityExecutorError("fresh quality execution requires prior_verdicts_visible=false")
    if not isinstance(packet["authoritative_rules"], list) or not packet["authoritative_rules"]:
        raise QualityExecutorError("packet authoritative_rules must be a non-empty array")
    if not isinstance(packet["evidence_allowed"], list) or not isinstance(
        packet["evidence_excluded"], list
    ):
        raise QualityExecutorError("packet evidence boundaries must be arrays")

    review_rel = safe_relative(str(packet["review_output_path"]), label="review_output_path")
    expected_parent = Path(".terminus") / "reviews" / task / str(packet["task_commit"])[:8]
    if review_rel.parent != expected_parent or review_rel.suffix != ".json":
        raise QualityExecutorError("review_output_path is not bound to task/task-commit")
    expected_packet = review_rel.with_name(review_rel.stem + ".packet.json")
    if relative != expected_packet:
        raise QualityExecutorError("packet path does not match review_output_path identity")
    return relative, packet


def select_backend(
    packet: Mapping[str, Any],
    *,
    executor: str,
    provider: str | None = None,
    model: str | None = None,
) -> QualitySelection:
    executor = executor.strip().lower()
    provider = provider.strip().lower() if provider else None
    model = model.strip() if model else ""
    if executor not in SUPPORTED_EXECUTORS:
        raise QualityExecutorError(f"executor must be one of {sorted(SUPPORTED_EXECUTORS)}")
    if executor == "cursor":
        if packet["role"] == Q8_ROLE:
            raise QualityExecutorError("difficulty simulation is API-key-only; Cursor is forbidden")
        if provider or model:
            raise QualityExecutorError("Cursor Q execution fixes model=auto; provider/model overrides are forbidden")
        return QualitySelection("cursor", None, "auto")
    if provider not in SUPPORTED_API_PROVIDERS:
        raise QualityExecutorError(
            f"API executor requires exactly one provider from {sorted(SUPPORTED_API_PROVIDERS)}"
        )
    if not model:
        raise QualityExecutorError("API executor requires an explicit provider model")
    return QualitySelection("api", provider, model)


def require_commit(root: Path, commit: str, label: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise QualityExecutorError(f"{label} commit is unavailable: {commit}")


def archive_bytes(root: Path, commit: str, paths: list[str]) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), "archive", "--format=tar", commit, "--", *paths],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise QualityExecutorError(f"git archive failed for {commit[:12]}: {detail}")
    return result.stdout


def extract_tar(data: bytes, destination: Path) -> None:
    destination = destination.resolve()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            try:
                target.relative_to(destination)
            except ValueError as exc:
                raise QualityExecutorError(f"archive path escapes workspace: {member.name}") from exc
            if member.issym() or member.islnk():
                raise QualityExecutorError(f"archive link is not allowed: {member.name}")
        archive.extractall(destination)


def git_object_exists(root: Path, spec: str) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", spec],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def git_list_files(root: Path, commit: str, prefix: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", commit, "--", prefix],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise QualityExecutorError(f"could not enumerate packet evidence under {prefix}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def q4_interface_paths(root: Path, packet: Mapping[str, Any]) -> list[str]:
    task = str(packet["task"])
    commit = str(packet["task_commit"])
    prefix = f"{task}/environment/"
    paths: list[str] = []
    for path in git_list_files(root, commit, f"{task}/environment"):
        relative = path[len(prefix) :] if path.startswith(prefix) else path
        candidate = Path(relative)
        if (
            candidate.name in Q4_INTERFACE_NAMES
            or candidate.suffix.lower() in Q4_INTERFACE_SUFFIXES
            or "docs" in {part.lower() for part in candidate.parts}
        ):
            paths.append(path)
    return paths


def task_projection_paths(root: Path, packet: Mapping[str, Any]) -> list[str]:
    task = str(packet["task"])
    commit = str(packet["task_commit"])
    role = str(packet["role"])
    if role == Q4_ROLE:
        candidates = [
            f"{task}/instruction.md",
            f"{task}/task.toml",
            f"{task}/tests",
        ]
    elif role == Q6_ROLE:
        candidates = [f"{task}/task.toml", f"{task}/environment"]
    else:
        candidates = [
            f"{task}/instruction.md",
            f"{task}/task.toml",
            f"{task}/environment",
        ]
    paths = [path for path in candidates if git_object_exists(root, f"{commit}:{path}")]
    if role == Q4_ROLE:
        paths.extend(q4_interface_paths(root, packet))
    if not paths:
        raise QualityExecutorError("packet task snapshot contains no role-authorized evidence")
    return sorted(set(paths))


def hash_files(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            hashes[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def materialize_projection(
    root: Path,
    packet_relative: Path,
    packet: Mapping[str, Any],
    destination: Path,
) -> Projection:
    root = root.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    task_commit = str(packet["task_commit"])
    control_commit = str(packet["control_plane_commit"])
    require_commit(root, task_commit, "task")
    require_commit(root, control_commit, "control-plane")

    extract_tar(archive_bytes(root, task_commit, task_projection_paths(root, packet)), destination)
    if packet["role"] == Q4_ROLE:
        test_map = f".terminus/designs/{packet['task']}-test-map.json"
        if git_object_exists(root, f"{task_commit}:{test_map}"):
            extract_tar(archive_bytes(root, task_commit, [test_map]), destination)
    elif packet["role"] == Q6_ROLE:
        report_candidates = [
            f".terminus/designs/{packet['task']}-production.json",
            f".terminus/designs/{packet['task']}-runtime-authenticity.json",
            f".terminus/designs/{packet['task']}-complexity.json",
        ]
        reports = [
            path for path in report_candidates if git_object_exists(root, f"{task_commit}:{path}")
        ]
        if reports:
            extract_tar(archive_bytes(root, task_commit, reports), destination)

    # The complete agent-policy subtree is projected from the control-plane commit so
    # transitive mandatory policy reads cannot silently fall back to task history.
    control_paths = [
        "TERMINUS_3_AI_INSTRUCTIONS.md",
        ".terminus/AGENT_SYSTEM.md",
        ".terminus/agents",
    ]
    extract_tar(archive_bytes(root, control_commit, control_paths), destination)

    packet_source = safe_child(root, packet_relative)
    packet_target = safe_child(destination, packet_relative)
    packet_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(packet_source, packet_target)
    review_rel = safe_relative(str(packet["review_output_path"]), label="review output")
    review_target = safe_child(destination, review_rel)
    review_target.unlink(missing_ok=True)

    # No git history, prior review directory, solution, or project-level model rules
    # are present in the generated workspace.
    for side_context in (".cursor", "AGENTS.md", "CLAUDE.md", ".cursorrules"):
        candidate = destination / side_context
        if candidate.is_dir():
            shutil.rmtree(candidate)
        elif candidate.exists():
            candidate.unlink()

    return Projection(
        root=destination.resolve(),
        packet_path=packet_target,
        review_path=review_target,
        baseline=hash_files(destination),
    )


def minimal_prompt(packet_relative: Path) -> str:
    return (
        "Execute exactly the Terminus quality review defined by:\n\n"
        f"{packet_relative.as_posix()}\n\n"
        "The packet and its referenced authoritative rules are the sole controlling instructions.\n\n"
        "Review only packet-authorized evidence in this workspace. Do not use prior review "
        "conclusions, excluded evidence, sibling repositories, git history, branches, remotes, "
        "or chat memory.\n\n"
        "Minimize fresh input tokens, output tokens, redundant reads/tool calls, and elapsed time "
        "without compromising accuracy, completeness, independence, evidence coverage, or required "
        "review depth. Never trade correctness for efficiency.\n\n"
        "Do not narrate progress or intermediate reasoning. Do not perform producer remediation.\n\n"
        "Persist the complete required schema-v3 result at the packet-defined output path. The "
        "persisted JSON is canonical. Final human-facing output should be only PASS, REVISE "
        "<blocking-count>, or the packet-authorized non-ready verdict when evidence is insufficient.\n"
    )


def workspace_changes(projection: Projection) -> list[str]:
    current = hash_files(projection.root)
    review_rel = projection.review_path.relative_to(projection.root).as_posix()
    return sorted(
        path
        for path in set(projection.baseline) | set(current)
        if path != review_rel and projection.baseline.get(path) != current.get(path)
    )


def validate_schema(review: Mapping[str, Any], schema_path: Path) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise QualityExecutorError("jsonschema is required for deterministic review validation") from exc
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(review), key=lambda item: list(item.absolute_path))
    if errors:
        details = "; ".join(
            f"{'.'.join(map(str, error.absolute_path)) or '$'}: {error.message}"
            for error in errors[:20]
        )
        raise QualityExecutorError(f"review schema validation failed: {details}")


def validate_review_result(projection: Projection, packet: Mapping[str, Any]) -> dict[str, Any]:
    if not projection.review_path.is_file():
        raise QualityExecutorError("executor did not persist the packet-defined review artifact")
    try:
        review = json.loads(projection.review_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QualityExecutorError(f"persisted review is invalid JSON: {exc}") from exc
    if not isinstance(review, dict):
        raise QualityExecutorError("persisted review must contain one JSON object")
    validate_schema(review, projection.root / REVIEW_SCHEMA)

    bindings = {
        "schema_version": packet["schema_version"],
        "review_id": packet["review_id"],
        "role": packet["role"],
        "task": packet["task"],
        "task_commit": packet["task_commit"],
        "control_plane_commit": packet["control_plane_commit"],
        "protocol_policy_version": packet["protocol_policy_version"],
        "prompt_policy_version": packet["prompt_policy_version"],
        "role_policy_version": packet["role_policy_version"],
        "role_contract_hash": packet["role_contract_hash"],
    }
    if "review_scope_hash" in packet:
        bindings["review_scope_hash"] = packet["review_scope_hash"]
    for field, expected in bindings.items():
        if review.get(field) != expected:
            raise QualityExecutorError(
                f"review {field} is not packet-bound: {review.get(field)!r} != {expected!r}"
            )
    expected_context = projection.packet_path.relative_to(projection.root).as_posix()
    if review.get("context_packet") != expected_context:
        raise QualityExecutorError("review context_packet does not match the exact packet path")

    finding_ids = [str(item.get("id", "")) for item in review.get("findings", [])]
    if "" in finding_ids or len(finding_ids) != len(set(finding_ids)):
        raise QualityExecutorError("review finding IDs must be unique and non-empty")
    if review["role"] == Q4_ROLE:
        role_output = review.get("role_output", {})
        blocking = set(role_output.get("BLOCKING_FINDING_IDS", []))
        advisory = set(role_output.get("ADVISORY_FINDING_IDS", []))
        if blocking & advisory or set(finding_ids) != blocking | advisory:
            raise QualityExecutorError("Q4 must classify every finding exactly once")
        if review["verdict"] == "REVISE" and not blocking:
            raise QualityExecutorError("Q4 REVISE requires at least one blocking finding")
        if review["verdict"] == "PASS":
            exhaustive = role_output.get("EXHAUSTIVENESS", {})
            required = {
                "REQUIREMENTS_ENUMERATED": "COMPLETE",
                "VERIFIER_BEHAVIORS_ENUMERATED": "COMPLETE",
                "FORWARD_MATRIX_COMPLETE": "YES",
                "REVERSE_MATRIX_COMPLETE": "YES",
                "DELEGATED_CONTRACTS_COMPLETE": "YES",
                "P2P_BOUNDARIES_COMPLETE": "YES",
                "F2P_BOUNDARIES_COMPLETE": "YES",
                "OUTPUT_INTERFACES_COMPLETE": "YES",
                "SECOND_PASS_OMISSION_SWEEP": "PASS",
            }
            if blocking:
                raise QualityExecutorError("Q4 PASS cannot contain blocking findings")
            for field, expected in required.items():
                if exhaustive.get(field) != expected:
                    raise QualityExecutorError(f"Q4 PASS requires {field}={expected}")
            if exhaustive.get("UNINSPECTED_SCOPE"):
                raise QualityExecutorError("Q4 PASS cannot contain uninspected scope")

    changed = workspace_changes(projection)
    if changed:
        raise QualityExecutorError(
            "quality executor modified files outside review_output_path: " + ", ".join(changed)
        )
    return review


class WorkspaceTools:
    """Read-only API model tools plus exactly one review-output sink."""

    def __init__(self, projection: Projection):
        self.projection = projection
        self.tool_calls = 0
        self.review_written = False

    def count(self) -> None:
        self.tool_calls += 1
        if self.tool_calls > MAX_API_TOOL_CALLS:
            raise QualityExecutorError("API executor exceeded tool-call budget")

    def path(self, value: str) -> Path:
        if value in {"", "."}:
            return self.projection.root
        return safe_child(self.projection.root, safe_relative(value, label="tool path"))

    def list_files(self, pattern: str = "**/*") -> dict[str, Any]:
        self.count()
        files = [
            path.relative_to(self.projection.root).as_posix()
            for path in sorted(self.projection.root.rglob("*"))
            if path.is_file()
            and fnmatch.fnmatch(path.relative_to(self.projection.root).as_posix(), pattern)
        ]
        return {"files": files[:MAX_LIST_FILES], "truncated": len(files) > MAX_LIST_FILES}

    def read_file(self, path: str, start_line: int = 1, end_line: int = 400) -> dict[str, Any]:
        self.count()
        target = self.path(path)
        if not target.is_file():
            return {"error": "not a file"}
        if target.stat().st_size > MAX_FILE_BYTES:
            return {"error": "file exceeds 2 MB read limit"}
        start = max(1, int(start_line))
        end = max(start, min(int(end_line), start + 499))
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        selected = lines[start - 1 : end]
        rendered = "\n".join(
            f"{number}: {line}" for number, line in enumerate(selected, start=start)
        )
        return {
            "path": target.relative_to(self.projection.root).as_posix(),
            "start_line": start,
            "end_line": min(end, len(lines)),
            "total_lines": len(lines),
            "content": rendered[:MAX_READ_CHARS],
            "truncated": len(rendered) > MAX_READ_CHARS,
        }

    def grep(self, pattern: str, path: str = ".", glob: str = "*") -> dict[str, Any]:
        self.count()
        base = self.path(path)
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            return {"error": f"invalid regex: {exc}"}
        candidates = [base] if base.is_file() else sorted(base.rglob("*"))
        matches: list[dict[str, Any]] = []
        for candidate in candidates:
            if not candidate.is_file() or candidate.stat().st_size > MAX_FILE_BYTES:
                continue
            rel = candidate.relative_to(self.projection.root).as_posix()
            if not fnmatch.fnmatch(candidate.name, glob) and not fnmatch.fnmatch(rel, glob):
                continue
            try:
                lines = candidate.read_text(encoding="utf-8", errors="strict").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(lines, 1):
                if regex.search(line):
                    matches.append({"path": rel, "line": number, "text": line[:1200]})
                    if len(matches) >= MAX_GREP_RESULTS:
                        return {"matches": matches, "truncated": True}
        return {"matches": matches, "truncated": False}

    def write_review(self, review: Mapping[str, Any]) -> dict[str, Any]:
        self.count()
        if self.review_written:
            raise QualityExecutorError("write_review may be called exactly once")
        self.projection.review_path.parent.mkdir(parents=True, exist_ok=True)
        self.projection.review_path.write_text(
            json.dumps(dict(review), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self.review_written = True
        return {
            "status": "persisted",
            "path": self.projection.review_path.relative_to(self.projection.root).as_posix(),
        }

    def dispatch(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if name == "list_files":
            return self.list_files(str(arguments.get("glob", "**/*")))
        if name == "read_file":
            return self.read_file(
                str(arguments.get("path", "")),
                int(arguments.get("start_line", 1)),
                int(arguments.get("end_line", 400)),
            )
        if name == "grep":
            return self.grep(
                str(arguments.get("pattern", "")),
                str(arguments.get("path", ".")),
                str(arguments.get("glob", "*")),
            )
        if name == "write_review":
            review = arguments.get("review")
            if not isinstance(review, Mapping):
                raise QualityExecutorError("write_review requires a review object")
            return self.write_review(review)
        raise QualityExecutorError(f"unknown API tool: {name}")


def openai_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": "list_files",
            "description": "List projected workspace files. Prefer narrow globs.",
            "parameters": {
                "type": "object",
                "properties": {"glob": {"type": "string"}},
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "read_file",
            "description": "Read at most 500 lines from one projected file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "grep",
            "description": "Regex search projected text files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "glob": {"type": "string"},
                },
                "required": ["pattern"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "write_review",
            "description": "Persist the complete packet-bound schema-v3 review exactly once.",
            "parameters": {
                "type": "object",
                "properties": {"review": {"type": "object", "additionalProperties": True}},
                "required": ["review"],
                "additionalProperties": False,
            },
        },
    ]


def anthropic_tools() -> list[dict[str, Any]]:
    return [
        {"name": item["name"], "description": item["description"], "input_schema": item["parameters"]}
        for item in openai_tools()
    ]


def cache_key(packet: Mapping[str, Any]) -> str:
    role = re.sub(r"[^a-z0-9]+", "-", str(packet["role"]).lower()).strip("-")
    return f"terminus-{role}-{str(packet['role_contract_hash'])[:24]}"


def run_openai(
    projection: Projection,
    packet_relative: Path,
    packet: Mapping[str, Any],
    model: str,
) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise QualityExecutorError("openai package is required for provider=openai") from exc
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise QualityExecutorError("OPENAI_API_KEY is required for provider=openai")
    tools = WorkspaceTools(projection)
    client = OpenAI(api_key=api_key)
    instructions = (
        "You are the packet-bound Terminus quality executor. Use only supplied workspace tools. "
        "Never expose or persist private chain-of-thought."
    )
    input_items: list[Any] = [{"role": "user", "content": minimal_prompt(packet_relative)}]
    usage = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    for _round in range(MAX_API_ROUNDS):
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=input_items,
            tools=openai_tools(),
            store=False,
            prompt_cache_key=cache_key(packet),
            prompt_cache_retention="24h",
        )
        if response.usage is not None:
            usage["input_tokens"] += int(getattr(response.usage, "input_tokens", 0) or 0)
            usage["output_tokens"] += int(getattr(response.usage, "output_tokens", 0) or 0)
            details = getattr(response.usage, "input_tokens_details", None)
            usage["cached_input_tokens"] += int(getattr(details, "cached_tokens", 0) or 0)
        calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]
        input_items.extend(response.output)
        if not calls:
            if tools.review_written:
                return {
                    "provider": "openai",
                    "model": model,
                    "usage": usage,
                    "tool_calls": tools.tool_calls,
                }
            raise QualityExecutorError("OpenAI executor stopped before write_review")
        for call in calls:
            try:
                arguments = json.loads(call.arguments)
            except json.JSONDecodeError as exc:
                raise QualityExecutorError(f"OpenAI tool arguments are invalid JSON: {exc}") from exc
            result = tools.dispatch(call.name, arguments)
            input_items.append(
                {"type": "function_call_output", "call_id": call.call_id, "output": canonical_json(result)}
            )
        if tools.review_written:
            return {
                "provider": "openai",
                "model": model,
                "usage": usage,
                "tool_calls": tools.tool_calls,
            }
    raise QualityExecutorError("OpenAI executor exceeded model-round budget")


def block_dict(block: Any) -> dict[str, Any]:
    if hasattr(block, "model_dump"):
        return block.model_dump(exclude_none=True)
    if isinstance(block, Mapping):
        return dict(block)
    raise QualityExecutorError("unsupported Anthropic content block")


def run_anthropic(
    projection: Projection,
    packet_relative: Path,
    packet: Mapping[str, Any],
    model: str,
) -> dict[str, Any]:
    del packet
    try:
        import anthropic
    except ImportError as exc:
        raise QualityExecutorError("anthropic package is required for provider=anthropic") from exc
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise QualityExecutorError("ANTHROPIC_API_KEY is required for provider=anthropic")
    tools = WorkspaceTools(projection)
    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict[str, Any]] = [{"role": "user", "content": minimal_prompt(packet_relative)}]
    system = [
        {
            "type": "text",
            "text": (
                "You are the packet-bound Terminus quality executor. Use only supplied workspace "
                "tools. Never expose or persist private chain-of-thought."
            ),
            "cache_control": {"type": "ephemeral"},
        }
    ]
    usage = {
        "input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "output_tokens": 0,
    }
    for _round in range(MAX_API_ROUNDS):
        response = client.messages.create(
            model=model,
            max_tokens=16_000,
            system=system,
            messages=messages,
            tools=anthropic_tools(),
            tool_choice={"type": "auto"},
        )
        for field in usage:
            usage[field] += int(getattr(response.usage, field, 0) or 0)
        blocks = [block_dict(block) for block in response.content]
        messages.append({"role": "assistant", "content": blocks})
        calls = [block for block in blocks if block.get("type") == "tool_use"]
        if not calls:
            if tools.review_written:
                return {
                    "provider": "anthropic",
                    "model": model,
                    "usage": usage,
                    "tool_calls": tools.tool_calls,
                }
            raise QualityExecutorError("Anthropic executor stopped before write_review")
        results: list[dict[str, Any]] = []
        for call in calls:
            arguments = call.get("input", {})
            if not isinstance(arguments, Mapping):
                raise QualityExecutorError("Anthropic tool input must be an object")
            result = tools.dispatch(str(call.get("name", "")), arguments)
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call["id"],
                    "content": canonical_json(result),
                }
            )
        if tools.review_written:
            return {
                "provider": "anthropic",
                "model": model,
                "usage": usage,
                "tool_calls": tools.tool_calls,
            }
        messages.append({"role": "user", "content": results})
    raise QualityExecutorError("Anthropic executor exceeded model-round budget")


def run_cursor(
    projection: Projection,
    packet_relative: Path,
    *,
    timeout_seconds: int,
    diagnostic_path: Path | None = None,
) -> dict[str, Any]:
    api_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not api_key:
        raise QualityExecutorError("CURSOR_API_KEY is required for Cursor execution")
    executable = shutil.which("cursor-agent")
    if not executable:
        raise QualityExecutorError("cursor-agent is not installed")
    help_result = subprocess.run([executable, "--help"], capture_output=True, text=True, check=False)
    command = [executable, "-p"]
    if "--trust" in help_result.stdout or "--trust" in help_result.stderr:
        command.append("--trust")
    command.extend(
        ["--model", "auto", "--output-format", "stream-json", minimal_prompt(packet_relative)]
    )
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", str(Path.home())),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "CURSOR_API_KEY": api_key,
    }
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=projection.root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        raise QualityExecutorError("Cursor executor timed out") from exc
    if process.returncode != 0:
        raise QualityExecutorError(f"Cursor executor failed rc={process.returncode}: {stderr[-4000:]}")

    terminal: dict[str, Any] | None = None
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            terminal = event
    if terminal is None or terminal.get("subtype") != "success" or terminal.get("is_error") is True:
        raise QualityExecutorError("Cursor stream did not end with a successful result event")
    # Never persist stream thinking events. Optional diagnostics retain only the terminal
    # result event, which is transport metadata/final response rather than scratchpad.
    if diagnostic_path is not None:
        diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostic_path.write_text(json.dumps(terminal, ensure_ascii=False) + "\n", encoding="utf-8")
    raw_usage = terminal.get("usage", {}) if isinstance(terminal.get("usage"), Mapping) else {}
    return {
        "provider": "cursor-auto",
        "model": "auto",
        "duration_seconds": round(time.monotonic() - started, 3),
        "session_id": terminal.get("session_id"),
        "request_id": terminal.get("request_id"),
        "usage": {
            "input_tokens": int(raw_usage.get("inputTokens", 0) or 0),
            "cached_input_tokens": int(raw_usage.get("cacheReadTokens", 0) or 0),
            "output_tokens": int(raw_usage.get("outputTokens", 0) or 0),
            "cache_write_tokens": int(raw_usage.get("cacheWriteTokens", 0) or 0),
        },
    }


def copy_validated_review(source: Path, destination: Path) -> None:
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def execute_quality_packet(
    root: Path,
    packet_path: str | Path,
    *,
    executor: str,
    provider: str | None = None,
    model: str | None = None,
    timeout_seconds: int = 2700,
    publish_result: bool = False,
    review_copy_path: Path | None = None,
    diagnostic_path: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    packet_relative, packet = load_packet(root, packet_path)
    selection = select_backend(packet, executor=executor, provider=provider, model=model)
    if timeout_seconds <= 0:
        raise QualityExecutorError("timeout_seconds must be positive")

    with tempfile.TemporaryDirectory(prefix="terminus-quality-") as temporary:
        projection = materialize_projection(root, packet_relative, packet, Path(temporary))
        if selection.executor == "cursor":
            backend = run_cursor(
                projection,
                packet_relative,
                timeout_seconds=timeout_seconds,
                diagnostic_path=diagnostic_path,
            )
        elif selection.provider == "openai":
            backend = run_openai(projection, packet_relative, packet, selection.model)
        else:
            backend = run_anthropic(projection, packet_relative, packet, selection.model)

        review = validate_review_result(projection, packet)
        artifact_path: str | None = None
        if review_copy_path is not None:
            copy_validated_review(projection.review_path, review_copy_path)
            artifact_path = str(review_copy_path.resolve())
        published_path: str | None = None
        if publish_result:
            destination = safe_child(
                root,
                safe_relative(str(packet["review_output_path"]), label="review output"),
            )
            copy_validated_review(projection.review_path, destination)
            published_path = destination.relative_to(root).as_posix()

        blocking: list[str] = []
        if review["role"] == Q4_ROLE:
            blocking = list(review.get("role_output", {}).get("BLOCKING_FINDING_IDS", []))
        return {
            "schema_version": "1.0",
            "status": "EXECUTED",
            "executor": selection.executor,
            "provider": backend["provider"],
            "model": backend["model"],
            "packet": packet_relative.as_posix(),
            "review_output_path": str(packet["review_output_path"]),
            "artifact_path": artifact_path,
            "published_path": published_path,
            "review": {
                "role": review["role"],
                "verdict": review["verdict"],
                "confidence": review["confidence"],
                "evidence_status": review["evidence_status"],
                "finding_count": len(review.get("findings", [])),
                "blocking_count": len(blocking),
            },
            "backend": backend,
            "deterministic_validation": "PASS",
            "fallback_attempted": False,
            "prior_review_projected": False,
            "git_history_projected": False,
        }
