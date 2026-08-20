from __future__ import annotations

import pathlib
import subprocess
import textwrap

ROOT = pathlib.Path("/app/routecp")
PKG = ROOT / "internal" / "controlplane"

BASE = r'''
package controlplane

import (
    "errors"
    "path/filepath"
    "testing"
    "time"
)

func matrixCP(t *testing.T) *ControlPlane {
    t.Helper()
    cp, err := Open(Config{StateDir:filepath.Join(t.TempDir(),"state"),ProtectedCIDRs:[]string{},MaxWave:4})
    if err != nil { t.Fatal(err) }
    if err := cp.UpsertNode(Node{ID:"n1",Hostname:"n1.local",ManagementIP:"192.0.2.10",Online:true,Labels:map[string]string{"role":"edge"}}); err != nil { t.Fatal(err) }
    return cp
}

func matrixRoute(id,dst string, table,metric int) Route {
    return Route{ID:id,NodeID:"n1",Destination:dst,Table:table,Metric:metric,Protocol:"static",Scope:"global",Type:"unicast",Owner:"routecp",NextHops:[]NextHop{{Gateway:"192.0.2.1",Interface:"eth0",Weight:1}}}
}

func matrixApply(t *testing.T, cp *ControlPlane, id,dst,key string) Transaction {
    t.Helper()
    p,err:=cp.Preview(ChangeRequest{BaseRevision:cp.Revision(),Actor:"matrix",RouteMutations:[]RouteMutation{{Operation:"add",Route:matrixRoute(id,dst,100,10)}}}); if err!=nil { t.Fatal(err) }
    tx,err:=cp.Apply(ApplyRequest{PlanID:p.ID,BaseRevision:p.BaseRevision,IdempotencyKey:key,Nodes:[]string{"n1"},Actor:"matrix"}); if err!=nil { t.Fatal(err) }
    return tx
}
'''


