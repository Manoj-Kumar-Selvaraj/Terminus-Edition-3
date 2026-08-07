package rulex

// LaneIndexInRange is the triage predicate for lane index in range.
func LaneIndexInRange(record Record) bool {
	return record.LaneIndex >= 0 && record.LaneIndex < 360
}
