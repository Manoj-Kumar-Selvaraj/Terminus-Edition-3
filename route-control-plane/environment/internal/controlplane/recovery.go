package controlplane

import (
    "fmt"
    "sort"
    "strings"
)

type TransactionSummary struct {
    ID string `json:"id"`
    PlanID string `json:"plan_id"`
    IdempotencyKey string `json:"idempotency_key"`
    BaseRevision uint64 `json:"base_revision"`
    TargetRevision uint64 `json:"target_revision"`
    Phase TransactionPhase `json:"phase"`
    Actor string `json:"actor"`
    Nodes int `json:"nodes"`
    FailedNodes int `json:"failed_nodes"`
}

type RecoveryAction struct {
    TransactionID string `json:"transaction_id"`
    Action string `json:"action"`
    Safe bool `json:"safe"`
    Reason string `json:"reason"`
    AffectedNodes []string `json:"affected_nodes"`
}

type RecoveryPlan struct {
    Revision uint64 `json:"revision"`
    Actions []RecoveryAction `json:"actions"`
    OrphanedIdempotencyKeys []string `json:"orphaned_idempotency_keys"`
    Blocking bool `json:"blocking"`
}

type AuditIntegrityReport struct {
    Events int `json:"events"`
    FirstSequence uint64 `json:"first_sequence"`
    LastSequence uint64 `json:"last_sequence"`
    StrictlyIncreasing bool `json:"strictly_increasing"`
    DuplicateSequences []uint64 `json:"duplicate_sequences"`
    Gaps []string `json:"gaps"`
    InvalidReferences []string `json:"invalid_references"`
}

func (c *ControlPlane) Transactions() []TransactionSummary {
    c.mu.RLock(); defer c.mu.RUnlock()
    out:=make([]TransactionSummary,0,len(c.transactions))
    for _,txn:=range c.transactions {
        summary:=TransactionSummary{ID:txn.ID,PlanID:txn.PlanID,IdempotencyKey:txn.IdempotencyKey,BaseRevision:txn.BaseRevision,TargetRevision:txn.TargetRevision,Phase:txn.Phase,Actor:txn.Actor,Nodes:len(txn.Nodes)}
        for _,node:=range txn.Nodes { if node.Phase==TransactionFailed || node.Error!="" { summary.FailedNodes++ } }
        out=append(out,summary)
    }
    sort.Slice(out,func(i,j int) bool {
        if out[i].TargetRevision!=out[j].TargetRevision { return out[i].TargetRevision>out[j].TargetRevision }
        return out[i].ID<out[j].ID
    })
    return out
}

func (c *ControlPlane) RecoveryPlan() RecoveryPlan {
    c.mu.RLock(); defer c.mu.RUnlock()
    plan:=RecoveryPlan{Revision:c.desired.Revision}
    for id,txn:=range c.transactions {
        nodes:=make([]string,0,len(txn.Nodes)); for nodeID:=range txn.Nodes { nodes=append(nodes,nodeID) }; sort.Strings(nodes)
        switch txn.Phase {
        case TransactionPrepared,TransactionApplying:
            safe:=txn.TargetRevision>=c.desired.Revision
            action:="fail_and_reconcile"
            reason:="transaction was persisted before reaching a terminal phase"
            if txn.TargetRevision<c.desired.Revision { safe=false; action="quarantine"; reason="incomplete transaction predates current desired revision" }
            plan.Actions=append(plan.Actions,RecoveryAction{TransactionID:id,Action:action,Safe:safe,Reason:reason,AffectedNodes:nodes})
        case TransactionRollingBack:
            plan.Actions=append(plan.Actions,RecoveryAction{TransactionID:id,Action:"quarantine",Safe:false,Reason:"rollback was interrupted and requires operator review",AffectedNodes:nodes})
        case TransactionFailed:
            plan.Actions=append(plan.Actions,RecoveryAction{TransactionID:id,Action:"reconcile",Safe:true,Reason:"failed transaction is terminal; nodes can be reconciled to current desired state",AffectedNodes:nodes})
        }
    }
    for key,id:=range c.idempotency { if _,ok:=c.transactions[id]; !ok { plan.OrphanedIdempotencyKeys=append(plan.OrphanedIdempotencyKeys,key) } }
    sort.Strings(plan.OrphanedIdempotencyKeys)
    sort.Slice(plan.Actions,func(i,j int) bool { return plan.Actions[i].TransactionID<plan.Actions[j].TransactionID })
    if len(plan.OrphanedIdempotencyKeys)>0 { plan.Blocking=true }
    for _,a:=range plan.Actions { if !a.Safe { plan.Blocking=true; break } }
    return plan
}

func (c *ControlPlane) AuditIntegrity() AuditIntegrityReport {
    c.mu.RLock(); defer c.mu.RUnlock()
    report:=AuditIntegrityReport{Events:len(c.audit),StrictlyIncreasing:true}
    if len(c.audit)==0 { return report }
    report.FirstSequence=c.audit[0].Sequence; report.LastSequence=c.audit[len(c.audit)-1].Sequence
    seen:=map[uint64]bool{}
    previous:=uint64(0)
    for i,event:=range c.audit {
        if seen[event.Sequence] { report.DuplicateSequences=append(report.DuplicateSequences,event.Sequence); report.StrictlyIncreasing=false }
        seen[event.Sequence]=true
        if i>0 {
            if event.Sequence<=previous { report.StrictlyIncreasing=false }
            if event.Sequence>previous+1 { report.Gaps=append(report.Gaps,fmt.Sprintf("%d-%d",previous+1,event.Sequence-1)) }
        }
        previous=event.Sequence
        if strings.TrimSpace(event.Action)=="" || strings.TrimSpace(event.ObjectType)=="" { report.InvalidReferences=append(report.InvalidReferences,fmt.Sprintf("sequence:%d missing action/object_type",event.Sequence)) }
        if event.ObjectType=="transaction" && event.ObjectID!="" {
            if _,ok:=c.transactions[event.ObjectID]; !ok && !strings.Contains(event.Action,"rollback") { report.InvalidReferences=append(report.InvalidReferences,fmt.Sprintf("sequence:%d unknown transaction:%s",event.Sequence,event.ObjectID)) }
        }
    }
    sort.Slice(report.DuplicateSequences,func(i,j int) bool { return report.DuplicateSequences[i]<report.DuplicateSequences[j] })
    sort.Strings(report.Gaps); sort.Strings(report.InvalidReferences)
    return report
}

func (c *ControlPlane) Transaction(id string) (Transaction,error) {
    c.mu.RLock(); defer c.mu.RUnlock()
    txn,ok:=c.transactions[strings.TrimSpace(id)]
    if !ok { return Transaction{},fmt.Errorf("%w: transaction %s",ErrNotFound,id) }
    return cloneTransaction(txn),nil
}
