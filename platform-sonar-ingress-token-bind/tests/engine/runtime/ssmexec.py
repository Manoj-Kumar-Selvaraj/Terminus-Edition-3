from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DOCUMENT = "AWS-RunShellScript"


def inventory_uses_ssm(aws_inventory: str) -> bool:
    return "ansible_connection: aws_ssm" in aws_inventory


def inventory_uses_ssh(aws_inventory: str) -> bool:
    return "ansible_connection: ssh" in aws_inventory or "ansible_ssh_private_key_file" in aws_inventory


def inventory_leaks_onprem(aws_inventory: str) -> bool:
    return "onprem" in aws_inventory or "~/.ssh" in aws_inventory


def runner_sg_opens_ssh(attrs: dict[str, Any]) -> bool:
    return bool(attrs.get("ingress_ssh"))


def dispatch_ok(
    aws_inventory: str,
    runner_sg: dict[str, Any],
    runner_id: str,
    expected_id: str,
) -> bool:
    if not inventory_uses_ssm(aws_inventory):
        return False
    if inventory_uses_ssh(aws_inventory) or inventory_leaks_onprem(aws_inventory):
        return False
    if runner_sg_opens_ssh(runner_sg):
        return False
    if not runner_id or runner_id != expected_id:
        return False
    return True


def write_command_log(path: Path, runner_id: str, ok: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not ok:
        return
    line = {"document": DOCUMENT, "instance": runner_id, "status": "Success"}
    path.write_text(json.dumps(line) + "\n", encoding="utf-8")
