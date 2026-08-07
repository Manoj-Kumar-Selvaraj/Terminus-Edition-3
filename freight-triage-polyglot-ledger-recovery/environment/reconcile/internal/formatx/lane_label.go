package formatx

import "fmt"

// LaneLabel renders a value with the lane label rule.
func LaneLabel(value int64) string {
	index := ((value % 1000) + 1000) % 1000
	return fmt.Sprintf("LN-%03d", index)
}
