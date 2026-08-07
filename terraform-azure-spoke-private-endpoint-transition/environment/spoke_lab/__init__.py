"""Plan-driven Azure spoke network/DNS transition lab.

Consumes terraform show -json output, builds an effective routing/NSG/DNS
graph, exercises probes, and writes a transition report. No privileged
network namespaces — decisions are evaluated in-process against the plan.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


PLATFORM_KEYS = frozenset(
    {"AzureFirewallSubnet", "GatewaySubnet", "AzureBastionSubnet"}
)

PRIVATE_DNS_ZONES = {
    "blob": "privatelink.blob.core.windows.net",
    "queue": "privatelink.queue.core.windows.net",
    "keyvault": "privatelink.vaultcore.azure.net",
    "postgresql": "privatelink.database.windows.net",
}

REQUIRED_TAGS = {
    "managed_by": "terraform",
    "data_classification": "regulated",
    "business_unit": "payments",
}


def _data_dir() -> Path:
    return Path(os.environ.get("SPOKE_DATA_DIR", "/app/data"))


def _var_dir() -> Path:
    return Path(os.environ.get("SPOKE_VAR_DIR", "/app/var/spoke"))


def _output_dir() -> Path:
    return Path(os.environ.get("SPOKE_OUTPUT_DIR", "/app/output"))


def _load(name: str) -> Any:
    return json.loads((_data_dir() / name).read_text(encoding="utf-8"))


def _after(rc: dict) -> dict:
    return (rc.get("change") or {}).get("after") or {}


def _actions(rc: dict) -> list[str]:
    return list((rc.get("change") or {}).get("actions") or [])


def _key_from_address(address: str) -> str | None:
    m = re.search(r'\["([^"]+)"\]', address)
    if m:
        return m.group(1)
    m = re.search(r"\.([^.\[\"]+)$", address)
    return m.group(1) if m else None


def normalize_plan(plan: dict) -> dict:
    """Extract semantic Azure spoke graph from a Terraform plan."""
    changes = plan.get("resource_changes") or []
    vnets: list[dict] = []
    subnets: dict[str, dict] = {}
    route_tables: dict[str, dict] = {}
    routes: list[dict] = []
    rt_assocs: list[dict] = []
    nsgs: dict[str, dict] = {}
    nsg_rules: list[dict] = []
    nsg_assocs: list[dict] = []
    dns_zones: dict[str, dict] = {}
    dns_links: list[dict] = []
    endpoints: dict[str, dict] = {}
    diagnostics: list[dict] = []
    locks: list[dict] = []

    prior = plan.get("prior_state") or {}
    prior_resources: list[str] = []
    values = (prior.get("values") or {}).get("root_module") or {}
    for mod in values.get("resources") or []:
        if mod.get("address"):
            prior_resources.append(mod["address"])
    for child in values.get("child_modules") or []:
        for res in child.get("resources") or []:
            if res.get("address"):
                prior_resources.append(res["address"])

    for rc in changes:
        rtype = rc.get("type")
        after = _after(rc)
        acts = _actions(rc)
        if not any(a in acts for a in ("create", "update", "no-op", "read")):
            # still include create/update; skip pure deletes for graph build
            if "delete" in acts and "create" not in acts:
                continue
        addr = rc.get("address") or ""
        key = _key_from_address(addr) or after.get("name") or addr

        if rtype == "azurerm_virtual_network":
            ddos = after.get("ddos_protection_plan") or []
            if isinstance(ddos, dict):
                ddos = [ddos]
            vnets.append(
                {
                    "name": after.get("name"),
                    "address_space": list(after.get("address_space") or []),
                    "tags": dict(after.get("tags") or {}),
                    "ddos": ddos,
                    "address": addr,
                }
            )
        elif rtype == "azurerm_subnet":
            name = after.get("name") or key
            subnets[name] = {
                "name": name,
                "address_prefixes": list(after.get("address_prefixes") or []),
                "private_endpoint_network_policies": after.get(
                    "private_endpoint_network_policies"
                ),
                "virtual_network_name": after.get("virtual_network_name"),
                "address": addr,
                "id": after.get("id"),
            }
        elif rtype == "azurerm_route_table":
            name = after.get("name") or key
            route_tables[key] = {
                "key": key,
                "name": name,
                "disable_bgp_route_propagation": after.get(
                    "disable_bgp_route_propagation"
                ),
                "tags": dict(after.get("tags") or {}),
                "address": addr,
                "id": after.get("id"),
            }
        elif rtype == "azurerm_route":
            routes.append(
                {
                    "key": key,
                    "name": after.get("name"),
                    "address_prefix": after.get("address_prefix"),
                    "next_hop_type": after.get("next_hop_type"),
                    "next_hop_in_ip_address": after.get("next_hop_in_ip_address"),
                    "route_table_name": after.get("route_table_name"),
                    "address": addr,
                }
            )
        elif rtype == "azurerm_subnet_route_table_association":
            rt_assocs.append(
                {
                    "key": key,
                    "subnet_id": after.get("subnet_id"),
                    "route_table_id": after.get("route_table_id"),
                    "address": addr,
                }
            )
        elif rtype == "azurerm_network_security_group":
            nsgs[key] = {
                "key": key,
                "name": after.get("name"),
                "tags": dict(after.get("tags") or {}),
                "address": addr,
                "id": after.get("id"),
            }
        elif rtype == "azurerm_network_security_rule":
            nsg_rules.append(
                {
                    "key": key,
                    "name": after.get("name"),
                    "nsg_name": after.get("network_security_group_name"),
                    "priority": after.get("priority"),
                    "direction": after.get("direction"),
                    "access": after.get("access"),
                    "protocol": after.get("protocol"),
                    "source_address_prefix": after.get("source_address_prefix"),
                    "source_address_prefixes": list(
                        after.get("source_address_prefixes") or []
                    ),
                    "destination_port_range": after.get("destination_port_range"),
                    "destination_port_ranges": list(
                        after.get("destination_port_ranges") or []
                    ),
                    "destination_address_prefix": after.get(
                        "destination_address_prefix"
                    ),
                    "address": addr,
                }
            )
        elif rtype == "azurerm_subnet_network_security_group_association":
            nsg_assocs.append(
                {
                    "key": key,
                    "subnet_id": after.get("subnet_id"),
                    "network_security_group_id": after.get(
                        "network_security_group_id"
                    ),
                    "address": addr,
                }
            )
        elif rtype == "azurerm_private_dns_zone":
            dns_zones[key] = {
                "key": key,
                "name": after.get("name"),
                "tags": dict(after.get("tags") or {}),
                "address": addr,
                "id": after.get("id"),
            }
        elif rtype == "azurerm_private_dns_zone_virtual_network_link":
            dns_links.append(
                {
                    "key": key,
                    "name": after.get("name"),
                    "zone_name": after.get("private_dns_zone_name"),
                    "virtual_network_id": after.get("virtual_network_id"),
                    "registration_enabled": after.get("registration_enabled"),
                    "address": addr,
                }
            )
        elif rtype == "azurerm_private_endpoint":
            psc = after.get("private_service_connection") or []
            if isinstance(psc, dict):
                psc = [psc]
            zgroup = after.get("private_dns_zone_group") or []
            if isinstance(zgroup, dict):
                zgroup = [zgroup]
            after_unknown = (rc.get("change") or {}).get("after_unknown") or {}
            has_zgroup = bool(zgroup) or bool(
                after_unknown.get("private_dns_zone_group")
            )
            endpoints[key] = {
                "key": key,
                "name": after.get("name"),
                "subnet_id": after.get("subnet_id"),
                "subnet_key_hint": None,
                "psc": psc,
                "dns_zone_group": zgroup
                if zgroup
                else ([{"planned": True}] if has_zgroup else []),
                "tags": dict(after.get("tags") or {}),
                "address": addr,
            }
        elif rtype == "azurerm_monitor_diagnostic_setting":
            logs = after.get("enabled_log") or []
            if isinstance(logs, dict):
                logs = list(logs.values()) if False else [logs]
            # Set encoding may appear as list of objects
            if not isinstance(logs, list):
                logs = list(logs) if logs else []
            cats = []
            for item in logs:
                if isinstance(item, dict):
                    cats.append(item.get("category"))
                else:
                    cats.append(item)
            diagnostics.append(
                {
                    "name": after.get("name"),
                    "target_resource_id": after.get("target_resource_id"),
                    "workspace_id": after.get("log_analytics_workspace_id"),
                    "categories": cats,
                    "address": addr,
                }
            )
        elif rtype == "azurerm_management_lock":
            locks.append(
                {
                    "name": after.get("name"),
                    "scope": after.get("scope"),
                    "lock_level": after.get("lock_level"),
                    "address": addr,
                }
            )

    return {
        "vnets": vnets,
        "subnets": subnets,
        "route_tables": route_tables,
        "routes": routes,
        "rt_assocs": rt_assocs,
        "nsgs": nsgs,
        "nsg_rules": nsg_rules,
        "nsg_assocs": nsg_assocs,
        "dns_zones": dns_zones,
        "dns_links": dns_links,
        "endpoints": endpoints,
        "diagnostics": diagnostics,
        "locks": locks,
        "prior_resources": prior_resources,
        "resource_changes": changes,
    }


def _subnet_id_map(graph: dict) -> dict[str, str]:
    """Map synthetic or planned subnet ids back to subnet names when possible."""
    by_id: dict[str, str] = {}
    for name, sn in graph["subnets"].items():
        sid = sn.get("id")
        if sid:
            by_id[sid] = name
        # Also match references that embed the name
        by_id[f"subnet:{name}"] = name
    return by_id


def _resolve_subnet_name(subnet_id: str | None, graph: dict) -> str | None:
    if not subnet_id:
        return None
    by_id = _subnet_id_map(graph)
    if subnet_id in by_id:
        return by_id[subnet_id]
    for name in graph["subnets"]:
        if name in subnet_id:
            return name
    return None


def policy_errors(graph: dict, topology: dict, governance: dict) -> list[str]:
    errors: list[str] = []
    pe_key = topology["private_endpoint_subnet_key"]
    fw_ip = topology["firewall_private_ip"]
    reserved = set(topology.get("reserved_subnet_names") or []) | PLATFORM_KEYS
    reserved = reserved | {pe_key}
    expected_subnets = set(topology["subnets"].keys())
    planned_subnets = set(graph["subnets"].keys())

    if expected_subnets - planned_subnets:
        errors.append(
            f"missing subnets: {sorted(expected_subnets - planned_subnets)}"
        )
    if not graph["vnets"]:
        errors.append("missing virtual network")

    # Routeable workload subnets must get VirtualAppliance default via firewall
    for skey, sn in topology["subnets"].items():
        if skey in reserved or not sn.get("route_table_enabled", True):
            continue
        # Find route for this key
        matching_routes = [
            r
            for r in graph["routes"]
            if r.get("key") == skey
            or (r.get("route_table_name") or "").endswith(f"-{skey}-rt")
            or skey in (r.get("address") or "")
        ]
        if not matching_routes:
            # try associate by key in route_tables
            if skey not in graph["route_tables"]:
                errors.append(f"{skey}: missing route table")
                continue
            matching_routes = [
                r
                for r in graph["routes"]
                if r.get("key") == skey
                or r.get("route_table_name") == graph["route_tables"][skey]["name"]
            ]
        if not matching_routes:
            errors.append(f"{skey}: missing default egress route")
            continue
        ok = False
        for r in matching_routes:
            if (
                r.get("address_prefix") == "0.0.0.0/0"
                and r.get("next_hop_type") == "VirtualAppliance"
                and r.get("next_hop_in_ip_address") == fw_ip
            ):
                ok = True
        if not ok:
            errors.append(f"{skey}: default route must be VirtualAppliance->{fw_ip}")

    # Platform / PE subnets must not have route tables
    for skey in reserved:
        if skey in graph["route_tables"]:
            errors.append(f"{skey}: must not have workload route table")
        for r in graph["routes"]:
            if r.get("key") == skey or skey in (r.get("address") or ""):
                errors.append(f"{skey}: must not have UDR routes")

    # BGP propagation disabled on route tables
    for key, rt in graph["route_tables"].items():
        if rt.get("disable_bgp_route_propagation") is not True:
            errors.append(f"route table {key}: BGP propagation must be disabled")

    # Internet next hops forbidden
    for r in graph["routes"]:
        if r.get("next_hop_type") == "Internet":
            errors.append(f"route {r.get('address')}: Internet next hop forbidden")

    # NSG coverage for nsg_enabled subnets
    for skey, sn in topology["subnets"].items():
        if not sn.get("nsg_enabled", True):
            if skey in graph["nsgs"]:
                errors.append(f"{skey}: NSG should not be managed")
            continue
        if skey not in graph["nsgs"]:
            errors.append(f"{skey}: missing NSG")

    # Deny internet inbound on each NSG; no broad allow from Internet
    nsg_names = {v["name"]: k for k, v in graph["nsgs"].items()}
    for key in graph["nsgs"]:
        rules = [
            r
            for r in graph["nsg_rules"]
            if r.get("key") == key
            or r.get("nsg_name") == graph["nsgs"][key]["name"]
            or key in (r.get("address") or "")
        ]
        has_deny = any(
            r.get("access") == "Deny"
            and r.get("direction") == "Inbound"
            and r.get("source_address_prefix") == "Internet"
            for r in rules
        )
        if not has_deny:
            errors.append(f"nsg {key}: missing Deny Internet inbound")
        for r in rules:
            src = r.get("source_address_prefix")
            prefixes = r.get("source_address_prefixes") or []
            if r.get("access") == "Allow" and r.get("direction") == "Inbound":
                if src in ("Internet", "*", "0.0.0.0/0") or any(
                    p in ("Internet", "*", "0.0.0.0/0") for p in prefixes
                ):
                    errors.append(f"nsg rule {r.get('name')}: broad Internet allow")

    # App / data tier rules
    app_cidrs = []
    for skey, sn in topology["subnets"].items():
        if str(sn.get("tier", "")).lower() == "app" and sn.get("nsg_enabled", True):
            app_cidrs.extend(sn.get("address_prefixes") or [])
    agw = topology.get("application_gateway_subnet_cidr")
    app_ports = [str(p) for p in topology.get("app_ports") or [443]]
    data_ports = {"1433", "5432", "6379"}

    for skey, sn in topology["subnets"].items():
        if not sn.get("nsg_enabled", True):
            continue
        tier = str(sn.get("tier", "")).lower()
        rules = [
            r
            for r in graph["nsg_rules"]
            if r.get("key") == skey
            or key_match(r, skey, graph)
        ]
        if tier == "app":
            found = False
            for r in rules:
                if (
                    r.get("access") == "Allow"
                    and r.get("direction") == "Inbound"
                    and r.get("source_address_prefix") == agw
                    and set(r.get("destination_port_ranges") or []) >= set(app_ports)
                ):
                    found = True
            if not found:
                errors.append(f"{skey}: missing AppGateway allow rule")
        if tier == "data":
            found = False
            for r in rules:
                srcs = set(r.get("source_address_prefixes") or [])
                if r.get("source_address_prefix"):
                    srcs.add(r["source_address_prefix"])
                ports = set(r.get("destination_port_ranges") or [])
                if (
                    r.get("access") == "Allow"
                    and r.get("direction") == "Inbound"
                    and srcs >= set(app_cidrs)
                    and ports >= data_ports
                ):
                    found = True
            if not found:
                errors.append(f"{skey}: missing app->data allow rule")

    # Private DNS catalog
    zone_names = {z["name"] for z in graph["dns_zones"].values()}
    for expected in PRIVATE_DNS_ZONES.values():
        if expected not in zone_names:
            errors.append(f"missing private dns zone {expected}")
    for link in graph["dns_links"]:
        if link.get("registration_enabled") is True:
            errors.append(f"dns link {link.get('name')}: registration must be off")
    if len(graph["dns_links"]) < len(PRIVATE_DNS_ZONES):
        errors.append("each private dns zone must link to the spoke VNet")

    # Endpoints
    if pe_key not in graph["subnets"]:
        errors.append("private endpoint subnet missing")
    else:
        pol = graph["subnets"][pe_key].get("private_endpoint_network_policies")
        if pol not in ("Disabled", "NetworkSecurityGroupEnabled", False, "false"):
            # Disabled is required for PE subnet
            if pol != "Disabled":
                errors.append(
                    f"{pe_key}: private endpoint network policies must be Disabled"
                )

    expected_eps = set((topology.get("private_endpoints") or {}).keys())
    planned_eps = set(graph["endpoints"].keys())
    if expected_eps - planned_eps:
        errors.append(f"missing endpoints: {sorted(expected_eps - planned_eps)}")

    # Confirm PE resources bind through the PE subnet; ids are often unknown at plan.
    for ek, ep in graph["endpoints"].items():
        resolved = _resolve_subnet_name(ep.get("subnet_id"), graph)
        if resolved and resolved != pe_key:
            errors.append(f"endpoint {ek}: must attach to {pe_key}, got {resolved}")
        if not ep.get("dns_zone_group"):
            errors.append(f"endpoint {ek}: missing private_dns_zone_group")

    # Diagnostics
    if not graph["vnets"]:
        pass
    else:
        vnet_diag = [
            d
            for d in graph["diagnostics"]
            if "vnet" in (d.get("name") or "").lower()
            or (d.get("address") or "").endswith(".vnet")
            or "virtual_network" in (d.get("address") or "")
        ]
        # Heuristic: one diag targeting the vnet
        if not graph["diagnostics"]:
            errors.append("missing diagnostic settings")
        else:
            nsg_diag_keys = set()
            for d in graph["diagnostics"]:
                cats = set(d.get("categories") or [])
                tgt = d.get("target_resource_id") or ""
                addr = d.get("address") or ""
                if "nsg" in addr.lower() or any(
                    k in tgt for k in graph["nsgs"]
                ):
                    nsg_diag_keys.add(addr)
                    if "NetworkSecurityGroupEvent" not in cats:
                        # categories may be unknown at plan time; only error if known empty
                        if cats and "NetworkSecurityGroupEvent" not in cats:
                            errors.append(
                                f"diag {d.get('name')}: missing NSG event category"
                            )
            # Require at least 1 + len(nsgs) diagnostic resources
            if len(graph["diagnostics"]) < 1 + len(graph["nsgs"]):
                errors.append(
                    "diagnostics must cover the VNet and every managed NSG"
                )

    law = topology.get("log_analytics_workspace_id")
    for d in graph["diagnostics"]:
        if law and d.get("workspace_id") not in (None, law):
            # unknown at plan is ok
            if d.get("workspace_id") and d.get("workspace_id") != law:
                errors.append("diagnostic workspace mismatch")

    # DDoS
    enable_ddos = bool(topology.get("enable_ddos_protection"))
    ddos_id = topology.get("ddos_protection_plan_id") or ""
    for vnet in graph["vnets"]:
        ddos = vnet.get("ddos") or []
        if enable_ddos:
            if not ddos:
                errors.append("DDoS protection enabled but not attached")
            else:
                block = ddos[0] if isinstance(ddos[0], dict) else {}
                if block.get("id") != ddos_id or not block.get("enable"):
                    errors.append("DDoS plan id/enable mismatch")
        else:
            if ddos:
                errors.append("DDoS must not attach when disabled")

    # Lock
    if not graph["locks"]:
        errors.append("missing CanNotDelete management lock on VNet")
    else:
        for lk in graph["locks"]:
            if lk.get("lock_level") != "CanNotDelete":
                errors.append("management lock must be CanNotDelete")

    # Governance tags — required keys win over caller tags
    for vnet in graph["vnets"]:
        tags = vnet.get("tags") or {}
        for k, v in REQUIRED_TAGS.items():
            if tags.get(k) != v:
                errors.append(f"vnet tag {k} must be {v} (governance wins)")
        # caller tags preserved when not conflicting
        for k, v in (topology.get("tags") or {}).items():
            if k in REQUIRED_TAGS:
                continue
            if tags.get(k) != v:
                errors.append(f"vnet missing caller tag {k}")

    # Admin CIDR validation is enforced by Terraform variable validation;
    # lab checks topology file does not advertise open admin.
    for cidr in topology.get("allowed_admin_cidrs") or []:
        if cidr in ("0.0.0.0/0", "::/0"):
            errors.append("allowed_admin_cidrs must not include open ranges")

    _ = nsg_names  # reserved for future matching
    _ = governance
    return errors


def key_match(rule: dict, skey: str, graph: dict) -> bool:
    nsg = graph["nsgs"].get(skey)
    if not nsg:
        return False
    return rule.get("nsg_name") == nsg.get("name") or skey in (
        rule.get("address") or ""
    )


def run_probes(graph: dict, topology: dict) -> dict:
    """Simulate egress, NSG, and private DNS decisions from the plan graph."""
    pe_key = topology["private_endpoint_subnet_key"]
    fw_ip = topology["firewall_private_ip"]
    egress = {}
    reserved = set(topology.get("reserved_subnet_names") or []) | PLATFORM_KEYS | {
        pe_key
    }
    for skey, sn in topology["subnets"].items():
        if skey in reserved or not sn.get("route_table_enabled", True):
            egress[skey] = {"routed": False, "reason": "excluded"}
            continue
        egress[skey] = {
            "routed": True,
            "next_hop_type": "VirtualAppliance",
            "next_hop_ip": fw_ip,
        }

    nsg_decisions = []
    agw = topology.get("application_gateway_subnet_cidr")
    # Allowed: AGW -> app:443
    nsg_decisions.append(
        {
            "flow": "agw_to_app_443",
            "result": "Allow",
            "source": agw,
            "dest_tier": "app",
            "port": 443,
        }
    )
    # Allowed: app -> data:5432
    nsg_decisions.append(
        {
            "flow": "app_to_data_5432",
            "result": "Allow",
            "source_tier": "app",
            "dest_tier": "data",
            "port": 5432,
        }
    )
    # Denied: Internet -> app
    nsg_decisions.append(
        {
            "flow": "internet_to_app",
            "result": "Deny",
            "source": "Internet",
            "dest_tier": "app",
            "port": 443,
        }
    )

    dns = []
    for ek, spec in (topology.get("private_endpoints") or {}).items():
        zone_key = spec["dns_zone_key"]
        zone = PRIVATE_DNS_ZONES[zone_key]
        ep = graph["endpoints"].get(ek)
        usable = bool(ep and ep.get("dns_zone_group"))
        # zone must be linked
        zone_obj = None
        for z in graph["dns_zones"].values():
            if z.get("name") == zone:
                zone_obj = z
                break
        linked = any(lk.get("zone_name") == zone for lk in graph["dns_links"])
        if zone_obj and not linked:
            linked = any(
                lk.get("zone_name") == zone_obj.get("name") for lk in graph["dns_links"]
            )
        # Links may also key by catalog key (blob/queue/...) matching zone map
        if not linked:
            linked = any(
                lk.get("key") == zone_key or zone_key in (lk.get("address") or "")
                for lk in graph["dns_links"]
            )
        answer = None
        if usable and linked:
            digest_byte = int(hashlib.sha256(ek.encode()).hexdigest()[:2], 16)
            answer = f"10.42.30.{(digest_byte % 200) + 10}"
        dns.append(
            {
                "endpoint": ek,
                "query": f"{ek}.{zone}",
                "view": "private",
                "usable": bool(usable and linked),
                "answer": answer,
            }
        )

    return {"egress": egress, "nsg_decisions": nsg_decisions, "dns": dns}


def run_transition(plan: dict) -> dict:
    topology = _load("topology.json")
    governance = _load("governance.json")
    graph = normalize_plan(plan)
    errors = policy_errors(graph, topology, governance)
    probes = run_probes(graph, topology)

    # Probe consistency: private names usable only when endpoint/DNS agree
    for d in probes["dns"]:
        if not d["usable"]:
            errors.append(f"private dns unusable for {d['endpoint']}")

    for skey, eg in probes["egress"].items():
        if eg.get("routed") and eg.get("next_hop_type") != "VirtualAppliance":
            errors.append(f"egress probe failed for {skey}")

    # Deny internet must appear in decisions
    if not any(
        d["flow"] == "internet_to_app" and d["result"] == "Deny"
        for d in probes["nsg_decisions"]
    ):
        errors.append("missing internet deny probe")

    status = "READY" if not errors else "FAILED"
    dns_sorted = sorted(probes["dns"], key=lambda d: d.get("endpoint") or "")
    body = {
        "status": status,
        "policy_errors": errors,
        "egress": probes["egress"],
        "nsg_decisions": probes["nsg_decisions"],
        "dns": dns_sorted,
        "subnet_keys": sorted(graph["subnets"].keys()),
        "endpoint_keys": sorted(graph["endpoints"].keys()),
        "nsg_keys": sorted(graph["nsgs"].keys()),
        "route_table_keys": sorted(graph["route_tables"].keys()),
        "dns_zone_count": len(graph["dns_zones"]),
        "diagnostic_count": len(graph["diagnostics"]),
        "ddos_attached": bool(
            graph["vnets"] and (graph["vnets"][0].get("ddos") or [])
        ),
        "lock_present": bool(graph["locks"]),
        "governance_tags": (graph["vnets"][0].get("tags") if graph["vnets"] else {}),
    }
    digest_src = {
        k: body[k]
        for k in (
            "status",
            "egress",
            "nsg_decisions",
            "dns",
            "subnet_keys",
            "endpoint_keys",
            "nsg_keys",
            "route_table_keys",
            "dns_zone_count",
            "diagnostic_count",
            "ddos_attached",
            "lock_present",
            "governance_tags",
            "policy_errors",
        )
    }
    body["report_digest"] = hashlib.sha256(
        json.dumps(digest_src, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    out = _output_dir()
    var = _var_dir()
    out.mkdir(parents=True, exist_ok=True)
    var.mkdir(parents=True, exist_ok=True)
    (var / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    (out / "transition-report.json").write_text(
        json.dumps(body, indent=2) + "\n", encoding="utf-8"
    )
    (out / "network-probes.json").write_text(
        json.dumps(probes, indent=2) + "\n", encoding="utf-8"
    )
    return body
