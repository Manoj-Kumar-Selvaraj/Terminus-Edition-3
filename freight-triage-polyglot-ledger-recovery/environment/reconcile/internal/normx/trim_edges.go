package normx

// TrimEdges normalizes with the trim edges rule.
func TrimEdges(text string) string {
	begin := 0
	end := len(text)
	for begin < end && (text[begin] == ' ' || text[begin] == '\t') {
		begin++
	}
	for end > begin && (text[end-1] == ' ' || text[end-1] == '\t') {
		end--
	}
	return text[begin:end]
}
