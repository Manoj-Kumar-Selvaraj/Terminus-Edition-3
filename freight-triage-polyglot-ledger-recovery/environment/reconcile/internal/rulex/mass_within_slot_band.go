package rulex

// MassWithinSlotBand is the triage predicate for mass within slot band.
func MassWithinSlotBand(record Record) bool {
	return record.MassKg >= 500 && record.MassKg <= 24000
}
