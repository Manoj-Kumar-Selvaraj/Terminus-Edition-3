from __future__ import annotations

import os
import pathlib
import subprocess
import textwrap

ROOT = pathlib.Path("/app/routecp")
PKG = ROOT / "internal" / "controlplane"


def run(cmd: list[str], *, cwd: pathlib.Path = ROOT, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=cwd, env=merged, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)


def write_quality_go_test(body: str) -> pathlib.Path:
    path = PKG / "quality_remediation_test.go"
    path.write_text(textwrap.dedent(body))
    return path


def test_management_reachability_is_preserved() -> None:
    test_file = write_quality_go_test(r'''
        package controlplane

        import (
            "path/filepath"
            "testing"
        )

        func TestQualityManagementReachability(t *testing.T) {
            cp, err := Open(Config{StateDir:filepath.Join(t.TempDir(),"state"),ProtectedCIDRs:[]string{"198.51.100.0/24"},MaxWave:5})
            if err != nil { t.Fatal(err) }
            if err := cp.UpsertNode(Node{ID:"n1",Hostname:"n1.local",ManagementIP:"198.51.100.10",Online:true}); err != nil { t.Fatal(err) }
            route := Route{ID:"mgmt",NodeID:"n1",Destination:"198.51.100.0/24",Table:100,Metric:10,Protocol:"static",Scope:"global",Type:"unicast",Owner:"routecp",NextHops:[]NextHop{{Gateway:"192.0.2.1",Weight:1}}}
            plan, err := cp.Preview(ChangeRequest{BaseRevision:0,Actor:"quality",RouteMutations:[]RouteMutation{{Operation:"add",Route:route}}})
            if err != nil { t.Fatal(err) }
            if _, err := cp.Apply(ApplyRequest{PlanID:plan.ID,BaseRevision:0,IdempotencyKey:"quality-mgmt",Nodes:[]string{"n1"},Actor:"quality"}); err != nil { t.Fatal(err) }
            decision, err := cp.Trace(TraceRequest{NodeID:"n1",Source:"198.51.100.10",Destination:"198.51.100.10"})
            if err != nil { t.Fatal(err) }
            if !decision.Reachable || decision.Route == nil || decision.Route.ID != "mgmt" { t.Fatalf("management path not preserved: %#v", decision) }
        }
    ''')
    try:
        result = run(["go", "test", "./internal/controlplane", "-run", "TestQualityManagementReachability", "-count=1"])
        assert result.returncode == 0, result.stdout
    finally:
        test_file.unlink(missing_ok=True)


def test_isolated_model_does_not_touch_host_routes() -> None:
    snapshots = [pathlib.Path("/proc/net/route"), pathlib.Path("/proc/net/ipv6_route")]
    before = {p: p.read_text() if p.exists() else "" for p in snapshots}
    test_file = write_quality_go_test(r'''
        package controlplane

        import (
            "path/filepath"
            "testing"
        )

        func TestQualityIsolatedMutation(t *testing.T) {
            cp, err := Open(Config{StateDir:filepath.Join(t.TempDir(),"state"),MaxWave:5})
            if err != nil { t.Fatal(err) }
            if err := cp.UpsertNode(Node{ID:"n1",Hostname:"n1.local",ManagementIP:"203.0.113.10",Online:true}); err != nil { t.Fatal(err) }
            route := Route{ID:"isolated",NodeID:"n1",Destination:"203.0.113.0/24",Table:100,Metric:10,Protocol:"static",Scope:"global",Type:"unicast",Owner:"routecp",NextHops:[]NextHop{{Gateway:"192.0.2.1",Weight:1}}}
            plan, err := cp.Preview(ChangeRequest{BaseRevision:0,Actor:"quality",RouteMutations:[]RouteMutation{{Operation:"add",Route:route}}})
            if err != nil { t.Fatal(err) }
            if _, err := cp.Apply(ApplyRequest{PlanID:plan.ID,BaseRevision:0,IdempotencyKey:"quality-isolation",Nodes:[]string{"n1"},Actor:"quality"}); err != nil { t.Fatal(err) }
        }
    ''')
    try:
        result = run(["go", "test", "./internal/controlplane", "-run", "TestQualityIsolatedMutation", "-count=1"])
        assert result.returncode == 0, result.stdout
    finally:
        test_file.unlink(missing_ok=True)
    after = {p: p.read_text() if p.exists() else "" for p in snapshots}
    assert after == before, "routecp isolated-model mutation changed the container host routing tables"


def test_ansible_projection_converges_on_second_run(tmp_path: pathlib.Path) -> None:
    config_dir = tmp_path / "etc-routecp"
    state_dir = tmp_path / "state"
    config_dir.mkdir()
    state_dir.mkdir()
    playbook = tmp_path / "convergence.yml"
    playbook.write_text(textwrap.dedent(f'''
        ---
        - hosts: localhost
          connection: local
          gather_facts: false
          vars:
            routecp_user: root
            routecp_group: root
            routecp_projection_owner: root
            routecp_projection_group: root
            routecp_projection_notify: convergence-marker
            routecp_config_dir: {config_dir}
            routecp_state_dir: {state_dir}
            routecp_listen: 127.0.0.1:18080
            routecp_max_wave: 5
            routecp_protected_cidrs: [10.0.0.0/8]
            routecp_labels: {{role: edge}}
            routecp_routes: []
            routecp_rules: []
            routecp_environment: test
          handlers:
            - name: convergence-marker
              ansible.builtin.debug:
                msg: projected configuration changed
          tasks:
            - ansible.builtin.include_role:
                name: routecp
                tasks_from: project
    '''))
    env = {"ANSIBLE_ROLES_PATH": str(ROOT / "ansible" / "roles"), "ANSIBLE_FORCE_COLOR": "0"}
    first = run(["ansible-playbook", str(playbook)], cwd=tmp_path, env=env)
    assert first.returncode == 0, first.stdout
    second = run(["ansible-playbook", str(playbook)], cwd=tmp_path, env=env)
    assert second.returncode == 0, second.stdout
    assert "changed=0" in second.stdout, second.stdout


def test_audit_sequence_is_publicly_monotonic() -> None:
    test_file = write_quality_go_test(r'''
        package controlplane

        import (
            "path/filepath"
            "testing"
        )

        func TestQualityAuditSequence(t *testing.T) {
            cp, err := Open(Config{StateDir:filepath.Join(t.TempDir(),"state"),MaxWave:5})
            if err != nil { t.Fatal(err) }
            for _, id := range []string{"n1","n2","n3"} {
                if err := cp.UpsertNode(Node{ID:id,Hostname:id+".local",ManagementIP:"198.51.100.10",Online:true}); err != nil { t.Fatal(err) }
            }
            events := cp.Audit(100)
            if len(events) < 3 { t.Fatalf("expected audit events, got %d", len(events)) }
            for i := 1; i < len(events); i++ {
                if events[i].Sequence <= events[i-1].Sequence { t.Fatalf("sequence is not strictly increasing: %d then %d",events[i-1].Sequence,events[i].Sequence) }
            }
        }
    ''')
    try:
        result = run(["go", "test", "./internal/controlplane", "-run", "TestQualityAuditSequence", "-count=1"])
        assert result.returncode == 0, result.stdout
    finally:
        test_file.unlink(missing_ok=True)
