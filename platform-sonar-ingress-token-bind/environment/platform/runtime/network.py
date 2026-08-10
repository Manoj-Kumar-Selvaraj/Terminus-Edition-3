from __future__ import annotations

from typing import Any


def _attr(tf: dict[tuple[str, str], dict[str, Any]], rtype: str, name: str) -> dict[str, Any]:
    return tf.get((rtype, name), {})


def public_subnets_tagged_for_alb(tf: dict[tuple[str, str], dict[str, Any]]) -> bool:
    for name in ("public_a", "public_b"):
        subnet = _attr(tf, "aws_subnet", name)
        if int(subnet.get("kubernetes_role_elb") or 0) != 1:
            return False
        if str(subnet.get("cluster_tag") or "") != "shared":
            return False
    return True


def private_subnets_tagged_for_internal(tf: dict[tuple[str, str], dict[str, Any]]) -> bool:
    for name in ("private_a", "private_b"):
        subnet = _attr(tf, "aws_subnet", name)
        if int(subnet.get("kubernetes_role_internal_elb") or 0) != 1:
            return False
    return True


def alb_ready(tf: dict[tuple[str, str], dict[str, Any]]) -> bool:
    vpc = _attr(tf, "aws_vpc", "main")
    if str(vpc.get("cluster_tag") or "") != "shared":
        return False
    if not public_subnets_tagged_for_alb(tf):
        return False
    if not private_subnets_tagged_for_internal(tf):
        return False
    return True


def efs_csi_ready(tf: dict[tuple[str, str], dict[str, Any]]) -> bool:
    release = _attr(tf, "helm_release", "efs_csi")
    return str(release.get("service_account") or "") == "efs-csi-controller-sa"
