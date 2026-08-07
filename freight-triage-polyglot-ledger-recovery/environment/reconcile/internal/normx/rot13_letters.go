package normx

// Rot13Letters normalizes with the rot13 letters rule.
func Rot13Letters(text string) string {
	out := []byte(text)
	for i, c := range out {
		switch {
		case c >= 'a' && c <= 'z':
			out[i] = 'a' + (c-'a'+13)%26
		case c >= 'A' && c <= 'Z':
			out[i] = 'A' + (c-'A'+13)%26
		}
	}
	return string(out)
}
