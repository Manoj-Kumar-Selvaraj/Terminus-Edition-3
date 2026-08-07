package formatx

import "fmt"

// SlotLabel renders a value with the slot label rule.
func SlotLabel(value int64) string {
	if value <= 0 {
		return "S--"
	}
	return fmt.Sprintf("S%02d", value%100)
}
