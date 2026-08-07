"""Local zonal egress drain lab: plan graph, namespaces, and traffic probes."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


def _data_dir() -> Path:
    return Path(os.environ.get("EGRESS_DATA_DIR", "/app/data"))


def _var_dir() -> Path:
    return Path(os.environ.get("EGRESS_VAR_DIR", "/app/var/egress"))


def _output_dir() -> Path:
    return Path(os.environ.get("EGRESS_OUTPUT_DIR", "/app/output"))


def _module_dir() -> Path | None:
    raw = os.environ.get("EGRESS_MODULE_DIR")
    return Path(raw) if raw else Path("/app/terraform/modules/egress")


def _load(name: str) -> Any:
    return json.loads((_data_dir() / name).read_text(encoding="utf-8"))


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _canonicalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        items = [_canonicalize(v) for v in value]

        def _sort_key(item: Any) -> str:
            if isinstance(item, dict):
                for key in ("id", "address", "name", "src", "dst"):
                    if key in item:
                        return json.dumps([str(item[key])], sort_keys=True)
            return json.dumps(item, sort_keys=True, separators=(",", ":"))

        items.sort(key=_sort_key)
        return items
    return value


def report_digest(report: dict) -> str:
    stable = {k: v for k, v in report.items() if k not in {"report_digest", "reason"}}
    blob = json.dumps(_canonicalize(stable), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def _iter_resources(plan: dict) -> list[dict]:
    values = ((plan.get("planned_values") or {}).get("root_module") or {})
    resources = list(values.get("resources") or [])
    stack = list(values.get("child_modules") or [])
    while stack:
        child = stack.pop()
        resources.extend(child.get("resources") or [])
        stack.extend(child.get("child_modules") or [])
    return resources


def _changes_by_type(plan: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for rc in plan.get("resource_changes") or []:
        out.setdefault(rc.get("type") or "", []).append(rc)
    return out


def _az_key_from_tags(tags: dict | None, topology: dict) -> str | None:
    tags = tags or {}
    name = str(tags.get("Name") or "")
    for key in topology["azs"]:
        if f"-{key}-" in f"-{name}-" or name.endswith(f"-{key}") or f"{key}-" in name:
            return key
    for cand in (tags.get("AZKey"), tags.get("AzKey"), tags.get("az_key")):
        if cand in topology["azs"]:
            return cand
    return None


def parse_moved_blocks(module_dir: Path | None = None) -> list[dict[str, str]]:
    """Parse moved blocks from submitted module HCL (native module structure)."""
    root = module_dir or _module_dir()
    if root is None or not root.is_dir():
        return []
    moved: list[dict[str, str]] = []
    pattern = re.compile(
        r"moved\s*\{[^}]*from\s*=\s*([^\n]+)\n[^}]*to\s*=\s*([^\n]+)",
        re.MULTILINE,
    )
    for path in sorted(root.glob("*.tf")):
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            moved.append(
                {
                    "from": match.group(1).strip(),
                    "to": match.group(2).strip(),
                }
            )
    return moved


def normalize_plan(plan: dict) -> dict:
    """Build a semantic egress graph from terraform show -json."""
    topology = _load("topology.json")
    services = _load("services.json")
    defaults = _load("defaults.json")
    resources = _iter_resources(plan)
    by_type: dict[str, list[dict]] = {}
    for res in resources:
        by_type.setdefault(res.get("type") or "", []).append(res)

    subnets: dict[str, dict] = {}
    for res in by_type.get("aws_subnet", []):
        vals = res.get("values") or {}
        tags = vals.get("tags") or vals.get("tags_all") or {}
        tier = (tags.get("Tier") or "").lower()
        key = _az_key_from_tags(tags, topology) or (
            res.get("index") if isinstance(res.get("index"), str) else None
        )
        cidr = vals.get("cidr_block")
        if not key:
            for az_key, az in topology["azs"].items():
                if cidr == az["public_cidr"]:
                    key, tier = az_key, tier or "public"
                elif cidr == az["app_cidr"]:
                    key, tier = az_key, tier or "app"
                elif cidr == az["data_cidr"]:
                    key, tier = az_key, tier or "data"
        if not key or not tier:
            continue
        subnets[f"{tier}:{key}"] = {
            "address": res.get("address"),
            "cidr": cidr,
            "az": vals.get("availability_zone"),
            "map_public": vals.get("map_public_ip_on_launch"),
            "tier": tier,
            "key": key,
        }

    nat_gateways: dict[str, dict] = {}
    for res in by_type.get("aws_nat_gateway", []):
        vals = res.get("values") or {}
        tags = vals.get("tags") or vals.get("tags_all") or {}
        key = _az_key_from_tags(tags, topology) or (
            res.get("index") if isinstance(res.get("index"), str) else None
        )
        if key:
            nat_gateways[key] = {"address": res.get("address"), "key": key}

    eips: dict[str, dict] = {}
    for idx, key in enumerate(sorted(topology["azs"])):
        eips[key] = {"lab_ip": f"203.0.113.{10 + idx}"}
    for res in by_type.get("aws_eip", []):
        vals = res.get("values") or {}
        tags = vals.get("tags") or vals.get("tags_all") or {}
        key = _az_key_from_tags(tags, topology) or (
            res.get("index") if isinstance(res.get("index"), str) else None
        )
        if key and key in eips:
            eips[key]["address"] = res.get("address")

    app_default: dict[str, dict] = {}
    data_default: dict[str, dict] = {}
    for res in by_type.get("aws_route", []):
        vals = res.get("values") or {}
        addr = (res.get("address") or "").lower()
        dest = vals.get("destination_cidr_block")
        key = res.get("index") if isinstance(res.get("index"), str) else None
        if dest != "0.0.0.0/0" or not key:
            continue
        entry = {
            "address": res.get("address"),
            "key": key,
            "nat_gateway_id": vals.get("nat_gateway_id"),
            "gateway_id": vals.get("gateway_id"),
        }
        if "data" in addr:
            data_default[key] = entry
        elif "app" in addr:
            app_default[key] = entry

    for rc in plan.get("resource_changes") or []:
        if rc.get("type") != "aws_route":
            continue
        after = (rc.get("change") or {}).get("after") or {}
        if after.get("destination_cidr_block") != "0.0.0.0/0":
            continue
        key = rc.get("index") if isinstance(rc.get("index"), str) else None
        addr = (rc.get("address") or "").lower()
        if not key:
            continue
        entry = {
            "address": rc.get("address"),
            "key": key,
            "nat_gateway_id": after.get("nat_gateway_id"),
            "gateway_id": after.get("gateway_id"),
        }
        if "data" in addr:
            data_default[key] = entry
        elif "app" in addr:
            app_default.setdefault(key, entry)

    endpoints_iface: dict[str, dict] = {}
    endpoints_gw: dict[str, dict] = {}
    for res in by_type.get("aws_vpc_endpoint", []):
        vals = res.get("values") or {}
        svc = vals.get("service_name") or ""
        short = res.get("index") if isinstance(res.get("index"), str) else res.get("name")
        match = re.search(r"com\.amazonaws\.[^.]+\.(.+)$", svc or "")
        if match:
            short = match.group(1)
        etype = vals.get("vpc_endpoint_type")
        entry = {
            "address": res.get("address"),
            "service": short,
            "private_dns": vals.get("private_dns_enabled"),
            "subnet_ids": list(vals.get("subnet_ids") or []),
            "security_group_ids": list(vals.get("security_group_ids") or []),
            "route_table_ids": list(vals.get("route_table_ids") or []),
        }
        if etype == "Interface" and short:
            endpoints_iface[str(short)] = entry
        elif etype == "Gateway" and short:
            endpoints_gw[str(short)] = entry

    sgs: dict[str, dict] = {}
    for res in by_type.get("aws_security_group", []):
        vals = res.get("values") or {}
        tags = vals.get("tags") or vals.get("tags_all") or {}
        name = (tags.get("Name") or res.get("name") or "").lower()
        kind = "other"
        if "endpoint" in name:
            kind = "endpoint"
        elif "resolver" in name:
            kind = "resolver"
        ingress = vals.get("ingress") or []
        if isinstance(ingress, dict):
            ingress = [ingress]
        sgs[kind] = {"address": res.get("address"), "ingress": ingress, "name": name}

    outputs = {}
    planned_outputs = (plan.get("planned_values") or {}).get("outputs") or {}
    # outputs may live on root or be empty when only module outputs; also check root output values
    for name, oval in planned_outputs.items():
        outputs[name] = oval.get("value")
    # Module outputs sometimes only appear under child — scan resource-less output in configuration
    for rc in plan.get("output_changes") or {}:
        pass
    output_changes = plan.get("output_changes") or {}
    for name, change in output_changes.items():
        after = (change or {}).get("after")
        if after is not None:
            outputs[name] = after

    return {
        "topology": topology,
        "services": services,
        "defaults": defaults,
        "subnets": subnets,
        "nat_gateways": nat_gateways,
        "eips": eips,
        "app_default": app_default,
        "data_default": data_default,
        "endpoints_iface": endpoints_iface,
        "endpoints_gw": endpoints_gw,
        "sgs": sgs,
        "moved": parse_moved_blocks(),
        "outputs": outputs,
        "changes": _changes_by_type(plan),
    }


def _ingress_cidrs(ingress: list) -> set[str]:
    cidrs: set[str] = set()
    for rule in ingress:
        cidrs.update(rule.get("cidr_blocks") or [])
    return cidrs


def plan_policy_errors(graph: dict) -> list[str]:
    errors: list[str] = []
    topology = graph["topology"]
    services = graph["services"]
    defaults = graph["defaults"]
    az_keys = sorted(topology["azs"])
    enabled = set(defaults.get("nat_enabled_azs") or [])
    required_nats = set(az_keys) if not enabled else set(enabled)

    for key in az_keys:
        for tier in ("public", "app", "data"):
            if f"{tier}:{key}" not in graph["subnets"]:
                errors.append(f"missing {tier} subnet for {key}")

        if key in required_nats and key not in graph["nat_gateways"]:
            errors.append(f"missing NAT gateway for {key}")

        if key not in graph["app_default"]:
            errors.append(f"missing app default route for {key}")

        if key in graph["data_default"]:
            errors.append(f"data default route present for {key}")

        pub = graph["subnets"].get(f"public:{key}")
        app = graph["subnets"].get(f"app:{key}")
        data = graph["subnets"].get(f"data:{key}")
        if pub and pub.get("map_public") is not True:
            errors.append(f"public subnet {key} must map public IP")
        if app and app.get("map_public") is True:
            errors.append(f"app subnet {key} must not map public IP")
        if data and data.get("map_public") is True:
            errors.append(f"data subnet {key} must not map public IP")
        if app and app.get("cidr") != topology["azs"][key]["app_cidr"]:
            errors.append(f"app CIDR mismatch for {key}")
        if data and data.get("cidr") != topology["azs"][key]["data_cidr"]:
            errors.append(f"data CIDR mismatch for {key}")
        if pub and pub.get("cidr") != topology["azs"][key]["public_cidr"]:
            errors.append(f"public CIDR mismatch for {key}")

    for svc in services["interface"]:
        ep = graph["endpoints_iface"].get(svc)
        if not ep:
            errors.append(f"missing interface endpoint {svc}")
        elif ep.get("private_dns") is not True:
            errors.append(f"interface endpoint {svc} requires private DNS")

    for svc in services["gateway"]:
        if svc not in graph["endpoints_gw"]:
            errors.append(f"missing gateway endpoint {svc}")

    endpoint_sg = graph["sgs"].get("endpoint")
    if not endpoint_sg:
        errors.append("missing endpoint security group")
    else:
        cidrs = _ingress_cidrs(endpoint_sg["ingress"])
        if "0.0.0.0/0" in cidrs:
            errors.append("endpoint SG must not allow 0.0.0.0/0")
        expected = {
            topology["azs"][k][tier]
            for k in az_keys
            for tier in ("app_cidr", "data_cidr")
        }
        if not expected.issubset(cidrs):
            errors.append("endpoint SG ingress must cover app and data CIDRs")
        for rule in endpoint_sg["ingress"]:
            if rule.get("protocol") == "tcp" and (
                rule.get("from_port") != 443 or rule.get("to_port") != 443
            ):
                errors.append("endpoint SG must only allow TCP 443 from workloads")

    resolver = graph["sgs"].get("resolver")
    if not resolver:
        errors.append("missing resolver security group")
    else:
        cidrs = _ingress_cidrs(resolver["ingress"])
        if "0.0.0.0/0" in cidrs:
            errors.append("resolver SG must not allow 0.0.0.0/0")
        dns_expected = {
            c for k in az_keys for c in topology["azs"][k]["corporate_dns_cidrs"]
        }
        if not dns_expected.issubset(cidrs):
            errors.append("resolver SG must use corporate DNS CIDRs")
        protos = {
            str(r.get("protocol")).lower()
            for r in resolver["ingress"]
            if r.get("from_port") == 53 and r.get("to_port") == 53
        }
        if "tcp" not in protos or "udp" not in protos:
            errors.append("resolver SG must allow TCP and UDP 53")

    matrix = graph["outputs"].get("egress_route_matrix")
    if not isinstance(matrix, dict):
        errors.append("missing egress_route_matrix output")
    else:
        for key in az_keys:
            row = matrix.get(key) or {}
            if row.get("nat_az") != key:
                errors.append(f"cross-AZ or wrong nat_az for {key} in egress_route_matrix")
            if row.get("data_has_default_route") is True:
                errors.append(f"egress_route_matrix marks data default for {key}")
            if row.get("app_cidr") != topology["azs"][key]["app_cidr"]:
                errors.append(f"egress_route_matrix app_cidr mismatch for {key}")
            if row.get("data_cidr") != topology["azs"][key]["data_cidr"]:
                errors.append(f"egress_route_matrix data_cidr mismatch for {key}")

    legacy = _load("legacy_addresses.json")
    moved = graph.get("moved") or parse_moved_blocks()
    for key in legacy.get("legacy_keys") or []:
        subnet_ok = any(
            f'private["{key}"]' in m.get("from", "") and f'app["{key}"]' in m.get("to", "")
            and "subnet" in m.get("from", "")
            for m in moved
        )
        rt_ok = any(
            f'private["{key}"]' in m.get("from", "")
            and f'app["{key}"]' in m.get("to", "")
            and "route_table" in m.get("from", "")
            for m in moved
        )
        if not subnet_ok or not rt_ok:
            errors.append(f"missing legacy moved mappings for {key}")

    # Same-AZ NAT coverage diagnostic for incomplete NAT sets
    if required_nats - set(graph["nat_gateways"]):
        # already reported missing NAT; ensure message class exists for validate failures
        pass

    return sorted(set(errors))


def _nat_action(health: str, policy: dict) -> str:
    if health == "healthy":
        return "allow"
    if health == "draining":
        return policy.get("new_flow_when_draining", "refuse")
    return policy.get("new_flow_when_failed", "refuse")


def run_cutover(plan: dict, fail_az: str | None = None) -> dict:
    """Materialize namespaces, probe traffic, write report."""
    graph = normalize_plan(plan)
    topology = graph["topology"]
    services = graph["services"]
    nat_health = dict(_load("nat_health.json"))
    drain_policy = _load("drain_policy.json")
    legacy = _load("legacy_addresses.json")
    if fail_az:
        nat_health[fail_az] = "failed"

    policy_errors = plan_policy_errors(graph)
    cross_az = any("nat_az" in e or "cross-AZ" in e for e in policy_errors)

    namespaces: list[dict] = []
    for key in sorted(topology["azs"]):
        for kind in ("public", "app", "data", "nat"):
            namespaces.append({"name": f"{kind}-{key}", "kind": kind, "az": key})
    for svc in services["interface"]:
        namespaces.append({"name": f"endpoint-{svc}", "kind": "endpoint", "az": None})
    for svc in services["gateway"]:
        namespaces.append({"name": f"gateway-{svc}", "kind": "gateway", "az": None})
    namespaces.append({"name": "external", "kind": "external", "az": None})

    nat_decisions = {
        key: {
            "health": nat_health.get(key, "failed"),
            "new_flow_action": _nat_action(nat_health.get(key, "failed"), drain_policy),
        }
        for key in sorted(topology["azs"])
    }

    flows: list[dict] = []

    def add_flow(
        fid: str,
        src: str,
        dst: str,
        protocol: str,
        path: list[str],
        translated: str | None,
        allowed: bool,
    ) -> None:
        flows.append(
            {
                "id": fid,
                "src": src,
                "dst": dst,
                "protocol": protocol,
                "path": path,
                "translated_source": translated,
                "allowed": allowed,
            }
        )

    for key in sorted(topology["azs"]):
        decision = nat_decisions[key]
        eip = graph["eips"][key]["lab_ip"]

        if cross_az:
            add_flow(
                f"app-internet-{key}",
                f"app-{key}",
                "external",
                "tcp",
                [f"app-{key}", "nat-UNAPPROVED", "external"],
                eip,
                False,
            )
        elif decision["new_flow_action"] != "allow":
            add_flow(
                f"app-internet-{key}",
                f"app-{key}",
                "external",
                "tcp",
                [f"app-{key}", f"nat-{key}"],
                None,
                False,
            )
        elif key in graph["nat_gateways"] and key in graph["app_default"]:
            add_flow(
                f"app-internet-{key}",
                f"app-{key}",
                "external",
                "tcp",
                [f"app-{key}", f"nat-{key}", "external"],
                eip,
                True,
            )
        else:
            add_flow(
                f"app-internet-{key}",
                f"app-{key}",
                "external",
                "tcp",
                [f"app-{key}"],
                None,
                False,
            )

        data_has_default = key in graph["data_default"]
        add_flow(
            f"data-internet-{key}",
            f"data-{key}",
            "external",
            "tcp",
            [f"data-{key}", f"nat-{key}", "external"] if data_has_default else [f"data-{key}"],
            eip if data_has_default else None,
            bool(data_has_default),
        )

        has_s3 = "s3" in graph["endpoints_gw"]
        add_flow(
            f"app-s3-{key}",
            f"app-{key}",
            "gateway-s3",
            "tcp",
            [f"app-{key}", "gateway-s3"] if has_s3 else [f"app-{key}", f"nat-{key}", "external"],
            None if has_s3 else eip,
            bool(has_s3),
        )

        has_ddb = "dynamodb" in graph["endpoints_gw"]
        add_flow(
            f"app-ddb-{key}",
            f"app-{key}",
            "gateway-dynamodb",
            "tcp",
            [f"app-{key}", "gateway-dynamodb"] if has_ddb else [f"app-{key}", f"nat-{key}", "external"],
            None if has_ddb else eip,
            bool(has_ddb),
        )

        has_logs = "logs" in graph["endpoints_iface"]
        add_flow(
            f"app-logs-{key}",
            f"app-{key}",
            "endpoint-logs",
            "tcp",
            [f"app-{key}", "endpoint-logs"] if has_logs else [f"app-{key}"],
            None,
            bool(has_logs),
        )

        resolver_ok = "resolver" in graph["sgs"] and not any(
            e.startswith("resolver SG") for e in policy_errors
        )
        add_flow(
            f"dns-udp-{key}",
            f"corp-dns-{key}",
            "resolver",
            "udp",
            [f"corp-dns-{key}", "resolver"] if resolver_ok else [f"corp-dns-{key}"],
            None,
            bool(resolver_ok),
        )

    gateway_bypass = {
        "s3": all(f["allowed"] and "gateway-s3" in f["path"] for f in flows if f["id"].startswith("app-s3-")),
        "dynamodb": all(
            f["allowed"] and "gateway-dynamodb" in f["path"]
            for f in flows
            if f["id"].startswith("app-ddb-")
        ),
    }

    dns = {
        svc: f"{svc.replace('.', '-')}.vpce.{graph['defaults']['region']}.local"
        for svc in services["interface"]
        if svc in graph["endpoints_iface"]
    }

    data_isolated = all(not f["allowed"] for f in flows if f["id"].startswith("data-internet-"))

    destructive = 0
    for rtype in ("aws_subnet", "aws_route_table"):
        for rc in graph["changes"].get(rtype, []):
            actions = set((rc.get("change") or {}).get("actions") or [])
            if actions >= {"create", "delete"} or "replace" in actions:
                destructive += 1

    missing_moved = [
        e.split()[-1]
        for e in policy_errors
        if e.startswith("missing legacy moved mappings")
    ]

    # Traffic invariants append errors
    for key, dec in nat_decisions.items():
        flow = next(f for f in flows if f["id"] == f"app-internet-{key}")
        if dec["new_flow_action"] == "allow" and not flow["allowed"] and not cross_az:
            policy_errors.append(f"healthy AZ {key} app flow not allowed")
        if dec["new_flow_action"] == "refuse" and flow["allowed"]:
            policy_errors.append(f"draining/failed AZ {key} must refuse new flows")

    if not data_isolated:
        policy_errors.append("data tier is not isolated from internet default")
    if not gateway_bypass.get("s3"):
        policy_errors.append("S3 gateway bypass failed")
    if not gateway_bypass.get("dynamodb"):
        policy_errors.append("DynamoDB gateway bypass failed")
    if drain_policy.get("allow_cross_az_failover"):
        policy_errors.append("drain policy must not allow cross-AZ failover")

    policy_errors = sorted(set(policy_errors))
    status = "READY" if not policy_errors else "FAILED"

    report = {
        "status": status,
        "reason": None if status == "READY" else "policy_or_traffic_failure",
        "policy_errors": policy_errors,
        "namespaces": namespaces,
        "flows": flows,
        "nat_decisions": nat_decisions,
        "dns": dns,
        "gateway_bypass": gateway_bypass,
        "data_isolated": data_isolated,
        "migration": {
            "legacy_keys": list(legacy.get("legacy_keys") or []),
            "destructive_actions": destructive,
            "missing_moved": missing_moved,
        },
    }
    report["report_digest"] = report_digest(report)

    var = _var_dir()
    out = _output_dir()
    var.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    (var / "namespaces.json").write_text(json.dumps(namespaces, indent=2), encoding="utf-8")
    (out / "cutover-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
