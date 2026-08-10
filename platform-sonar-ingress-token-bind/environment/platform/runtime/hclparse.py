from __future__ import annotations

import re
from pathlib import Path
from typing import Any

RESOURCE_RE = re.compile(
    r'^(?:resource|data)\s+"([^"]+)"\s+"([^"]+)"\s*\{',
    re.MULTILINE,
)


def _strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.split("#", 1)[0]
        lines.append(stripped)
    return "\n".join(lines)


def _parse_body(body: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line == "{" or line == "}":
            continue
        if "=" not in line:
            continue
        key, _, rest = line.partition("=")
        key = key.strip()
        rest = rest.strip().rstrip(",")
        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            if not inner:
                values[key] = []
                continue
            items = []
            for part in inner.split(","):
                items.append(_scalar(part.strip()))
            values[key] = items
            continue
        values[key] = _scalar(rest)
    return values


def _scalar(token: str) -> Any:
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1]
    if token.lower() == "true":
        return True
    if token.lower() == "false":
        return False
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    return token


def parse_terraform(path: Path) -> list[dict[str, Any]]:
    text = _strip_comments(path.read_text(encoding="utf-8"))
    resources: list[dict[str, Any]] = []
    matches = list(RESOURCE_RE.finditer(text))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        depth = 1
        cut = 0
        for offset, char in enumerate(body):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    cut = offset
                    break
        attrs = _parse_body(body[:cut])
        resources.append(
            {
                "kind": "terraform",
                "type": match.group(1),
                "name": match.group(2),
                "attrs": attrs,
            }
        )
    return resources
