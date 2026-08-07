package formatx

// Base36Upper renders a value with the base36 upper rule.
func Base36Upper(value int64) string {
	const digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	if value == 0 {
		return "0"
	}
	negative := value < 0
	absolute := value
	if negative {
		absolute = -absolute
	}
	out := make([]byte, 0, 16)
	for absolute > 0 {
		out = append(out, digits[absolute%36])
		absolute /= 36
	}
	for i, j := 0, len(out)-1; i < j; i, j = i+1, j-1 {
		out[i], out[j] = out[j], out[i]
	}
	if negative {
		return "-" + string(out)
	}
	return string(out)
}
