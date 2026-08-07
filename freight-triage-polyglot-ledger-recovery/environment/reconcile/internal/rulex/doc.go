// Package rulex holds the triage rule predicates.
package rulex

// Record is a synthetic triage record used by the conformance probe.
type Record struct {
	RecordID    string
	LaneIndex   int64
	MassKg      int64
	Priority    int64
	HazmatClass int64
	SealLength  int64
}

// Rule is a named triage predicate.
type Rule struct {
	Name  string
	Apply func(record Record) bool
}
