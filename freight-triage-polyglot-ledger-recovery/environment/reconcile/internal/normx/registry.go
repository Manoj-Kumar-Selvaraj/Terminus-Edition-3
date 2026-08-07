package normx

// Registry lists every normalizer in catalogue order.
func Registry() []Normalizer {
	return []Normalizer{
		{Name: "upper_ascii", Apply: UpperAscii},
		{Name: "lower_ascii", Apply: LowerAscii},
		{Name: "trim_edges", Apply: TrimEdges},
		{Name: "collapse_spaces", Apply: CollapseSpaces},
		{Name: "strip_non_alnum", Apply: StripNonAlnum},
		{Name: "dash_to_underscore", Apply: DashToUnderscore},
		{Name: "pad_left_eight", Apply: PadLeftEight},
		{Name: "reverse_bytes", Apply: ReverseBytes},
		{Name: "rot13_letters", Apply: Rot13Letters},
		{Name: "digits_only", Apply: DigitsOnly},
	}
}
