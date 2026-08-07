package codecx

// EncodeEscapeHigh applies the escape_high encoding.
func EncodeEscapeHigh(data []byte) []byte {
	out := make([]byte, 0, len(data))
	for _, b := range data {
		switch {
		case b == 0x1B:
			out = append(out, 0x1B, 0x7F)
		case b >= 0x80:
			out = append(out, 0x1B, b-0x80)
		default:
			out = append(out, b)
		}
	}
	return out
}

// DecodeEscapeHigh inverts the escape_high encoding.
func DecodeEscapeHigh(data []byte) []byte {
	out := make([]byte, 0, len(data))
	for i := 0; i < len(data); i++ {
		if data[i] != 0x1B {
			out = append(out, data[i])
			continue
		}
		if i+1 >= len(data) {
			break
		}
		i++
		if data[i] == 0x7F {
			out = append(out, 0x1B)
		} else {
			out = append(out, data[i]+0x80)
		}
	}
	return out
}
