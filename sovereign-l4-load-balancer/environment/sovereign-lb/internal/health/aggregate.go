package health

import (
	"sort"
	"strconv"
	"sync"
	"time"

	"sovereign-lb/internal/model"
)

type Sample struct {
	NodeID     string    `json:"node_id"`
	Healthy    bool      `json:"healthy"`
	ObservedAt time.Time `json:"observed_at"`
	Reason     string    `json:"reason"`
}

type State struct {
	Target     string    `json:"target"`
	Healthy    int       `json:"healthy"`
	Unhealthy  int       `json:"unhealthy"`
	Unknown    int       `json:"unknown"`
	Effective  string    `json:"effective"`
	UpdatedAt  time.Time `json:"updated_at"`
	SampleSize int       `json:"sample_size"`
}

type Aggregator struct {
	mutex   sync.RWMutex
	maximum int
	samples map[string]map[string]Sample
	stale   time.Duration
}

func New(maximum int) *Aggregator {
	if maximum < 1 {
		maximum = 1
	}
	return &Aggregator{
		maximum: maximum,
		samples: map[string]map[string]Sample{},
		stale:   2 * time.Minute,
	}
}

func (aggregator *Aggregator) SetStaleAfter(duration time.Duration) {
	aggregator.mutex.Lock()
	defer aggregator.mutex.Unlock()
	if duration > 0 {
		aggregator.stale = duration
	}
}

func (aggregator *Aggregator) Observe(target string, sample Sample) {
	if target == "" || sample.NodeID == "" {
		return
	}
	if sample.ObservedAt.IsZero() {
		sample.ObservedAt = time.Now().UTC()
	}
	aggregator.mutex.Lock()
	defer aggregator.mutex.Unlock()
	byNode := aggregator.samples[target]
	if byNode == nil {
		byNode = map[string]Sample{}
		aggregator.samples[target] = byNode
	}
	if previous, ok := byNode[sample.NodeID]; !ok || sample.ObservedAt.After(previous.ObservedAt) {
		byNode[sample.NodeID] = sample
	}
	if len(byNode) <= aggregator.maximum {
		return
	}
	values := make([]Sample, 0, len(byNode))
	for _, value := range byNode {
		values = append(values, value)
	}
	sort.Slice(values, func(i, j int) bool { return values[i].ObservedAt.Before(values[j].ObservedAt) })
	for _, value := range values[:len(values)-aggregator.maximum] {
		delete(byNode, value.NodeID)
	}
}

func (aggregator *Aggregator) ObserveNode(node model.NodeStatus, now time.Time) {
	reason := "disconnected"
	healthy := false
	if node.Connected {
		healthy = node.ActiveGeneration > 0
		if healthy {
			reason = "serving_active_generation"
		} else if node.PreparedGeneration > 0 {
			reason = "prepared_only"
		} else {
			reason = "connected_idle"
		}
	}
	aggregator.Observe("node:"+node.NodeID, Sample{
		NodeID:     node.NodeID,
		Healthy:    healthy,
		ObservedAt: now.UTC(),
		Reason:     reason,
	})
}

func (aggregator *Aggregator) ObserveTargets(nodeID string, snapshot model.Snapshot, now time.Time) {
	for _, group := range snapshot.TargetGroups {
		for _, target := range group.Targets {
			identity := target.ID
			if identity == "" {
				identity = target.Address + ":" + strconv.Itoa(target.Port)
			}
			aggregator.Observe(identity, Sample{
				NodeID:     nodeID,
				Healthy:    target.AdministrativeState != "disabled",
				ObservedAt: now.UTC(),
				Reason:     "snapshot_" + target.AdministrativeState,
			})
		}
	}
}

func (aggregator *Aggregator) State(target string, currentNodes map[string]bool) State {
	aggregator.mutex.RLock()
	defer aggregator.mutex.RUnlock()
	result := State{Target: target, Effective: "unknown"}
	cutoff := time.Now().UTC().Add(-aggregator.stale)
	for nodeID, sample := range aggregator.samples[target] {
		if currentNodes != nil && !currentNodes[nodeID] {
			continue
		}
		if sample.ObservedAt.Before(cutoff) {
			result.Unknown++
			continue
		}
		if sample.ObservedAt.After(result.UpdatedAt) {
			result.UpdatedAt = sample.ObservedAt
		}
		result.SampleSize++
		if sample.Healthy {
			result.Healthy++
		} else {
			result.Unhealthy++
		}
	}
	switch {
	case result.Healthy > result.Unhealthy && result.Healthy > 0:
		result.Effective = "healthy"
	case result.Unhealthy > 0:
		result.Effective = "unhealthy"
	case result.Unknown > 0:
		result.Effective = "stale"
	}
	return result
}

func (aggregator *Aggregator) Snapshot(currentNodes map[string]bool) []State {
	aggregator.mutex.RLock()
	targets := make([]string, 0, len(aggregator.samples))
	for target := range aggregator.samples {
		targets = append(targets, target)
	}
	aggregator.mutex.RUnlock()
	sort.Strings(targets)
	result := make([]State, 0, len(targets))
	for _, target := range targets {
		result = append(result, aggregator.State(target, currentNodes))
	}
	return result
}

func (aggregator *Aggregator) EvictStale(now time.Time) int {
	aggregator.mutex.Lock()
	defer aggregator.mutex.Unlock()
	cutoff := now.UTC().Add(-aggregator.stale)
	removed := 0
	for target, byNode := range aggregator.samples {
		for nodeID, sample := range byNode {
			if sample.ObservedAt.Before(cutoff) {
				delete(byNode, nodeID)
				removed++
			}
		}
		if len(byNode) == 0 {
			delete(aggregator.samples, target)
		}
	}
	return removed
}

func (aggregator *Aggregator) EffectiveSummary(currentNodes map[string]bool) map[string]int {
	summary := map[string]int{"healthy": 0, "unhealthy": 0, "unknown": 0, "stale": 0}
	for _, state := range aggregator.Snapshot(currentNodes) {
		summary[state.Effective]++
	}
	return summary
}
