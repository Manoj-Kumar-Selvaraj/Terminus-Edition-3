from __future__ import annotations

import pathlib
import subprocess
import textwrap

ROOT = pathlib.Path("/app/routecp")
PKG = ROOT / "internal" / "controlplane"


def run_go(source: str) -> None:
    path = PKG / "boundary_contract_test.go"
    path.write_text(textwrap.dedent(source))
    try:
        proc = subprocess.run(
            ["go", "test", "./internal/controlplane", "-run", "TestBoundary", "-count=1", "-timeout=120s"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=180,
        )
        assert proc.returncode == 0, proc.stdout
    finally:
        path.unlink(missing_ok=True)


def test_route_rule_and_transaction_boundaries() -> None:
    run_go(r'''
        package controlplane

        import (
            "errors"
            "path/filepath"
            "testing"
            "time"
        )

        func boundaryCP(t *testing.T) *ControlPlane {
            t.Helper()
            cp, err := Open(Config{StateDir:filepath.Join(t.TempDir(),"state"),ProtectedCIDRs:[]string{},MaxWave:4})
            if err != nil { t.Fatal(err) }
            if err := cp.UpsertNode(Node{ID:"n1",Hostname:"n1.local",ManagementIP:"198.51.100.10",Online:true,Labels:map[string]string{"role":"edge"}}); err != nil { t.Fatal(err) }
            return cp
        }

        func boundaryRoute(id,dst string, table int) Route {
            return Route{ID:id,NodeID:"n1",Destination:dst,Table:table,Metric:10,Protocol:"static",Scope:"global",Type:"unicast",Owner:"routecp",NextHops:[]NextHop{{Gateway:"192.0.2.1",Interface:"eth0",Weight:1}}}
        }

        func TestBoundaryDefaultAndIPv6FamiliesStayDistinct(t *testing.T) {
            v4, err := normalizeRoute(boundaryRoute("v4","default",100)); if err != nil { t.Fatal(err) }
            v6, err := normalizeRoute(boundaryRoute("v6","::/0",100)); if err != nil { t.Fatal(err) }
            if v4.Family != "ipv4" || v6.Family != "ipv6" { t.Fatalf("families v4=%s v6=%s",v4.Family,v6.Family) }
            if routeIdentity(v4) == routeIdentity(v6) { t.Fatal("IPv4 and IPv6 default routes collided") }
        }

        func TestBoundaryUnknownNodeRouteRejected(t *testing.T) {
            state := DesiredState{Routes:[]Route{{ID:"r",NodeID:"missing",Destination:"198.51.100.0/24",Table:100,Type:"unicast"}}}
            if err := validateDesired(state,map[string]Node{"n1":{ID:"n1"}}); !errors.Is(err,ErrNotFound) { t.Fatalf("got %v",err) }
        }

        func TestBoundarySamePrefixDifferentTablesRemainDistinct(t *testing.T) {
            a := boundaryRoute("a","198.51.100.0/24",100)
            b := boundaryRoute("b","198.51.100.0/24",200)
            if routeIdentity(a) == routeIdentity(b) { t.Fatal("routing tables collapsed") }
        }

        func TestBoundaryStalePreviewCannotApply(t *testing.T) {
            cp := boundaryCP(t)
            p1, err := cp.Preview(ChangeRequest{BaseRevision:0,Actor:"x",RouteMutations:[]RouteMutation{{Operation:"add",Route:boundaryRoute("r1","198.51.100.0/24",100)}}}); if err != nil { t.Fatal(err) }
            p2, err := cp.Preview(ChangeRequest{BaseRevision:0,Actor:"x",RouteMutations:[]RouteMutation{{Operation:"add",Route:boundaryRoute("r2","203.0.113.0/24",200)}}}); if err != nil { t.Fatal(err) }
            if _, err := cp.Apply(ApplyRequest{PlanID:p1.ID,BaseRevision:0,IdempotencyKey:"a",Nodes:[]string{"n1"},Actor:"x"}); err != nil { t.Fatal(err) }
            if _, err := cp.Apply(ApplyRequest{PlanID:p2.ID,BaseRevision:0,IdempotencyKey:"b",Nodes:[]string{"n1"},Actor:"x"}); !errors.Is(err,ErrConflict) { t.Fatalf("stale preview got %v",err) }
        }

        func TestBoundaryOfflineApplyPreservesDesiredState(t *testing.T) {
            cp := boundaryCP(t)
            plan, err := cp.Preview(ChangeRequest{BaseRevision:0,Actor:"x",RouteMutations:[]RouteMutation{{Operation:"add",Route:boundaryRoute("r1","198.51.100.0/24",100)}}}); if err != nil { t.Fatal(err) }
            cp.mu.Lock(); n:=cp.nodes["n1"]; n.Online=false; cp.nodes["n1"]=n; cp.mu.Unlock()
            if _, err := cp.Apply(ApplyRequest{PlanID:plan.ID,BaseRevision:0,IdempotencyKey:"offline",Nodes:[]string{"n1"},Actor:"x"}); err == nil { t.Fatal("offline apply succeeded") }
            if cp.Revision()!=0 || len(cp.Routes("n1",""))!=0 { t.Fatal("failed apply mutated desired state") }
        }

        func TestBoundaryIncompleteTransactionMarkedFailedAfterRestart(t *testing.T) {
            dir:=filepath.Join(t.TempDir(),"state")
            cp,err:=Open(Config{StateDir:dir,MaxWave:4}); if err!=nil { t.Fatal(err) }
            cp.mu.Lock(); cp.transactions["partial"]=Transaction{ID:"partial",Phase:TransactionApplying,CreatedAt:time.Now().UTC(),UpdatedAt:time.Now().UTC()}; if err:=cp.persistLocked(); err!=nil { t.Fatal(err) }; cp.mu.Unlock()
            reopened,err:=Open(Config{StateDir:dir,MaxWave:4}); if err!=nil { t.Fatal(err) }
            if reopened.transactions["partial"].Phase!=TransactionFailed { t.Fatalf("phase=%s",reopened.transactions["partial"].Phase) }
        }

        func TestBoundaryWaveSizeAbovePolicyRejected(t *testing.T) {
            cp:=boundaryCP(t)
            _,err:=cp.Rollout(RolloutRequest{Revision:0,Selector:map[string]string{"role":"edge"},WaveSize:5,Actor:"x"})
            if err==nil { t.Fatal("oversized wave accepted") }
        }

        func TestBoundaryCanaryOutsideSelectorRejected(t *testing.T) {
            cp:=boundaryCP(t)
            cp.mu.Lock(); cp.nodes["n2"]=Node{ID:"n2",Hostname:"n2.local",ManagementIP:"192.0.2.11",Online:true,HeartbeatAt:time.Now().UTC(),Labels:map[string]string{"role":"db"}}; cp.mu.Unlock()
            _,err:=cp.Rollout(RolloutRequest{Revision:0,Selector:map[string]string{"role":"edge"},WaveSize:1,CanaryNodes:[]string{"n2"},Actor:"x"})
            if err==nil { t.Fatal("out-of-selector canary accepted") }
        }
    ''')


def test_solution_entrypoint_is_general_and_repeatable() -> None:
    solve = (ROOT / ".." / "route-control-plane" / "solution" / "solve.sh")
    # In the task runtime only /app/routecp is guaranteed. This check is structural
    # when the solution tree is mounted beside the task during Oracle execution.
    if solve.exists():
        text = solve.read_text()
        assert "repair.py" in text
        assert "go test ./..." in text
        assert "go build" in text


def test_verifier_does_not_branch_on_named_hidden_cases() -> None:
    corpus = "\n".join(path.read_text() for path in pathlib.Path("/tests").glob("*.py"))
    forbidden = ["HIDDEN" + "_TEST", "grader" + "_case", "test_name " + "==", "PYTEST_" + "CURRENT_TEST"]
    assert not any(token in corpus for token in forbidden)
