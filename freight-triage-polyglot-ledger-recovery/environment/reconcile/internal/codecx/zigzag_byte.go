package codecx

// EncodeZigzagByte applies the zigzag_byte encoding.
func EncodeZigzagByte(data []byte) []byte {
	out := make([]byte, len(data))
	for i, b := range data {
		value := int8(b)
		out[i] = byte((value << 1) ^ (value >> 7))
	}
	return out
}

// DecodeZigzagByte inverts the zigzag_byte encoding.
func DecodeZigzagByte(data []byte) []byte {
	out := make([]byte, len(data))
	for i, b := range data {
		out[i] = byte(int8(b) >> 1)
	}
	return out
}
