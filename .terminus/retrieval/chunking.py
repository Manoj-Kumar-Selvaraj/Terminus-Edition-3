"""Deterministic structural chunking for retrieval sources."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from .models import RawChunk

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SYMBOL = re.compile(
    r"^\s*(?:class|def|func|function|interface|struct|type)\s+([A-Za-z_][\w$]*)",
    re.MULTILINE,
)


def chunk_text(
    path: Path,
    text: str,
    strategy: str,
    *,
    max_chars: int = 12000,
    overlap_chars: int = 500,
) -> list[RawChunk]:
    """Chunk a source structurally, using bounded windows only as a fallback."""
    if strategy in {"HEADING_SECTION", "SESSION_SECTION"}:
        chunks = _markdown_sections(text)
    elif strategy in {"JSON_OBJECT", "PACKET_SECTION"}:
        chunks = _json_sections(text) if _looks_json(text) else _markdown_sections(text)
    elif strategy == "CODE_SYMBOL":
        chunks = _code_sections(path, text)
    elif strategy in {"CI_STEP", "LOG_EVENT_WINDOW", "EXTERNAL_SECTION"}:
        chunks = _paragraph_sections(text, strategy)
    else:
        chunks = [
            RawChunk(
                content=text,
                chunk_type="DOCUMENT",
                structural_locator="document",
                ordinal=0,
                line_start=1 if text else None,
                line_end=max(1, len(text.splitlines())) if text else None,
            )
        ]
    return _split_oversized(chunks, max_chars=max_chars, overlap_chars=overlap_chars)


def _looks_json(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def _markdown_sections(text: str) -> list[RawChunk]:
    lines = text.splitlines()
    if not lines:
        return [RawChunk("", "DOCUMENT", "document", 0)]

    sections: list[RawChunk] = []
    stack: list[tuple[int, str]] = []
    start = 0
    current_path: tuple[str, ...] = ()
    current_heading = "preamble"

    def emit(end: int) -> None:
        nonlocal start
        content = "\n".join(lines[start:end]).strip("\n")
        if not content and sections:
            start = end
            return
        sections.append(
            RawChunk(
                content=content,
                chunk_type="HEADING_SECTION" if current_path else "DOCUMENT",
                structural_locator=" / ".join(current_path) if current_path else current_heading,
                ordinal=len(sections),
                section_path=current_path,
                line_start=start + 1,
                line_end=max(start + 1, end),
            )
        )
        start = end

    for index, line in enumerate(lines):
        match = _HEADING.match(line)
        if not match:
            continue
        if index > start:
            emit(index)
        level = len(match.group(1))
        heading = match.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, heading))
        current_path = tuple(item[1] for item in stack)
        current_heading = heading
        start = index
    emit(len(lines))
    return sections or [RawChunk(text, "DOCUMENT", "document", 0)]


def _json_sections(text: str) -> list[RawChunk]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return [RawChunk(text, "DOCUMENT", "document", 0)]

    chunks: list[RawChunk] = []
    if isinstance(value, dict):
        for key, item in value.items():
            chunks.append(
                RawChunk(
                    content=json.dumps({key: item}, indent=2, sort_keys=True),
                    chunk_type="JSON_OBJECT",
                    structural_locator=f"$.{key}",
                    ordinal=len(chunks),
                    section_path=(str(key),),
                )
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            chunks.append(
                RawChunk(
                    content=json.dumps(item, indent=2, sort_keys=True),
                    chunk_type="JSON_OBJECT",
                    structural_locator=f"$[{index}]",
                    ordinal=len(chunks),
                    section_path=(str(index),),
                )
            )
    return chunks or [RawChunk(text, "DOCUMENT", "document", 0)]


def _code_sections(path: Path, text: str) -> list[RawChunk]:
    if path.suffix == ".py":
        return _python_sections(text)
    return _generic_code_sections(text)


def _python_sections(text: str) -> list[RawChunk]:
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [RawChunk(text, "CODE_MODULE", "module", 0)]

    chunks: list[RawChunk] = []
    first_symbol_line = len(lines) + 1
    nodes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    if nodes:
        first_symbol_line = min(node.lineno for node in nodes)
    if first_symbol_line > 1:
        preamble = "\n".join(lines[: first_symbol_line - 1]).strip("\n")
        if preamble:
            chunks.append(
                RawChunk(
                    content=preamble,
                    chunk_type="CODE_MODULE",
                    structural_locator="module:preamble",
                    ordinal=len(chunks),
                    line_start=1,
                    line_end=first_symbol_line - 1,
                )
            )
    for node in nodes:
        end = getattr(node, "end_lineno", node.lineno)
        kind = "CODE_CLASS" if isinstance(node, ast.ClassDef) else "CODE_FUNCTION"
        chunks.append(
            RawChunk(
                content="\n".join(lines[node.lineno - 1 : end]),
                chunk_type=kind,
                structural_locator=f"symbol:{node.name}",
                ordinal=len(chunks),
                section_path=(node.name,),
                symbol=node.name,
                line_start=node.lineno,
                line_end=end,
            )
        )
    return chunks or [RawChunk(text, "CODE_MODULE", "module", 0)]


def _generic_code_sections(text: str) -> list[RawChunk]:
    matches = list(_SYMBOL.finditer(text))
    if not matches:
        return [RawChunk(text, "CODE_MODULE", "module", 0)]
    chunks: list[RawChunk] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        symbol = match.group(1)
        line_start = text.count("\n", 0, start) + 1
        line_end = text.count("\n", 0, end) + 1
        chunks.append(
            RawChunk(
                content=text[start:end].strip("\n"),
                chunk_type="CODE_SYMBOL",
                structural_locator=f"symbol:{symbol}",
                ordinal=index,
                section_path=(symbol,),
                symbol=symbol,
                line_start=line_start,
                line_end=line_end,
            )
        )
    return chunks


def _paragraph_sections(text: str, strategy: str) -> list[RawChunk]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    chunk_type = "EXTERNAL_SECTION" if strategy == "EXTERNAL_SECTION" else "LOG_EVENT_WINDOW"
    return [
        RawChunk(
            content=block,
            chunk_type=chunk_type,
            structural_locator=f"block:{index}",
            ordinal=index,
        )
        for index, block in enumerate(blocks)
    ] or [RawChunk(text, "DOCUMENT", "document", 0)]


def _split_oversized(
    chunks: list[RawChunk], *, max_chars: int, overlap_chars: int
) -> list[RawChunk]:
    output: list[RawChunk] = []
    for chunk in chunks:
        if len(chunk.content) <= max_chars:
            output.append(_replace_ordinal(chunk, len(output)))
            continue
        step = max(1, max_chars - overlap_chars)
        for part_index, start in enumerate(range(0, len(chunk.content), step)):
            part = chunk.content[start : start + max_chars]
            if not part:
                break
            output.append(
                RawChunk(
                    content=part,
                    chunk_type=chunk.chunk_type,
                    structural_locator=f"{chunk.structural_locator}#part-{part_index}",
                    ordinal=len(output),
                    section_path=chunk.section_path,
                    symbol=chunk.symbol,
                    line_start=chunk.line_start,
                    line_end=chunk.line_end,
                )
            )
            if start + max_chars >= len(chunk.content):
                break
    return output


def _replace_ordinal(chunk: RawChunk, ordinal: int) -> RawChunk:
    return RawChunk(
        content=chunk.content,
        chunk_type=chunk.chunk_type,
        structural_locator=chunk.structural_locator,
        ordinal=ordinal,
        section_path=chunk.section_path,
        symbol=chunk.symbol,
        line_start=chunk.line_start,
        line_end=chunk.line_end,
    )
