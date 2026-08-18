"""Select one Q backend and support the existing STB AI credential without refresh.

The repository-wide Q flags choose exactly one of Cursor, direct OpenAI, direct
Claude, or the existing STB/Portkey AI credential.  STB_AI_API_KEY is consumed
as-is against Portkey's OpenAI-compatible Responses API; this module never logs
in, rotates, refreshes, or mints credentials.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .quality_executor import (
    MAX_API_ROUNDS,
    Q4_ROLE,
    QualityExecutorError,
    WorkspaceTools,
    canonical_json,
    copy_validated_review,
    execute_quality_packet,
    load_packet,
    materialize_projection,
    minimal_prompt,
    openai_tools,
    safe_child,
    safe_relative,
    validate_review_result,
)

BACKEND_CURSOR = "cursor"
BACKEND_OPENAI = "openai"
BACKEND_CLAUDE = "claude"
BACKEND_STB_AI = "stb_ai"
QUALITY_BACKENDS = (BACKEND_CURSOR, BACKEND_OPENAI, BACKEND_CLAUDE, BACKEND_STB_AI)
STB_AI_GATEWAY_URL = "https://api.portkey.ai/v1"


@dataclass(frozen=True)
class FlagSelection:
    backend: str
    model: str | None


def _enabled(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def select_flag_backend(
    *,
    cursor: str | bool | None,
    openai: str | bool | None,
    claude: str | bool | None,
    stb_ai: str | bool | None,
    openai_model: str | None = None,
    claude_model: str | None = None,
    stb_ai_model: str | None = None,
) -> FlagSelection:
    """Resolve the global Q flags; exactly one backend must be enabled."""

    flags = {
        BACKEND_CURSOR: _enabled(cursor),
        BACKEND_OPENAI: _enabled(openai),
        BACKEND_CLAUDE: _enabled(claude),
        BACKEND_STB_AI: _enabled(stb_ai),
    }
    selected = [name for name, enabled in flags.items() if enabled]
    if len(selected) != 1:
        raise QualityExecutorError(
            "exactly one Q backend flag must be enabled: " + ", ".join(QUALITY_BACKENDS)
        )
    backend = selected[0]
    models = {
        BACKEND_OPENAI: (openai_model or "").strip(),
        BACKEND_CLAUDE: (claude_model or "").strip(),
        BACKEND_STB_AI: (stb_ai_model or "").strip(),
    }
    if backend == BACKEND_CURSOR:
        return FlagSelection(backend, None)
    model = models[backend]
    if not model:
        raise QualityExecutorError(f"{backend} Q backend requires an explicit model")
    return FlagSelection(backend, model)


def credential_env_for_backend(backend: str) -> str:
    return {
        BACKEND_CURSOR: "CURSOR_API_KEY",
        BACKEND_OPENAI: "OPENAI_API_KEY",
        BACKEND_CLAUDE: "ANTHROPIC_API_KEY",
        BACKEND_STB_AI: "STB_AI_API_KEY",
    }[backend]


def _run_stb_ai(
    projection: Any,
    packet_relative: Path,
    model: str,
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Run one Q review through the existing STB/Portkey AI credential."""

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise QualityExecutorError("openai package is required for backend=stb_ai") from exc

    api_key = os.environ.get("STB_AI_API_KEY", "").strip()
    if not api_key:
        raise QualityExecutorError("STB_AI_API_KEY is required for backend=stb_ai")
    base_url = os.environ.get("STB_AI_BASE_URL", STB_AI_GATEWAY_URL).strip()
    if not base_url.startswith("https://"):
        raise QualityExecutorError("STB_AI_BASE_URL must be HTTPS")

    tools = WorkspaceTools(projection)
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
    instructions = (
        "You are the packet-bound Terminus quality executor. Use only supplied workspace tools. "
        "Never expose or persist private chain-of-thought."
    )
    input_items: list[Any] = [{"role": "user", "content": minimal_prompt(packet_relative)}]
    usage = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}

    for _round in range(MAX_API_ROUNDS):
        # Portkey's Open Responses surface is provider-agnostic.  Do not send OpenAI-only
        # prompt-cache controls here; the existing STB credential/gateway policy remains authoritative.
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=input_items,
            tools=openai_tools(),
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
                    "provider": "stb-ai-gateway",
                    "model": model,
                    "usage": usage,
                    "tool_calls": tools.tool_calls,
                }
            raise QualityExecutorError("STB AI executor stopped before write_review")

        for call in calls:
            try:
                arguments = json.loads(call.arguments)
            except json.JSONDecodeError as exc:
                raise QualityExecutorError(f"STB AI tool arguments are invalid JSON: {exc}") from exc
            result = tools.dispatch(call.name, arguments)
            input_items.append(
                {"type": "function_call_output", "call_id": call.call_id, "output": canonical_json(result)}
            )
        if tools.review_written:
            return {
                "provider": "stb-ai-gateway",
                "model": model,
                "usage": usage,
                "tool_calls": tools.tool_calls,
            }

    raise QualityExecutorError("STB AI executor exceeded model-round budget")


