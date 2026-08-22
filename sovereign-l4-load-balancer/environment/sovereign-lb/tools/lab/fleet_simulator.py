#!/usr/bin/env python3
"""Deterministic fleet inventory helpers for the sovereign loopback lab."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FleetNode:
    node_id: str
    zone: str
    control: str
    status: str
    config_path: Path


def load_fleet(root: Path) -> list[FleetNode]:
    inventory = json.loads((root / "config" / "fleet.json").read_text(encoding="utf-8"))
    nodes: list[FleetNode] = []
    for item in inventory["nodes"]:
        node_id = str(item["id"])
        nodes.append(
            FleetNode(
                node_id=node_id,
                zone=str(item["zone"]),
                control=str(item["control"]),
                status=str(item["status"]),
                config_path=root / "config" / "nodes" / f"{node_id}.json",
            )
        )
    return nodes


def wait_port(address: str, timeout: float = 10.0) -> None:
    host, port_text = address.rsplit(":", 1)
    port = int(port_text)
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            try:
                sock.connect((host, port))
                return
            except OSError:
                time.sleep(0.1)
    raise TimeoutError(f"port {address} did not open")


def start_dataplane(root: Path, node: FleetNode, log_dir: Path) -> subprocess.Popen[str]:
    binary = root / "build" / "bin" / "lb-dataplane"
    if not binary.is_file():
        binary = Path("/app/sovereign-lb/build/bin/lb-dataplane")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{node.node_id}.log"
    output = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [str(binary), "--config", str(node.config_path)],
        cwd=root,
        stdout=output,
        stderr=subprocess.STDOUT,
        text=True,
    )
    wait_port(node.status, timeout=15.0)
    return process


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def summarize(nodes: list[FleetNode]) -> dict[str, Any]:
    zones: dict[str, list[str]] = {}
    for node in nodes:
        zones.setdefault(node.zone, []).append(node.node_id)
    return {
        "node_count": len(nodes),
        "zones": {zone: sorted(values) for zone, values in sorted(zones.items())},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("list", "summary", "start-one"))
    parser.add_argument("--root", default="/app/sovereign-lb")
    parser.add_argument("--node", default="dp-01")
    parser.add_argument("--log-dir", default="/app/sovereign-lb/state/fleet-sim")
    args = parser.parse_args()
    root = Path(args.root)
    nodes = load_fleet(root)
    if args.command == "list":
        print(json.dumps([node.__dict__ | {"config_path": str(node.config_path)} for node in nodes], indent=2))
        return 0
    if args.command == "summary":
        print(json.dumps(summarize(nodes), indent=2, sort_keys=True))
        return 0
    selected = next((node for node in nodes if node.node_id == args.node), None)
    if selected is None:
        print(f"unknown node {args.node}", file=sys.stderr)
        return 2
    process = start_dataplane(root, selected, Path(args.log_dir))
    print(json.dumps({"node_id": selected.node_id, "pid": process.pid, "status": selected.status}))
    try:
        while process.poll() is None:
            time.sleep(0.5)
    finally:
        stop_process(process)
    return 0


if __name__ == "__main__":
    sys.exit(main())
