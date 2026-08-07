package normx

// LowerAscii normalizes with the lower ascii rule.
func LowerAscii(text string) string {
	out := []byte(text)
	for i, c := range out {
		if c >= 'A' && c <= 'Z' {
			out[i] = c + 32
		}
	}
	return string(out)
}