def go_case(body: str) -> None:
    path = PKG / "matrix_contract_test.go"
    path.write_text(BASE + "\n" + textwrap.dedent(body))
    try:
        proc = subprocess.run(
            ["go", "test", "./internal/controlplane", "-run", "TestMatrix", "-count=1", "-timeout=90s"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        assert proc.returncode == 0, proc.stdout
    finally:
        path.unlink(missing_ok=True)


def test_f2p_ipv6_aliases_canonicalize() -> None:
    go_case(r'''func TestMatrixIPv6(t *testing.T){ got,err:=canonicalPrefix("2001:db8:0:0::1/64"); if err!=nil||got!="2001:db8::/64"{t.Fatalf("got=%q err=%v",got,err)} }''')


def test_f2p_multipath_order_is_semantically_stable() -> None:
    go_case(r'''func TestMatrixMultipath(t *testing.T){ a:=matrixRoute("a","198.51.100.0/24",100,10); a.NextHops=[]NextHop{{Gateway:"192.0.2.2",Interface:"eth1",Weight:1},{Gateway:"192.0.2.1",Interface:"eth0",Weight:1}}; b:=a; b.ID="b"; b.NextHops=[]NextHop{{Gateway:"192.0.2.1",Interface:"eth0",Weight:1},{Gateway:"192.0.2.2",Interface:"eth1",Weight:1}}; if routeIdentity(a)!=routeIdentity(b){t.Fatal("order changed identity")} }''')


def test_f2p_route_metric_updates_do_not_change_identity() -> None:
    go_case(r'''func TestMatrixMetric(t *testing.T){ a:=matrixRoute("a","198.51.100.0/24",100,10); b:=matrixRoute("b","198.51.100.0/24",100,200); if routeIdentity(a)!=routeIdentity(b){t.Fatal("metric changed identity")} }''')


def test_f2p_same_prefix_in_distinct_tables_remains_distinct() -> None:
    go_case(r'''func TestMatrixTables(t *testing.T){ a:=matrixRoute("a","198.51.100.0/24",100,10); b:=matrixRoute("b","198.51.100.0/24",200,10); if routeIdentity(a)==routeIdentity(b){t.Fatal("tables collapsed")} }''')


def test_f2p_route_owner_normalizes_before_ownership_checks() -> None:
    go_case(r'''func TestMatrixOwner(t *testing.T){ r:=matrixRoute("a","198.51.100.0/24",100,10); r.Owner=" RouteCP "; n,err:=normalizeRoute(r); if err!=nil||n.Owner!="routecp"{t.Fatalf("owner=%q err=%v",n.Owner,err)} }''')


def test_f2p_duplicate_effective_rule_priority_is_rejected() -> None:
    go_case(r'''func TestMatrixPriority(t *testing.T){ s:=DesiredState{Routes:[]Route{matrixRoute("r","198.51.100.0/24",100,10)},Rules:[]PolicyRule{{ID:"a",NodeID:"n1",Family:"ipv4",Priority:100,Source:"192.0.2.1/32",Table:100,Action:"lookup",Owner:"routecp"},{ID:"b",NodeID:"n1",Family:"ipv4",Priority:100,Source:"192.0.2.2/32",Table:100,Action:"lookup",Owner:"routecp"}}}; if err:=validateDesired(s,map[string]Node{"n1":{ID:"n1"}}); !errors.Is(err,ErrConflict){t.Fatalf("got %v",err)} }''')


def test_f2p_rule_lookup_requires_existing_table() -> None:
    go_case(r'''func TestMatrixRuleTable(t *testing.T){ s:=DesiredState{Rules:[]PolicyRule{{ID:"a",NodeID:"n1",Family:"ipv4",Priority:100,Table:100,Action:"lookup",Owner:"routecp"}}}; if err:=validateDesired(s,map[string]Node{"n1":{ID:"n1"}}); err==nil{t.Fatal("missing table accepted")} }''')


def test_f2p_unknown_node_route_is_rejected() -> None:
    go_case(r'''func TestMatrixNode(t *testing.T){ r:=matrixRoute("r","198.51.100.0/24",100,10); r.NodeID="missing"; if err:=validateDesired(DesiredState{Routes:[]Route{r}},map[string]Node{"n1":{ID:"n1"}}); !errors.Is(err,ErrNotFound){t.Fatalf("got %v",err)} }''')


def test_f2p_stale_preview_cannot_apply_after_new_revision() -> None:
    go_case(r'''func TestMatrixStalePreview(t *testing.T){ cp:=matrixCP(t); p1,_:=cp.Preview(ChangeRequest{BaseRevision:0,RouteMutations:[]RouteMutation{{Operation:"add",Route:matrixRoute("a","198.51.100.0/24",100,10)}}}); p2,_:=cp.Preview(ChangeRequest{BaseRevision:0,RouteMutations:[]RouteMutation{{Operation:"add",Route:matrixRoute("b","203.0.113.0/24",100,10)}}}); if _,err:=cp.Apply(ApplyRequest{PlanID:p1.ID,BaseRevision:0,IdempotencyKey:"a",Nodes:[]string{"n1"}});err!=nil{t.Fatal(err)}; if _,err:=cp.Apply(ApplyRequest{PlanID:p2.ID,BaseRevision:0,IdempotencyKey:"b",Nodes:[]string{"n1"}});!errors.Is(err,ErrConflict){t.Fatalf("got %v",err)} }''')


def test_f2p_idempotency_replay_returns_same_transaction() -> None:
    go_case(r'''func TestMatrixIdempotent(t *testing.T){ cp:=matrixCP(t); p,_:=cp.Preview(ChangeRequest{BaseRevision:0,RouteMutations:[]RouteMutation{{Operation:"add",Route:matrixRoute("a","198.51.100.0/24",100,10)}}}); req:=ApplyRequest{PlanID:p.ID,BaseRevision:0,IdempotencyKey:"key",Nodes:[]string{"n1"}}; a,err:=cp.Apply(req);if err!=nil{t.Fatal(err)}; before:=len(cp.Audit(100)); b,err:=cp.Apply(req);if err!=nil{t.Fatal(err)}; if a.ID!=b.ID||len(cp.Audit(100))!=before{t.Fatal("idempotency replay changed state")} }''')


def test_f2p_idempotency_key_cannot_rebind_to_new_plan() -> None:
    go_case(r'''func TestMatrixKeyFence(t *testing.T){ cp:=matrixCP(t); matrixApply(t,cp,"a","198.51.100.0/24","same"); p,err:=cp.Preview(ChangeRequest{BaseRevision:1,RouteMutations:[]RouteMutation{{Operation:"add",Route:matrixRoute("b","203.0.113.0/24",100,10)}}});if err!=nil{t.Fatal(err)}; if _,err:=cp.Apply(ApplyRequest{PlanID:p.ID,BaseRevision:1,IdempotencyKey:"same",Nodes:[]string{"n1"}});!errors.Is(err,ErrConflict){t.Fatalf("got %v",err)} }''')


def test_f2p_offline_apply_preserves_last_desired_revision() -> None:
    go_case(r'''func TestMatrixOffline(t *testing.T){ cp:=matrixCP(t); p,_:=cp.Preview(ChangeRequest{BaseRevision:0,RouteMutations:[]RouteMutation{{Operation:"add",Route:matrixRoute("a","198.51.100.0/24",100,10)}}}); cp.mu.Lock(); n:=cp.nodes["n1"];n.Online=false;cp.nodes["n1"]=n;cp.mu.Unlock(); if _,err:=cp.Apply(ApplyRequest{PlanID:p.ID,BaseRevision:0,IdempotencyKey:"offline",Nodes:[]string{"n1"}});err==nil{t.Fatal("offline apply succeeded")}; if cp.Revision()!=0||len(cp.Routes("n1",""))!=0{t.Fatal("failed apply published state")} }''')


def test_f2p_rollback_is_a_new_monotonic_revision() -> None:
    go_case(r'''func TestMatrixRollbackRevision(t *testing.T){ cp:=matrixCP(t); tx:=matrixApply(t,cp,"a","198.51.100.0/24","a"); rb,err:=cp.Rollback(RollbackRequest{TransactionID:tx.ID,Actor:"x"});if err!=nil{t.Fatal(err)}; if rb.TargetRevision!=2||cp.Revision()!=2||len(cp.Routes("n1",""))!=0{t.Fatalf("target=%d current=%d routes=%d",rb.TargetRevision,cp.Revision(),len(cp.Routes("n1","")))} }''')


def test_f2p_stale_rollback_cannot_clobber_newer_revision() -> None:
    go_case(r'''func TestMatrixRollbackFence(t *testing.T){ cp:=matrixCP(t); first:=matrixApply(t,cp,"a","198.51.100.0/24","a"); matrixApply(t,cp,"b","203.0.113.0/24","b"); if _,err:=cp.Rollback(RollbackRequest{TransactionID:first.ID});!errors.Is(err,ErrConflict){t.Fatalf("got %v",err)} }''')


def test_f2p_incomplete_transaction_is_failed_on_restart() -> None:
    go_case(r'''func TestMatrixRestart(t *testing.T){ dir:=filepath.Join(t.TempDir(),"state"); cp,err:=Open(Config{StateDir:dir,MaxWave:4});if err!=nil{t.Fatal(err)}; cp.mu.Lock();cp.transactions["partial"]=Transaction{ID:"partial",Phase:TransactionApplying,CreatedAt:time.Now().UTC(),UpdatedAt:time.Now().UTC()};if err:=cp.persistLocked();err!=nil{t.Fatal(err)};cp.mu.Unlock(); reopened,err:=Open(Config{StateDir:dir,MaxWave:4});if err!=nil{t.Fatal(err)};if reopened.transactions["partial"].Phase!=TransactionFailed{t.Fatalf("phase=%s",reopened.transactions["partial"].Phase)} }''')


def test_f2p_reconcile_rejects_stale_observed_snapshot() -> None:
    go_case(r'''func TestMatrixReconcileFence(t *testing.T){ cp:=matrixCP(t);matrixApply(t,cp,"a","198.51.100.0/24","a");cp.mu.Lock();o:=cp.observed["n1"];o.Revision=0;cp.observed["n1"]=o;cp.mu.Unlock();if _,err:=cp.Reconcile(ReconcileRequest{NodeID:"n1"});!errors.Is(err,ErrConflict){t.Fatalf("got %v",err)} }''')


def test_f2p_reconcile_preserves_unowned_unexpected_route() -> None:
    go_case(r'''func TestMatrixExternal(t *testing.T){ cp:=matrixCP(t);r:=matrixRoute("external","203.0.113.0/24",100,10);r.Owner="kernel";cp.mu.Lock();cp.observed["n1"]=ObservedState{Revision:0,Routes:[]Route{r},CollectedAt:time.Now().UTC()};cp.mu.Unlock();res,err:=cp.Reconcile(ReconcileRequest{NodeID:"n1"});if err!=nil{t.Fatal(err)};if res.Applied{t.Fatal("external-only drift applied")};cp.mu.RLock();n:=len(cp.observed["n1"].Routes);cp.mu.RUnlock();if n!=1{t.Fatal("external route removed")} }''')


def test_f2p_rollout_rejects_stale_heartbeat() -> None:
    go_case(r'''func TestMatrixHeartbeat(t *testing.T){ cp:=matrixCP(t);matrixApply(t,cp,"a","198.51.100.0/24","a");cp.mu.Lock();n:=cp.nodes["n1"];n.HeartbeatAt=time.Now().Add(-10*time.Minute);cp.nodes["n1"]=n;o:=cp.observed["n1"];o.Revision=0;cp.observed["n1"]=o;cp.mu.Unlock();ro,err:=cp.Rollout(RolloutRequest{Revision:1,Selector:map[string]string{"role":"edge"},WaveSize:1,CanaryNodes:[]string{"n1"}});if err!=nil{t.Fatal(err)};if ro.Status!="failed"{t.Fatalf("status=%s",ro.Status)} }''')


def test_f2p_rollout_skips_nodes_already_at_target_revision() -> None:
    go_case(r'''func TestMatrixAlreadyCurrent(t *testing.T){ cp:=matrixCP(t);matrixApply(t,cp,"a","198.51.100.0/24","a");before:=len(cp.Snapshot().Transactions);ro,err:=cp.Rollout(RolloutRequest{Revision:1,Selector:map[string]string{"role":"edge"},WaveSize:1});if err!=nil{t.Fatal(err)};if ro.Status!="succeeded"||len(cp.Snapshot().Transactions)!=before{t.Fatal("already-current node reapplied")} }''')


def test_f2p_rollout_rejects_canary_outside_selector() -> None:
    go_case(r'''func TestMatrixCanary(t *testing.T){ cp:=matrixCP(t);cp.mu.Lock();cp.nodes["n2"]=Node{ID:"n2",Hostname:"n2",ManagementIP:"192.0.2.11",Online:true,HeartbeatAt:time.Now().UTC(),Labels:map[string]string{"role":"db"}};cp.mu.Unlock();if _,err:=cp.Rollout(RolloutRequest{Selector:map[string]string{"role":"edge"},WaveSize:1,CanaryNodes:[]string{"n2"}});err==nil{t.Fatal("foreign canary accepted")} }''')


def test_f2p_rollout_enforces_configured_wave_limit() -> None:
    go_case(r'''func TestMatrixWaveLimit(t *testing.T){ cp:=matrixCP(t);if _,err:=cp.Rollout(RolloutRequest{Selector:map[string]string{"role":"edge"},WaveSize:5});err==nil{t.Fatal("oversized wave accepted")} }''')
