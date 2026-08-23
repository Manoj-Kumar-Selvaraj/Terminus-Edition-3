package health

import (
	"sort"
	"sync"
	"time"
)

type Sample struct { NodeID string `json:"node_id"`; Healthy bool `json:"healthy"`; ObservedAt time.Time `json:"observed_at"`; Reason string `json:"reason"` }
type State struct { Target string `json:"target"`; Healthy int `json:"healthy"`; Unhealthy int `json:"unhealthy"`; Unknown int `json:"unknown"`; Effective string `json:"effective"`; UpdatedAt time.Time `json:"updated_at"` }
type Aggregator struct { mutex sync.RWMutex; maximum int; samples map[string]map[string]Sample }

func New(maximum int) *Aggregator { if maximum < 1 { maximum = 1 }; return &Aggregator{maximum: maximum, samples: map[string]map[string]Sample{}} }

func (aggregator *Aggregator) Observe(target string, sample Sample) {
	aggregator.mutex.Lock(); defer aggregator.mutex.Unlock()
	byNode := aggregator.samples[target]; if byNode == nil { byNode = map[string]Sample{}; aggregator.samples[target] = byNode }
	if previous, ok := byNode[sample.NodeID]; !ok || sample.ObservedAt.After(previous.ObservedAt) { byNode[sample.NodeID] = sample }
	if len(byNode) <= aggregator.maximum { return }
	values := make([]Sample, 0, len(byNode)); for _, value := range byNode { values = append(values, value) }
	sort.Slice(values, func(i, j int) bool { return values[i].ObservedAt.Before(values[j].ObservedAt) })
	for _, value := range values[:len(values)-aggregator.maximum] { delete(byNode, value.NodeID) }
}

func (aggregator *Aggregator) State(target string, currentNodes map[string]bool) State {
	aggregator.mutex.RLock(); defer aggregator.mutex.RUnlock()
	result := State{Target: target, Effective: "unknown"}
	for nodeID, sample := range aggregator.samples[target] {
		if !currentNodes[nodeID] { continue }
		if sample.ObservedAt.After(result.UpdatedAt) { result.UpdatedAt = sample.ObservedAt }
		if sample.Healthy { result.Healthy++ } else { result.Unhealthy++ }
	}
	if result.Healthy > result.Unhealthy { result.Effective = "healthy" } else if result.Unhealthy > 0 { result.Effective = "unhealthy" }
	return result
}