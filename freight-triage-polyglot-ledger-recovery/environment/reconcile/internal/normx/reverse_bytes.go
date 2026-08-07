package normx

// ReverseBytes normalizes with the reverse bytes rule.
func ReverseBytes(text string) string {
	out := []byte(text)
	for i, j := 0, len(out)-1; i < j; i, j = i+1, j-1 {
		out[i], out[j] = out[j], out[i]
	}
	return string(out)
}
