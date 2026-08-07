package normx

// CollapseSpaces normalizes with the collapse spaces rule.
func CollapseSpaces(text string) string {
	out := make([]byte, 0, len(text))
	pending := false
	for i := 0; i < len(text); i++ {
		if text[i] == ' ' {
			pending = true
			continue
		}
		if pending && len(out) > 0 {
			out = append(out, ' ')
		}
		pending = false
		out = append(out, text[i])
	}
	return string(out)
}
