#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/app/routecp")
role = root / "ansible" / "roles" / "routecp"
main = role / "tasks" / "main.yml"
project = role / "tasks" / "project.yml"

if project.exists():
    main_text = main.read_text()
    import_block = '''- name: Materialize routecp projected configuration
  ansible.builtin.import_tasks: project.yml
'''
    repaired_block = '''- name: Materialize routecp projected configuration
  ansible.builtin.import_tasks: project.yml
  vars:
    routecp_effective_routes: "{{ (routecp_routes | default([])) + (routecp_protected_routes | default([])) + (routecp_host_routes | default([])) }}"
'''
    if "routecp_effective_routes:" not in main_text:
        if import_block not in main_text:
            raise RuntimeError("routecp projected-configuration import block not found")
        main.write_text(main_text.replace(import_block, repaired_block))

    project_text = project.read_text()
    old = "'routes': routecp_routes,"
    direct = "'routes': ((routecp_routes | default([])) + (routecp_protected_routes | default([])) + (routecp_host_routes | default([]))),"
    effective = "'routes': routecp_effective_routes,"
    if effective not in project_text:
        if direct in project_text:
            project_text = project_text.replace(direct, effective)
        elif old in project_text:
            project_text = project_text.replace(old, effective)
        else:
            raise RuntimeError("route projection expression not found in delegated project task")
        project.write_text(project_text)
    target = project
else:
    text = main.read_text()
    old = "'routes': routecp_routes,"
    new = "'routes': ((routecp_routes | default([])) + (routecp_protected_routes | default([])) + (routecp_host_routes | default([]))),"
    if new not in text:
        if old not in text:
            raise RuntimeError("route projection expression not found in tasks/main.yml")
        main.write_text(text.replace(old, new))
    target = main

print(f"routecp ansible reference projection repaired via {target.relative_to(root)}")
