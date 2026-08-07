package rulex

// Registry lists every triage rule in catalogue order.
func Registry() []Rule {
	return []Rule{
		{Name: "lane_index_in_range", Apply: LaneIndexInRange},
		{Name: "mass_within_slot_band", Apply: MassWithinSlotBand},
		{Name: "priority_is_expedite", Apply: PriorityIsExpedite},
		{Name: "hazmat_requires_escort", Apply: HazmatRequiresEscort},
		{Name: "seal_length_is_canonical", Apply: SealLengthIsCanonical},
		{Name: "mass_is_multiple_of_ten", Apply: MassIsMultipleOfTen},
		{Name: "lane_is_cross_dock", Apply: LaneIsCrossDock},
		{Name: "priority_matches_hazmat", Apply: PriorityMatchesHazmat},
		{Name: "mass_exceeds_soft_cap", Apply: MassExceedsSoftCap},
		{Name: "seal_and_lane_parity", Apply: SealAndLaneParity},
		{Name: "record_is_auditable", Apply: RecordIsAuditable},
		{Name: "record_needs_manual_triage", Apply: RecordNeedsManualTriage},
	}
}
