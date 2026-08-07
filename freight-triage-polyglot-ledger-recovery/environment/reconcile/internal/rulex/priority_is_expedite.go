package rulex

// PriorityIsExpedite is the triage predicate for priority is expedite.
func PriorityIsExpedite(record Record) bool {
	return record.Priority >= 3
}
