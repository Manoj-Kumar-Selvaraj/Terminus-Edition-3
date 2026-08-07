package normx

import "strings"

// PadLeftEight normalizes with the pad left eight rule.
func PadLeftEight(text string) string {
	if len(text) >= 8 {
		return text
	}
	return strings.Repeat("0", 8-len(text)) + text
}
