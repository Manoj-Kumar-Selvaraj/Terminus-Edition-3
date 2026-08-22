package rollout

import (
	"errors"
	"sync"
	"time"

	"sovereign-lb/internal/model"
	"sovereign-lb/internal/nodes"
)

var ErrNoRollout = errors.New("no rollout in progress")
var ErrMismatch = errors.New("response does not match candidate")
var ErrWrongPhase = errors.New("response is invalid for rollout phase")

type Coordinator struct { mutex sync.RWMutex; registry *nodes.Registry; current *model.Rollout; active uint64 }

func NewCoordinator(registry *nodes.Registry, active uint64) *Coordinator { return &Coordinator{registry: registry, active: active} }

func (coordinator *Coordinator) Begin(snapshot model.Snapshot, digest string, policy model.RolloutPolicy, now time.Time) (model.Rollout, error) {
	coordinator.mutex.Lock(); defer coordinator.mutex.Unlock()
	if coordinator.current != nil && (coordinator.current.Phase == "preparing" || coordinator.current.Phase == "activating") { return model.Rollout{}, errors.New("rollout already in progress") }
	value := model.Rollout{Generation: snapshot.Generation, Digest: digest, Revision: snapshot.Revision, Phase: "preparing", PreviousActive: coordinator.active, PrepareQuorum: policy.PrepareQuorum, ActivateQuorum: policy.ActivateQuorum, Deadline: now.Add(time.Duration(policy.PrepareTimeout)*time.Millisecond), NodeResponses: map[string]model.NodeResponse{}}
	coordinator.current = &value
	return clone(value), nil
}

func (coordinator *Coordinator) Record(envelope model.Envelope, now time.Time, activateTimeout time.Duration) (model.Rollout, error) {
	coordinator.mutex.Lock(); defer coordinator.mutex.Unlock()
	if coordinator.current == nil { return model.Rollout{}, ErrNoRollout }
	rollout := coordinator.current
	if envelope.Generation != rollout.Generation || envelope.Digest != rollout.Digest { return clone(*rollout), ErrMismatch }
	if !coordinator.registry.Current(envelope.NodeID, envelope.SessionID) { return clone(*rollout), nodes.ErrStaleSession }
	if now.After(rollout.Deadline) { rollout.Phase = "aborted"; return clone(*rollout), errors.New("rollout phase deadline exceeded") }
	if envelope.Type == "rejected" {
		rollout.NodeResponses[envelope.NodeID] = response(envelope, "rejected")
		rollout.Phase = "rejected"
		return clone(*rollout), nil
	}
	if rollout.Phase == "preparing" && envelope.Type == "prepared" {
		rollout.NodeResponses[envelope.NodeID] = response(envelope, "prepared")
		if count(rollout.NodeResponses, "prepared") >= rollout.PrepareQuorum { rollout.Phase = "activating"; rollout.Deadline = now.Add(activateTimeout) }
		return clone(*rollout), nil
	}
    if rollout.Phase == "activating" && envelope.Type == "active" {
		prior, exists := rollout.NodeResponses[envelope.NodeID]
		if !exists || prior.SessionID != envelope.SessionID || prior.State != "prepared" { return clone(*rollout), ErrWrongPhase }
		rollout.NodeResponses[envelope.NodeID] = response(envelope, "active")
		if count(rollout.NodeResponses, "active") >= 1 && rollout.ActivateQuorum > 0 { rollout.Phase = "active"; coordinator.active = rollout.Generation }
		return clone(*rollout), nil
	}
	return clone(*rollout), ErrWrongPhase
}

func (coordinator *Coordinator) Snapshot() (model.Rollout, bool) { coordinator.mutex.RLock(); defer coordinator.mutex.RUnlock(); if coordinator.current == nil { return model.Rollout{}, false }; return clone(*coordinator.current), true }
func response(value model.Envelope, state string) model.NodeResponse { return model.NodeResponse{SessionID: value.SessionID, Sequence: value.Sequence, Generation: value.Generation, Digest: value.Digest, State: state} }
func count(values map[string]model.NodeResponse, state string) int { total := 0; for _, value := range values { if value.State == state { total++ } }; return total }
func clone(value model.Rollout) model.Rollout { source := value.NodeResponses; value.NodeResponses = map[string]model.NodeResponse{}; for key, item := range source { value.NodeResponses[key] = item }; return value }