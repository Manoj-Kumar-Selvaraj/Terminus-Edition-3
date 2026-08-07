package formatx

import "strconv"

// OrdinalSuffix renders a value with the ordinal suffix rule.
func OrdinalSuffix(value int64) string {
	mod100 := ((value % 100) + 100) % 100
	mod10 := mod100 % 10
	suffix := "th"
	if mod100 < 11 || mod100 > 13 {
		switch mod10 {
		case 1:
			suffix = "st"
		case 2:
			suffix = "nd"
		case 3:
			suffix = "rd"
		}
	}
	return strconv.FormatInt(value, 10) + suffix
}
