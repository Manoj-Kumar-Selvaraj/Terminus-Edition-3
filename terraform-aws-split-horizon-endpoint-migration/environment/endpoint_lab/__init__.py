"""Split-horizon endpoint lab: plan graph, dnsmasq views, reachability probes."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

DATA = Path(os.environ.get("ENDPOINT_DATA_DIR", "/app/data"))
VAR = Path(os.environ.get("ENDPOINT_VAR_DIR", "/app/var/endpoint"))
OUTPUT = Path(os.environ.get("ENDPOINT_OUTPUT_DIR", "/app/output"))

PRIVATE_DNS_PORT = 5353
PUBLIC_DNS_PORT = 5354


def _load_json(name: str) -> Any:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _canonicalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        items = [_canonicalize(v) for v in value]

        def _sort_key(item: Any) -> str:
            if isinstance(item, dict):
                ident = item.get("address") or item.get("name") or item.get("key")
                if ident is not None:
                    return json.dumps([str(ident)], sort_keys=True)
            return json.dumps(item, sort_keys=True, separators=(",", ":"))

        items.sort(key=_sort_key)
        return items
    return value


def plan_digest(plan: dict) -> str:
    stable = {k: v for k, v in plan.items() if k != "timestamp"}
    blob = json.dumps(_canonicalize(stable), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def _walk_modules(module: dict) -> list[dict]:
    resources = list(module.get("resources") or [])
    for child in module.get("child_modules") or []:
        resources.extend(_walk_modules(child))
    return resources


def _walk_config_modules(module: dict) -> list[dict]:
    resources = list(module.get("resources") or [])
    for child in module.get("module_calls") or {}.values() if False else []:
        pass
    # configuration uses module_calls differently; flatten recursively
    calls = module.get("module_calls") or {}
    for call in calls.values():
        nested = (call.get("module") or {})
        resources.extend(_walk_config_modules(nested))
    return resources


def _resource_address_key(address: str) -> str | None:
    m = re.search(r'\["([^"]+)"\]', address)
    return m.group(1) if m else None


def _collect_planned(plan: dict) -> dict[str, list[dict]]:
    root = ((plan.get("planned_values") or {}).get("root_module") or {})
    by_type: dict[str, list[dict]] = {}
    for res in _walk_modules(root):
        by_type.setdefault(res.get("type") or "", []).append(res)
    return by_type


def _collect_changes(plan: dict) -> list[dict]:
    return list(plan.get("resource_changes") or [])


def normalize_plan(plan: dict, inventory: dict | None = None) -> dict:
    """Build a domain graph from terraform show -json plus public inventory."""
    inventory = inventory or _load_json("inventory.json")
    endpoints = _load_json("endpoints.json")
    zones = _load_json("dns_zones.json")
    allowed = _load_json("allowed_sources.json")

    by_type = _collect_planned(plan)
    changes = _collect_changes(plan)

    # Association keys encode relationships: "s3:private-a", "ssm:private-a"
    gw_rt_keys: set[str] = set()
    if_subnet_keys: set[str] = set()
    for res in by_type.get("aws_vpc_endpoint_route_table_association", []):
        key = res.get("name") or _resource_address_key(res.get("address") or "")
        # for_each resources use index in address; name is the resource label
        addr = res.get("address") or ""
        fk = _resource_address_key(addr)
        if fk:
            gw_rt_keys.add(fk)
    for ch in changes:
        if ch.get("type") == "aws_vpc_endpoint_route_table_association":
            fk = _resource_address_key(ch.get("address") or "")
            if fk:
                gw_rt_keys.add(fk)
        if ch.get("type") == "aws_vpc_endpoint_subnet_association":
            fk = _resource_address_key(ch.get("address") or "")
            if fk:
                if_subnet_keys.add(fk)

    # Also accept for_each on the endpoint resources themselves via tags
    gateway_eps: dict[str, dict] = {}
    interface_eps: dict[str, dict] = {}
    for res in by_type.get("aws_vpc_endpoint", []):
        vals = res.get("values") or {}
        addr = res.get("address") or ""
        key = _resource_address_key(addr) or res.get("name") or ""
        tags = vals.get("tags") or {}
        kind = (tags.get("EndpointKind") or vals.get("vpc_endpoint_type") or "").lower()
        svc = tags.get("Service") or key
        entry = {
            "key": key,
            "service": svc,
            "type": vals.get("vpc_endpoint_type") or tags.get("EndpointKind"),
            "private_dns_enabled": bool(vals.get("private_dns_enabled")),
            "tags": tags,
            "address": addr,
        }
        if str(entry["type"]).lower() == "gateway" or kind == "gateway":
            gateway_eps[svc] = entry
        else:
            interface_eps[svc] = entry

    # Fall back: parse association keys from resource_changes addresses only
    for ch in changes:
        addr = ch.get("address") or ""
        fk = _resource_address_key(addr)
        if not fk:
            continue
        if ch.get("type") == "aws_vpc_endpoint_route_table_association":
            gw_rt_keys.add(fk)
        if ch.get("type") == "aws_vpc_endpoint_subnet_association":
            if_subnet_keys.add(fk)

    # Security group ingress from dedicated rules or inline
    ingress_cidrs: list[str] = []
    ingress_sgs: list[str] = []
    ingress_ipv6: list[str] = []
    for res in by_type.get("aws_vpc_security_group_ingress_rule", []):
        vals = res.get("values") or {}
        tags = vals.get("tags") or {}
        if vals.get("cidr_ipv4"):
            ingress_cidrs.append(vals["cidr_ipv4"])
        if vals.get("cidr_ipv6"):
            ingress_ipv6.append(vals["cidr_ipv6"])
        # referenced SG ids are often unknown; accept tag SourceSg
        if tags.get("SourceSg"):
            ingress_sgs.append(tags["SourceSg"])
        if vals.get("referenced_security_group_id"):
            ingress_sgs.append(str(vals["referenced_security_group_id"]))

    for res in by_type.get("aws_security_group", []):
        vals = res.get("values") or {}
        for rule in vals.get("ingress") or []:
            ingress_cidrs.extend(rule.get("cidr_blocks") or [])
            ingress_ipv6.extend(rule.get("ipv6_cidr_blocks") or [])
            ingress_sgs.extend(rule.get("security_groups") or [])

    # Private zones + records. Ownership is ZoneKey/OwnerVpc tags; extra
    # aws_route53_zone_association for_each keys use "zone:vpc".
    zone_keys: set[str] = set()
    zone_owner: dict[str, str] = {}
    zone_assoc: set[str] = set()
    records: dict[str, str] = {}
    for res in by_type.get("aws_route53_zone", []):
        vals = res.get("values") or {}
        tags = vals.get("tags") or {}
        zk = tags.get("ZoneKey") or _resource_address_key(res.get("address") or "") or res.get("name")
        if zk:
            zone_keys.add(str(zk))
            owner = tags.get("OwnerVpc")
            if owner:
                zone_owner[str(zk)] = str(owner)
                zone_assoc.add(f"{zk}:{owner}")
    for ch in changes:
        if ch.get("type") == "aws_route53_zone_association":
            fk = _resource_address_key(ch.get("address") or "")
            if fk:
                zone_assoc.add(fk)
        if ch.get("type") == "aws_route53_record":
            after = (ch.get("change") or {}).get("after") or {}
            name = (after.get("name") or "").rstrip(".")
            records_list = after.get("records") or []
            if name and records_list:
                records[name] = records_list[0]
        if ch.get("type") == "aws_route53_zone":
            after = (ch.get("change") or {}).get("after") or {}
            tags = after.get("tags") or {}
            zk = tags.get("ZoneKey") or _resource_address_key(ch.get("address") or "")
            if zk:
                zone_keys.add(str(zk))
                owner = tags.get("OwnerVpc")
                if owner:
                    zone_owner[str(zk)] = str(owner)
                    zone_assoc.add(f"{zk}:{owner}")

    # Outputs from planned values
    outputs = ((plan.get("planned_values") or {}).get("outputs") or {})
    output_names = set(outputs.keys())

    private_rt_keys = [
        k for k, v in inventory["route_tables"].items() if v.get("tier") == "private"
    ]
    public_rt_keys = [
        k for k, v in inventory["route_tables"].items() if v.get("tier") == "public"
    ]
    private_subnet_keys = [
        k for k, v in inventory["subnets"].items() if v.get("tier") == "private"
    ]
    public_subnet_keys = [
        k for k, v in inventory["subnets"].items() if v.get("tier") == "public"
    ]

    required_gw = set(endpoints["gateway"].keys())
    required_if = set(endpoints["interface"].keys())

    gw_coverage = {svc: set() for svc in required_gw}
    for fk in gw_rt_keys:
        if ":" in fk:
            svc, rt = fk.split(":", 1)
            if svc in gw_coverage:
                gw_coverage[svc].add(rt)

    if_placement = {svc: set() for svc in required_if}
    for fk in if_subnet_keys:
        if ":" in fk:
            svc, sn = fk.split(":", 1)
            if svc in if_placement:
                if_placement[svc].add(sn)

    graph = {
        "inventory": inventory,
        "endpoints_catalog": endpoints,
        "zones_catalog": zones,
        "allowed": allowed,
        "gateway_eps": gateway_eps,
        "interface_eps": interface_eps,
        "gw_rt_keys": sorted(gw_rt_keys),
        "if_subnet_keys": sorted(if_subnet_keys),
        "gw_coverage": {k: sorted(v) for k, v in gw_coverage.items()},
        "if_placement": {k: sorted(v) for k, v in if_placement.items()},
        "private_rt_keys": private_rt_keys,
        "public_rt_keys": public_rt_keys,
        "private_subnet_keys": private_subnet_keys,
        "public_subnet_keys": public_subnet_keys,
        "ingress_cidrs": sorted(set(ingress_cidrs)),
        "ingress_sgs": sorted(set(ingress_sgs)),
        "ingress_ipv6": sorted(set(ingress_ipv6)),
        "zone_keys": sorted(zone_keys),
        "zone_owner": zone_owner,
        "zone_assoc": sorted(zone_assoc),
        "records": records,
        "output_names": sorted(output_names),
        "required_outputs": [
            "vpc_id",
            "vpc_cidr_block",
            "private_subnet_ids",
            "public_subnet_ids",
            "private_route_table_ids",
            "public_route_table_ids",
            "gateway_vpc_endpoint_ids",
            "interface_vpc_endpoint_ids",
            "endpoint_security_group_id",
            "endpoint_security_group_ids",
            "network",
            "endpoint_ids",
        ],
    }
    return graph


def validate_graph(graph: dict) -> list[str]:
    errors: list[str] = []
    catalog = graph["endpoints_catalog"]
    allowed = graph["allowed"]

    for svc in catalog["gateway"]:
        if svc not in graph["gateway_eps"]:
            errors.append(f"missing gateway endpoint {svc}")
            continue
        covered = set(graph["gw_coverage"].get(svc) or [])
        need = set(graph["private_rt_keys"])
        if covered != need:
            errors.append(f"gateway {svc} rt coverage {sorted(covered)} != {sorted(need)}")
        if covered & set(graph["public_rt_keys"]):
            errors.append(f"gateway {svc} attached to public route tables")

    for svc, meta in catalog["interface"].items():
        if svc not in graph["interface_eps"]:
            errors.append(f"missing interface endpoint {svc}")
            continue
        ep = graph["interface_eps"][svc]
        if not ep.get("private_dns_enabled"):
            errors.append(f"interface {svc} private_dns_enabled is false")
        placed = set(graph["if_placement"].get(svc) or [])
        need = set(graph["private_subnet_keys"])
        if placed != need:
            errors.append(f"interface {svc} subnet placement {sorted(placed)} != {sorted(need)}")
        if placed & set(graph["public_subnet_keys"]):
            errors.append(f"interface {svc} placed in public subnet")

    if "0.0.0.0/0" in graph["ingress_cidrs"] or "::/0" in graph["ingress_ipv6"]:
        errors.append("endpoint SG admits the world")

    for cidr in allowed.get("cidr_blocks") or []:
        if cidr not in graph["ingress_cidrs"]:
            errors.append(f"missing ingress cidr {cidr}")
    for sg in allowed.get("security_group_ids") or []:
        # Accept either literal id in tags or presence via SourceSg tags
        if sg not in graph["ingress_sgs"] and not any(
            sg in s for s in graph["ingress_sgs"]
        ):
            # Starter may encode via tags SourceSg=<id>
            if sg not in graph["ingress_sgs"]:
                errors.append(f"missing ingress source sg {sg}")

    for name in graph["required_outputs"]:
        if name not in graph["output_names"]:
            errors.append(f"missing output {name}")

    # Shared VPC must own vpce + shared-services; foreign overlap must stay foreign.
    for zk in ("vpce", "shared-services"):
        if zk not in graph["zone_keys"]:
            errors.append(f"missing private zone {zk}")
        if graph.get("zone_owner", {}).get(zk) != "shared":
            errors.append(f"zone {zk} owner is not shared VPC")
        if f"{zk}:shared" not in graph["zone_assoc"]:
            errors.append(f"zone {zk} not associated to shared VPC")
    if graph.get("zone_owner", {}).get("overlap-shadow") not in (None, "foreign"):
        if graph.get("zone_owner", {}).get("overlap-shadow") == "shared":
            errors.append("foreign overlapping zone owned by shared VPC")
    if "overlap-shadow:shared" in graph["zone_assoc"]:
        errors.append("foreign overlapping zone associated to shared VPC")
    if "overlap-shadow" in graph["zone_keys"]:
        if graph.get("zone_owner", {}).get("overlap-shadow") != "foreign":
            errors.append("overlap-shadow zone not owned by foreign VPC")

    return errors


def _write_hosts(path: Path, records: dict[str, str]) -> None:
    lines = [f"{ip} {name}" for name, ip in sorted(records.items())]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _start_dnsmasq(port: int, hosts_file: Path, pid_file: Path, log_file: Path) -> subprocess.Popen:
    cmd = [
        "dnsmasq",
        "--no-daemon",
        "--port",
        str(port),
        "--listen-address=127.0.0.1",
        "--bind-interfaces",
        f"--addn-hosts={hosts_file}",
        "--no-resolv",
        "--no-hosts",
        f"--pid-file={pid_file}",
        f"--log-facility={log_file}",
    ]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _dig(port: int, qname: str) -> str | None:
    proc = subprocess.run(
        ["dig", "+short", "+time=1", "+tries=1", "@127.0.0.1", "-p", str(port), qname, "A"],
        text=True,
        capture_output=True,
    )
    out = (proc.stdout or "").strip()
    if not out:
        return None
    # dig may return CNAME then A; take last IPv4-looking token
    for line in reversed(out.splitlines()):
        line = line.strip()
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", line):
            return line
    return None


def build_view_records(graph: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Private view gets interface + owned zone records; public does not."""
    catalog = graph["endpoints_catalog"]
    zones = graph["zones_catalog"]
    private: dict[str, str] = {}
    public: dict[str, str] = {
        # Public view keeps a distinct decoy for overlap name so leaks are visible
        "api.shared.services.internal": "198.51.100.99",
    }

    for svc, meta in catalog["interface"].items():
        ep = graph["interface_eps"].get(svc)
        if ep and ep.get("private_dns_enabled"):
            private[meta["private_dns_name"]] = meta["lab_ipv4"]
            # Public must not get the private lab address
        else:
            # disabled private dns: neither view gets private answer from AWS name
            pass

    for zone in zones["zones"]:
        if zone["owner_vpc_key"] != "shared":
            continue
        if f"{zone['key']}:shared" not in graph["zone_assoc"]:
            continue
        for rec in zone.get("records") or []:
            name = rec["name"]
            if rec.get("endpoint_key"):
                meta = catalog["interface"][rec["endpoint_key"]]
                private[name] = meta["lab_ipv4"]
            elif rec.get("static_ipv4"):
                private[name] = rec["static_ipv4"]

    return private, public


