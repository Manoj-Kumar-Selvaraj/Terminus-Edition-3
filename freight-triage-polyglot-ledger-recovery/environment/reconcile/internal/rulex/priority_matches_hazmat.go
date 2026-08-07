package rulex

// PriorityMatchesHazmat is the triage predicate for priority matches hazmat.
func PriorityMatchesHazmat(record Record) bool {
	return record.Priority == record.HazmatClass%5
}
