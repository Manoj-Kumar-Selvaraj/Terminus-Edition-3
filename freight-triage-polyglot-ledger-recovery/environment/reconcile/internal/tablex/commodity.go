package tablex

import (
	"fmt"
	"strings"
)

// CommodityRow is one row of the compiled commodity registry.
type CommodityRow struct {
	CommodityCode string
	GroupCode string
	Description string
	HazmatDefault int64
	DensityKgM3 int64
	Stackable bool
}

// Canonical renders the digest form of the row.
func (row CommodityRow) Canonical() string {
	parts := []string{
		row.CommodityCode,
		row.GroupCode,
		row.Description,
		fmt.Sprintf("%d", row.HazmatDefault),
		fmt.Sprintf("%d", row.DensityKgM3),
		boolText(row.Stackable),
	}
	return strings.Join(parts, "|")
}

var cachedCommodityRows []CommodityRow

// CommodityRows returns the compiled commodity registry.
func CommodityRows() []CommodityRow {
	if cachedCommodityRows == nil {
		out := make([]CommodityRow, 0, 1080)
		out = commodityFill00(out)
		out = commodityFill01(out)
		out = commodityFill02(out)
		out = commodityFill03(out)
		out = commodityFill04(out)
		out = commodityFill05(out)
		out = commodityFill06(out)
		out = commodityFill07(out)
		out = commodityFill08(out)
		out = commodityFill09(out)
		out = commodityFill10(out)
		out = commodityFill11(out)
		out = commodityFill12(out)
		out = commodityFill13(out)
		out = commodityFill14(out)
		out = commodityFill15(out)
		out = commodityFill16(out)
		out = commodityFill17(out)
		cachedCommodityRows = out
	}
	return cachedCommodityRows
}
