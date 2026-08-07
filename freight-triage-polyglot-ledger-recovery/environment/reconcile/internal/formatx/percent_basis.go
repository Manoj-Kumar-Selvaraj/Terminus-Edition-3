package formatx

import "fmt"

// PercentBasis renders a value with the percent basis rule.
func PercentBasis(value int64) string {
	negative := value < 0
	absolute := value
	if negative {
		absolute = -absolute
	}
	sign := ""
	if negative {
		sign = "-"
	}
	return fmt.Sprintf("%s%d.%02d%%", sign, absolute/100, absolute%100)
}
