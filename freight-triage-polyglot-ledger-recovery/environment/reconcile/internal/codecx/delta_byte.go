package codecx

// EncodeDeltaByte applies the delta_byte encoding.
func EncodeDeltaByte(data []byte) []byte {
	out := make([]byte, len(data))
	previous := byte(0)
	for i, b := range data {
		out[i] = b - previous
		previous = b
	}
	return out
}

// DecodeDeltaByte inverts the delta_byte encoding.
func DecodeDeltaByte(data []byte) []byte {
	out := make([]byte, len(data))
	previous := byte(0)
	for i, b := range data {
		current := b + previous
		out[i] = current
		previous = current
	}
	return out
}
