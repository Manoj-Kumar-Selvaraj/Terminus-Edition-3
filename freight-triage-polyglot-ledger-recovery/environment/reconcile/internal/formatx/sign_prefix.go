package formatx

import "strconv"

// SignPrefix renders a value with the sign prefix rule.
func SignPrefix(value int64) string {
	if value == 0 {
		return "0"
	}
	if value > 0 {
		return "+" + strconv.FormatInt(value, 10)
	}
	return strconv.FormatInt(value, 10)
}
