package rulex

// SealAndLaneParity is the triage predicate for seal and lane parity.
func SealAndLaneParity(record Record) bool {
	return (record.SealLength+record.LaneIndex)%2 == 0
}
