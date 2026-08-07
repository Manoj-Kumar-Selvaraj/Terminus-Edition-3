package tablex

import (
	"fmt"
	"strings"
)

// ZoneRow is one row of the compiled zone registry.
type ZoneRow struct {
	ZoneKey string
	Abbrev string
	OffsetMinutes int64
	DstShiftMinutes int64
	Hub string
}

// Canonical renders the digest form of the row.
func (row ZoneRow) Canonical() string {
	parts := []string{
		row.ZoneKey,
		row.Abbrev,
		fmt.Sprintf("%d", row.OffsetMinutes),
		fmt.Sprintf("%d", row.DstShiftMinutes),
		row.Hub,
	}
	return strings.Join(parts, "|")
}

var cachedZoneRows []ZoneRow

// ZoneRows returns the compiled zone registry.
func ZoneRows() []ZoneRow {
	if cachedZoneRows == nil {
		out := make([]ZoneRow, 0, 320)
		out = zoneFill00(out)
		out = zoneFill01(out)
		out = zoneFill02(out)
		out = zoneFill03(out)
		out = zoneFill04(out)
		out = zoneFill05(out)
		cachedZoneRows = out
	}
	return cachedZoneRows
}
