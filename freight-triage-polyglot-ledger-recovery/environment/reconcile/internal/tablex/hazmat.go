package tablex

import (
	"fmt"
	"strings"
)

// HazmatRow is one row of the compiled hazmat registry.
type HazmatRow struct {
	RuleID string
	HazmatClass int64
	MinEscortPriority int64
	SegregationCode string
	MaxSlotKg int64
}

// Canonical renders the digest form of the row.
func (row HazmatRow) Canonical() string {
	parts := []string{
		row.RuleID,
		fmt.Sprintf("%d", row.HazmatClass),
		fmt.Sprintf("%d", row.MinEscortPriority),
		row.SegregationCode,
		fmt.Sprintf("%d", row.MaxSlotKg),
	}
	return strings.Join(parts, "|")
}

var cachedHazmatRows []HazmatRow

// HazmatRows returns the compiled hazmat registry.
func HazmatRows() []HazmatRow {
	if cachedHazmatRows == nil {
		out := make([]HazmatRow, 0, 120)
		out = hazmatFill00(out)
		out = hazmatFill01(out)
		cachedHazmatRows = out
	}
	return cachedHazmatRows
}
