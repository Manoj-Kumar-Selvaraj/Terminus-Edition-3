package codecx

// EncodeRunLength applies the run_length encoding.
func EncodeRunLength(data []byte) []byte {
	out := make([]byte, 0, len(data))
	index := 0
	for index < len(data) {
		value := data[index]
		run := 1
		for index+run < len(data) && data[index+run] == value && run < 255 {
			run++
		}
		out = append(out, byte(run), value)
		index += run
	}
	return out
}

// DecodeRunLength inverts the run_length encoding.
func DecodeRunLength(data []byte) []byte {
	out := make([]byte, 0, len(data))
	for i := 0; i+1 < len(data); i += 2 {
		run := int(data[i])
		for k := 0; k < run; k++ {
			out = append(out, data[i+1])
		}
	}
	return out
}
