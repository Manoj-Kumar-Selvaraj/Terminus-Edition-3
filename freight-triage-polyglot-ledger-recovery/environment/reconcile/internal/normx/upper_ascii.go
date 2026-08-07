package normx

// UpperAscii normalizes with the upper ascii rule.
func UpperAscii(text string) string {
	out := []byte(text)
	for i, c := range out {
		if c >= 'a' && c <= 'z' {
			out[i] = c - 32
		}
	}
	return string(out)
}
