package readiness

import (
	"sync"

	"sovereign-lb/internal/model"
	"sovereign-lb/internal/nodes"
	"sovereign-lb/internal/snapshot"
)

type Evaluator struct {
	mutex      sync.RWMutex
	repository *snapshot.Repository
	registry   *nodes.Registry
	active     uint64
}

func New(repository *snapshot.Repository, registry *nodes.Registry) *Evaluator {
	return &Evaluator{repository: repository, registry: registry}
}

func (evaluator *Evaluator) SetActive(generation uint64) {
	evaluator.mutex.Lock()
	defer evaluator.mutex.Unlock()
	evaluator.active = generation
}

func (evaluator *Evaluator) Ready() (bool, map[string]any) {
	evaluator.mutex.RLock()
	active := evaluator.active
	evaluator.mutex.RUnlock()
	details := map[string]any{"active_generation": active}
	if active == 0 {
		current, err := evaluator.repository.Current()
		if err != nil {
			details["reason"] = "no verified generation"
			return false, details
		}
		active = current.Snapshot.Generation
		details["active_generation"] = active
	}
	compiled, err := evaluator.repository.Load(active)
	if err != nil {
		details["reason"] = "active generation is not loadable"
		return false, details
	}
	details["digest_prefix"] = compiled.Digest[:12]
	details["listener_count"] = len(compiled.Snapshot.Listeners)
	live := evaluator.registry.List()
	connected := 0
	matched := 0
	for _, node := range live {
		if !node.Connected {
			continue
		}
		connected++
		if node.ActiveGeneration == active {
			matched++
		}
	}
	details["connected_nodes"] = connected
	details["nodes_on_active_generation"] = matched
	if connected > 0 && matched == 0 {
		details["reason"] = "no connected node serves active generation"
		return false, details
	}
	return true, details
}

func (evaluator *Evaluator) MatchesRollout(rollout model.Rollout) bool {
	if rollout.Phase != "active" {
		return false
	}
	evaluator.mutex.RLock()
	defer evaluator.mutex.RUnlock()
	return evaluator.active == rollout.Generation
}