def run_dns_probes(graph: dict) -> list[dict]:
    VAR.mkdir(parents=True, exist_ok=True)
    private_records, public_records = build_view_records(graph)
    priv_hosts = VAR / "private.hosts"
    pub_hosts = VAR / "public.hosts"
    _write_hosts(priv_hosts, private_records)
    _write_hosts(pub_hosts, public_records)

    procs: list[subprocess.Popen] = []
    probes: list[dict] = []
    try:
        procs.append(
            _start_dnsmasq(
                PRIVATE_DNS_PORT,
                priv_hosts,
                VAR / "private.pid",
                VAR / "private.dnsmasq.log",
            )
        )
        procs.append(
            _start_dnsmasq(
                PUBLIC_DNS_PORT,
                pub_hosts,
                VAR / "public.pid",
                VAR / "public.dnsmasq.log",
            )
        )
        time.sleep(0.4)

        catalog = graph["endpoints_catalog"]
        for svc, meta in catalog["interface"].items():
            q = meta["private_dns_name"]
            ans = _dig(PRIVATE_DNS_PORT, q)
            ok = ans == meta["lab_ipv4"] and bool(
                graph["interface_eps"].get(svc, {}).get("private_dns_enabled")
            )
            probes.append(
                {"name": f"private-dns:{svc}", "view": "private", "qname": q, "answer": ans, "ok": ok}
            )
            pub = _dig(PUBLIC_DNS_PORT, q)
            leak = pub == meta["lab_ipv4"]
            probes.append(
                {
                    "name": f"public-isolation:{svc}",
                    "view": "public",
                    "qname": q,
                    "answer": pub,
                    "ok": not leak,
                }
            )

        overlap = "api.shared.services.internal"
        priv = _dig(PRIVATE_DNS_PORT, overlap)
        expected = catalog["interface"]["ssm"]["lab_ipv4"]
        probes.append(
            {
                "name": "overlap-private-owner",
                "view": "private",
                "qname": overlap,
                "answer": priv,
                "ok": priv == expected,
            }
        )
        pub = _dig(PUBLIC_DNS_PORT, overlap)
        probes.append(
            {
                "name": "overlap-public-not-private",
                "view": "public",
                "qname": overlap,
                "answer": pub,
                "ok": pub != expected,
            }
        )
    finally:
        for p in procs:
            p.terminate()
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                p.kill()
    return probes


