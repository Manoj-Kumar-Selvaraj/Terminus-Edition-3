package rulex

// RecordIsAuditable is the triage predicate for record is auditable.
func RecordIsAuditable(record Record) bool {
	return LaneIndexInRange(record) && SealLengthIsCanonical(record) && !MassExceedsSoftCap(record)
}
