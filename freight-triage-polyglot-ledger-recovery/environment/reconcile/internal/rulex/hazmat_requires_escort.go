package rulex

// HazmatRequiresEscort is the triage predicate for hazmat requires escort.
func HazmatRequiresEscort(record Record) bool {
	return record.HazmatClass >= 3 && record.Priority < 2
}