def run_reachability_probes(graph: dict) -> list[dict]:
    probes: list[dict] = []
    catalog = graph["endpoints_catalog"]
    for svc in catalog["gateway"]:
        covered = set(graph["gw_coverage"].get(svc) or [])
        need = set(graph["private_rt_keys"])
        ok = covered == need and not (covered & set(graph["public_rt_keys"]))
        probes.append(
            {
                "name": f"gateway-path:{svc}",
                "ok": ok,
                "detail": {"covered": sorted(covered), "need": sorted(need)},
            }
        )
    for svc in catalog["interface"]:
        placed = set(graph["if_placement"].get(svc) or [])
        need = set(graph["private_subnet_keys"])
        ok = (
            placed == need
            and not (placed & set(graph["public_subnet_keys"]))
            and bool(graph["interface_eps"].get(svc, {}).get("private_dns_enabled"))
        )
        probes.append(
            {
                "name": f"interface-placement:{svc}",
                "ok": ok,
                "detail": {"placed": sorted(placed), "need": sorted(need)},
            }
        )
    world = "0.0.0.0/0" in graph["ingress_cidrs"] or "::/0" in graph["ingress_ipv6"]
    probes.append({"name": "endpoint-sg-closed", "ok": not world})
    return probes


def migration_is_safe(plan_against_legacy: dict) -> bool:
    """True when list-indexed legacy identities are moved, not destroyed/replaced."""
    indexed = re.compile(
        r"(aws_subnet\.private\[\d+\]|aws_route_table\.private\[\d+\]|"
        r"aws_security_group\.endpoint\[\d+\])"
    )
    named = re.compile(
        r'(aws_subnet\.this\["private-[ab]"\]|aws_route_table\.this\["private-[ab]"\]|'
        r"module\.network\.aws_security_group\.endpoint$|module\.network\.aws_vpc\.this$)"
    )
    for ch in plan_against_legacy.get("resource_changes") or []:
        addr = ch.get("address") or ""
        actions = set(ch.get("change", {}).get("actions") or [])
        if indexed.search(addr) and "delete" in actions:
            return False
        if named.search(addr) and (
            actions >= {"create", "delete"} or actions == {"delete"}
        ):
            return False
    return True


