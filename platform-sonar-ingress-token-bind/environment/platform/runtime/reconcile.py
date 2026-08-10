from __future__ import annotations

import os
import stat
from typing import Any

from . import paths
from . import dns as dnsmod
from . import network as netmod
from . import ssmexec
from .hclparse import parse_terraform
from .kubeload import load_kubernetes
from .state import dump_json, identities_from_db, load_json, load_tfc, rds_address, connect


EXPECTED_HEALTH = {
    "jenkins.platform.test": "/login",
    "sonar.platform.test": "/api/system/status",
    "artifactory.platform.test": "/artifactory/api/system/ping",
}
DOMAIN = "platform.test"
CLUSTER = "platform-mvp-dev"
GROUP = "platform-ingress"


def _index_tf(resources: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(item["type"], item["name"]): item["attrs"] for item in resources}


def _meta(doc: dict[str, Any]) -> dict[str, Any]:
    return doc.get("metadata") or {}


def _ann(doc: dict[str, Any]) -> dict[str, str]:
    annotations = _meta(doc).get("annotations") or {}
    return {str(k): str(v) for k, v in annotations.items()}


def _data(doc: dict[str, Any]) -> dict[str, str]:
    data = doc.get("data") or {}
    return {str(k): str(v) for k, v in data.items()}


def load_stack() -> dict[str, Any]:
    tf_items: list[dict[str, Any]] = []
    kube_items: list[dict[str, Any]] = []
    for path in sorted((paths.stack_dir() / "terraform").glob("*.tf")):
        tf_items.extend(parse_terraform(path))
    for path in sorted((paths.stack_dir() / "k8s").glob("*.yaml")):
        kube_items.extend(load_kubernetes(path))
    ansible_aws = (paths.stack_dir() / "ansible" / "inventories" / "aws" / "hosts.yml").read_text(
        encoding="utf-8"
    )
    ansible_onprem = (
        paths.stack_dir() / "ansible" / "inventories" / "onprem" / "hosts.yml"
    ).read_text(encoding="utf-8")
    jcasc = (paths.stack_dir() / "jenkins" / "casc.yaml").read_text(encoding="utf-8")
    return {
        "terraform": tf_items,
        "tf": _index_tf(tf_items),
        "k8s": kube_items,
        "ansible_aws": ansible_aws,
        "ansible_onprem": ansible_onprem,
        "jcasc": jcasc,
        "tfc": load_tfc(),
    }


def _secret(k8s: list[dict[str, Any]], name: str) -> dict[str, str]:
    for doc in k8s:
        if doc.get("kind") == "Secret" and _meta(doc).get("name") == name:
            return _data(doc)
    return {}


