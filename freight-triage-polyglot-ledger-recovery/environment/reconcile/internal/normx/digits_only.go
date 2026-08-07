package normx

// DigitsOnly normalizes with the digits only rule.
func DigitsOnly(text string) string {
	out := make([]byte, 0, len(text))
	for i := 0; i < len(text); i++ {
		if text[i] >= '0' && text[i] <= '9' {
			out = append(out, text[i])
		}
	}
	return string(out)
}
