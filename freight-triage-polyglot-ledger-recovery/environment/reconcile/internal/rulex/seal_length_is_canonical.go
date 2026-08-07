package rulex

// SealLengthIsCanonical is the triage predicate for seal length is canonical.
func SealLengthIsCanonical(record Record) bool {
	return record.SealLength == 9
}
