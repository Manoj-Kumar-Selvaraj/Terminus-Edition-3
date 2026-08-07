package tablex

import (
	"fmt"
	"strings"
)

// LaneRow is one row of the compiled lane registry.
type LaneRow struct {
	LaneID string
	OriginHub string
	DestHub string
	ServiceClass string
	SlotCount int64
	SlotCapacityKg int64
	TransitMinutes int64
	CrossDock bool
}

// Canonical renders the digest form of the row.
func (row LaneRow) Canonical() string {
	parts := []string{
		row.LaneID,
		row.OriginHub,
		row.DestHub,
		row.ServiceClass,
		fmt.Sprintf("%d", row.SlotCount),
		fmt.Sprintf("%d", row.SlotCapacityKg),
		fmt.Sprintf("%d", row.TransitMinutes),
		boolText(row.CrossDock),
	}
	return strings.Join(parts, "|")
}

var cachedLaneRows []LaneRow

// LaneRows returns the compiled lane registry.
func LaneRows() []LaneRow {
	if cachedLaneRows == nil {
		out := make([]LaneRow, 0, 520)
		out = laneFill00(out)
		out = laneFill01(out)
		out = laneFill02(out)
		out = laneFill03(out)
		out = laneFill04(out)
		out = laneFill05(out)
		out = laneFill06(out)
		out = laneFill07(out)
		out = laneFill08(out)
		cachedLaneRows = out
	}
	return cachedLaneRows
}
