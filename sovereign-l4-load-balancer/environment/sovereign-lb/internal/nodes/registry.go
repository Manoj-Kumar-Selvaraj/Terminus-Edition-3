package nodes

import (
	"errors"
	"sort"
	"sync"
	"time"

	"sovereign-lb/internal/model"
)

var ErrStaleSession = errors.New("stale node session")
var ErrSequence = errors.New("invalid acknowledgement sequence")

type Registry struct { mutex sync.RWMutex; nodes map[string]model.NodeStatus }

func NewRegistry() *Registry { return &Registry{nodes: map[string]model.NodeStatus{}} }

func (registry *Registry) Register(nodeID, sessionID, zone string, now time.Time) (model.NodeStatus, bool) {
	registry.mutex.Lock(); defer registry.mutex.Unlock()
	previous, replaced := registry.nodes[nodeID]
	current := model.NodeStatus{NodeID: nodeID, SessionID: sessionID, Zone: zone, Connected: true, LastSeen: now.UTC()}
	if previous.SessionID == sessionID {
		previous.Connected = true
		previous.LastSeen = now.UTC()
		registry.nodes[nodeID] = previous
		return previous, false
	}
	registry.nodes[nodeID] = current
	return current, replaced
}

func (registry *Registry) Accept(envelope model.Envelope, now time.Time) (model.NodeStatus, error) {
	registry.mutex.Lock(); defer registry.mutex.Unlock()
	current, ok := registry.nodes[envelope.NodeID]
	if !ok || !current.Connected || current.SessionID != envelope.SessionID { return model.NodeStatus{}, ErrStaleSession }
	if envelope.Sequence <= current.LastSequence { return model.NodeStatus{}, ErrSequence }
	current.LastSequence = envelope.Sequence
	current.LastSeen = now.UTC()
	switch envelope.Type {
	case "prepared": current.PreparedGeneration = envelope.Generation
	case "active": current.PreparedGeneration = 0; current.ActiveGeneration = envelope.Generation
	case "rejected", "status":
	default: return model.NodeStatus{}, errors.New("message is not a node acknowledgement")
	}
	registry.nodes[envelope.NodeID] = current
	return current, nil
}

func (registry *Registry) Disconnect(nodeID, sessionID string, now time.Time) bool {
	registry.mutex.Lock(); defer registry.mutex.Unlock()
	current, ok := registry.nodes[nodeID]
	if !ok || current.SessionID != sessionID { return false }
	current.Connected = false; current.LastSeen = now.UTC(); registry.nodes[nodeID] = current
	return true
}

func (registry *Registry) Current(nodeID, sessionID string) bool {
	registry.mutex.RLock(); defer registry.mutex.RUnlock()
	current, ok := registry.nodes[nodeID]
	return ok && current.Connected && current.SessionID == sessionID
}

func (registry *Registry) List() []model.NodeStatus {
	registry.mutex.RLock(); defer registry.mutex.RUnlock()
	result := make([]model.NodeStatus, 0, len(registry.nodes))
	for _, value := range registry.nodes { result = append(result, value) }
	sort.Slice(result, func(i, j int) bool { return result[i].NodeID < result[j].NodeID })
	return result
}