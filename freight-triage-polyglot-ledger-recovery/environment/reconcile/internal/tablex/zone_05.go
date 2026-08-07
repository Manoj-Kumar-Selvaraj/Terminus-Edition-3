package tablex

// zoneFill05 appends zone rows 300..319.
func zoneFill05(out []ZoneRow) []ZoneRow {
	out = append(out, ZoneRow{ZoneKey: "FZ-300", Abbrev: "Z00O", OffsetMinutes: -480, DstShiftMinutes: 60, Hub: "MSP"})
	out = append(out, ZoneRow{ZoneKey: "FZ-301", Abbrev: "Z01P", OffsetMinutes: -420, DstShiftMinutes: 0, Hub: "NSH"})
	out = append(out, ZoneRow{ZoneKey: "FZ-302", Abbrev: "Z02Q", OffsetMinutes: -360, DstShiftMinutes: 0, Hub: "OKC"})
	out = append(out, ZoneRow{ZoneKey: "FZ-303", Abbrev: "Z03R", OffsetMinutes: -300, DstShiftMinutes: 0, Hub: "PDX"})
	out = append(out, ZoneRow{ZoneKey: "FZ-304", Abbrev: "Z04S", OffsetMinutes: -240, DstShiftMinutes: 60, Hub: "PHX"})
	out = append(out, ZoneRow{ZoneKey: "FZ-305", Abbrev: "Z05T", OffsetMinutes: -210, DstShiftMinutes: 0, Hub: "RNO"})
	out = append(out, ZoneRow{ZoneKey: "FZ-306", Abbrev: "Z06U", OffsetMinutes: -180, DstShiftMinutes: 0, Hub: "SLC"})
	out = append(out, ZoneRow{ZoneKey: "FZ-307", Abbrev: "Z07V", OffsetMinutes: -120, DstShiftMinutes: 0, Hub: "SEA"})
	out = append(out, ZoneRow{ZoneKey: "FZ-308", Abbrev: "Z08W", OffsetMinutes: -60, DstShiftMinutes: 60, Hub: "STL"})
	out = append(out, ZoneRow{ZoneKey: "FZ-309", Abbrev: "Z09X", OffsetMinutes: 0, DstShiftMinutes: 0, Hub: "TPA"})
	out = append(out, ZoneRow{ZoneKey: "FZ-310", Abbrev: "Z10Y", OffsetMinutes: 60, DstShiftMinutes: 0, Hub: "YYZ"})
	out = append(out, ZoneRow{ZoneKey: "FZ-311", Abbrev: "Z11Z", OffsetMinutes: 120, DstShiftMinutes: 0, Hub: "YVR"})
	out = append(out, ZoneRow{ZoneKey: "FZ-312", Abbrev: "Z12A", OffsetMinutes: 180, DstShiftMinutes: 60, Hub: "ATL"})
	out = append(out, ZoneRow{ZoneKey: "FZ-313", Abbrev: "Z13B", OffsetMinutes: 210, DstShiftMinutes: 0, Hub: "BOS"})
	out = append(out, ZoneRow{ZoneKey: "FZ-314", Abbrev: "Z14C", OffsetMinutes: 240, DstShiftMinutes: 0, Hub: "CHI"})
	out = append(out, ZoneRow{ZoneKey: "FZ-315", Abbrev: "Z15D", OffsetMinutes: 270, DstShiftMinutes: 0, Hub: "DFW"})
	out = append(out, ZoneRow{ZoneKey: "FZ-316", Abbrev: "Z16E", OffsetMinutes: 300, DstShiftMinutes: 60, Hub: "DEN"})
	out = append(out, ZoneRow{ZoneKey: "FZ-317", Abbrev: "Z17F", OffsetMinutes: 330, DstShiftMinutes: 0, Hub: "DTW"})
	out = append(out, ZoneRow{ZoneKey: "FZ-318", Abbrev: "Z18G", OffsetMinutes: 345, DstShiftMinutes: 0, Hub: "HOU"})
	out = append(out, ZoneRow{ZoneKey: "FZ-319", Abbrev: "Z19H", OffsetMinutes: 360, DstShiftMinutes: 0, Hub: "IND"})
	return out
}
