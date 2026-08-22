from __future__ import annotations

import pathlib
import subprocess
import textwrap

ROOT = pathlib.Path("/app/routecp")
PKG = ROOT / "internal" / "controlplane"


def run(cmd: list[str], *, cwd: pathlib.Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)


def test_go_runtime_contracts() -> None:
    assert (ROOT / "go.mod").exists(), "route-control-plane Go module is missing"
    test_file = PKG / "oracle_contract_test.go"
    test_file.write_text(textwrap.dedent(r'''
        package controlplane

        import (
            "errors"
            "path/filepath"
            "testing"
            "time"
        )

        func verifierCP(t *testing.T) *ControlPlane {
            t.Helper()
            cp, err := Open(Config{StateDir: filepath.Join(t.TempDir(), "state"), ProtectedCIDRs: []string{"10.0.0.0/8"}, MaxWave: 10})
            if err != nil { t.Fatal(err) }
            if err := cp.UpsertNode(Node{ID:"n1",Hostname:"n1.local",Site:"lab",Environment:"test",ManagementIP:"198.51.100.10",Online:true,Labels:map[string]string{"role":"edge"}}); err != nil { t.Fatal(err) }
            return cp
        }

        func verifierRoute(id, dst string, metric int) Route {
            return Route{ID:id,NodeID:"n1",Destination:dst,Table:100,Metric:metric,Protocol:"static",Scope:"global",Type:"unicast",Owner:"routecp",NextHops:[]NextHop{{Gateway:"192.0.2.1",Interface:"eth0",Weight:1}}}
        }

        func verifierApplyRoute(t *testing.T, cp *ControlPlane, id, dst, key string) Transaction {
            t.Helper()
            plan, err := cp.Preview(ChangeRequest{BaseRevision:cp.Revision(),Actor:"test",Reason:"add",RouteMutations:[]RouteMutation{{Operation:"add",Route:verifierRoute(id,dst,100)}}})
            if err != nil { t.Fatal(err) }
            txn, err := cp.Apply(ApplyRequest{PlanID:plan.ID,BaseRevision:plan.BaseRevision,IdempotencyKey:key,Nodes:[]string{"n1"},Actor:"test"})
            if err != nil { t.Fatal(err) }
            return txn
        }

        func TestVerifierIPv6CanonicalPrefix(t *testing.T) {
            got, err := canonicalPrefix("2001:db8:0:0::1/64")
            if err != nil { t.Fatal(err) }
            if got != "2001:db8::/64" { t.Fatalf("canonical prefix=%q", got) }
        }

        func TestVerifierMultipathOrderingIsNotIdentity(t *testing.T) {
            a := verifierRoute("a","198.51.100.0/24",100)
            a.NextHops = []NextHop{{Gateway:"192.0.2.2",Interface:"eth1",Weight:1},{Gateway:"192.0.2.1",Interface:"eth0",Weight:1}}
            b := a
            b.ID = "b"
            b.NextHops = []NextHop{{Gateway:"192.0.2.1",Interface:"eth0",Weight:1},{Gateway:"192.0.2.2",Interface:"eth1",Weight:1}}
            if routeIdentity(a) != routeIdentity(b) { t.Fatalf("equivalent multipath routes have different identity") }
        }

        func TestVerifierMetricIsMutableNotRouteIdentity(t *testing.T) {
            a := verifierRoute("a","198.51.100.0/24",10)
            b := verifierRoute("b","198.51.100.0/24",200)
            if routeIdentity(a) != routeIdentity(b) { t.Fatalf("metric change must be replaceable under one route identity") }
        }

        func TestVerifierOwnerNormalization(t *testing.T) {
            route := verifierRoute("a","198.51.100.0/24",10)
            route.Owner = " RouteCP "
            got, err := normalizeRoute(route)
            if err != nil { t.Fatal(err) }
            if got.Owner != "routecp" { t.Fatalf("owner=%q", got.Owner) }
        }

        func TestVerifierRulePriorityIsEffectiveIdentity(t *testing.T) {
            a := PolicyRule{ID:"a",NodeID:"n1",Family:"ipv4",Priority:100,Source:"192.0.2.1/32",Table:100,Action:"lookup",Owner:"routecp"}
            b := a
            b.ID = "b"
            b.Source = "192.0.2.2/32"
            if ruleIdentity(a) != ruleIdentity(b) { t.Fatalf("same effective priority must collide") }
        }

        func TestVerifierDuplicateRulePriorityRejected(t *testing.T) {
            nodes := map[string]Node{"n1":{ID:"n1"}}
            state := DesiredState{Routes:[]Route{verifierRoute("r","198.51.100.0/24",10)},Rules:[]PolicyRule{
                {ID:"a",NodeID:"n1",Family:"ipv4",Priority:100,Source:"192.0.2.1/32",Table:100,Action:"lookup",Owner:"routecp"},
                {ID:"b",NodeID:"n1",Family:"ipv4",Priority:100,Source:"192.0.2.2/32",Table:100,Action:"lookup",Owner:"routecp"},
            }}
            if err := validateDesired(state,nodes); !errors.Is(err,ErrConflict) { t.Fatalf("expected priority conflict, got %v", err) }
        }

        func TestVerifierRuleCannotReferenceMissingTable(t *testing.T) {
            nodes := map[string]Node{"n1":{ID:"n1"}}
            state := DesiredState{Rules:[]PolicyRule{{ID:"a",NodeID:"n1",Family:"ipv4",Priority:100,Source:"192.0.2.1/32",Table:100,Action:"lookup",Owner:"routecp"}}}
            if err := validateDesired(state,nodes); err == nil { t.Fatal("missing table accepted") }
        }

        func TestVerifierIdempotencyReplayIsStable(t *testing.T) {
            cp := verifierCP(t)
            plan, err := cp.Preview(ChangeRequest{BaseRevision:0,Actor:"test",RouteMutations:[]RouteMutation{{Operation:"add",Route:verifierRoute("r1","198.51.100.0/24",100)}}})
            if err != nil { t.Fatal(err) }
            req := ApplyRequest{PlanID:plan.ID,BaseRevision:0,IdempotencyKey:"same",Nodes:[]string{"n1"},Actor:"test"}
            first, err := cp.Apply(req); if err != nil { t.Fatal(err) }
            auditLen := len(cp.Audit(1000))
            second, err := cp.Apply(req); if err != nil { t.Fatal(err) }
            if first.ID != second.ID { t.Fatalf("idempotency changed transaction") }
            if len(cp.Audit(1000)) != auditLen { t.Fatalf("idempotency replay appended audit") }
        }

        func TestVerifierIdempotencyKeyCannotBindAnotherPlan(t *testing.T) {
            cp := verifierCP(t)
            verifierApplyRoute(t,cp,"r1","198.51.100.0/24","same")
            plan, err := cp.Preview(ChangeRequest{BaseRevision:1,Actor:"test",RouteMutations:[]RouteMutation{{Operation:"add",Route:verifierRoute("r2","203.0.113.0/24",100)}}})
            if err != nil { t.Fatal(err) }
            _, err = cp.Apply(ApplyRequest{PlanID:plan.ID,BaseRevision:1,IdempotencyKey:"same",Nodes:[]string{"n1"},Actor:"test"})
            if !errors.Is(err,ErrConflict) { t.Fatalf("expected idempotency conflict, got %v", err) }
        }

        func TestVerifierRollbackCreatesMonotonicDesiredRevision(t *testing.T) {
            cp := verifierCP(t)
            txn := verifierApplyRoute(t,cp,"r1","198.51.100.0/24","k1")
            rb, err := cp.Rollback(RollbackRequest{TransactionID:txn.ID,Actor:"test",Reason:"undo"})
            if err != nil { t.Fatal(err) }
            if rb.TargetRevision != 2 || cp.Revision() != 2 { t.Fatalf("rollback revision target=%d current=%d", rb.TargetRevision, cp.Revision()) }
            if len(cp.Routes("n1","")) != 0 { t.Fatalf("rolled-back desired route still published") }
        }

        func TestVerifierOldRollbackCannotClobberNewRevision(t *testing.T) {
            cp := verifierCP(t)
            first := verifierApplyRoute(t,cp,"r1","198.51.100.0/24","k1")
            verifierApplyRoute(t,cp,"r2","203.0.113.0/24","k2")
            _, err := cp.Rollback(RollbackRequest{TransactionID:first.ID,Actor:"test",Reason:"stale undo"})
            if !errors.Is(err,ErrConflict) { t.Fatalf("expected stale rollback conflict, got %v", err) }
        }

        func TestVerifierReconcileRejectsStaleObservedSnapshot(t *testing.T) {
            cp := verifierCP(t)
            verifierApplyRoute(t,cp,"r1","198.51.100.0/24","k1")
            cp.mu.Lock(); stale := cp.observed["n1"]; stale.Revision = 0; stale.CollectedAt = time.Now().Add(-time.Minute); cp.observed["n1"] = stale; cp.mu.Unlock()
            _, err := cp.Reconcile(ReconcileRequest{NodeID:"n1",Actor:"test",DryRun:false})
            if !errors.Is(err,ErrConflict) { t.Fatalf("expected stale observation conflict, got %v", err) }
        }

        func TestVerifierUnownedUnexpectedRouteIsNotDeleted(t *testing.T) {
            cp := verifierCP(t)
            external := verifierRoute("external","203.0.113.0/24",50); external.Owner = "kernel"
            cp.mu.Lock(); cp.observed["n1"] = ObservedState{Revision:0,Routes:[]Route{external},CollectedAt:time.Now().UTC()}; cp.mu.Unlock()
            result, err := cp.Reconcile(ReconcileRequest{NodeID:"n1",ExpectedObservedRevision:0,Actor:"test",DryRun:false})
            if err != nil { t.Fatal(err) }
            if result.Applied { t.Fatalf("unowned-only drift triggered reconciliation") }
            cp.mu.RLock(); got := len(cp.observed["n1"].Routes); cp.mu.RUnlock()
            if got != 1 { t.Fatalf("unowned route removed") }
        }

        func TestVerifierRolloutRejectsStaleHeartbeat(t *testing.T) {
            cp := verifierCP(t)
            verifierApplyRoute(t,cp,"r1","198.51.100.0/24","k1")
            cp.mu.Lock(); node := cp.nodes["n1"]; node.Online = true; node.HeartbeatAt = time.Now().Add(-10*time.Minute); cp.nodes["n1"] = node; observed := cp.observed["n1"]; observed.Revision = 0; cp.observed["n1"] = observed; cp.mu.Unlock()
            ro, err := cp.Rollout(RolloutRequest{Revision:1,Selector:map[string]string{"role":"edge"},WaveSize:1,CanaryNodes:[]string{"n1"},Actor:"test"})
            if err != nil { t.Fatal(err) }
            if ro.Status != "failed" { t.Fatalf("stale heartbeat rollout status=%s", ro.Status) }
        }

        func TestVerifierRolloutAlreadyCurrentDoesNotCreateTransaction(t *testing.T) {
            cp := verifierCP(t)
            verifierApplyRoute(t,cp,"r1","198.51.100.0/24","k1")
            before := len(cp.Snapshot().Transactions)
            ro, err := cp.Rollout(RolloutRequest{Revision:1,Selector:map[string]string{"role":"edge"},WaveSize:1,Actor:"test"})
            if err != nil { t.Fatal(err) }
            if ro.Status != "succeeded" { t.Fatalf("rollout status=%s", ro.Status) }
            if len(cp.Snapshot().Transactions) != before { t.Fatalf("already-current rollout created transaction") }
        }

        func TestVerifierPersistenceRetainsIdempotency(t *testing.T) {
            dir := filepath.Join(t.TempDir(),"state")
            cp, err := Open(Config{StateDir:dir,ProtectedCIDRs:[]string{},MaxWave:10}); if err != nil { t.Fatal(err) }
            if err := cp.UpsertNode(Node{ID:"n1",Hostname:"n1.local",ManagementIP:"198.51.100.10",Online:true}); err != nil { t.Fatal(err) }
            txn := verifierApplyRoute(t,cp,"r1","198.51.100.0/24","persist-key")
            reopened, err := Open(Config{StateDir:dir,ProtectedCIDRs:[]string{},MaxWave:10}); if err != nil { t.Fatal(err) }
            plan := Plan{ID:txn.PlanID}
            _ = plan
            if reopened.idempotency["persist-key"] != txn.ID { t.Fatalf("idempotency mapping not durable") }
            if reopened.Revision() != 1 { t.Fatalf("revision after restart=%d", reopened.Revision()) }
        }

        func TestVerifierAuditSequenceStrictlyIncreases(t *testing.T) {
            cp := verifierCP(t)
            verifierApplyRoute(t,cp,"r1","198.51.100.0/24","k1")
            events := cp.Audit(1000)
            for i := 1; i < len(events); i++ { if events[i].Sequence <= events[i-1].Sequence { t.Fatalf("audit order is not monotonic") } }
        }
    '''))
    try:
        result = run(["go", "test", "./internal/controlplane", "-run", "TestVerifier", "-count=1", "-timeout=120s"])
        assert result.returncode == 0, result.stdout
    finally:
        test_file.unlink(missing_ok=True)


