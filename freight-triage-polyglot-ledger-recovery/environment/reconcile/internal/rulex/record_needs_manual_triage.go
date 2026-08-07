package rulex

// RecordNeedsManualTriage is the triage predicate for record needs manual triage.
func RecordNeedsManualTriage(record Record) bool {
	return HazmatRequiresEscort(record) || MassExceedsSoftCap(record) || !LaneIndexInRange(record)
}
