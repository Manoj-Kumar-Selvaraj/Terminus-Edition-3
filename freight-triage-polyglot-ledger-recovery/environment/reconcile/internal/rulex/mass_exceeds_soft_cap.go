package rulex

// MassExceedsSoftCap is the triage predicate for mass exceeds soft cap.
func MassExceedsSoftCap(record Record) bool {
	return record.MassKg > 18000
}