def _execute_stb_ai_packet(
    root: Path,
    packet_path: str | Path,
    *,
    model: str,
    timeout_seconds: int,
    publish_result: bool,
    review_copy_path: Path | None,
) -> dict[str, Any]:
    root = root.resolve()
    packet_relative, packet = load_packet(root, packet_path)
    if timeout_seconds <= 0:
        raise QualityExecutorError("timeout_seconds must be positive")

    with tempfile.TemporaryDirectory(prefix="terminus-quality-") as temporary:
        projection = materialize_projection(root, packet_relative, packet, Path(temporary))
        backend = _run_stb_ai(
            projection,
            packet_relative,
            model,
            timeout_seconds=timeout_seconds,
        )
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
            "executor": "api",
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


def execute_flag_backend(
    root: Path,
    packet_path: str | Path,
    *,
    backend: str,
    model: str | None = None,
    timeout_seconds: int = 2700,
    publish_result: bool = False,
    review_copy_path: Path | None = None,
    diagnostic_path: Path | None = None,
) -> dict[str, Any]:
    """Execute exactly one already-selected backend with no fallback."""

    if backend == BACKEND_CURSOR:
        if model:
            raise QualityExecutorError("Cursor Q backend fixes model=auto")
        result = execute_quality_packet(
            root,
            packet_path,
            executor="cursor",
            timeout_seconds=timeout_seconds,
            publish_result=publish_result,
            review_copy_path=review_copy_path,
            diagnostic_path=diagnostic_path,
        )
    elif backend == BACKEND_OPENAI:
        if not model:
            raise QualityExecutorError("OpenAI Q backend requires an explicit model")
        result = execute_quality_packet(
            root,
            packet_path,
            executor="api",
            provider="openai",
            model=model,
            timeout_seconds=timeout_seconds,
            publish_result=publish_result,
            review_copy_path=review_copy_path,
        )
    elif backend == BACKEND_CLAUDE:
        if not model:
            raise QualityExecutorError("Claude Q backend requires an explicit model")
        result = execute_quality_packet(
            root,
            packet_path,
            executor="api",
            provider="anthropic",
            model=model,
            timeout_seconds=timeout_seconds,
            publish_result=publish_result,
            review_copy_path=review_copy_path,
        )
    elif backend == BACKEND_STB_AI:
        if not model:
            raise QualityExecutorError("STB AI Q backend requires an explicit model")
        result = _execute_stb_ai_packet(
            root,
            packet_path,
            model=model,
            timeout_seconds=timeout_seconds,
            publish_result=publish_result,
            review_copy_path=review_copy_path,
        )
    else:
        raise QualityExecutorError(f"unsupported Q backend: {backend!r}")

    result["selected_backend"] = backend
    result["credential_source"] = credential_env_for_backend(backend)
    return result
