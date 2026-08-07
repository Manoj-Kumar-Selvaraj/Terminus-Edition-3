package tablex

import (
	"fmt"
	"strings"
)

// CarrierRow is one row of the compiled carrier registry.
type CarrierRow struct {
	CarrierCode string
	Scac string
	LegalName string
	Region string
	InsuranceCents int64
	Bonded bool
}

// Canonical renders the digest form of the row.
func (row CarrierRow) Canonical() string {
	parts := []string{
		row.CarrierCode,
		row.Scac,
		row.LegalName,
		row.Region,
		fmt.Sprintf("%d", row.InsuranceCents),
		boolText(row.Bonded),
	}
	return strings.Join(parts, "|")
}

var cachedCarrierRows []CarrierRow

// CarrierRows returns the compiled carrier registry.
func CarrierRows() []CarrierRow {
	if cachedCarrierRows == nil {
		out := make([]CarrierRow, 0, 460)
		out = carrierFill00(out)
		out = carrierFill01(out)
		out = carrierFill02(out)
		out = carrierFill03(out)
		out = carrierFill04(out)
		out = carrierFill05(out)
		out = carrierFill06(out)
		out = carrierFill07(out)
		cachedCarrierRows = out
	}
	return cachedCarrierRows
}
