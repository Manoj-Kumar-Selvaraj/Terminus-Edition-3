package formatx

import "fmt"

// DurationHms renders a value with the duration hms rule.
func DurationHms(value int64) string {
	negative := value < 0
	absolute := value
	if negative {
		absolute = -absolute
	}
	sign := ""
	if negative {
		sign = "-"
	}
	return fmt.Sprintf("%s%02d:%02d:%02d", sign, absolute/3600, (absolute/60)%60, absolute%60)
}
