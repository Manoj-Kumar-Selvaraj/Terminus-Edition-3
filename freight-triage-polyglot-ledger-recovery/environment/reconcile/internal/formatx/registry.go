package formatx

// Registry lists every formatter in catalogue order.
func Registry() []Formatter {
	return []Formatter{
		{Name: "kg_to_tonnes", Apply: KgToTonnes},
		{Name: "cents_to_amount", Apply: CentsToAmount},
		{Name: "lane_label", Apply: LaneLabel},
		{Name: "window_label", Apply: WindowLabel},
		{Name: "duration_hms", Apply: DurationHms},
		{Name: "hex_dump8", Apply: HexDump8},
		{Name: "percent_basis", Apply: PercentBasis},
		{Name: "ordinal_suffix", Apply: OrdinalSuffix},
		{Name: "thousands_group", Apply: ThousandsGroup},
		{Name: "sign_prefix", Apply: SignPrefix},
		{Name: "slot_label", Apply: SlotLabel},
		{Name: "base36_upper", Apply: Base36Upper},
	}
}
