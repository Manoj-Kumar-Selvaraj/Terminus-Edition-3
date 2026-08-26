package ops

import (
	"fmt"
	"sort"
	"time"

	"sovereign-lb/internal/fleet"
	"sovereign-lb/internal/model"
	"sovereign-lb/internal/nodes"
)

type Membership struct {
	ExpectedNodes   int            `json:"expected_nodes"`
	ConnectedNodes  int            `json:"connected_nodes"`
	MissingNodes    []string       `json:"missing_nodes"`
	UnexpectedNodes []string       `json:"unexpected_nodes"`
	ZoneCoverage    map[string]int `json:"zone_coverage"`
	ZonesMissing    []string       `json:"zones_missing"`
	QuorumCapable   bool           `json:"quorum_capable"`
	ObservedAt      time.Time      `json:"observed_at"`
}

type GenerationView struct {
	ActiveGeneration   uint64   `json:"active_generation"`
	NodesOnActive      int      `json:"nodes_on_active"`
	NodesPreparedOnly  int      `json:"nodes_prepared_only"`
	NodesLagging       []string `json:"nodes_lagging"`
	RolloutPhase       string   `json:"rollout_phase,omitempty"`
	RetentionProtected int      `json:"retention_protected"`
}

func ReconcileFleet(inventory fleet.Inventory, registry *nodes.Registry, now time.Time) Membership {
	live := registry.List()
	connected := map[string]model.NodeStatus{}
	for _, node := range live {
		if node.Connected {
			connected[node.NodeID] = node
		}
	}
	expected := map[string]fleet.NodeRecord{}
	for _, node := range inventory.Nodes {
		expected[node.ID] = node
	}
	membership := Membership{
		ExpectedNodes:  len(expected),
		ConnectedNodes: len(connected),
		MissingNodes:   make([]string, 0),
		UnexpectedNodes: make([]string, 0),
		ZoneCoverage:   map[string]int{},
		ZonesMissing:   make([]string, 0),
		ObservedAt:     now.UTC(),
	}
	for id, record := range expected {
		if _, ok := connected[id]; !ok {
			membership.MissingNodes = append(membership.MissingNodes, id)
			continue
		}
		membership.ZoneCoverage[record.Zone]++
	}
	for id := range connected {
		if _, ok := expected[id]; !ok && len(expected) > 0 {
			membership.UnexpectedNodes = append(membership.UnexpectedNodes, id)
		}
	}
	sort.Strings(membership.MissingNodes)
	sort.Strings(membership.UnexpectedNodes)
	for _, zone := range inventory.Zones() {
		if membership.ZoneCoverage[zone] == 0 {
			membership.ZonesMissing = append(membership.ZonesMissing, zone)
		}
	}
	sort.Strings(membership.ZonesMissing)
	if len(expected) == 0 {
		membership.QuorumCapable = membership.ConnectedNodes > 0
	} else {
		availableZones := len(inventory.Zones()) - len(membership.ZonesMissing)
		membership.QuorumCapable = membership.ConnectedNodes > 0 && availableZones >= 1
	}
	return membership
}

func GenerationAlignment(registry *nodes.Registry, active uint64, rollout model.Rollout, protectedLeases int) GenerationView {
	view := GenerationView{
		ActiveGeneration:   active,
		NodesLagging:       make([]string, 0),
		RolloutPhase:       rollout.Phase,
		RetentionProtected: protectedLeases,
	}
	for _, node := range registry.List() {
		if !node.Connected {
			continue
		}
		switch {
		case active > 0 && node.ActiveGeneration == active:
			view.NodesOnActive++
		case node.PreparedGeneration > 0 && node.ActiveGeneration != active:
			view.NodesPreparedOnly++
			view.NodesLagging = append(view.NodesLagging, node.NodeID)
		case active > 0 && node.ActiveGeneration != active:
			view.NodesLagging = append(view.NodesLagging, node.NodeID)
		}
	}
	sort.Strings(view.NodesLagging)
	return view
}

func DescribeMembership(membership Membership) string {
	if membership.ExpectedNodes == 0 {
		return fmt.Sprintf("ad-hoc fleet connected=%d", membership.ConnectedNodes)
	}
	return fmt.Sprintf(
		"expected=%d connected=%d missing=%d unexpected=%d zones_missing=%d quorum_capable=%t",
		membership.ExpectedNodes,
		membership.ConnectedNodes,
		len(membership.MissingNodes),
		len(membership.UnexpectedNodes),
		len(membership.ZonesMissing),
		membership.QuorumCapable,
	)
}