def write_evidence(
    staging_plan: dict,
    consumer_plan: dict,
    graph: dict,
    dns_probes: list[dict],
    reach_probes: list[dict],
    migration_safe: bool,
) -> dict:
    graph_errors = validate_graph(graph)
    all_probes = dns_probes + reach_probes
    ready = (
        migration_safe
        and not graph_errors
        and all(p.get("ok") for p in all_probes)
    )
    status = "READY" if ready else "FAILED"
    stable = {
        "status": status,
        "plan_digest": plan_digest(staging_plan),
        "consumer_plan_digest": plan_digest(consumer_plan),
        "migration_safe": migration_safe,
        "dns_probes": dns_probes,
        "reachability_probes": reach_probes,
        "graph_errors": graph_errors,
    }
    digest = hashlib.sha256(
        json.dumps(
            {
                "status": status,
                "plan_digest": stable["plan_digest"],
                "consumer_plan_digest": stable["consumer_plan_digest"],
                "migration_safe": migration_safe,
                "dns_probes": dns_probes,
                "reachability_probes": reach_probes,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    evidence = {**stable, "evidence_digest": digest}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    VAR.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "migration-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    (VAR / "plan.json").write_text(json.dumps(staging_plan) + "\n", encoding="utf-8")
    return evidence


def run_lab(
    staging_plan: dict,
    consumer_plan: dict,
    legacy_plan: dict | None = None,
) -> dict:
    graph = normalize_plan(staging_plan)
    dns = run_dns_probes(graph)
    reach = run_reachability_probes(graph)
    safe = True if legacy_plan is None else migration_is_safe(legacy_plan)
    return write_evidence(staging_plan, consumer_plan, graph, dns, reach, safe)
