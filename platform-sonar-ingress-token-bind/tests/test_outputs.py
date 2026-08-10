"""Behavioral checks for the platform Sonar token bind."""

from __future__ import annotations

import copy
import json
import sqlite3
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from runtime import paths
from runtime.httpd import serve
from runtime.reconcile import evaluate, load_stack, reload_platform
from runtime.state import identities_from_db, load_json, load_tfc

INGRESS = "http://127.0.0.1:8443"


def _live() -> dict:
    return load_json(paths.live_path())


@pytest.fixture(scope="session", autouse=True)
def _platform_httpd() -> None:
    """Start the ingress listener when Harbor or a local pytest run has not already bound it."""
    if not _live():
        reload_platform()
    try:
        code, _ = _get("jenkins.platform.test", "/login")
        if code in {200, 404, 503}:
            return
    except (urllib.error.URLError, TimeoutError, OSError):
        pass
    server = serve()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    for _ in range(30):
        try:
            _get("jenkins.platform.test", "/login")
            break
        except (urllib.error.URLError, TimeoutError, OSError):
            continue


def _get(host: str, path: str, token: str | None = None) -> tuple[int, str]:
    req = urllib.request.Request(
        INGRESS + path,
        headers={"Host": host, **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def _stack_eval(**tfc_overlay: object) -> dict:
    stack = copy.deepcopy(load_stack())
    stack["tfc"].update(tfc_overlay)
    con = sqlite3.connect(str(paths.db_path()))
    con.row_factory = sqlite3.Row
    try:
        identities = identities_from_db(con)
    finally:
        con.close()
    return evaluate(stack, identities)


def _mutate_secret_key(key: str) -> dict:
    stack = copy.deepcopy(load_stack())
    for doc in stack["k8s"]:
        if doc.get("kind") == "Secret" and (doc.get("metadata") or {}).get("name") == "jenkins-sonarqube-token":
            doc["data"] = {key: ""}
    con = sqlite3.connect(str(paths.db_path()))
    con.row_factory = sqlite3.Row
    try:
        identities = identities_from_db(con)
    finally:
        con.close()
    return evaluate(stack, identities)


def _break_jdbc() -> dict:
    stack = copy.deepcopy(load_stack())
    stack["tf"][("helm_release", "sonarqube")]["postgresql_enabled"] = True
    con = sqlite3.connect(str(paths.db_path()))
    con.row_factory = sqlite3.Row
    try:
        identities = identities_from_db(con)
    finally:
        con.close()
    return evaluate(stack, identities)


def test_f2p_token_validates_against_sonar() -> None:
    """Bound Jenkins token must validate against Sonar through the ingress host."""
    live = _live()
    token = live.get("bound_token")
    assert token
    code, body = _get("sonar.platform.test", "/api/authentication/validate", token=str(token))
    assert code == 200
    assert json.loads(body).get("valid") is True


def test_f2p_credential_id_is_sonarqube_token() -> None:
    """JCasC credential and installation must use id sonarqube-token."""
    live = _live()
    assert live.get("credential_id") == "sonarqube-token"
    assert live.get("install_cred") == "sonarqube-token"


def test_f2p_empty_secret_key_does_not_bind() -> None:
    """A missing sonarqube-token secret key must refuse bind even if TFC has a token."""
    live = _mutate_secret_key("token")
    assert not live.get("bound_token")
    assert live.get("bind_reason") == "secret_key"


def test_f2p_installation_name_sonarqube() -> None:
    """withSonarQubeEnv expects the named installation SonarQube."""
    assert _live().get("install_name") == "SonarQube"


def test_f2p_server_url_is_ingress_https() -> None:
    """Sonar installation URL must be the public ingress https host."""
    assert _live().get("server_url") == "https://sonar.platform.test"


def test_f2p_server_url_is_not_rds_host() -> None:
    """Jenkins must not aim scans at the RDS hostname."""
    url = str(_live().get("server_url") or "")
    assert "cluster.platform.test" not in url
    assert not url.startswith("jdbc:")


def test_f2p_secret_key_sonarqube_token() -> None:
    """jenkins-sonarqube-token must expose data key sonarqube-token."""
    live = _live()
    assert "sonarqube-token" in live.get("token_secret_keys", [])
    assert live.get("token_key") == "sonarqube-token"


def test_f2p_artifactory_secret_keys() -> None:
    """Artifactory secret must use artifactory-username and artifactory-password keys."""
    keys = set(_live().get("artifactory_secret_keys") or [])
    assert keys >= {"artifactory-username", "artifactory-password"}


def test_f2p_db_secret_key_password() -> None:
    """Sonar DB secret key must be password."""
    assert "password" in (_live().get("db_secret_keys") or [])


def test_f2p_single_ingress_group() -> None:
    """All public ingresses share group.name platform-ingress."""
    live = _live()
    assert live.get("groups") == ["platform-ingress"]
    for item in (live.get("hosts") or {}).values():
        assert item.get("group") == "platform-ingress"


def test_f2p_three_hosts_one_listener() -> None:
    """One TLS listener must front jenkins, sonar, and artifactory."""
    live = _live()
    assert live.get("listener_ok") is True
    assert set((live.get("hosts") or {})) == {"jenkins", "sonar", "artifactory"}


def test_f2p_host_header_jenkins_login() -> None:
    """Host jenkins.platform.test /login must answer 200 on the shared listener."""
    code, body = _get("jenkins.platform.test", "/login")
    assert code == 200
    assert "jenkins-login" in body


def test_f2p_host_header_sonar_status() -> None:
    """Host sonar.platform.test /api/system/status must report UP."""
    code, body = _get("sonar.platform.test", "/api/system/status")
    assert code == 200
    assert json.loads(body).get("status") == "UP"


def test_f2p_host_header_artifactory_ping() -> None:
    """Host artifactory.platform.test ping path must answer OK."""
    code, body = _get("artifactory.platform.test", "/artifactory/api/system/ping")
    assert code == 200
    assert "OK" in body


def test_f2p_dns_names_published() -> None:
    """ExternalDNS zone must contain the three public platform.test names."""
    zone = load_json(paths.zone_path())
    records = zone.get("records") or {}
    for host in ("jenkins.platform.test", "sonar.platform.test", "artifactory.platform.test"):
        assert host in records


def test_f2p_txt_owner_cluster_id() -> None:
    """TXT owner records must use txtOwnerId platform-mvp-dev."""
    live = _live()
    assert live.get("txt_owner") == "platform-mvp-dev"
    zone = load_json(paths.zone_path())
    txt = zone.get("txt") or {}
    assert txt.get("_owner.sonar.platform.test") == "platform-mvp-dev"


def test_f2p_jdbc_address_not_endpoint_port() -> None:
    """JDBC URL must not double the :5432 from aws endpoint."""
    url = str(_live().get("jdbc_url") or "")
    assert url.count(":5432") == 1
    assert ":5432:5432" not in url


def test_f2p_jdbc_uses_ternary_identity() -> None:
    """RDS ternary must select restored address when enable_dr_restore is set."""
    default = _live()
    assert default.get("sonar_up") is True
    assert default.get("jdbc_address") == "platform-mvp-sonarqube.cluster.platform.test"
    live = _stack_eval(enable_dr_restore=True)
    assert live.get("jdbc_address") == "platform-mvp-sonarqube-restored.cluster.platform.test"


def test_f2p_embedded_postgres_disabled() -> None:
    """Sonar must not run embedded postgres when RDS is contracted."""
    assert _live().get("embedded_postgres") is False


def test_f2p_jenkins_home_uid_1000() -> None:
    """Jenkins home must record access-point uid 1000."""
    live = _live()
    assert live.get("posix_uid") == 1000
    uid_file = paths.jenkins_home() / ".uid"
    assert uid_file.is_file()
    assert uid_file.read_text(encoding="utf-8").strip() == "1000"


def test_f2p_artifactory_path_isolated() -> None:
    """Artifactory data path must not equal Jenkins home."""
    live = _live()
    assert live.get("artifactory_mount")
    assert live.get("jenkins_mount")
    assert live.get("artifactory_mount") != live.get("jenkins_mount")
    assert not (paths.jenkins_home() / "artifactory-blob").exists()


def test_f2p_reclaim_retain() -> None:
    """StorageClass reclaim policy must be Retain so home survives rolls."""
    assert _live().get("reclaim") == "Retain"


def test_f2p_num_executors_zero() -> None:
    """Controller must not run builds on the EFS home writer."""
    assert _live().get("num_executors") == 0


def test_f2p_controller_on_platform_control() -> None:
    """Jenkins controller must land on platform-control with the control taint."""
    assert _live().get("on_control") is True


def test_f2p_ansible_connection_ssm() -> None:
    """AWS inventory must use aws_ssm, not SSH."""
    live = _live()
    assert live.get("ssm_ok") is True
    assert live.get("ssh_open") is False


def test_f2p_runner_id_set() -> None:
    """ANSIBLE_RUNNER_ID must match the TFC/runner instance id."""
    tfc = load_tfc()
    assert _live().get("runner_id") == tfc.get("ansible_runner_id")


def test_f2p_ssh_not_admitted() -> None:
    """Runner security group must not admit SSH and inventory must not reference on-prem keys."""
    aws = (paths.stack_dir() / "ansible/inventories/aws/hosts.yml").read_text(encoding="utf-8")
    assert "ansible_connection: ssh" not in aws
    assert "~/.ssh" not in aws
    assert "onprem" not in aws


def test_f2p_second_reload_keeps_token() -> None:
    """A second reload must keep the TFC analysis token rather than minting another."""
    first = str(_live().get("bound_token") or "")
    again = reload_platform()
    assert again.get("bound_token") == first
    assert again.get("bound_token") == load_tfc().get("sonarqube_token")


def test_f2p_home_survives_reload() -> None:
    """Files already in Jenkins home must survive reload."""
    assert _live().get("posix_uid") == 1000
    marker = paths.jenkins_home() / "job-seed.txt"
    marker.write_text("keep-me\n", encoding="utf-8")
    reload_platform()
    assert marker.is_file()
    assert marker.read_text(encoding="utf-8") == "keep-me\n"


def test_f2p_bind_requires_sonar_up() -> None:
    """Bind must be refused while Sonar JDBC identity is down."""
    assert _live().get("sonar_up") is True
    live = _break_jdbc()
    assert live.get("sonar_up") is False
    assert not live.get("bound_token")
    assert live.get("bind_reason") == "sonar_down"


def test_p2p_analysis_journal_present() -> None:
    """Inherited Sonar analysis journal must remain queryable after bind."""
    con = sqlite3.connect(str(paths.db_path()))
    try:
        count = con.execute("SELECT COUNT(*) FROM sonar_analysis").fetchone()[0]
    finally:
        con.close()
    assert count == 12000


def test_p2p_login_stays_up() -> None:
    """Jenkins /login remains reachable as a non-regression after the incident."""
    code, _ = _get("jenkins.platform.test", "/login")
    assert code == 200


def test_p2p_artifactory_creds_exist() -> None:
    """Artifactory credentials secret remains present for publish steps."""
    assert len(_live().get("artifactory_secret_keys") or []) >= 2


def test_p2p_ssm_document_name() -> None:
    """Successful SSM dispatch records AWS-RunShellScript."""
    log = Path(paths.ssm_log())
    assert log.is_file()
    row = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert row.get("document") == "AWS-RunShellScript"
    assert row.get("status") == "Success"


def test_p2p_domain_is_platform_test() -> None:
    """Published names stay under platform.test, not a personal zone."""
    zone = load_json(paths.zone_path())
    for host in zone.get("records") or {}:
        assert str(host).endswith(".platform.test")