def test_dashboard_apply_is_bound_to_preview_revision() -> None:
    text = (ROOT / "web" / "app.ts").read_text()
    assert "base_revision: plan.base_revision" in text, "dashboard Apply is not fenced to the exact Preview revision"


def test_ansible_preserves_host_specific_protected_routes() -> None:
    defaults = (ROOT / "ansible" / "roles" / "routecp" / "defaults" / "main.yml").read_text()
    tasks = (ROOT / "ansible" / "roles" / "routecp" / "tasks" / "main.yml").read_text()
    assert "routecp_protected_routes:" in defaults
    assert "routecp_host_routes:" in defaults
    assert "routecp_protected_routes | default([])" in tasks
    assert "routecp_host_routes | default([])" in tasks


def test_public_api_surface_remains_present() -> None:
    text = (ROOT / "cmd" / "routecp" / "main.go").read_text()
    required = [
        "GET /healthz", "GET /v1/state", "GET /v1/nodes", "POST /v1/nodes",
        "GET /v1/routes", "POST /v1/revisions/preview", "POST /v1/revisions/apply",
        "POST /v1/revisions/rollback", "GET /v1/drift", "POST /v1/reconcile",
        "POST /v1/rollouts", "GET /v1/audit",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, f"missing API surfaces: {missing}"


def test_repaired_runtime_builds() -> None:
    result = run(["go", "build", "./cmd/routecp"])
    assert result.returncode == 0, result.stdout
