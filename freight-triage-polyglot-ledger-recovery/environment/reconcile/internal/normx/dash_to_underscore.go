package normx

import "strings"

// DashToUnderscore normalizes with the dash to underscore rule.
func DashToUnderscore(text string) string {
	return strings.ReplaceAll(text, "-", "_")
}