def _ingress(k8s: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for doc in k8s:
        if doc.get("kind") == "Ingress" and _meta(doc).get("name") == name:
            return doc
    return None


def _sc(k8s: list[dict[str, Any]]) -> dict[str, Any] | None:
    for doc in k8s:
        if doc.get("kind") == "StorageClass":
            return doc
    return None


def _deploy(k8s: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for doc in k8s:
        if doc.get("kind") == "Deployment" and _meta(doc).get("name") == name:
            return doc
    return None


def _pvc(k8s: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for doc in k8s:
        if doc.get("kind") == "PersistentVolumeClaim" and _meta(doc).get("name") == name:
            return doc
    return None


def _host_from_ingress(doc: dict[str, Any]) -> str:
    rules = (doc.get("spec") or {}).get("rules") or []
    if rules:
        return str(rules[0].get("host") or "")
    return ""


def _jdbc_ok(url: str, address: str, embedded: bool, password_key: str, password: str) -> bool:
    if embedded:
        return False
    if password_key != "password" or not password:
        return False
    expected = f"jdbc:postgresql://{address}:5432/sonarqube"
    return url == expected


def _parse_jcasc(text: str) -> dict[str, Any]:
    import yaml

    data = yaml.safe_load(text) or {}
    return data if isinstance(data, dict) else {}


def evaluate(stack: dict[str, Any], identities: dict[str, dict[str, Any]]) -> dict[str, Any]:
    tfc = stack["tfc"]
    tf = stack["tf"]
    k8s = stack["k8s"]
    jcasc = _parse_jcasc(stack["jcasc"])
    address = rds_address(tfc, identities)

    sonar_values = tf.get(("helm_release", "sonarqube"), {})
    jenkins_helm = tf.get(("helm_release", "jenkins"), {})
    ext_dns = tf.get(("helm_release", "external_dns"), {})
    runner = tf.get(("aws_instance", "ansible_runner"), {})
    runner_sg = tf.get(("aws_security_group", "ansible_runner"), {})
    efs_ap = tf.get(("aws_efs_access_point", "jenkins"), {})

    jdbc_url = str(sonar_values.get("jdbc_url") or "")
    embedded = bool(sonar_values.get("postgresql_enabled"))
    db_secret = _secret(k8s, "sonarqube-db-credentials")
    jdbc_key = str(sonar_values.get("jdbc_password_key") or "")
    db_password = db_secret.get(jdbc_key, db_secret.get("password", ""))
    sonar_up = _jdbc_ok(jdbc_url, address, embedded, jdbc_key or "password", db_password)

    token_secret = _secret(k8s, "jenkins-sonarqube-token")
    artifactory_secret = _secret(k8s, "jenkins-artifactory-credentials")
    admin_secret = _secret(k8s, "jenkins-admin-credentials")
    token_key = str(jenkins_helm.get("sonarqube_secret_key") or "sonarqube-token")
    mounted_token = token_secret.get(token_key, "")
    if not mounted_token:
        mounted_token = token_secret.get("sonarqube-token", "")

    creds = (((jcasc.get("credentials") or {}).get("system") or {}).get("domainCredentials") or [{}])
    string_creds = []
    if creds:
        string_creds = (creds[0].get("credentials") or []) if isinstance(creds[0], dict) else []
    sonar_cred_id = ""
    sonar_secret_ref = ""
    for item in string_creds:
        if not isinstance(item, dict):
            continue
        string = item.get("string") or item
        if not isinstance(string, dict):
            continue
        if "id" in string:
            sonar_cred_id = str(string.get("id") or "")
            sonar_secret_ref = str(string.get("secret") or "")

    installations = (
        ((jcasc.get("unclassified") or {}).get("sonarGlobalConfiguration") or {}).get(
            "installations"
        )
        or []
    )
    install_name = ""
    server_url = ""
    install_cred = ""
    if installations and isinstance(installations[0], dict):
        install_name = str(installations[0].get("name") or "")
        server_url = str(installations[0].get("serverUrl") or "")
        install_cred = str(installations[0].get("credentialsId") or "")

    env_vars = {}
    for block in (jcasc.get("jenkins") or {}).get("globalNodeProperties") or []:
        if not isinstance(block, dict) or "envVars" not in block:
            continue
        env_block = block["envVars"]
        if isinstance(env_block, dict) and "env" in env_block:
            env_block = env_block["env"]
        if isinstance(env_block, dict):
            env_vars.update({str(k): str(v) for k, v in env_block.items()})
        elif isinstance(env_block, list):
            for env in env_block:
                if isinstance(env, dict) and "key" in env:
                    env_vars[str(env.get("key"))] = str(env.get("value") or "")
                elif isinstance(env, dict):
                    env_vars.update({str(k): str(v) for k, v in env.items()})

    num_executors = int((jcasc.get("jenkins") or {}).get("numExecutors", jenkins_helm.get("num_executors", 2)))
    jenkins_deploy = _deploy(k8s, "jenkins") or {}
    selector = ((jenkins_deploy.get("spec") or {}).get("template") or {}).get("spec") or {}
    node_selector = selector.get("nodeSelector") or {}
    tolerations = selector.get("tolerations") or []
    on_control = node_selector.get("role") == "platform-control"
    has_taint = any(
        isinstance(tol, dict)
        and tol.get("key") == "platform-control"
        and str(tol.get("value")) == "true"
        for tol in tolerations
    )

    storage = _sc(k8s) or {}
    reclaim = str(storage.get("reclaimPolicy") or "")
    art_pvc = _pvc(k8s, "artifactory-data") or {}
    jen_pvc = _pvc(k8s, "jenkins-home") or {}
    art_path = str(((art_pvc.get("metadata") or {}).get("annotations") or {}).get("platform/mount-path") or "")
    jen_path = str(((jen_pvc.get("metadata") or {}).get("annotations") or {}).get("platform/mount-path") or "")
    uid = int(efs_ap.get("posix_uid", 0) or 0)

    hosts = {}
    groups = set()
    for name in ("jenkins", "sonar", "artifactory"):
        ing = _ingress(k8s, name)
        if not ing:
            continue
        host = _host_from_ingress(ing)
        annotations = _ann(ing)
        group = annotations.get("alb.ingress.kubernetes.io/group.name", "")
        health = annotations.get("alb.ingress.kubernetes.io/healthcheck-path", "")
        dns_host = annotations.get("external-dns.alpha.kubernetes.io/hostname", "")
        groups.add(group)
        hosts[name] = {
            "host": host,
            "group": group,
            "healthcheck": health,
            "dns_annotation": dns_host,
            "healthy": health == EXPECTED_HEALTH.get(host, "") and group == GROUP,
        }

    domain_filters = ext_dns.get("domain_filters") or []
    if isinstance(domain_filters, str):
        domain_filters = [domain_filters]
    txt_owner = str(ext_dns.get("txt_owner_id") or "")
    policy = str(ext_dns.get("policy") or "")
    dns_ok = dnsmod.owner_ok(txt_owner, policy, domain_filters)
    zone_next = dnsmod.publish_zone(hosts, txt_owner, dns_ok)
    published = {
        host: {"owner": txt_owner, "type": "A"} for host in zone_next.get("records", {})
    }

    token_value = str(tfc.get("sonarqube_token") or "")
    ref = sonar_secret_ref.strip().replace("$${", "${")
    interpolates = ref in {"${sonarqube-token}", "{sonarqube-token}"}
    bound_token = ""
    bind_reason = ""
    if not sonar_up:
        bind_reason = "sonar_down"
    elif token_key != "sonarqube-token" or "sonarqube-token" not in token_secret:
        bind_reason = "secret_key"
    elif not interpolates:
        bind_reason = "interpolation"
    elif sonar_cred_id != "sonarqube-token" or install_cred != "sonarqube-token":
        bind_reason = "credential_id"
    elif install_name != "SonarQube":
        bind_reason = "installation_name"
    elif server_url != "https://sonar.platform.test":
        bind_reason = "server_url"
    elif not token_value:
        bind_reason = "empty_token"
    else:
        bound_token = token_value

    expected_runner = str(tfc.get("ansible_runner_id") or runner.get("id") or "")
    runner_env = env_vars.get("ANSIBLE_RUNNER_ID", "")
    ssh_open = ssmexec.runner_sg_opens_ssh(runner_sg) or ssmexec.inventory_uses_ssh(stack["ansible_aws"])
    ssm_ok = ssmexec.dispatch_ok(stack["ansible_aws"], runner_sg, runner_env, expected_runner)
    alb_ok = netmod.alb_ready(tf) and netmod.efs_csi_ready(tf)
    listener_ok = (
        groups == {GROUP}
        and len(hosts) == 3
        and all(h["healthy"] for h in hosts.values())
        and alb_ok
    )

    return {
        "sonar_up": sonar_up,
        "jdbc_url": jdbc_url,
        "jdbc_address": address,
        "embedded_postgres": embedded,
        "db_secret_keys": sorted(db_secret),
        "token_secret_keys": sorted(token_secret),
        "artifactory_secret_keys": sorted(artifactory_secret),
        "admin_secret_keys": sorted(admin_secret),
        "token_key": token_key,
        "bound_token": bound_token,
        "bind_reason": bind_reason,
        "credential_id": sonar_cred_id,
        "install_name": install_name,
        "server_url": server_url,
        "install_cred": install_cred,
        "hosts": hosts,
        "groups": sorted(groups),
        "listener_ok": listener_ok,
        "published": published,
        "zone_next": zone_next,
        "txt_owner": txt_owner,
        "dns_ok": dns_ok,
        "dns_policy": policy,
        "num_executors": num_executors,
        "on_control": on_control and has_taint,
        "reclaim": reclaim,
        "jenkins_mount": jen_path,
        "artifactory_mount": art_path,
        "posix_uid": uid,
        "ssm_ok": ssm_ok,
        "ssh_open": ssh_open,
        "runner_id": env_vars.get("ANSIBLE_RUNNER_ID", ""),
        "env": env_vars,
        "analysis_token_source": token_value,
    }


def materialize(live: dict[str, Any]) -> None:
    paths.var_dir().mkdir(parents=True, exist_ok=True)
    home = paths.jenkins_home()
    art = paths.artifactory_data()
    home.mkdir(parents=True, exist_ok=True)
    art.mkdir(parents=True, exist_ok=True)

    marker = home / ".keep-jobs"
    if not marker.exists():
        marker.write_text("seed-jobs\n", encoding="utf-8")

    uid = int(live.get("posix_uid") or 0)
    isolated = live.get("artifactory_mount") != live.get("jenkins_mount")
    if isolated and uid == 1000 and live.get("reclaim") == "Retain":
        try:
            os.chmod(home, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        except OSError:
            pass
        chown = getattr(os, "chown", None)
        if callable(chown):
            try:
                chown(home, 1000, 1000)
            except OSError:
                pass
        (home / ".uid").write_text("1000\n", encoding="utf-8")
    else:
        (home / ".uid").write_text(str(uid) + "\n", encoding="utf-8")
        if not isolated:
            leak = home / "artifactory-blob"
            leak.write_text("shared-writer\n", encoding="utf-8")

    previous_zone = load_json(paths.zone_path())
    zone = dnsmod.sync_deletes_unowned(
        previous_zone,
        live.get("zone_next") or {"records": {}, "txt": {}},
        str(live.get("dns_policy") or ""),
    )
    dump_json(paths.zone_path(), zone)

    ssmexec.write_command_log(paths.ssm_log(), str(live.get("runner_id") or ""), bool(live.get("ssm_ok")))

    dump_json(paths.live_path(), live)


def reload_platform() -> dict[str, Any]:
    stack = load_stack()
    con = connect()
    try:
        identities = identities_from_db(con)
    finally:
        con.close()
    previous = load_json(paths.live_path())
    live = evaluate(stack, identities)
    if previous.get("bound_token") and live.get("bound_token"):
        if live["analysis_token_source"] == previous.get("analysis_token_source"):
            live["bound_token"] = previous["bound_token"]
        elif live["analysis_token_source"] != previous.get("analysis_token_source"):
            # rotation from TFC is allowed; minting a different value without TFC change is not
            if live["analysis_token_source"] != previous.get("analysis_token_source"):
                live["token_rotated"] = True
    if not live.get("bound_token") and previous.get("bound_token") and live.get("bind_reason") == "sonar_down":
        live["previous_token_cleared"] = True
    materialize(live)
    dump_json(paths.desired_path(), {"evaluated": True})
    return live
