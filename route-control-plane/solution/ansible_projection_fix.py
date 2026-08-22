#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/app/routecp")
role = root / "ansible" / "roles" / "routecp"
project = role / "tasks" / "project.yml"
target = project if project.exists() else role / "tasks" / "main.yml"

text = target.read_text()
old = "'routes': routecp_routes,"
new = "'routes': ((routecp_routes | default([])) + (routecp_protected_routes | default([])) + (routecp_host_routes | default([]))),"
if new not in text:
    if old not in text:
        raise RuntimeError(f"route projection expression not found in {target}")
    text = text.replace(old, new)
    target.write_text(text)

print(f"routecp ansible reference projection repaired in {target.relative_to(root)}")
