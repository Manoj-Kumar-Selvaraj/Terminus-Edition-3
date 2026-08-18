"""Packet-bound Q4/Q6/Q8 execution with exactly one Cursor or API backend.

The executor materializes a git-history-free evidence projection, runs one selected
backend with no fallback/verdict shopping, validates the persisted schema-v3 review
independently, and optionally publishes only that validated review artifact.
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

QUALITY_ROLES = frozenset(
    {
        "Spec-Test Contract Reviewer",
        "Production Logic Auditor",
        "Model Perspective Difficulty Simulator",
    }
)
DIFFICULTY_ROLE = "Model Perspective Difficulty Simulator"
SUPPORTED_EXECUTORS = frozenset({"cursor", "api"})
SUPPORTED_API_PROVIDERS = frozenset({"openai", "anthropic"})
_REVIEW_SCHEMA = ".terminus/agents/schemas/review_result.schema.json"
_MAX_FILE_BYTES = 2_000_000
_MAX_READ_CHARS = 120_000
_MAX_LIST_FILES = 800
_MAX_GREP_RESULTS = 200
_MAX_API_ROUNDS = 80
_MAX_API_TOOL_CALLS = 300


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


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _safe_relative(value: str, *, label: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise QualityExecutorError(f"{label} must be a safe repository-relative path")
    return path


def _safe_child(root: Path, relative: Path) -> Path:
    target = (root / relative).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise QualityExecutorError(f"path escapes projected workspace: {relative}") from exc
    return target


def _require_commit(root: Path, commit: str, label: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise QualityExecutorError(f"{label} commit is unavailable: {commit}")


def load_packet(root: Path, packet_path: str | Path) -> tuple[Path, dict[str, Any]]:
    root = root.resolve()
    relative = _safe_relative(str(packet_path), label="packet path")
    absolute = _safe_child(root, relative)
    if not absolute.is_file():
        raise QualityExecutorError(f"packet does not exist: {relative.as_posix()}")
    try:
        value = json.loads(absolute.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QualityExecutorError(f"packet is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
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
    missing = required - set(value)
    if missing:
        raise QualityExecutorError(f"packet missing fields: {sorted(missing)}")
    if value["schema_version"] != "3.0":
        raise QualityExecutorError("quality executor requires schema-v3 review packets")
    if value["role"] not in QUALITY_ROLES:
        raise QualityExecutorError(f"unsupported packet role: {value['role']!r}")
    task = str(value["task"])
    if not task or task.startswith(".") or "/" in task or "\\" in task or ".." in task:
        raise QualityExecutorError("packet task must be one safe top-level task directory")
    for field in ("task_commit", "control_plane_commit"):
        if not re.fullmatch(r"[0-9a-fA-F]{40}", str(value[field])):
            raise QualityExecutorError(f"packet {field} must be a full git SHA")
    if value["output_schema"] != _REVIEW_SCHEMA:
        raise QualityExecutorError("packet must use the canonical schema-v3 review schema")
    if value["prior_verdicts_visible"] is not False:
        raise QualityExecutorError("quality execution requires prior_verdicts_visible=false")
    if not isinstance(value["authoritative_rules"], list) or not value["authoritative_rules"]:
        raise QualityExecutorError("packet authoritative_rules must be non-empty")
    if not isinstance(value["evidence_allowed"], list) or not isinstance(
        value["evidence_excluded"], list
    ):
        raise QualityExecutorError("packet evidence boundaries must be arrays")

    review_rel = _safe_relative(str(value["review_output_path"]), label="review_output_path")
    expected_prefix = Path(".terminus") / "reviews" / task / str(value["task_commit"])[:8]
    if review_rel.parent != expected_prefix or review_rel.suffix != ".json":
        raise QualityExecutorError("review_output_path is not bound to task/task-commit directory")
    packet_rel_expected = review_rel.with_name(review_rel.stem + ".packet.json")
    if relative != packet_rel_expected:
        raise QualityExecutorError("packet path does not match its review_output_path identity")
    return relative, value


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
        if packet["role"] == DIFFICULTY_ROLE:
            raise QualityExecutorError("difficulty simulation is API-key-only; Cursor is forbidden")
        if provider or model:
            raise QualityExecutorError("Cursor Q execution fixes model=auto and accepts no API provider/model")
        return QualitySelection(executor="cursor", provider=None, model="auto")
    if provider not in SUPPORTED_API_PROVIDERS:
        raise QualityExecutorError(
            f"API executor requires exactly one provider from {sorted(SUPPORTED_API_PROVIDERS)}"
        )
    if not model:
        raise QualityExecutorError("API executor requires an explicit provider model")
    return QualitySelection(executor="api", provider=provider, model=model)


def _archive_bytes(root: Path, commit: str, paths: list[str]) -> bytes:
    command = ["git", "-C", str(root), "archive", "--format=tar", commit, "--", *paths]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise QualityExecutorError(f"git archive failed for {commit[:12]}: {detail}")
    return result.stdout


def _extract_tar(data: bytes, destination: Path) -> None:
    destination = destination.resolve()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            try:
                target.relative_to(destination)
            except ValueError as exc:
                raise QualityExecutorError(f"archive path escapes workspace: {member.name}") from exc
            if member.issym() or member.islnk():
                raise QualityExecutorError(f"archive symlink/hardlink is not allowed: {member.name}")
        archive.extractall(destination)


def _hash_files(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _copy_packet(source_root: Path, packet_relative: Path, workspace: Path) -> Path:
    source = _safe_child(source_root, packet_relative)
    target = _safe_child(workspace, packet_relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target


def materialize_projection(
    root: Path,
    packet_relative: Path,
    packet: Mapping[str, Any],
    destination: Path,
) -> Projection:
    root = root.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    _require_commit(root, str(packet["task_commit"]), "task")
    _require_commit(root, str(packet["control_plane_commit"]), "control-plane")

    task = str(packet["task"])
    task_archive = _archive_bytes(root, str(packet["task_commit"]), [task])
    _extract_tar(task_archive, destination)

    # Hidden reference solutions are never quality-review evidence for Q4/Q6/Q8.
    shutil.rmtree(destination / task / "solution", ignore_errors=True)

    # Q4 may use the private map only for classification; preserve the exact task snapshot.
    test_map = f".terminus/designs/{task}-test-map.json"
    probe = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{packet['task_commit']}:{test_map}"],
        capture_output=True,
        check=False,
    )
    if probe.returncode == 0:
        _extract_tar(_archive_bytes(root, str(packet["task_commit"]), [test_map]), destination)

    # Transitive policy reads must come from the packet-bound control plane, not task history.
    control_paths = [
        "TERMINUS_3_AI_INSTRUCTIONS.md",
        ".terminus/AGENT_SYSTEM.md",
        ".terminus/agents",
    ]
    _extract_tar(
        _archive_bytes(root, str(packet["control_plane_commit"]), control_paths), destination
    )

    projected_packet = _copy_packet(root, packet_relative, destination)
    review_relative = _safe_relative(str(packet["review_output_path"]), label="review output")
    projected_review = _safe_child(destination, review_relative)
    projected_review.unlink(missing_ok=True)

    # No project-level Cursor/Claude rule injection or git history is projected.
    for side_context in (".cursor", "AGENTS.md", "CLAUDE.md", ".cursorrules"):
        path = destination / side_context
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

    return Projection(
        root=destination.resolve(),
        packet_path=projected_packet,
        review_path=projected_review,
        baseline=_hash_files(destination),
    )


def minimal_prompt(packet_relative: Path) -> str:
    return f"""Execute exactly the Terminus quality review defined by:\n\n{packet_relative.as_posix()}\n\nThe packet and its referenced authoritative rules are the sole controlling instructions.\n\nReview only packet-authorized evidence in this workspace. Do not use prior review conclusions, excluded evidence, sibling repositories, git history, branches, remotes, or chat memory.\n\nMinimize fresh input tokens, output tokens, redundant reads/tool calls, and elapsed time without compromising accuracy, completeness, independence, evidence coverage, or required review depth. Never trade correctness for efficiency.\n\nDo not narrate progress or intermediate reasoning. Do not perform producer remediation.\n\nPersist the complete required schema-v3 result at the packet-defined output path.\n\nFinal human-facing output must be only `PASS` or `REVISE <blocking-count>` (or the packet-authorized non-ready verdict when evidence is insufficient). The persisted JSON is canonical.\n"""


def _workspace_changes(projection: Projection) -> list[str]:
    current = _hash_files(projection.root)
    review_rel = projection.review_path.relative_to(projection.root).as_posix()
    changed = sorted(
        path
        for path in set(projection.baseline) | set(current)
        if projection.baseline.get(path) != current.get(path) and path != review_rel
    )
    return changed


def _validate_schema(review: Mapping[str, Any], schema_path: Path) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise QualityExecutorError("jsonschema is required for deterministic review validation") from exc
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(review), key=lambda item: list(item.absolute_path))
    if errors:
        rendered = "; ".join(
            f"{'.'.join(map(str, error.absolute_path)) or '$'}: {error.message}"
            for error in errors[:20]
        )
        raise QualityExecutorError(f"review schema validation failed: {rendered}")


def validate_review_result(projection: Projection, packet: Mapping[str, Any]) -> dict[str, Any]:
    if not projection.review_path.is_file():
        raise QualityExecutorError("executor did not persist the packet-defined review artifact")
    try:
        review = json.loads(projection.review_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QualityExecutorError(f"persisted review is invalid JSON: {exc}") from exc
    if not isinstance(review, dict):
        raise QualityExecutorError("persisted review must contain one JSON object")
    _validate_schema(review, projection.root / _REVIEW_SCHEMA)

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
    for field, expected in bindings.items():
        if review.get(field) != expected:
            raise QualityExecutorError(
                f"review {field} is not packet-bound: {review.get(field)!r} != {expected!r}"
            )
    expected_context = projection.packet_path.relative_to(projection.root).as_posix()
    if review.get("context_packet") != expected_context:
        raise QualityExecutorError("review context_packet does not match the exact packet path")

    finding_ids = [str(item.get("id", "")) for item in review.get("findings", [])]
    if "" in finding_ids or len(set(finding_ids)) != len(finding_ids):
        raise QualityExecutorError("review finding IDs must be unique and non-empty")
    if review["role"] == "Spec-Test Contract Reviewer":
        role_output = review.get("role_output", {})
        blocking = set(role_output.get("BLOCKING_FINDING_IDS", []))
        advisory = set(role_output.get("ADVISORY_FINDING_IDS", []))
        if blocking & advisory or set(finding_ids) != blocking | advisory:
            raise QualityExecutorError(
                "Q4 must classify every finding exactly once as blocking or advisory"
            )
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
        elif review["verdict"] == "REVISE" and not blocking:
            raise QualityExecutorError("Q4 REVISE requires at least one blocking finding")

    changes = _workspace_changes(projection)
    if changes:
        raise QualityExecutorError(
            "quality executor modified files outside review_output_path: " + ", ".join(changes)
        )
    return review


class WorkspaceTools:
    """Read-only repository tools plus one exact write_review sink for API models."""

    def __init__(self, projection: Projection):
        self.projection = projection
        self.tool_calls = 0
        self.review_written = False

    def _count(self) -> None:
        self.tool_calls += 1
        if self.tool_calls > _MAX_API_TOOL_CALLS:
            raise QualityExecutorError("API executor exceeded tool-call budget")

    def _path(self, value: str) -> Path:
        relative = _safe_relative(value or ".", label="tool path")
        return _safe_child(self.projection.root, relative)

    def list_files(self, glob: str = "**/*") -> dict[str, Any]:
        self._count()
        files = [
            path.relative_to(self.projection.root).as_posix()
            for path in sorted(self.projection.root.rglob("*"))
            if path.is_file()
            and fnmatch.fnmatch(path.relative_to(self.projection.root).as_posix(), glob)
        ]
        truncated = len(files) > _MAX_LIST_FILES
        return {"files": files[:_MAX_LIST_FILES], "truncated": truncated}

    def read_file(self, path: str, start_line: int = 1, end_line: int = 400) -> dict[str, Any]:
        self._count()
        target = self._path(path)
        if not target.is_file():
            return {"error": "not a file"}
        if target.stat().st_size > _MAX_FILE_BYTES:
            return {"error": "file exceeds 2 MB read limit"}
        start = max(1, int(start_line))
        end = max(start, min(int(end_line), start + 499))
        text = target.read_text(encoding="utf-8", errors="replace").splitlines()
        selected = text[start - 1 : end]
        rendered = "\n".join(f"{index}: {line}" for index, line in enumerate(selected, start=start))
        return {
            "path": target.relative_to(self.projection.root).as_posix(),
            "start_line": start,
            "end_line": min(end, len(text)),
            "total_lines": len(text),
            "content": rendered[:_MAX_READ_CHARS],
            "truncated": len(rendered) > _MAX_READ_CHARS,
        }

    def grep(self, pattern: str, path: str = ".", glob: str = "*") -> dict[str, Any]:
        self._count()
        base = self._path(path)
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            return {"error": f"invalid regex: {exc}"}
        candidates = [base] if base.is_file() else sorted(base.rglob("*"))
        matches: list[dict[str, Any]] = []
        for candidate in candidates:
            if not candidate.is_file() or candidate.stat().st_size > _MAX_FILE_BYTES:
                continue
            rel = candidate.relative_to(self.projection.root).as_posix()
            if not fnmatch.fnmatch(candidate.name, glob) and not fnmatch.fnmatch(rel, glob):
                continue
            try:
                lines = candidate.read_text(encoding="utf-8", errors="strict").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for number, line in enumerate(lines, 1):
                if regex.search(line):
                    matches.append({"path": rel, "line": number, "text": line[:1200]})
                    if len(matches) >= _MAX_GREP_RESULTS:
                        return {"matches": matches, "truncated": True}
        return {"matches": matches, "truncated": False}

    def write_review(self, review: Mapping[str, Any]) -> dict[str, Any]:
        self._count()
        if self.review_written:
            raise QualityExecutorError("write_review may be called exactly once")
        if not isinstance(review, Mapping):
            raise QualityExecutorError("write_review.review must be an object")
        self.projection.review_path.parent.mkdir(parents=True, exist_ok=True)
        self.projection.review_path.write_text(
            json.dumps(dict(review), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self.review_written = True
        return {"status": "persisted", "path": self.projection.review_path.relative_to(self.projection.root).as_posix()}

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
                raise QualityExecutorError("write_review requires review object")
            return self.write_review(review)
        raise QualityExecutorError(f"unknown API tool: {name}")


def _tool_specs_openai() -> list[dict[str, Any]]:
    return [
        {"type": "function", "name": "list_files", "description": "List projected workspace files. Use narrow globs when possible.", "parameters": {"type": "object", "properties": {"glob": {"type": "string"}}, "additionalProperties": False}},
        {"type": "function", "name": "read_file", "description": "Read at most 500 lines from one projected file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}}, "required": ["path"], "additionalProperties": False}},
        {"type": "function", "name": "grep", "description": "Regex search projected text files.", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}, "glob": {"type": "string"}}, "required": ["pattern"], "additionalProperties": False}},
        {"type": "function", "name": "write_review", "description": "Persist the complete packet-bound schema-v3 review. Call exactly once after the exhaustive review.", "parameters": {"type": "object", "properties": {"review": {"type": "object", "additionalProperties": True}}, "required": ["review"], "additionalProperties": False}},
    ]


def _tool_specs_anthropic() -> list[dict[str, Any]]:
    return [
        {"name": item["name"], "description": item["description"], "input_schema": item["parameters"]}
        for item in _tool_specs_openai()
    ]


def _cache_key(packet: Mapping[str, Any]) -> str:
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
    prompt = minimal_prompt(packet_relative)
    response = client.responses.create(
        model=model,
        instructions="You are the packet-bound Terminus quality executor. Use only supplied workspace tools and never expose private chain-of-thought.",
        input=prompt,
        tools=_tool_specs_openai(),
        store=False,
        prompt_cache_key=_cache_key(packet),
        prompt_cache_retention="24h",
    )
    usage = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    for _round in range(_MAX_API_ROUNDS):
        if response.usage is not None:
            usage["input_tokens"] += int(getattr(response.usage, "input_tokens", 0) or 0)
            usage["output_tokens"] += int(getattr(response.usage, "output_tokens", 0) or 0)
            details = getattr(response.usage, "input_tokens_details", None)
            usage["cached_input_tokens"] += int(getattr(details, "cached_tokens", 0) or 0)
        calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]
        if not calls:
            if tools.review_written:
                return {"provider": "openai", "model": model, "usage": usage, "tool_calls": tools.tool_calls}
            raise QualityExecutorError("OpenAI executor stopped before write_review")
        outputs: list[dict[str, Any]] = []
        for call in calls:
            try:
                arguments = json.loads(call.arguments)
            except json.JSONDecodeError as exc:
                raise QualityExecutorError(f"OpenAI tool arguments are invalid JSON: {exc}") from exc
            result = tools.dispatch(call.name, arguments)
            outputs.append({"type": "function_call_output", "call_id": call.call_id, "output": _canonical_json(result)})
        if tools.review_written:
            return {"provider": "openai", "model": model, "usage": usage, "tool_calls": tools.tool_calls}
        response = client.responses.create(
            model=model,
            instructions="You are the packet-bound Terminus quality executor. Use only supplied workspace tools and never expose private chain-of-thought.",
            previous_response_id=response.id,
            input=outputs,
            tools=_tool_specs_openai(),
            store=False,
            prompt_cache_key=_cache_key(packet),
            prompt_cache_retention="24h",
        )
    raise QualityExecutorError("OpenAI executor exceeded model-round budget")


def _anthropic_block_dict(block: Any) -> dict[str, Any]:
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
            "text": "You are the packet-bound Terminus quality executor. Use only supplied workspace tools and never expose private chain-of-thought.",
            "cache_control": {"type": "ephemeral"},
        }
    ]
    usage = {
        "input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "output_tokens": 0,
    }
    for _round in range(_MAX_API_ROUNDS):
        response = client.messages.create(
            model=model,
            max_tokens=16_000,
            system=system,
            messages=messages,
            tools=_tool_specs_anthropic(),
            tool_choice={"type": "auto"},
        )
        for field in usage:
            usage[field] += int(getattr(response.usage, field, 0) or 0)
        blocks = [_anthropic_block_dict(block) for block in response.content]
        calls = [block for block in blocks if block.get("type") == "tool_use"]
        messages.append({"role": "assistant", "content": blocks})
        if not calls:
            if tools.review_written:
                return {"provider": "anthropic", "model": model, "usage": usage, "tool_calls": tools.tool_calls}
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
                    "content": _canonical_json(result),
                }
            )
        if tools.review_written:
            return {"provider": "anthropic", "model": model, "usage": usage, "tool_calls": tools.tool_calls}
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
    command.extend(["--model", "auto", "--output-format", "stream-json", minimal_prompt(packet_relative)])
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
    assert process.stdout is not None and process.stderr is not None
    lines: list[str] = []
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        raise QualityExecutorError("Cursor executor timed out") from exc
    if diagnostic_path is not None:
        diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostic_path.write_text(stdout, encoding="utf-8")
    if process.returncode != 0:
        raise QualityExecutorError(f"Cursor executor failed rc={process.returncode}: {stderr[-4000:]}")
    lines = [line for line in stdout.splitlines() if line.strip()]
    terminal: dict[str, Any] | None = None
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            terminal = event
    if terminal is None or terminal.get("subtype") != "success" or terminal.get("is_error") is True:
        raise QualityExecutorError("Cursor stream did not end with a successful result event")
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


def execute_quality_packet(
    root: Path,
    packet_path: str | Path,
    *,
    executor: str,
    provider: str | None = None,
    model: str | None = None,
    timeout_seconds: int = 2700,
    publish_result: bool = False,
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
        published_path: str | None = None
        if publish_result:
            destination = _safe_child(
                root,
                _safe_relative(str(packet["review_output_path"]), label="review output"),
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(projection.review_path, destination)
            published_path = destination.relative_to(root).as_posix()
        blocking = []
        if review["role"] == "Spec-Test Contract Reviewer":
            blocking = list(review.get("role_output", {}).get("BLOCKING_FINDING_IDS", []))
        return {
            "schema_version": "1.0",
            "status": "EXECUTED",
            "executor": selection.executor,
            "provider": backend["provider"],
            "model": backend["model"],
            "packet": packet_relative.as_posix(),
            "review_output_path": str(packet["review_output_path"]),
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
