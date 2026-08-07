package tablex

import (
	"fmt"
	"strings"
)

// TariffRow is one row of the compiled tariff registry.
type TariffRow struct {
	GroupCode string
	Band string
	RateCents int64
}

// Canonical renders the digest form of the row.
func (row TariffRow) Canonical() string {
	parts := []string{
		row.GroupCode,
		row.Band,
		fmt.Sprintf("%d", row.RateCents),
	}
	return strings.Join(parts, "|")
}

var cachedTariffRows []TariffRow

// TariffRows returns the compiled tariff registry.
func TariffRows() []TariffRow {
	if cachedTariffRows == nil {
		out := make([]TariffRow, 0, 96)
		out = tariffFill00(out)
		out = tariffFill01(out)
		cachedTariffRows = out
	}
	return cachedTariffRows
}
