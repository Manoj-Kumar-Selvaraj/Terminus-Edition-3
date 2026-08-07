package formatx

import "fmt"

// KgToTonnes renders a value with the kg to tonnes rule.
func KgToTonnes(value int64) string {
	negative := value < 0
	absolute := value
	if negative {
		absolute = -absolute
	}
	sign := ""
	if negative {
		sign = "-"
	}
	return fmt.Sprintf("%s%d.%03d", sign, absolute/1000, absolute%1000)
}
