package rulex

// MassIsMultipleOfTen is the triage predicate for mass is multiple of ten.
func MassIsMultipleOfTen(record Record) bool {
	return record.MassKg%10 == 0
}
