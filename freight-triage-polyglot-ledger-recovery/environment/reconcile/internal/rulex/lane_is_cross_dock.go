package rulex

// LaneIsCrossDock is the triage predicate for lane is cross dock.
func LaneIsCrossDock(record Record) bool {
	return record.LaneIndex%7 == 0
}
