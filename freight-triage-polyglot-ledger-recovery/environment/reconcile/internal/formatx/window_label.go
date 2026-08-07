package formatx

import "fmt"

// WindowLabel renders a value with the window label rule.
func WindowLabel(value int64) string {
	index := ((value % 1000000) + 1000000) % 1000000
	return fmt.Sprintf("W-%06d", index)
}
